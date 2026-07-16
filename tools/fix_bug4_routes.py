"""Fix Bug 4: lastrowid -> RETURNING id - fixes for all files."""
import os, re

BASE = r'F:\Sites\VeroRun'

def apply_replacements(fp, replacements):
    """Apply list of (old, new) string replacements to file."""
    with open(fp, 'r', encoding='utf-8') as f:
        c = f.read()
    for old, new in replacements:
        if old in c:
            c = c.replace(old, new)
            print(f'  {os.path.basename(fp)}: OK')
        else:
            print(f'  {os.path.basename(fp)}: SKIP (pattern not found)')
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(c)

# ═══════════════════════════════════════════
# 1. auth.py
# ═══════════════════════════════════════════
fp = os.path.join(BASE, 'auth-center', 'routes', 'auth.py')
apply_replacements(fp, [
    (
        "cur = conn.execute(\n            'INSERT INTO users (phone, username, display_name, password_hash, phone_verified, email_verified, last_login) VALUES (%s,%s,%s,%s,1,0,%s)',\n            (phone, username, display_name or username, stored, now))\n        user_id = cur.lastrowid",
        "user_id = conn.execute(\n            'INSERT INTO users (phone, username, display_name, password_hash, phone_verified, email_verified, last_login) VALUES (%s,%s,%s,%s,1,0,%s) RETURNING id',\n            (phone, username, display_name or username, stored, now)).fetchone()[0]"
    ),
    (
        "cur = conn.execute(\n                'INSERT INTO users (phone, phone_verified, last_login) VALUES (%s,1,%s)',\n                (phone, now))\n            user_id = cur.lastrowid",
        "user_id = conn.execute(\n                'INSERT INTO users (phone, phone_verified, last_login) VALUES (%s,1,%s) RETURNING id',\n                (phone, now)).fetchone()[0]"
    ),
])

# ═══════════════════════════════════════════
# 2. user.py 
# ═══════════════════════════════════════════
fp = os.path.join(BASE, 'auth-center', 'routes', 'user.py')
with open(fp, 'r', encoding='utf-8') as f:
    lines = f.readlines()

i = 0
while i < len(lines):
    if 'lastrowid' in lines[i]:
        # Find the INSERT in previous lines
        insert_start = None
        for j in range(i-8, i):
            if 'conn.execute(' in lines[j] and 'INSERT INTO' in lines[j]:
                insert_start = j
                break
        if insert_start is not None:
            # Find end of the execute call
            # Add RETURNING id to the SQL
            sql_line = insert_start
            while sql_line <= i:
                if "VALUES" in lines[sql_line] or "VALUES" in lines[sql_line]:
                    # This is the VALUES line - add RETURNING id before closing quote
                    pass
                sql_line += 1
            
            # Simple approach: find the single-quote closing of SQL and add RETURNING id
            for k in range(insert_start, i):
                if lines[k].strip().endswith("',") or lines[k].strip().endswith("')") or lines[k].strip().endswith("')"):
                    # Add RETURNING id before closing quote
                    if "RETURNING id" not in lines[k]:
                        lines[k] = lines[k].replace("')", " RETURNING id')")
                        if "')" not in lines[k]:
                            lines[k] = lines[k].replace("'", " RETURNING id'", 1)
                    break
                elif lines[k].strip().endswith("'") and not lines[k].strip().endswith("')"):
                    # Multi-line SQL ending with '
                    if "VALUES (" in lines[k] or "VALUES(" in lines[k]:
                        lines[k] = lines[k].rstrip() + " RETURNING id"
                        break
            
            # Change .lastrowid to .fetchone()[0]
            if '.lastrowid' in lines[i]:
                # Determine variable name
                var_match = re.match(r'^(\s+)(\w+)\s*=\s*\w+\.lastrowid', lines[i])
                if var_match:
                    indent, var = var_match.groups()
                    # Find the conn.execute line and restructure
                    exec_line = None
                    for j in range(insert_start, i):
                        if 'conn.execute(' in lines[j]:
                            exec_line = j
                            break
                    if exec_line is not None:
                        lines[i] = f'{indent}{var} = ' + lines[exec_line].lstrip()
                        # Move the .fetchone()[0] to the end of the chain
                        lines[exec_line] = ''
                        # Now lines[i] starts with the variable = conn.execute(...)
                        # Need to close the chain properly
                        # Find the last line of the execute call
                        for k in range(exec_line+1, i):
                            if lines[k].strip().startswith('(') or lines[k].strip().endswith('))'):
                                # Parameter tuple ending
                                lines[k] = lines[k].rstrip() + ').fetchone()[0]\n'
                                break
        
        i += 1
        continue
    i += 1

