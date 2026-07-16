#!/usr/bin/env python3
"""
i18n — Internationalization Module (DB-first + YAML fallback)

Data priority:
    1. i18n_strings table (hot-reloadable, editable from admin panel)
    2. YAML fallback files
    3. Original text (fallback)

Usage:
    from i18n import _, get_lang

    # In Python code
    return api_err(_('Please enter a valid phone number'))

    # In Jinja2 templates (injected via app.context_processor)
    <h1>{{ _('Log In') }}</h1>

    # Write translations from admin
    from i18n import set_translation, seed_from_yaml
    set_translation('en', '登录', 'Login')
    seed_from_yaml('en')  # sync YAML to DB
"""
import os
import hashlib
import functools
import yaml

_market = os.environ.get('DEPLOY_MARKET', 'cn')
DEPLOY_LANG = os.environ.get('DEPLOY_LANG', 'en')

# ─── YAML fallback 缓存（模块加载时一次性读取） ───
_yaml_cache = {}

def _load_yaml(locale: str = None) -> dict:
    """读取 YAML 翻译文件，返回 dict（文件不存在返回空）"""
    locale = locale or DEPLOY_LANG
    if locale in _yaml_cache:
        return _yaml_cache[locale]
    yml_path = os.path.join(os.path.dirname(__file__), f'{locale}.yml')
    try:
        with open(yml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        _yaml_cache[locale] = data
        return data
    except FileNotFoundError:
        print(f'[i18n] Warning: YAML file not found: {yml_path}')
        return {}
    except Exception as e:
        print(f'[i18n] Error loading YAML: {e}')
        return {}


# ─── DB 连接 ───
def _get_db_path() -> str:
    """获取数据库路径，与环境变量和项目结构一致"""
    return os.environ.get('DB_PATH', os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'x7k2m9a4.db'
    ))


def _get_db():
    """返回 PostgreSQL 数据库连接（与 models.database 配置一致）"""
    import psycopg2
    import psycopg2.extras
    PG_CONFIG = {
        'host': os.environ.get('PG_HOST', 'localhost'),
        'port': int(os.environ.get('PG_PORT', 5432)),
        'dbname': os.environ.get('PG_DB', 'verorun'),
        'user': os.environ.get('PG_USER', 'verorun'),
        'password': os.environ.get('PG_PASSWORD', ''),
    }
    conn = psycopg2.connect(**PG_CONFIG)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    conn.autocommit = False
    return conn


