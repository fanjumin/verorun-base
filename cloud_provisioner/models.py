#!/usr/bin/env python3
"""Cloud Provisioner — 数据库模型与初始化"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'auth-center'))
from models import get_db


def init_tables():
    """创建云服务开通相关表（幂等）"""
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS cloud_instances (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        TEXT NOT NULL,
            user_id         INTEGER NOT NULL,
            product_id      INTEGER NOT NULL,
            product_title   TEXT DEFAULT '',
            provider        TEXT NOT NULL DEFAULT 'template',
                            -- template / aliyun / tencent / baidu
            service_type    TEXT NOT NULL DEFAULT 'vps',
                            -- vps / oss / cdn / rds / domain / ssl
            region          TEXT DEFAULT 'auto',
            specs           TEXT DEFAULT '{}',
                            -- JSON: {"cpu":1,"memory_gb":2,"disk_gb":20}
            resource_id     TEXT DEFAULT '',
                            -- 云厂商资源ID / Docker容器名
            connect_info    TEXT DEFAULT '{}',
                            -- JSON: {"ip":"","port":"","username":"","password":"","domain":""}
            status          TEXT DEFAULT 'pending',
                            -- pending / provisioning / running / stopped / terminated / failed
            provision_log   TEXT DEFAULT '',
            expire_at       TEXT,
            auto_renew      INTEGER DEFAULT 0,
            metadata        TEXT DEFAULT '{}',
            created_at      TEXT DEFAULT (CURRENT_TIMESTAMP),
            updated_at      TEXT DEFAULT (CURRENT_TIMESTAMP)
        )''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ci_user ON cloud_instances(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ci_order ON cloud_instances(order_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ci_status ON cloud_instances(status)')

        conn.execute('''CREATE TABLE IF NOT EXISTS provision_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id     INTEGER NOT NULL,
            step            TEXT NOT NULL,
                            -- validate / create_resource / wait_ready / run_script / notify
            status          TEXT NOT NULL DEFAULT 'running',
                            -- running / success / failed
            message         TEXT DEFAULT '',
            duration_ms     INTEGER DEFAULT 0,
            raw_output      TEXT DEFAULT '',
            created_at      TEXT DEFAULT (CURRENT_TIMESTAMP)
        )''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_pl_instance ON provision_logs(instance_id)')

        # 添加 product_config 字段（如果不存在）
        try:
            cols = [r['name'] for r in conn.execute('PRAGMA table_info(products)').fetchall()]
            if 'product_config' not in cols:
                conn.execute("ALTER TABLE products ADD COLUMN product_config TEXT DEFAULT '{}'")
                print('[CloudProvisioner] products.product_config column added')
        except Exception as e:
            print(f'[CloudProvisioner] product_config migration: {e}')

        conn.commit()
    print('[CloudProvisioner] ✅ Tables ready')


def create_instance(data: dict) -> int:
    """创建云资源实例记录"""
    with get_db() as conn:
        conn.execute('''INSERT INTO cloud_instances
            (order_id, user_id, product_id, product_title, provider, service_type,
             region, specs, status, expire_at, auto_renew, metadata)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (data['order_id'], data['user_id'], data['product_id'],
             data.get('product_title', ''), data.get('provider', 'template'),
             data.get('service_type', 'vps'), data.get('region', 'auto'),
             json.dumps(data.get('specs', {})), 'pending',
             data.get('expire_at'), int(data.get('auto_renew', 0)),
             json.dumps(data.get('metadata', {}))))
        conn.commit()
        return conn.execute('SELECT last_insert_rowid()').fetchone()[0]


def update_instance(instance_id: int, **kwargs):
    """更新云资源实例"""
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in ('specs', 'connect_info', 'metadata'):
            v = json.dumps(v) if isinstance(v, dict) else v
        fields.append(f'{k}=?')
        values.append(v)
    if not fields:
        return
    fields.append("updated_at=CURRENT_TIMESTAMP")
    values.append(instance_id)
    with get_db() as conn:
        conn.execute(f'UPDATE cloud_instances SET {",".join(fields)} WHERE id=?', values)
        conn.commit()


def get_instance(instance_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute('SELECT * FROM cloud_instances WHERE id=?', (instance_id,)).fetchone()
        return _parse_row(row) if row else None


def get_user_instances(user_id: int, status: str = None) -> list:
    with get_db() as conn:
        sql = 'SELECT * FROM cloud_instances WHERE user_id=?'
        params = [user_id]
        if status:
            sql += ' AND status=?'
            params.append(status)
        sql += ' ORDER BY created_at DESC'
        rows = conn.execute(sql, params).fetchall()
        return [_parse_row(r) for r in rows]


def get_all_instances(status: str = None, limit: int = 50) -> list:
    with get_db() as conn:
        sql = 'SELECT ci.*, u.username, u.phone FROM cloud_instances ci LEFT JOIN users u ON ci.user_id=u.id'
        params = []
        if status:
            sql += ' WHERE ci.status=?'
            params.append(status)
        sql += ' ORDER BY ci.created_at DESC LIMIT ?'
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [_parse_row(r) for r in rows]


def add_log(instance_id: int, step: str, status: str = 'running', message: str = '', raw_output: str = '', duration_ms: int = 0):
    with get_db() as conn:
        conn.execute('''INSERT INTO provision_logs
            (instance_id, step, status, message, raw_output, duration_ms)
            VALUES (?,?,?,?,?,?)''',
            (instance_id, step, status, message[:500], raw_output[:2000], duration_ms))
        conn.commit()


def get_logs(instance_id: int) -> list:
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM provision_logs WHERE instance_id=? ORDER BY id ASC',
            (instance_id,)).fetchall()
        return [dict(r) for r in rows]


def _parse_row(row):
    d = dict(row)
    for field in ('specs', 'connect_info', 'metadata'):
        try:
            d[field] = json.loads(d.get(field, '{}'))
        except (json.JSONDecodeError, TypeError):
            d[field] = {}
    return d
