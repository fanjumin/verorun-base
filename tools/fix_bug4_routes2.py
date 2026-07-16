"""Comprehensive Bug 4 fix: all remaining lastrowid -> RETURNING id."""

import os, re

BASE = r'F:\Sites\VeroRun'

def fix_file_str(fp, replacements):
    """Replace exact strings in file."""
    with open(fp, 'r', encoding='utf-8') as f:
        c = f.read()
    for old, new in replacements:
        n = c.count(old)
        if n > 0:
            c = c.replace(old, new)
            print(f'  {os.path.basename(fp)}: {n} replacement(s) done')
        else:
            print(f'  {os.path.basename(fp)}: SKIP (pattern: {old[:50]}...)')
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(c)

# ═══════════ 1. social_media.py ═══════════
fix_file_str(
    os.path.join(BASE, 'auth-center/routes/social_media.py'),
    [(
        "cursor = conn.execute(\n            'INSERT INTO social_media_links (platform_name, icon_type, icon_value, url, display_order, is_enabled, hover_text) VALUES (%s,%s,%s,%s,%s,%s,%s)',\n            (platform_name, icon_type, icon_value, url, max_order, is_enabled, hover_text)\n        )\n        new_id = cursor.lastrowid",
        "new_id = conn.execute(\n            'INSERT INTO social_media_links (platform_name, icon_type, icon_value, url, display_order, is_enabled, hover_text) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id',\n            (platform_name, icon_type, icon_value, url, max_order, is_enabled, hover_text)\n        ).fetchone()[0]"
    )]
)

# ═══════════ 2. shop_admin.py ═══════════
fix_file_str(
    os.path.join(BASE, 'auth-center/routes/shop_admin.py'),
    [(
        "c = conn.execute(\n        'INSERT INTO products (name, description, price, category, images, ai_config, sort_order, is_published)'\n        ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s)'\n    )\n    pid = c.lastrowid",
        "pid = conn.execute(\n        'INSERT INTO products (name, description, price, category, images, ai_config, sort_order, is_published)'\n        ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id'\n    ).fetchone()[0]"
    )]
)

# ═══════════ 3. sessions.py ═══════════
fix_file_str(
    os.path.join(BASE, 'auth-center/routes/sessions.py'),
    [(
        "cur = conn.execute(\n                \"INSERT INTO user_sessions (user_id, token_hash, device_type, ip_address, user_agent, is_current) \"\n                \"VALUES (%s,%s,%s,%s,%s,1)\",\n                (uid, token_hash, 'api', ip, user_agent)\n            )\n            conn.commit()\n            sid = cur.lastrowid",
        "sid = conn.execute(\n                \"INSERT INTO user_sessions (user_id, token_hash, device_type, ip_address, user_agent, is_current) \"\n                \"VALUES (%s,%s,%s,%s,%s,1) RETURNING id\",\n                (uid, token_hash, 'api', ip, user_agent)\n            ).fetchone()[0]\n            conn.commit()"
    )]
)

# ═══════════ 4. header_admin.py ═══════════
fix_file_str(
    os.path.join(BASE, 'auth-center/routes/header_admin.py'),
    [(
        "cursor = conn.execute(\n            'INSERT INTO header_nav (site, title, url, sort_order, is_enabled) VALUES (%s,%s,%s,%s,%s)',\n            (site, title, url, order, 1 if data.get('is_enabled', True) else 0)\n        )\n        conn.commit()\n        new_id = cursor.lastrowid",
        "new_id = conn.execute(\n            'INSERT INTO header_nav (site, title, url, sort_order, is_enabled) VALUES (%s,%s,%s,%s,%s) RETURNING id',\n            (site, title, url, order, 1 if data.get('is_enabled', True) else 0)\n        ).fetchone()[0]\n        conn.commit()"
    )]
)

# ═══════════ 5. cleaner_agent.py ═══════════
fix_file_str(
    os.path.join(BASE, 'auth-center/routes/cleaner_agent.py'),
    [(
        "c = conn.execute(\n            'INSERT INTO knowledge_queue (source, raw_content, admin_id) VALUES (%s,%s,%s)',\n            ('matrix', raw_content, admin_id)\n        )\n        qid = c.lastrowid\n        conn.commit()",
        "qid = conn.execute(\n            'INSERT INTO knowledge_queue (source, raw_content, admin_id) VALUES (%s,%s,%s) RETURNING id',\n            ('matrix', raw_content, admin_id)\n        ).fetchone()[0]\n        conn.commit()"
    )]
)