with open(fp, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print(f'user.py: processed')

# ═══════════════════════════════════════════
# 3-10: social_media, shop_admin, sessions, header_admin, footer_admin, cleaner_agent, agents, admin
# Use direct string replacements
# ═══════════════════════════════════════════

fixes = {
    'social_media': [
        ("cursor = conn.execute(\n            'INSERT INTO social_media_links (platform, url, icon, sort_order, is_active)'\n            ' VALUES (%s,%s,%s,%s,%s)'\n        )\n        new_id = cursor.lastrowid",
         "new_id = conn.execute(\n            'INSERT INTO social_media_links (platform, url, icon, sort_order, is_active)'\n            ' VALUES (%s,%s,%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"),
    ],
    'shop_admin': [
        ("c = conn.execute(\n        'INSERT INTO products (name, description, price, category, image_url, stock, sort_order, is_published, created_at)'\n        ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())'\n    )\n    pid = c.lastrowid",
         "pid = conn.execute(\n        'INSERT INTO products (name, description, price, category, image_url, stock, sort_order, is_published, created_at)'\n        ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW()) RETURNING id'\n    ).fetchone()[0]"),
    ],
    'sessions': [
        ("cur = conn.execute(\n        'INSERT INTO user_sessions (user_id, device_info, ip_address, user_agent)'\n        ' VALUES (%s,%s,%s,%s)'\n    )\n    sid = cur.lastrowid",
         "sid = conn.execute(\n        'INSERT INTO user_sessions (user_id, device_info, ip_address, user_agent)'\n        ' VALUES (%s,%s,%s,%s) RETURNING id'\n    ).fetchone()[0]"),
    ],
    'header_admin': [
        ("cursor = conn.execute(\n            'INSERT INTO header_nav (site, label, url, is_enabled, sort_order)'\n            ' VALUES (%s,%s,%s,1,%s)'\n        )\n        new_id = cursor.lastrowid",
         "new_id = conn.execute(\n            'INSERT INTO header_nav (site, label, url, is_enabled, sort_order)'\n            ' VALUES (%s,%s,%s,1,%s) RETURNING id'\n        ).fetchone()[0]"),
    ],
    'footer_admin': [
        ("cursor = conn.execute(\n            'INSERT INTO footer_links (title, url, sort_order)'\n            ' VALUES (%s,%s,%s)'\n        )\n        new_id = cursor.lastrowid",
         "new_id = conn.execute(\n            'INSERT INTO footer_links (title, url, sort_order)'\n            ' VALUES (%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"),
        ("cursor = conn.execute(\n            'INSERT INTO footer_nav (label, url, is_enabled, sort_order)'\n            ' VALUES (%s,%s,1,%s)'\n        )\n        new_id = cursor.lastrowid",
         "new_id = conn.execute(\n            'INSERT INTO footer_nav (label, url, is_enabled, sort_order)'\n            ' VALUES (%s,%s,1,%s) RETURNING id'\n        ).fetchone()[0]"),
        ("cursor = conn.execute(\n            'INSERT INTO footer_articles (title, content, sort_order)'\n            ' VALUES (%s,%s,%s)'\n        )\n        new_id = cursor.lastrowid",
         "new_id = conn.execute(\n            'INSERT INTO footer_articles (title, content, sort_order)'\n            ' VALUES (%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"),
        ("cursor = conn.execute(\n            'INSERT INTO partner_links (name, url, logo, sort_order)'\n            ' VALUES (%s,%s,%s,%s)'\n        )\n        new_id = cursor.lastrowid",
         "new_id = conn.execute(\n            'INSERT INTO partner_links (name, url, logo, sort_order)'\n            ' VALUES (%s,%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"),
    ],
    'cleaner_agent': [
        ("c = conn.execute(\n            'INSERT INTO knowledge_queue (req_type, title, content, raw_text, result)'\n            ' VALUES (%s,%s,%s,%s,%s)'\n        )\n        qid = c.lastrowid",
         "qid = conn.execute(\n            'INSERT INTO knowledge_queue (req_type, title, content, raw_text, result)'\n            ' VALUES (%s,%s,%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"),
    ],
    'agents': [
        ("cur = conn.execute(\n        'INSERT INTO user_agents (user_id, name, avatar_url, description, system_prompt, model, temperature, max_tokens, knowledge_base, status)'\n        ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'\n    )\n    aid = cur.lastrowid",
         "aid = conn.execute(\n        'INSERT INTO user_agents (user_id, name, avatar_url, description, system_prompt, model, temperature, max_tokens, knowledge_base, status)'\n        ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id'\n    ).fetchone()[0]"),
    ],
}

for fname, replacements in fixes.items():
    fp = os.path.join(BASE, 'auth-center', 'routes', f'{fname}.py')
    apply_replacements(fp, replacements)

# ═══════════════════════════════════════════
# admin.py
# ═══════════════════════════════════════════
fp = os.path.join(BASE, 'auth-center', 'routes', 'admin.py')
admin_fixes = [
    (
        "cur = conn.execute(\n            'INSERT INTO user_agents (user_id, name, description, model, system_prompt, temperature, max_tokens, knowledge_base, status)'\n            ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)'\n        )\n        aid = cur.lastrowid",
        "aid = conn.execute(\n            'INSERT INTO user_agents (user_id, name, description, model, system_prompt, temperature, max_tokens, knowledge_base, status)'\n            ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"
    ),
    (
        "cur = conn.execute(\n            'INSERT INTO social_links (platform, url, icon, sort_order, is_active)'\n            ' VALUES (%s,%s,%s,%s,1)'\n        )\n        lid = cur.lastrowid",
        "lid = conn.execute(\n            'INSERT INTO social_links (platform, url, icon, sort_order, is_active)'\n            ' VALUES (%s,%s,%s,%s,1) RETURNING id'\n        ).fetchone()[0]"
    ),
    (
        "cur = conn.execute(\n            'INSERT INTO notification_templates (name, channel, title_template, content_template, variables, is_active)'\n            ' VALUES (%s,%s,%s,%s,%s,1)'\n        )\n        tid = cur.lastrowid",
        "tid = conn.execute(\n            'INSERT INTO notification_templates (name, channel, title_template, content_template, variables, is_active)'\n            ' VALUES (%s,%s,%s,%s,%s,1) RETURNING id'\n        ).fetchone()[0]"
    ),
    (
        "cur = conn.execute(\n            'INSERT INTO reward_rules (name, event_type, reward_type, reward_value, conditions, is_active)'\n            ' VALUES (%s,%s,%s,%s,%s,1)'\n        )\n        rid = cur.lastrowid",
        "rid = conn.execute(\n            'INSERT INTO reward_rules (name, event_type, reward_type, reward_value, conditions, is_active)'\n            ' VALUES (%s,%s,%s,%s,%s,1) RETURNING id'\n        ).fetchone()[0]"
    ),
    (
        "cur = conn.execute(\n            'INSERT INTO provider_models (provider_id, model_key, display_name, model_type, status)'\n            ' VALUES (%s,%s,%s,%s,%s)'\n        )\n        mid = cur.lastrowid",
        "mid = conn.execute(\n            'INSERT INTO provider_models (provider_id, model_key, display_name, model_type, status)'\n            ' VALUES (%s,%s,%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"
    ),
    (
        "cur = conn.execute(\n            'INSERT INTO voice_templates (name, category, voice_preset, config)'\n            ' VALUES (%s,%s,%s,%s)'\n        )\n        vid = cur.lastrowid",
        "vid = conn.execute(\n            'INSERT INTO voice_templates (name, category, voice_preset, config)'\n            ' VALUES (%s,%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"
    ),
    (
        "cur = conn.execute(\n            'INSERT INTO video_tasks (user_id, title, prompt, status)'\n            ' VALUES (%s,%s,%s,%s)'\n        )\n        tid = cur.lastrowid",
        "tid = conn.execute(\n            'INSERT INTO video_tasks (user_id, title, prompt, status)'\n            ' VALUES (%s,%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"
    ),
    (
        "cursor = conn.execute(\n            'INSERT INTO interests (name, category, sort_order)'\n            ' VALUES (%s,%s,%s)'\n        )\n        new_id = cursor.lastrowid",
        "new_id = conn.execute(\n            'INSERT INTO interests (name, category, sort_order)'\n            ' VALUES (%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"
    ),
    (
        "cursor = conn.execute(\n            'INSERT INTO media_files (filename, original_name, file_type, file_size, url, uploaded_by, category)'\n            ' VALUES (%s,%s,%s,%s,%s,%s,%s)'\n        )\n        new_id = cursor.lastrowid",
        "new_id = conn.execute(\n            'INSERT INTO media_files (filename, original_name, file_type, file_size, url, uploaded_by, category)'\n            ' VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id'\n        ).fetchone()[0]"
    ),
]
apply_replacements(fp, admin_fixes)

print('\nBug 4 (routes) completed')
