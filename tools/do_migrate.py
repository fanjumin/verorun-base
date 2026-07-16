"""Simple data migration: SQLite → PostgreSQL with OVERRIDING SYSTEM VALUE."""
import os, sys, sqlite3, time

sys.path.insert(0, r'F:\Sites\VeroRun')

# PG connection
import psycopg2
from psycopg2.extras import RealDictCursor

PG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'verorun',
    'user': 'easykai',
    'password': '***REMOVED***',
}

# SQLite source
DATA_DIR = r'F:\Sites\VeroRun\data'
SQ_MAIN = os.path.join(DATA_DIR, 'x7k2m9a4.db')
SQ_SHOP = os.path.join(DATA_DIR, 'shop.db')

# Tables to migrate (from x7k2m9a4.db → public schema)
TABLES = [
    'users', 'sessions', 'site_configs', 'system_config', 'subscriptions',
    'cms_posts', 'cms_categories', 'cms_blocks', 'admin_profiles',
    'brand_settings', 'header_nav', 'footer_links', 'footer_nav',
    'footer_articles', 'partner_links', 'directory_listings',
    'interests', 'user_interests', 'app_authorizations', 'user_agents',
    'social_media_links', 'user_sessions', 'user_tickets',
    'products', 'categories', 'carts', 'user_purchases',
    'notification_templates', 'reward_rules', 'admin_logs',
    'media_files', 'social_links', 'provider_models',
    'voice_templates', 'video_tasks', 'knowledge_blocks',
    'knowledge_queue', 'sso_tokens', 'user_preferences',
    'addresses', 'password_resets', 'email_verifications',
    'phone_verifications', 'audit_logs', 'login_attempts',
]

def migrate_table(pg_conn, sqlite_path, table, schema='public'):
    """Migrate one table from SQLite to PG."""
    if not os.path.exists(sqlite_path):
        print(f"  SKIP {table}: {sqlite_path} not found")
        return 0
    
    sq = sqlite3.connect(sqlite_path)
    sq.row_factory = sqlite3.Row
    
    # Get columns
    try:
        cols = [d[1] for d in sq.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception as e:
        print(f"  SKIP {table}: {e}")
        sq.close()
        return 0
    
    if not cols:
        print(f"  SKIP {table}: no columns in SQLite")
        sq.close()
        return 0
    
    # Check if table exists in PG
    cur = pg_conn.cursor()
    cur.execute(f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='{schema}' AND table_name='{table}')")
    exists = cur.fetchone()[0]
    cur.close()
    if not exists:
        print(f"  SKIP {table}: not in PG ({schema})")
        sq.close()
        return 0
    
    # Check if already has data
    cur = pg_conn.cursor()
    cur.execute(f'SELECT count(*) FROM "{schema}"."{table}"')
    existing = cur.fetchone()[0]
    cur.close()
    if existing > 0:
        print(f"  SKIP {table}: already has {existing} rows")
        sq.close()
        return 0
    
    # Read from SQLite
    rows = sq.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        print(f"  SKIP {table}: no data in SQLite")
        sq.close()
        return 0
    
    # Check if id is SERIAL/IDENTITY (need OVERRIDING SYSTEM VALUE)
    cur = pg_conn.cursor()
    cur.execute(f"""
        SELECT column_default FROM information_schema.columns
        WHERE table_schema='{schema}' AND table_name='{table}' 
        AND column_name='id' AND column_default IS NOT NULL
    """)
    default = cur.fetchone()
    use_override = default and ('identity' in default[0].lower() or 'nextval' in default[0].lower())
    cur.close()
    
    # Build INSERT
    col_list = ', '.join(f'"{c}"' for c in cols)
    placeholders = ', '.join(f'%s' for _ in cols)
    prefix = 'OVERRIDING SYSTEM VALUE ' if use_override else ''
    insert_sql = f'INSERT INTO "{schema}"."{table}" ({col_list}) {prefix}VALUES ({placeholders}) ON CONFLICT DO NOTHING'
    
    # Batch insert
    cur = pg_conn.cursor()
    batch = [tuple(r[c] for c in cols) for r in rows]
    count = 0
    for row in batch:
        try:
            cur.execute(insert_sql, row)
            count += 1
        except Exception as e:
            if 'duplicate key' not in str(e).lower():
                print(f"    ERR {table}: {str(e)[:80]}")
            pg_conn.rollback()
            cur.close()
            cur = pg_conn.cursor()
    pg_conn.commit()
    cur.close()
    sq.close()
    
    if count > 0:
        print(f"  OK {table}: {count}/{len(batch)} rows")
    return count

# Main
print("="*60)
print("DATA MIGRATION: SQLite → PostgreSQL")
print("="*60)

pg = psycopg2.connect(**PG)
pg.autocommit = False

total = 0
for table in TABLES:
    n = migrate_table(pg, SQ_MAIN, table)
    total += n

# Shop tables
shop_tables = ['products', 'categories', 'carts', 'user_purchases']
for table in shop_tables:
    n = migrate_table(pg, SQ_SHOP, table, schema='shop')
    total += n

print(f"\nTotal migrated: {total} rows")
pg.close()
print("Done.")