def _source_hash(text: str) -> str:
    """生成原文的 hash 用于索引查找"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


# ─── 核心翻译函数 ───

def _(text: str, locale: str = None, **kwargs) -> str:
    """
    翻译一个字符串。
    优先级：DB → YAML fallback → 原文
    支持参数替换：_('Hello {name}', name='World')
    """
    if not text:
        return ''

    locale = locale or DEPLOY_LANG

    # 从内存缓存字典取（get_all_translations 带 lru_cache，
    # 内部已按 YAML 打底 + DB 覆盖，结果与逐条查 DB 等价）。
    # 一个 locale 仅首次触发 1 次 DB 全量读取，之后全部命中内存，
    # 避免每个 {{ _() }} 都新建 SQLite 连接导致的严重性能问题。
    translations = get_all_translations(locale)
    result = translations.get(text)
    if result:  # 空串/None 时回退原文，与原 DB 优先逻辑一致
        if kwargs:
            return result.format(**kwargs)
        return result

    # 回退原文
    if kwargs:
        return text.format(**kwargs)
    return text


def _t(text: str, locale: str = None, **kwargs) -> str:
    """别名，同 _()"""
    return _(text, locale, **kwargs)


# ─── 管理函数 ───

def set_translation(locale: str, source: str, translation: str,
                    is_auto: int = 0) -> bool:
    """
    写入/更新一条翻译到 DB。
    用于管理后台编辑。
    """
    if not source:
        return False
    s_hash = _source_hash(source)
    try:
        conn = _get_db()
        conn.execute(
            '''INSERT INTO i18n_strings (locale, source_hash, source, translation, is_auto)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT(locale, source_hash) DO UPDATE SET
                   translation=excluded.translation,
                   is_auto=excluded.is_auto,
                   updated_at=NOW()''',
            (locale, s_hash, source, translation, is_auto)
        )
        conn.commit()
        conn.close()
        get_all_translations.cache_clear()
        return True
    except Exception as e:
        print(f'[i18n] set_translation error: {e}')
        return False


def delete_translation(translation_id: int) -> bool:
    """删除一条翻译"""
    try:
        conn = _get_db()
        conn.execute('DELETE FROM i18n_strings WHERE id=%s', (translation_id,))
        conn.commit()
        conn.close()
        get_all_translations.cache_clear()
        return True
    except Exception as e:
        print(f'[i18n] delete_translation error: {e}')
        return False


@functools.lru_cache(maxsize=4)
def get_all_translations(locale: str = None) -> dict:
    """
    返回完整翻译字典（用于前端注入）。
    优先从 DB 读，缺失的从 YAML 补。
    """
    locale = locale or DEPLOY_LANG
    result = {}

    # YAML 基础
    result.update(_load_yaml(locale))

    # DB 覆盖
    try:
        conn = _get_db()
        rows = conn.execute(
            'SELECT source, translation FROM i18n_strings WHERE locale=%s',
            (locale,)
        ).fetchall()
        conn.close()
        for row in rows:
            result[row['source']] = row['translation']
    except Exception:
        pass

    return result


def list_translations(locale: str = None, search: str = '',
                      offset: int = 0, limit: int = 50) -> dict:
    """
    从 DB 列出翻译（分页+搜索），用于管理后台。
    返回: {total, items: [{id, locale, source, translation, is_auto, updated_at}]}
    """
    locale = locale or DEPLOY_LANG
    try:
        conn = _get_db()
        where = 'WHERE locale=%s'
        params = [locale]
        if search:
            where += ' AND (source LIKE %s OR translation LIKE %s)'
            s = f'%{search}%'
            params.extend([s, s])

        total = conn.execute(
            f'SELECT COUNT(*) as c FROM i18n_strings {where}', params
        ).fetchone()['c']

        rows = conn.execute(
            f'SELECT id, locale, source, translation, is_auto, updated_at '
            f'FROM i18n_strings {where} ORDER BY updated_at DESC LIMIT %s OFFSET %s',
            params + [limit, offset]
        ).fetchall()
        conn.close()

        return {
            'total': total,
            'items': [dict(r) for r in rows],
        }
    except Exception as e:
        print(f'[i18n] list_translations error: {e}')
        return {'total': 0, 'items': []}


def seed_from_yaml(locale: str = None) -> int:
    """
    将 YAML 文件中的翻译导入到 DB（已存在的跳过）。
    返回本次导入的数量。
    """
    locale = locale or DEPLOY_LANG
    yml = _load_yaml(locale)
    if not yml:
        return 0

    count = 0
    try:
        conn = _get_db()
        for source, translation in yml.items():
            if not source or not translation or source == translation:
                continue  # 跳过无效条目和源=译的条目
            s_hash = _source_hash(source)
            exist = conn.execute(
                'SELECT id FROM i18n_strings WHERE locale=%s AND source_hash=%s',
                (locale, s_hash)
            ).fetchone()
            if not exist:
                conn.execute(
                    'INSERT INTO i18n_strings (locale, source_hash, source, translation, is_auto) VALUES (%s,%s,%s,%s,%s)',
                    (locale, s_hash, source, translation, 1)
                )
                count += 1
        conn.commit()
        conn.close()
        if count:
            get_all_translations.cache_clear()
        print(f'[i18n] Seeded {count} translations from {locale}.yml')
    except Exception as e:
        print(f'[i18n] seed_from_yaml error: {e}')
    return count


def get_lang() -> str:
    """返回当前语言代码"""
    return DEPLOY_LANG


# ─── 插件翻译支持 ──────────────────────────────────────────

def seed_plugin_translations(plugin_id: str, locale_dir: str) -> int:
    """
    将插件 locale 目录下的 YAML 翻译文件写入 i18n DB。
    每次调用都会 UPSERT（根据 locale+source_hash 去重），幂等安全。
    返回本次写入的条目数。
    """
    count = 0
    for locale in ('zh-CN', 'en'):
        yml_path = os.path.join(locale_dir, f'{locale}.yml')
        if not os.path.isfile(yml_path):
            continue
        try:
            with open(yml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f'[i18n] plugin {plugin_id} {locale} load error: {e}')
            continue
        if not data:
            continue
        try:
            conn = _get_db()
            for source, translation in data.items():
                if not source or not translation:
                    continue
                s_hash = _source_hash(source)
                conn.execute(
                    '''INSERT INTO i18n_strings
                       (locale, source_hash, source, translation, is_auto)
                       VALUES (%s,%s,%s,%s,%s)
                       ON CONFLICT(locale, source_hash) DO UPDATE SET
                           translation=EXCLUDED.translation,
                           is_auto=EXCLUDED.is_auto''',
                    (locale, s_hash, source, translation, 1)
                )
                count += 1
            conn.commit()
            conn.close()
        except Exception as e:
            print(f'[i18n] plugin {plugin_id} {locale} db error: {e}')
    if count:
        print(f'[i18n] plugin {plugin_id}: seeded {count} translations')
    return count
