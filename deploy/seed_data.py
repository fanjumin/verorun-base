#!/usr/bin/env python3
"""
VeroRun — Standalone seed data injector.

Usage:
    python3 seed_data.py                      # auto-detect .env in current dir
    python3 seed_data.py --env /path/to/.env  # explicit .env path
    python3 seed_data.py --sqlite /path/to/db # force SQLite mode
"""

import os, sys, hashlib, secrets, json, argparse

# ── Admin credentials ─────────────────────────────────────────────────
# Username is randomly generated on each seed run to prevent guessing.
# It prints at install time; save it or check deploy output.
import secrets as _secrets
ADMIN_PHONE    = "13800000000"
ADMIN_USERNAME = os.environ.get("VR_ADMIN_USERNAME", "adm_" + _secrets.token_hex(8))
ADMIN_PASSWORD = os.environ.get("VR_ADMIN_PASSWORD", "***REMOVED***")
ADMIN_DISPLAY  = "Administrator"

# ── Seed data ─────────────────────────────────────────────────────────

DEFAULT_PLUGIN_PRODUCTS = [
    {"plugin_key": "content_factory",  "name": "Content Factory",      "category": "content",  "price_month_fen": 2900,  "price_year_fen": 29000,  "sort_order": 1, "is_featured": 1},
    {"plugin_key": "analytics",        "name": "Advanced Analytics",    "category": "analytics", "price_month_fen": 4900,  "price_year_fen": 49000,  "sort_order": 2, "is_featured": 1},
    {"plugin_key": "social_publisher", "name": "Social Publisher",      "category": "content",  "price_month_fen": 1900,  "price_year_fen": 19000,  "sort_order": 3, "is_featured": 0},
    {"plugin_key": "automation",       "name": "Workflow Automation",   "category": "automation","price_month_fen": 3900,  "price_year_fen": 39000,  "sort_order": 4, "is_featured": 1},
    {"plugin_key": "sms_gateway",      "name": "SMS Gateway",           "category": "comm",     "price_month_fen": 900,   "price_year_fen": 9000,   "sort_order": 5, "is_featured": 0},
    {"plugin_key": "email_service",    "name": "Email Service",         "category": "comm",     "price_month_fen": 900,   "price_year_fen": 9000,   "sort_order": 6, "is_featured": 0},
    {"plugin_key": "oauth_provider",   "name": "OAuth Provider",        "category": "auth",     "price_month_fen": 1900,  "price_year_fen": 19000,  "sort_order": 7, "is_featured": 0},
]

DEFAULT_QUOTAS = [
    {"target_type": "global", "daily_limit": 100000, "rate_limit": 30},
    {"target_type": "user",   "daily_limit": 20,     "rate_limit": 5},
    {"target_type": "agent",  "daily_limit": 1000,   "rate_limit": 60},
]


# ======================================================================
# Helpers
# ======================================================================

def parse_env(env_path: str) -> dict:
    """Parse a .env file into a dict."""
    config = {}
    if not os.path.exists(env_path):
        print(f"[WARN] .env not found: {env_path}")
        return config
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            config[key.strip()] = val.strip()
    return config


