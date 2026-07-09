import sqlite3, os

# 1. Server easykai.db - pull it first to local
# We'll use the tables list we already have from the server
server_easykai_tables = {
    'ad_placements','admin_logs','admin_profiles','agent_api_keys','agent_conversations',
    'agent_experiences','agent_logs','agent_matrix','agent_tasks','agent_token_daily',
    'agent_token_logs','agents','alert_config','ali_api_tokens','ali_api_user_stats',
    'ali_oauth_states','analytics_alerts','analytics_daily_stats','analytics_device_stats',
    'analytics_events','analytics_geo_stats','analytics_hourly_stats','analytics_logs',
    'analytics_page_stats','analytics_privacy_config','analytics_source_stats',
    'analytics_visitor_sessions','api_keys','app_authorizations','billing_orders',
    'brand_settings','career_options','carts','categories','channel_configs',
    'chat_history','chat_messages','check_history','check_runs','cluster_services',
    'cms_blocks','cms_categories','cms_posts','cms_settings','contact_messages',
    'content_sources','content_tasks','coupon_redemptions','coupons','cron_jobs',
    'deployment_codes','downloads','email_codes','email_sent','execution_logs',
    'express_companies','favorites','health_checks','health_trend','industries',
    'interests','invoices','job_dependencies','knowledge_blocks','knowledge_queue',
    'login_attempts','media_files','mp_profiles','notification_logs',
    'notification_preferences','notification_templates','oauth_providers','order_items',
    'product_skus','product_spec_values','product_specs','products','provider_models',
    'providers','raw_contents','reward_claims','reward_rules','scheduler_state',
    'service_plans','site_blocks','site_configs','site_plans','site_theme_config',
    'skill_pushes','sms_codes','sms_rate_limits','sms_templates','social_links',
    'social_push_logs','subscription_audit_log','subscription_orders','subscription_plans',
    'subscriptions','system_agents','system_config','task_logs','themes',
    'user_activity','user_addresses','user_agents','user_feedback','user_interests',
    'user_notifications','user_profiles','user_purchases','user_sessions','user_tickets',
    'users','verification_requests','video_tasks','voice_templates',
    'workflow_definitions','workflow_instances','workflow_node_instances',
}

# 2. Local verorun.db (new schema)
conn_new = sqlite3.connect(r'F:\Sites\VeroRun\data\verorun.db')
verorun_tables = set(row[0] for row in conn_new.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall())
conn_new.close()

# 3. Local easykai.db (old full db)
conn_old = sqlite3.connect(r'F:\Sites\VeroRun\data\easykai.db')
easykai_tables = set(row[0] for row in conn_old.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall())
conn_old.close()

print("=" * 60)
print("服务器 easykai.db 表数:", len(server_easykai_tables))
print("本地 verorun.db (新库) 表数:", len(verorun_tables))
print("本地 easykai.db (完整旧库) 表数:", len(easykai_tables))
print("=" * 60)

# Tables in verorun.db but NOT in server easykai.db
missing_from_server = verorun_tables - server_easykai_tables
print(f"\n=== 服务器 easykai.db 缺少的表 ({len(missing_from_server)} 个) ===")
for t in sorted(missing_from_server):
    print(f"  + {t}")

# Tables in verorun.db but NOT in local easykai.db
missing_from_local_old = verorun_tables - easykai_tables
print(f"\n=== 本地 easykai.db 缺少的表 ({len(missing_from_local_old)} 个) ===")
for t in sorted(missing_from_local_old):
    print(f"  + {t}")

# For each missing table, get the CREATE TABLE from verorun.db
print("\n\n=== 需创建的表的 DDL ===")
conn_new = sqlite3.connect(r'F:\Sites\VeroRun\data\verorun.db')
for t in sorted(missing_from_server):
    sql = conn_new.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
    ).fetchone()
    if sql:
        print(f"\n-- {t}")
        print(sql[0])
    else:
        print(f"\n-- {t} (NO DDL FOUND)")
conn_new.close()

# Also check: tables in x7k2m9a4.db but not in server easykai.db (these are the newest additions)
print("\n\n=== verorun.db 特有表（相对 easykai.db）的 CREATE TABLE ===")
for t in sorted(missing_from_local_old):
    sql = None
    # Try verorun.db first
    conn_check = sqlite3.connect(r'F:\Sites\VeroRun\data\verorun.db')
    sql = conn_check.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
    ).fetchone()
    conn_check.close()
    if sql:
        print(f"\n-- {t}")
        print(sql[0])