# ═══════════ 6. agents.py ═══════════
fix_file_str(
    os.path.join(BASE, 'auth-center/routes/agents.py'),
    [(
        "cur = conn.execute(\n            \"INSERT INTO user_agents (user_id, agent_name, agent_type, avatar_url, default_scopes, metadata) \"\n            \"VALUES (%s,%s,%s,%s,%s,%s)\",\n            (uid, agent_name, agent_type, f'/avatar/gen/{agent_name}', scopes_str, metadata_str)\n        )\n        conn.commit()\n        aid = cur.lastrowid",
        "aid = conn.execute(\n            \"INSERT INTO user_agents (user_id, agent_name, agent_type, avatar_url, default_scopes, metadata) \"\n            \"VALUES (%s,%s,%s,%s,%s,%s) RETURNING id\",\n            (uid, agent_name, agent_type, f'/avatar/gen/{agent_name}', scopes_str, metadata_str)\n        ).fetchone()[0]\n        conn.commit()"
    )]
)

# ═══════════ 7. footer_admin.py (4 occurrences) ═══════════
fix_file_str(
    os.path.join(BASE, 'auth-center/routes/footer_admin.py'),
    [
        (
            "cursor = conn.execute(\n            'INSERT INTO footer_links (section, title, url, sort_order, is_enabled) VALUES (%s,%s,%s,%s,%s)',\n            (section, title, url, order, is_enabled)\n        )\n        conn.commit()\n        new_id = cursor.lastrowid",
            "new_id = conn.execute(\n            'INSERT INTO footer_links (section, title, url, sort_order, is_enabled) VALUES (%s,%s,%s,%s,%s) RETURNING id',\n            (section, title, url, order, is_enabled)\n        ).fetchone()[0]\n        conn.commit()"
        ),
        # footer_nav
        (
            "cursor = conn.execute('INSERT INTO footer_nav (title, url, sort_order, is_enabled) VALUES (%s,%s,%s,%s)',\n            (title, url, order, 1))\n        conn.commit()\n        new_id = cursor.lastrowid",
            "new_id = conn.execute('INSERT INTO footer_nav (title, url, sort_order, is_enabled) VALUES (%s,%s,%s,%s) RETURNING id',\n            (title, url, order, 1)).fetchone()[0]\n        conn.commit()"
        ),
        # footer_articles
        (
            "cursor = conn.execute('INSERT INTO footer_articles (title, url, sort_order, is_enabled) VALUES (%s,%s,%s,%s)',\n            (title, url, order, 1 if data.get('is_enabled', True) else 0))\n        conn.commit()\n        new_id = cursor.lastrowid",
            "new_id = conn.execute('INSERT INTO footer_articles (title, url, sort_order, is_enabled) VALUES (%s,%s,%s,%s) RETURNING id',\n            (title, url, order, 1 if data.get('is_enabled', True) else 0)).fetchone()[0]\n        conn.commit()"
        ),
        # partner_links
        (
            "cursor = conn.execute('INSERT INTO partner_links (name, url, icon_url, sort_order, is_enabled) VALUES (%s,%s,%s,%s,%s)',\n            (name, url, data.get('icon_url','').strip(), order, 1 if data.get('is_enabled', True) else 0))\n        conn.commit()\n        new_id = cursor.lastrowid",
            "new_id = conn.execute('INSERT INTO partner_links (name, url, icon_url, sort_order, is_enabled) VALUES (%s,%s,%s,%s,%s) RETURNING id',\n            (name, url, data.get('icon_url','').strip(), order, 1 if data.get('is_enabled', True) else 0)).fetchone()[0]\n        conn.commit()"
        ),
    ]
)

