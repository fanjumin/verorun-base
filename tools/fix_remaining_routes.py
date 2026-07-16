"""Fix remaining Bug 4 occurrences by using line-numbered replacements."""
import os, re

BASE = r'F:\Sites\VeroRun'

def file_to_lines(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        return f.readlines()

def lines_to_file(fp, lines):
    with open(fp, 'w', encoding='utf-8') as f:
        f.writelines(lines)

# ── admin.py:2306-2310 notification_templates ──
fp = os.path.join(BASE, 'auth-center', 'routes', 'admin.py')
lines = file_to_lines(fp)
# Line 2306-2310 (0-indexed: 2305-2309)
if 'lastrowid' in lines[2309]:
    lines[2305] = "            tid = conn.execute(\n"
    lines[2306] = "                'INSERT INTO notification_templates (event_type, title_template, content_template, link_url_template, type) VALUES (%s,%s,%s,%s,%s) RETURNING id',\n"
    lines[2307] = "                (event_type, title_tmpl, content_tmpl, link_url_tmpl, ntype)\n"
    lines[2308] = "            ).fetchone()[0]\n"
    lines[2309] = "            conn.commit()\n"
    lines_to_file(fp, lines)
    print('admin.py notification_templates: fixed')
else:
    print('admin.py notification_templates: already fixed or not found')

# ── footer_admin.py:96-99 footer_nav ──
fp = os.path.join(BASE, 'auth-center', 'routes', 'footer_admin.py')
lines = file_to_lines(fp)
for i, line in enumerate(lines):
    if "'INSERT INTO footer_nav" in line and 'lastrowid' not in lines[i+3]:
        lines[i] = "        new_id = conn.execute('INSERT INTO footer_nav (title, url, sort_order, is_enabled) VALUES (%s,%s,%s,%s) RETURNING id',\n"
        lines[i+1] = "            (title, url, order, 1 if data.get('is_enabled', True) else 0)).fetchone()[0]\n"
        lines[i+2] = "        conn.commit()\n"
        lines[i+3] = "        # remove cursor.lastrowid line\n"
        lines_to_file(fp, lines)
        print('footer_admin.py footer_nav: fixed')
        break
else:
    print('footer_admin.py footer_nav: already fixed or not found')

# ── shop_admin.py:330 ──
fp = os.path.join(BASE, 'auth-center', 'routes', 'shop_admin.py')
lines = file_to_lines(fp)
for i, line in enumerate(lines):
    if 'pid = c.lastrowid' in line:
        # Find the INSERT start
        for j in range(i-5, i):
            if 'c = conn.execute(' in lines[j] or "c = conn.execute(" in lines[j]:
                # Line j has the execute. Replace everything from j to i
                # Find the SQL: lines[j+1] has the SQL, lines with params end before i
                lines[j] = "        pid = conn.execute(\n"
                # Add RETURNING id to the last SQL line before the params
                for k in range(j+1, i):
                    line_stripped = lines[k].strip()
                    if line_stripped.startswith("' VALUES") or line_stripped.startswith("'VALUES"):
                        lines[k] = lines[k].replace("')", " RETURNING id')")
                        break
                lines[i] = "        ).fetchone()[0]\n"
                lines_to_file(fp, lines)
                print('shop_admin.py: fixed')
                break
        break

# ── social_media.py:52 ──
fp = os.path.join(BASE, 'auth-center', 'routes', 'social_media.py')
lines = file_to_lines(fp)
for i, line in enumerate(lines):
    if 'new_id = cursor.lastrowid' in line and i == 51:
        lines[47] = "        new_id = conn.execute(\n"
        lines[48] = "            'INSERT INTO social_media_links (platform_name, icon_type, icon_value, url, display_order, is_enabled, hover_text) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id',\n"
        lines[49] = "            (platform_name, icon_type, icon_value, url, max_order, is_enabled, hover_text)\n"
        lines[50] = "        ).fetchone()[0]\n"
        lines[51] = "        conn.commit()\n"
        lines_to_file(fp, lines)
        print('social_media.py: fixed')
        break

# ── cms.py: all 4 occurrences ──
# These use: cur.execute(sql, params); conn.commit(); data['id'] = cur.lastrowid
# Need: data['id'] = conn.execute(sql + ' RETURNING id', params).fetchone()[0]; conn.commit()
fp = os.path.join(BASE, 'auth-center', 'models', 'cms.py')
lines = file_to_lines(fp)
# Find each lastrowid and look back for the execute
for i in range(len(lines)-1, -1, -1):
    if "data['id'] = cur.lastrowid" in lines[i] or 'data["id"] = cur.lastrowid' in lines[i]:
        # This line should now be data['id'] = cur.fetchone()[0]
        lines[i] = lines[i].replace('cur.lastrowid', 'cur.fetchone()[0]')
        # The preceding conn.commit() can stay
        # But we need to ensure the INSERT has RETURNING id
        # Look for the cur.execute line
        for j in range(i-5, i):
            if 'cur.execute(' in lines[j]:
                # Find the closing of SQL
                for k in range(j, i):
                    if "')" in lines[k] or "')\n" in lines[k]:
                        if 'RETURNING id' not in lines[k]:
                            lines[k] = lines[k].replace("')", " RETURNING id')")
                        break
                break
        print(f'cms.py: data[id] fixed at line {i+1}')
lines_to_file(fp, lines)

print('\nRoutes remaining fixes done.')
