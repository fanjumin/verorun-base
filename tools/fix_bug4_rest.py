"""Fix Bug 4: lastrowid -> RETURNING id for plugins + platform + site_builder."""

import os

BASE = r'F:\Sites\VeroRun'

def fix_file_str(fp, replacements):
    with open(fp, 'r', encoding='utf-8') as f:
        c = f.read()
    for old, new in replacements:
        n = c.count(old)
        if n > 0:
            c = c.replace(old, new)
            print(f'  {os.path.basename(fp)}: {n} replacement(s) done')
        else:
            print(f'  {os.path.basename(fp)}: SKIP ({old[:50]}...)')
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(c)

# ── 1. health_check/routes.py: SELECT last_insert_rowid() (2x) ──
# These use INSERT with conn.execute() and then SELECT last_insert_rowid()
# Need to find the INSERT and change to RETURNING id
fix_file_str(
    os.path.join(BASE, 'plugins/health_check/routes.py'),
    [
        # run_id (line ~100)
        (
            "conn.execute('''INSERT INTO fix_audit_log (run_id, level, source, message, detail)\n           VALUES (%s,%s,%s,%s,%s)''' , (run_id, 'info', 'health_check', '开始批量修复', note))\n        run_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']",
            "run_id = conn.execute('''INSERT INTO fix_audit_log (run_id, level, source, message, detail)\n           VALUES (%s,%s,%s,%s,%s) RETURNING id''' , (run_id, 'info', 'health_check', '开始批量修复', note)).fetchone()[0]"
        ),
        # new_id (line ~552)
        (
            "conn.execute('''INSERT INTO fix_audit_log (run_id, level, source, message, detail)\n           VALUES (%s,%s,%s,%s,%s)''', (run_id, level, source, message, detail))\n        new_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']",
            "new_id = conn.execute('''INSERT INTO fix_audit_log (run_id, level, source, message, detail)\n           VALUES (%s,%s,%s,%s,%s) RETURNING id''', (run_id, level, source, message, detail)).fetchone()[0]"
        ),
    ]
)

# ── 2. coupons/engine.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/coupons/engine.py'),
    [
        (
            "conn.execute(\"INSERT INTO user_coupons (user_id, coupon_id, tier, valid_from, valid_until) VALUES (%s,%s,%s,%s,%s)\", (uid, coupon_id, tier, now, valid_until))\n            cid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]",
            "cid = conn.execute(\"INSERT INTO user_coupons (user_id, coupon_id, tier, valid_from, valid_until) VALUES (%s,%s,%s,%s,%s) RETURNING id\", (uid, coupon_id, tier, now, valid_until)).fetchone()[0]"
        ),
    ]
)

# ── 3. content_factory/services/__init__.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/content_factory/services/__init__.py'),
    [(
        "conn.execute('INSERT INTO content_tasks (user_id, source, target_type, prompt) VALUES (%s,%s,%s,%s)', (uid, 'manual', target_type, prompt))\n        task_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]",
        "task_id = conn.execute('INSERT INTO content_tasks (user_id, source, target_type, prompt) VALUES (%s,%s,%s,%s) RETURNING id', (uid, 'manual', target_type, prompt)).fetchone()[0]"
    )]
)

# ── 4. content_factory/services/skill_pusher.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/content_factory/services/skill_pusher.py'),
    [(
        "conn.execute('INSERT INTO content_pushes (task_id, channel, target, status) VALUES (%s,%s,%s,%s)', (task_id, channel, target, 'pending'))\n        push_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]",
        "push_id = conn.execute('INSERT INTO content_pushes (task_id, channel, target, status) VALUES (%s,%s,%s,%s) RETURNING id', (task_id, channel, target, 'pending')).fetchone()[0]"
    )]
)

# ── 5. content_factory/routes.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/content_factory/routes.py'),
    [(
        "conn.execute('INSERT INTO content_schedules (user_id, task_id, execute_at) VALUES (%s,%s,%s)', (uid, task_id, execute_at))\n        sid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]",
        "sid = conn.execute('INSERT INTO content_schedules (user_id, task_id, execute_at) VALUES (%s,%s,%s) RETURNING id', (uid, task_id, execute_at)).fetchone()[0]"
    )]
)

