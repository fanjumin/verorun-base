"""Database connection pool — asyncpg with pgvector support"""
import asyncpg
from config import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DATABASE

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=PG_HOST, port=PG_PORT,
            user=PG_USER, password=PG_PASSWORD,
            database=PG_DATABASE,
            min_size=2, max_size=10,
            init=_init_connection,
        )
    return _pool


async def _init_connection(conn):
    """Register pgvector type codec on each new connection."""
    try:
        from pgvector.asyncpg import register_vector
        await register_vector(conn)
    except ImportError:
        pass  # pgvector not installed, fallback to string-based vector queries


async def init_db():
    """Create database if not exists, run schema."""
    import asyncpg
    sys_conn = await asyncpg.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASSWORD,
        database='postgres'
    )
    exists = await sys_conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname=$1", PG_DATABASE
    )
    if not exists:
        await sys_conn.execute(f'CREATE DATABASE "{PG_DATABASE}"')
    await sys_conn.close()

    pool = await get_pool()
    import os
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    async with pool.acquire() as conn:
        await conn.execute(open(schema_path).read())
    return pool


async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