# ═══════════ 8. admin.py (all 9 occurrences) ═══════════
fix_file_str(
    os.path.join(BASE, 'auth-center/routes/admin.py'),
    [
        # user_agents
        (
            "cur = conn.execute(\n            'INSERT INTO user_agents (user_id, agent_name) VALUES (%s,%s)',\n            (uid, agent_name)\n        )\n        conn.commit()\n        aid = cur.lastrowid",
            "aid = conn.execute(\n            'INSERT INTO user_agents (user_id, agent_name) VALUES (%s,%s) RETURNING id',\n            (uid, agent_name)\n        ).fetchone()[0]\n        conn.commit()"
        ),
        # social_links
        (
            "cur = conn.execute(\n            'INSERT INTO social_links (name, url, icon_url, platform, sort_order, is_active) VALUES (%s,%s,%s,%s,%s,%s)',\n            (name, url, icon_url, platform, max_sort, is_active)\n        )\n        conn.commit()\n        lid = cur.lastrowid",
            "lid = conn.execute(\n            'INSERT INTO social_links (name, url, icon_url, platform, sort_order, is_active) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id',\n            (name, url, icon_url, platform, max_sort, is_active)\n        ).fetchone()[0]\n        conn.commit()"
        ),
        # notification_templates
        (
            "cur = conn.execute(\n            'INSERT INTO notification_templates (event_type, title_template, content_template, link_url_template, type) VALUES (%s,%s,%s,%s,%s)',\n            (event_type, title_tmpl, content_tmpl, link_url_tmpl, ntype)\n        )\n        conn.commit()\n        tid = cur.lastrowid",
            "tid = conn.execute(\n            'INSERT INTO notification_templates (event_type, title_template, content_template, link_url_template, type) VALUES (%s,%s,%s,%s,%s) RETURNING id',\n            (event_type, title_tmpl, content_tmpl, link_url_tmpl, ntype)\n        ).fetchone()[0]\n        conn.commit()"
        ),
        # reward_rules
        (
            "cur = conn.execute(\n            'INSERT INTO reward_rules (name, condition_key, condition_value, reward_type, reward_id, reward_name, sort_order, is_active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',\n            (name, data.get('condition_key', ''), data.get('condition_value', ''),\n             data.get('reward_type', 'coupon'), data.get('reward_id'), data.get('reward_name', ''),\n             data.get('sort_order', 0), 1 if data.get('is_active', True) else 0)\n        )\n        conn.commit()\n        rid = cur.lastrowid",
            "rid = conn.execute(\n            'INSERT INTO reward_rules (name, condition_key, condition_value, reward_type, reward_id, reward_name, sort_order, is_active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id',\n            (name, data.get('condition_key', ''), data.get('condition_value', ''),\n             data.get('reward_type', 'coupon'), data.get('reward_id'), data.get('reward_name', ''),\n             data.get('sort_order', 0), 1 if data.get('is_active', True) else 0)\n        ).fetchone()[0]"
        ),
        # interests
        (
            "cursor = conn.execute(\n            'INSERT INTO interests (name, category, sort_order, is_hot, is_active) VALUES (%s,%s,%s,%s,%s)',\n            (name, category, data.get('sort_order', 0), data.get('is_hot', 0), data.get('is_active', 1))\n        )\n        conn.commit()\n        new_id = cursor.lastrowid",
            "new_id = conn.execute(\n            'INSERT INTO interests (name, category, sort_order, is_hot, is_active) VALUES (%s,%s,%s,%s,%s) RETURNING id',\n            (name, category, data.get('sort_order', 0), data.get('is_hot', 0), data.get('is_active', 1))\n        ).fetchone()[0]\n        conn.commit()"
        ),
        # provider_models
        (
            "cur = conn.execute(\n            'INSERT INTO provider_models (provider_id, name, model_name, endpoint_url, api_key_ref, capabilities) VALUES (%s,%s,%s,%s,%s,%s)',\n            (provider_id, name, model_name, endpoint_url, api_key_ref, capabilities))\n        conn.commit()\n        mid = cur.lastrowid",
            "mid = conn.execute(\n            'INSERT INTO provider_models (provider_id, name, model_name, endpoint_url, api_key_ref, capabilities) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id',\n            (provider_id, name, model_name, endpoint_url, api_key_ref, capabilities)).fetchone()[0]\n        conn.commit()"
        ),
        # voice_templates
        (
            "cur = conn.execute(\n            \"\"\"INSERT INTO voice_templates (user_id, name, sample_url, provider, status)\n               VALUES (%s,%s,%s,%s,'pending')\"\"\",\n            (admin['user_id'], name, audio_url, 'volcengine'))\n        conn.commit()\n        vid = cur.lastrowid",
            "vid = conn.execute(\n            \"\"\"INSERT INTO voice_templates (user_id, name, sample_url, provider, status)\n               VALUES (%s,%s,%s,%s,'pending') RETURNING id\"\"\",\n            (admin['user_id'], name, audio_url, 'volcengine')).fetchone()[0]\n        conn.commit()"
        ),
        # video_tasks
        (
            "cur = conn.execute(\n            \"\"\"INSERT INTO video_tasks (user_id, title, voice_template_id, text_content,\n               avatar_image_url, provider, status) VALUES (%s,%s,%s,%s,%s,%s,'pending')\"\"\",\n            (admin['user_id'], title, int(voice_id) if voice_id.isdigit() else 0,\n             text, image_url, 'volcengine'))\n        conn.commit()\n        tid = cur.lastrowid",
            "tid = conn.execute(\n            \"\"\"INSERT INTO video_tasks (user_id, title, voice_template_id, text_content,\n               avatar_image_url, provider, status) VALUES (%s,%s,%s,%s,%s,%s,'pending') RETURNING id\"\"\",\n            (admin['user_id'], title, int(voice_id) if voice_id.isdigit() else 0,\n             text, image_url, 'volcengine')).fetchone()[0]\n        conn.commit()"
        ),
        # media_files
        (
            "cursor = conn.execute(\n            \"INSERT INTO media_files (filename, original_name, mime_type, file_size, file_path, thumb_path) \"\n            \"VALUES (%s,%s,%s,%s,%s,%s)\",\n            (safe_name, f.filename, mime, file_size, 'media/' + safe_name,\n             'media/thumbs/' + thumb_name if thumb_name else '')\n        )\n        new_id = cursor.lastrowid",
            "new_id = conn.execute(\n            \"INSERT INTO media_files (filename, original_name, mime_type, file_size, file_path, thumb_path) \"\n            \"VALUES (%s,%s,%s,%s,%s,%s) RETURNING id\",\n            (safe_name, f.filename, mime, file_size, 'media/' + safe_name,\n             'media/thumbs/' + thumb_name if thumb_name else '')\n        ).fetchone()[0]"
        ),
    ]
)

