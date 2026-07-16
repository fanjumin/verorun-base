#!/usr/bin/env python3
"""
Schema Sync Script — 主库 Schema 同步/创建
============================================
.. deprecated:: 2026-07
    This script uses SQLite and is no longer maintained.
    Schema is now managed via PostgreSQL (see auth-center/models/database.py).
    Kept for historical reference only — do NOT use for production.

可重复运行，幂等。只创建缺失的表，不碰已有数据。

用法:
    python scripts/sync_schema.py                          # 默认 data/verorun.db
    python scripts/sync_schema.py --db data/easykai.db     # 指定数据库
    python scripts/sync_schema.py --rebuild                # 重建（删旧库重建）
"""

import os
import re
import sys
import sqlite3
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(BASE_DIR, 'data', 'verorun.db')

EXCLUDED_TABLES = {
    'ali_api_items', 'ali_api_reviews', 'ali_api_logs',
    'ali_api_user_stats', 'ali_api_tokens', 'ali_oauth_states', 'ali_api_config',
    'coupons', 'coupon_redemptions', 'product_reviews', 'wishlist',
    'agent_reputation', 'graph_edges', 'skills',
    'thesis_embeddings', 'predictions', 'prediction_results',
    'sqlite_sequence',
}

MODEL_FILES = [
    'auth-center/models/database.py',
    'auth-center/models/cms.py',
    'orchestrator/models.py',
    'agent_matrix/models.py',
    'health_check/models.py',
    'analytics/models.py',
    'plugin_manager/models.py',
    'plugin_manager/models_store.py',
]


def extract_sql_blocks(filepath: str) -> list[str]:
    """
    逐行解析 Python 文件，提取所有包含 CREATE TABLE 的三重引号块。
    捕获 execute/executescript 调用 + 普通变量赋值中的 SQL。
    """
    if not os.path.exists(filepath):
        print(f'    SKIP (not found): {filepath}')
        return []

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    blocks = []

    # ── 方法1: execute/executescript 调用中的 SQL ──
    for func_name in ['executescript', 'execute']:
        i = 0
        while i < len(text):
            idx = text.find(func_name + '(', i)
            if idx == -1:
                break
            rest = text[idx + len(func_name) + 1:]
            rest_lstrip = rest.lstrip()
            ws_skipped = len(rest) - len(rest_lstrip)
            if rest_lstrip.startswith('"""'):
                q = '"""'
            elif rest_lstrip.startswith("'''"):
                q = "'''"
            else:
                i = idx + 1
                continue
            start_pos = idx + len(func_name) + 1 + ws_skipped + len(q)
            end_pos = text.find(q, start_pos)
            if end_pos == -1:
                break
            sql_content = text[start_pos:end_pos].strip()
            if sql_content and 'CREATE TABLE' in sql_content.upper():
                blocks.append(sql_content)
            i = end_pos + len(q)

    # ── 方法2: 文件中所有三重引号串（捕获 SCHEMA_SQL = """...""" 等）──
    # 避免重复：只取尚未被方法1处理过的块
    # 通过找所有 """ 或 ''' 内的内容
    for q in ['"""', "'''"]:
        i = 0
        while i < len(text):
            idx = text.find(q, i)
            if idx == -1:
                break
            # 跳过方法1已处理的 execute/executescript 调用
            pre_context = text[max(0, idx-50):idx].strip()
            if pre_context.endswith('execute(') or pre_context.endswith('executescript('):
                i = idx + 1
                continue
            # 提取字符串内容
            start_pos = idx + len(q)
            end_pos = text.find(q, start_pos)
            if end_pos == -1:
                break
            sql_content = text[start_pos:end_pos].strip()
            if sql_content and 'CREATE TABLE' in sql_content.upper():
                blocks.append(sql_content)
            i = end_pos + len(q)

    return blocks