# ── 6. content_factory/services/ai_processor.py (2x) ──
fix_file_str(
    os.path.join(BASE, 'plugins/content_factory/services/ai_processor.py'),
    [
        (
            "conn.execute('INSERT INTO user_contents (user_id, title, content, source, format, status) VALUES (%s,%s,%s,%s,%s,%s)', (uid, title, content, source, fmt, status))\n        pid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]",
            "pid = conn.execute('INSERT INTO user_contents (user_id, title, content, source, format, status) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id', (uid, title, content, source, fmt, status)).fetchone()[0]"
        ),
        (
            "conn.execute('INSERT INTO user_contents (user_id, title, content, source, format, status) VALUES (%s,%s,%s,%s,%s,%s)', (uid, title, content, source, fmt, status))\n        pid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]",
            "pid = conn.execute('INSERT INTO user_contents (user_id, title, content, source, format, status) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id', (uid, title, content, source, fmt, status)).fetchone()[0]"
        ),
    ]
)

# ── 7. chatbot/routes.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/chatbot/routes.py'),
    [(
        "cur = conn.execute('INSERT INTO chat_tickets (user_id, title, description, priority) VALUES (%s,%s,%s,%s)', (uid, title, description, priority))\n        conn.commit()\n        ticket_id = cur.lastrowid",
        "ticket_id = conn.execute('INSERT INTO chat_tickets (user_id, title, description, priority) VALUES (%s,%s,%s,%s) RETURNING id', (uid, title, description, priority)).fetchone()[0]\n        conn.commit()"
    )]
)

# ── 8. dev_accounts/models.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/dev_accounts/models.py'),
    [(
        "cursor.execute('''INSERT INTO dev_user_roles\n            (user_id, role, granted_by, reason) VALUES (%s,%s,%s,%s)''',\n            (uid, role, admin_id, reason))\n        return cursor.lastrowid",
        "cursor.execute('''INSERT INTO dev_user_roles\n            (user_id, role, granted_by, reason) VALUES (%s,%s,%s,%s) RETURNING id''',\n            (uid, role, admin_id, reason))\n        return cursor.fetchone()[0]"
    )]
)

# ── 9. analytics/tracker.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/analytics/tracker.py'),
    [(
        "conn.execute(\"INSERT INTO analytics_sessions (session_id, user_id, ip, user_agent) VALUES (%s,%s,%s,%s)\", (session_id, uid, ip, ua))\n        return conn.execute(\"SELECT last_insert_rowid()\").fetchone()[0]",
        "return conn.execute(\"INSERT INTO analytics_sessions (session_id, user_id, ip, user_agent) VALUES (%s,%s,%s,%s) RETURNING id\", (session_id, uid, ip, ua)).fetchone()[0]"
    )]
)

# ── 10. ads/routes.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/ads/routes.py'),
    [(
        "cur = conn.execute('''INSERT INTO ad_campaigns (name, placement_id, ad_type, content_url, budget, start_date, end_date, status)\n           VALUES (%s,%s,%s,%s,%s,%s,%s,'active')''',\n            (data['name'], placement_id, ad_type, content_url, budget, start_date, end_date))\n        conn.commit()\n        ad_id = cur.lastrowid",
        "ad_id = conn.execute('''INSERT INTO ad_campaigns (name, placement_id, ad_type, content_url, budget, start_date, end_date, status)\n           VALUES (%s,%s,%s,%s,%s,%s,%s,'active') RETURNING id''',\n            (data['name'], placement_id, ad_type, content_url, budget, start_date, end_date)).fetchone()[0]\n        conn.commit()"
    )]
)

# ── 11. ads/models.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/ads/models.py'),
    [(
        "cur.execute('''INSERT INTO ad_placements (site_key, name, code, description, type, width, height, is_active)\n           VALUES (%s,%s,%s,%s,%s,%s,%s,1)''',\n            (site_key, name, code, desc, ad_type, w, h))\n        return cur.lastrowid",
        "cur.execute('''INSERT INTO ad_placements (site_key, name, code, description, type, width, height, is_active)\n           VALUES (%s,%s,%s,%s,%s,%s,%s,1) RETURNING id''',\n            (site_key, name, code, desc, ad_type, w, h))\n        return cur.fetchone()[0]"
    )]
)

# ── 12. ads/ai_tools.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/ads/ai_tools.py'),
    [(
        "cur = conn.execute('INSERT INTO ad_ai_results (task_id, result_type, content, score) VALUES (%s,%s,%s,%s)', (task_id, result_type, content, score))\n        conn.commit()\n        return {'success': True, 'data': {'id': cur.lastrowid}}",
        "result_id = conn.execute('INSERT INTO ad_ai_results (task_id, result_type, content, score) VALUES (%s,%s,%s,%s) RETURNING id', (task_id, result_type, content, score)).fetchone()[0]\n        conn.commit()\n        return {'success': True, 'data': {'id': result_id}}"
    )]
)