def hash_password(password: str, iterations: int = 600000) -> str:
    """PBKDF2-SHA256 hash with random salt, matches auth-center format."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"pbkdf2:sha256:{iterations}:{salt}:{pw_hash}"


# ======================================================================
# Database abstraction
# ======================================================================

class SeedDB:
    """Minimal database wrapper supporting both PostgreSQL and SQLite."""

    def __init__(self, env: dict, sqlite_path: str = None):
        self.env = env
        self.sqlite_path = sqlite_path
        self.conn = None
        self._connect()

    def _connect(self):
        pg_host = self.env.get("PG_HOST", "")
        if pg_host and not self.sqlite_path:
            # PostgreSQL mode
            import psycopg2
            self.conn = psycopg2.connect(
                host=pg_host,
                port=int(self.env.get("PG_PORT", 5432)),
                dbname=self.env.get("PG_DB", "verorun"),
                user=self.env.get("PG_USER", "verorun"),
                password=self.env.get("PG_PASSWORD", ""),
            )
            self.conn.autocommit = True
            self._db_type = "postgresql"
            self._param_style = "%s"
        else:
            # SQLite mode
            import sqlite3
            db_path = self.sqlite_path or self.env.get("DB_PATH", "data/verorun.db")
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self._db_type = "sqlite"
            self._param_style = "?"

    def close(self):
        if self.conn:
            self.conn.close()

    def execute(self, sql: str, params: tuple = None):
        cur = self.conn.cursor()
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        return cur

    def insert_on_conflict(self, table: str, data: dict, conflict_col: str = None):
        """Idempotent insert — insert or skip on conflict."""
        cols = ", ".join(data.keys())
        placeholders = ", ".join([self._param_style] * len(data))
        if self._db_type == "postgresql":
            conflict = conflict_col or "id"
            sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT ({conflict}) DO NOTHING"
        else:
            sql = f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})"
        self.execute(sql, tuple(data.values()))

    def table_exists(self, name: str) -> bool:
        if self._db_type == "postgresql":
            cur = self.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                (name,)
            )
        else:
            cur = self.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (name,)
            )
        return cur.fetchone() is not None


# ======================================================================
# Seed functions
# ======================================================================

def seed_base_plan(db: SeedDB):
    """Seed the free base plan."""
    db.insert_on_conflict("base_plans", {
        "plan_key": "free",
        "name": "Free",
        "description": "Free entry plan with 20 API calls per day",
        "daily_limit": 20,
    }, conflict_col="plan_key")
    print("  [OK] base_plan: free")


def seed_plugin_products(db: SeedDB):
    """Seed initial plugin product catalog."""
    for p in DEFAULT_PLUGIN_PRODUCTS:
        db.insert_on_conflict("plugin_products", p, conflict_col="plugin_key")
        print(f"  [OK] plugin_product: {p['plugin_key']}")


def seed_admin_user(db: SeedDB):
    """Create or update the admin user."""
    pw_hash = hash_password(ADMIN_PASSWORD)

    if db._db_type == "postgresql":
        # Check if exists
        cur = db.execute(
            "SELECT id FROM users WHERE username = %s OR phone = %s",
            (ADMIN_USERNAME, ADMIN_PHONE)
        )
    else:
        cur = db.execute(
            "SELECT id FROM users WHERE username = ? OR phone = ?",
            (ADMIN_USERNAME, ADMIN_PHONE)
        )

    row = cur.fetchone()
    if row:
        user_id = row[0]
        db.execute(
            "UPDATE users SET username = %s, display_name = %s, password_hash = %s, is_admin = 1, active = 1, phone_verified = 1, password_changed_at = NULL WHERE id = %s"
            if db._db_type == "postgresql" else
            "UPDATE users SET username = ?, display_name = ?, password_hash = ?, is_admin = 1, active = 1, phone_verified = 1, password_changed_at = NULL WHERE id = ?",
            (ADMIN_USERNAME, ADMIN_DISPLAY, pw_hash, user_id)
        )
        print(f"  [OK] admin user updated (id={user_id})")
    else:
        cur = db.execute(
            "INSERT INTO users (username, phone, display_name, password_hash, is_admin, active, phone_verified) "
            "VALUES (%s, %s, %s, %s, 1, 1, 1) RETURNING id"
            if db._db_type == "postgresql" else
            "INSERT INTO users (username, phone, display_name, password_hash, is_admin, active, phone_verified) "
            "VALUES (?, ?, ?, ?, 1, 1, 1)",
            (ADMIN_USERNAME, ADMIN_PHONE, ADMIN_DISPLAY, pw_hash)
        )
        if db._db_type == "postgresql":
            user_id = cur.fetchone()[0]
        else:
            user_id = cur.lastrowid
        print(f"  [OK] admin user created (id={user_id})")

    return user_id


def seed_quotas(db: SeedDB):
    """Seed default usage quotas."""
    for q in DEFAULT_QUOTAS:
        db.insert_on_conflict("usage_quotas", q, conflict_col="id")
        print(f"  [OK] quota: {q['target_type']}")


def seed_admin_subscription(db: SeedDB, user_id: int):
    """Create a free subscription for the admin user."""
    db.insert_on_conflict("user_subscriptions", {
        "user_id": user_id,
        "plan_key": "free",
        "status": "active",
        "daily_limit": 20,
    }, conflict_col="user_id")
    print(f"  [OK] admin subscription: free (user_id={user_id})")


# ======================================================================
# Main
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="VeroRun seed data injector")
    parser.add_argument("--env", default=None, help="Path to .env file")
    parser.add_argument("--sqlite", default=None, help="Force SQLite mode with explicit path")
    args = parser.parse_args()

    # Locate .env
    env_path = args.env
    if not env_path:
        for candidate in [".env", "../.env", os.path.join(os.path.dirname(__file__), "..", ".env")]:
            if os.path.exists(candidate):
                env_path = os.path.abspath(candidate)
                break
    if not env_path:
        env_path = os.path.abspath(".env")

    print(f"[i] Loading config from: {env_path}")
    env = parse_env(env_path)

    db = SeedDB(env, sqlite_path=args.sqlite)

    # Verify required tables exist
    required = ["users", "base_plans", "plugin_products", "usage_quotas", "user_subscriptions"]
    missing = [t for t in required if not db.table_exists(t)]
    if missing:
        print(f"[FAIL] Tables not found: {', '.join(missing)}")
        print("       Run database migrations first, or verify .env config.")
        db.close()
        sys.exit(1)

    print("[i] Seeding data...")
    seed_base_plan(db)
    seed_plugin_products(db)
    user_id = seed_admin_user(db)
    seed_quotas(db)
    seed_admin_subscription(db, user_id)

    db.conn.commit()
    db.close()

    print(f"\n[OK] Seed data injected successfully.")
    print(f"     Admin account: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    print(f"     Plugins seeded: {len(DEFAULT_PLUGIN_PRODUCTS)}")


if __name__ == "__main__":
    main()