def parse_tables(sql: str) -> list[tuple[str, str]]:
    """从 SQL 文本中解析所有 CREATE TABLE 语句。"""
    results = []
    # 找所有 CREATE TABLE 语句（可能跨行，直到;）
    pos = 0
    while True:
        # Find next CREATE TABLE
        ct = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?', sql, re.I)
        if not ct:
            break
        start = ct.start()
        # Extract table name
        name_match = re.match(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["`]?(\w+)["`]?\s*\(',
            sql[start:], re.I
        )
        if not name_match:
            pos = start + 1
            sql = sql[pos:]
            continue

        tbl_name = name_match.group(1).lower()
        # Find the closing ); - count parens
        paren_depth = 0
        stmt_start = start
        found = False
        for j in range(start, len(sql)):
            c = sql[j]
            if c == '(':
                paren_depth += 1
            elif c == ')':
                paren_depth -= 1
                if paren_depth == 0 and j + 1 < len(sql) and sql[j+1] == ';':
                    # Full statement
                    stmt = sql[start:j+2]
                    if 'IF NOT EXISTS' not in stmt.upper()[:30]:
                        stmt = stmt.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ', 1)
                    results.append((tbl_name, stmt))
                    pos = j + 2
                    sql = sql[pos:]
                    found = True
                    break
                elif paren_depth == 0:
                    stmt = sql[start:j+1] + ';'
                    if 'IF NOT EXISTS' not in stmt.upper()[:30]:
                        stmt = stmt.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ', 1)
                    results.append((tbl_name, stmt))
                    pos = j + 1
                    sql = sql[pos:]
                    found = True
                    break

        if not found:
            pos = start + 1
            sql = sql[pos:]

    return results


def collect_all_tables() -> dict[str, tuple[str, str]]:
    all_tables = {}
    for mf in MODEL_FILES:
        filepath = os.path.join(BASE_DIR, mf)
        print(f'  Scan: {mf}')
        blocks = extract_sql_blocks(filepath)
        for block in blocks:
            tables = parse_tables(block)
            for name, ddl in tables:
                if name in EXCLUDED_TABLES:
                    print(f'    Skip (plugin/pg): {name}')
                    continue
                if name not in all_tables:
                    all_tables[name] = (ddl, mf)
    return all_tables


def get_existing_tables(db_path: str) -> set[str]:
    if not os.path.exists(db_path):
        return set()
    conn = sqlite3.connect(db_path)
    tables = set(r[0].lower() for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall())
    conn.close()
    return tables


def create_database(db_path: str, rebuild: bool = False):
    if rebuild and os.path.exists(db_path):
        print(f'  Remove old db: {db_path}')
        os.remove(db_path)

    print(f'\nScanning code for table definitions...')
    all_tables = collect_all_tables()
    print(f'\n  Total tables from code: {len(all_tables)}')

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    existing = get_existing_tables(db_path)
    print(f'  Existing in db:       {len(existing)}')

    created = []
    skipped = []
    errors = []
    for name in sorted(all_tables.keys()):
        ddl, src = all_tables[name]
        if name in existing:
            skipped.append(name)
            continue
        try:
            conn.execute(ddl)
            created.append(name)
        except Exception as e:
            errors.append((name, str(e)))

    conn.commit()

    print(f'\n{"="*50}')
    print(f'REPORT')
    print(f'{"="*50}')
    print(f'  All tables defined in code: {len(all_tables)}')
    print(f'  Already in db:              {len(existing)}')
    print(f'  Newly created:              {len(created)}')
    print(f'  Skipped (existed):          {len(skipped)}')
    print(f'  Errors:                     {len(errors)}')

    if created:
        print(f'\n  Created tables:')
        for t in created:
            print(f'    + {t} ({all_tables[t][1]})')

    if errors:
        print(f'\n  Errors:')
        for n, e in errors:
            print(f'    - {n}: {e}')

    extra = existing - set(all_tables.keys())
    if extra:
        print(f'\n  Tables in db but not in code:')
        for t in sorted(extra):
            print(f'    ? {t}')

    conn.close()
    return created, errors


def main():
    parser = argparse.ArgumentParser(description='Main DB schema sync tool')
    parser.add_argument('--db', default=DEFAULT_DB)
    parser.add_argument('--rebuild', action='store_true')
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    print(f'Schema Sync')
    print(f'  DB:    {db_path}')
    print(f'  Rebuild: {args.rebuild}')

    created, errors = create_database(db_path, rebuild=args.rebuild)

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    print(f'\nFinal table count: {count}')
    conn.close()

    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