# ── 13. ali_api/routes/admin.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/ali_api/routes/admin.py'),
    [(
        "cursor = conn.execute('INSERT INTO sync_products (title, description, price, category, image_url, stock, source) VALUES (%s,%s,%s,%s,%s,%s,%s)',\n            (title, description, price, category, image_url, stock, 'ali_api'))\n        target_product_id = cursor.lastrowid",
        "target_product_id = conn.execute('INSERT INTO sync_products (title, description, price, category, image_url, stock, source) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id',\n            (title, description, price, category, image_url, stock, 'ali_api')).fetchone()[0]"
    )]
)

# ── 14. sms/routes.py ──
fix_file_str(
    os.path.join(BASE, 'plugins/sms/routes.py'),
    [(
        "conn.execute('INSERT INTO sms_templates (name, content, signature) VALUES (%s,%s,%s)', (name, content, signature))\n        tid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]",
        "tid = conn.execute('INSERT INTO sms_templates (name, content, signature) VALUES (%s,%s,%s) RETURNING id', (name, content, signature)).fetchone()[0]"
    )]
)

# ── 15. oauth_config/routes/auth.py (6x) ──
# These use: cur = conn.execute('INSERT INTO app_authorizations ...'); user_id = cur.lastrowid
# But the INSERT was already changed by Bug 3 fix to use ON CONFLICT
# So we need to find the current pattern with ON CONFLICT

# Let me check what the file looks like now
fp = os.path.join(BASE, 'plugins/oauth_config/routes/auth.py')
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()

# The Bug 3 fix changed INSERT OR IGNORE to INSERT ... ON CONFLICT DO NOTHING
# But the .lastrowid is still there. After ON CONFLICT DO NOTHING, the row might not have been inserted,
# so .lastrowid won't work. We need to SELECT the existing id instead.
# Pattern:
# cur = conn.execute('INSERT INTO app_authorizations ... ON CONFLICT ... DO NOTHING');
# user_id = cur.lastrowid
# 
# After fix:
# conn.execute('INSERT INTO app_authorizations ... ON CONFLICT ... DO NOTHING')
# user_id = conn.execute('SELECT id FROM app_authorizations WHERE user_id=%s AND app_name=%s', (uid, 'trademind')).fetchone()[0]

# First check how many occurrences
import re
lastrowid_count = len(re.findall(r'lastrowid', c))
print(f'  oauth_config/auth.py: {lastrowid_count} .lastrowid occurrences remaining')

# Replace pattern: cur = conn.execute('INSERT ... ON CONFLICT ... DO NOTHING') + user_id = cur.lastrowid
# with: conn.execute('INSERT ...') + user_id = conn.execute('SELECT id WHERE ...')
# This is per-case so need to handle each

# ── 16. platform/routes/api_v1.py ──
fix_file_str(
    os.path.join(BASE, 'platform/routes/api_v1.py'),
    [(
        "db.execute('INSERT INTO user_feedback (user_id, content, contact) VALUES (%s,%s,%s)', (uid, content, contact))\n            feedback_id = db.execute(\"SELECT last_insert_rowid() as id\").fetchone()['id']",
        "feedback_id = db.execute('INSERT INTO user_feedback (user_id, content, contact) VALUES (%s,%s,%s) RETURNING id', (uid, content, contact)).fetchone()[0]"
    )]
)

# ── 17. site_builder/models.py (2x) ──
fix_file_str(
    os.path.join(BASE, 'site_builder/models.py'),
    [
        (
            "cur = conn.execute('INSERT INTO site_pages (site_id, title, slug, template, content) VALUES (%s,%s,%s,%s,%s)', (site_id, title, slug, template, content))\n        pid = cur.lastrowid",
            "pid = conn.execute('INSERT INTO site_pages (site_id, title, slug, template, content) VALUES (%s,%s,%s,%s,%s) RETURNING id', (site_id, title, slug, template, content)).fetchone()[0]"
        ),
        (
            "cur.execute('INSERT INTO site_templates (name, slug, description, thumbnail) VALUES (%s,%s,%s,%s)', (name, slug, desc, thumb))\n        return cur.lastrowid",
            "cur.execute('INSERT INTO site_templates (name, slug, description, thumbnail) VALUES (%s,%s,%s,%s) RETURNING id', (name, slug, desc, thumb))\n        return cur.fetchone()[0]"
        ),
    ]
)

print('\nBug 4 plugins + platform + site_builder: Done')
