#!/usr/bin/env python3
"""
Logistics Plugin Models — 独立数据库 logistics.db
==================================================
完全独立于主库。
- logistics_queries: 物流查询日志
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'logistics.db')

_logistics_conn = None


def get_logistics_db():
    """获取物流插件独立数据库连接（单例）"""
    global _logistics_conn
    if _logistics_conn is None:
        _logistics_conn = psycopg2.connect(
            host=os.environ.get('PG_HOST','localhost'),
            port=int(os.environ.get('PG_PORT',5432)),
            dbname=os.environ.get('PG_DB','verorun'),
            user=os.environ.get('PG_USER','verorun'),
            password=os.environ.get('PG_PASSWORD',''),
            cursor_factory=RealDictCursor
        )
        _logistics_conn.execute("CREATE SCHEMA IF NOT EXISTS logistics")
        _logistics_conn.execute("SET search_path TO logistics")
    return _logistics_conn


def init_logistics_db():
    """初始化物流插件数据库表（幂等）"""
    conn = get_logistics_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS logistics_queries (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        shipper_code    TEXT NOT NULL,
        logistic_code   TEXT NOT NULL,
        order_code      TEXT DEFAULT '',
        success         BIGINT DEFAULT 0,
        error_msg       TEXT DEFAULT '',
        queried_at      TEXT DEFAULT NOW()
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_logistics_queries_code ON logistics_queries(logistic_code)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_logistics_queries_at ON logistics_queries(queried_at)')
    conn.commit()
    print('[LogisticsPlugin] logistics.db 已初始化')


# 兼容旧接口名
ensure_logistics_tables = init_logistics_db