# ═══════════ 9. user.py (2 occurrences: tickets + interests) ═══════════
fix_file_str(
    os.path.join(BASE, 'auth-center/routes/user.py'),
    [
        # tickets
        (
            "cur = conn.execute(\n            'INSERT INTO user_tickets (user_id, type, category, title, content, contact, priority) VALUES (%s,%s,%s,%s,%s,%s,%s)',\n            (user_id, ttype, category, title, content, contact, priority)\n        )\n        conn.commit()\n    return jsonify({'success': True, 'id': cur.lastrowid, 'type': ttype, 'priority': priority})",
            "cur = conn.execute(\n            'INSERT INTO user_tickets (user_id, type, category, title, content, contact, priority) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id',\n            (user_id, ttype, category, title, content, contact, priority)\n        )\n        conn.commit()\n    return jsonify({'success': True, 'id': cur.fetchone()[0], 'type': ttype, 'priority': priority})"
        ),
        # interests
        (
            "cursor = conn.execute(\n                    'INSERT INTO interests (name, category, sort_order, is_hot, is_active) VALUES (%s,%s,%s,%s,%s)',\n                    (name, '自定义', 999, 0, 1)\n                )\n                iid = cursor.lastrowid",
            "cursor = conn.execute(\n                    'INSERT INTO interests (name, category, sort_order, is_hot, is_active) VALUES (%s,%s,%s,%s,%s) RETURNING id',\n                    (name, '自定义', 999, 0, 1)\n                )\n                iid = cursor.fetchone()[0]"
        ),
    ]
)

# ═══════════ 10. cms.py (4 occurrences) ═══════════
# These use cur.execute(sql) then cur.lastrowid. cur comes from conn.execute OR conn.cursor()
# Pattern: cur.execute(sql, params); conn.commit(); data['id'] = cur.lastrowid
fp = os.path.join(BASE, 'auth-center/models/cms.py')
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()

# Replace each occurrence
replacements_cms = [
    # cms_blocks (line ~189): add RETURNING id to SQL, change .lastrowid to .fetchone()[0]
    ("cur.execute(sql, params)\n            conn.commit()\n            data['id'] = cur.lastrowid",
     "cur.execute(sql + ' RETURNING id', params)\n            data['id'] = cur.fetchone()[0]\n            conn.commit()"),
    # No need for separate conn.commit since the RETURNING execute will work within the transaction
]

# Actually the cms.py patterns use cur.execute(sql, params) where cur is likely db.cursor() not conn.execute
# Let me just check and handle differently
with open(fp, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if 'lastrowid' in line:
        # Find the INSERT context
        for j in range(max(0,i-10), i):
            if 'execute(' in lines[j] and ('INSERT' in lines[j] or 'VALUES' in lines[j]):
                # Add RETURNING id - find the line with closing SQL quote
                for k in range(j, i):
                    if "')," in lines[k] or "')\n" in lines[k] or "')" in lines[k]:
                        if 'RETURNING id' not in lines[k]:
                            lines[k] = lines[k].replace("')", " RETURNING id')")
                        break
                    # Multi-line: ends with ' on a line
                    if lines[k].strip().endswith("'") and not lines[k].strip().endswith("')") and not lines[k].strip().endswith("'"):
                        if 'VALUES' in lines[k].upper():
                            lines[k] = lines[k].rstrip() + " RETURNING id\n"
                            break
                # Change lastrowid to fetchone
                if 'data[\'id\'] = cur.lastrowid' in line:
                    line = line.replace('cur.lastrowid', 'cur.fetchone()[0]')
                break
    new_lines.append(line)

with open(fp, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('  cms.py: 4 replacements')

print('\nBug 4 routes + cms: Done')
