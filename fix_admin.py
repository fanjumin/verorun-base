#!/usr/bin/env python3
"""Pyramid: concat admin partials, replace Jinja2 with valid JS, node --check"""
import os, re, subprocess

DIR = os.path.join(os.path.dirname(__file__), 'admin', 'templates', 'partials')

ORDER = ['icons.html','core.html','dashboard.html','users.html','customers.html',
 'enterprise_verify.html','customer_agents.html','agents.html','api_keys.html',
 'posts.html','tickets.html','channels.html','cluster_services.html','plans.html',
 'subscriptions.html','sub_orders.html','coupons.html','ads.html',
 'shop_products.html','shop_categories.html','shop_orders.html','shop_coupons.html',
 'shop_purchases.html','sub_stats.html','sub_events.html','orders.html','oauth.html',
 'config.html','nav_settings.html','logs.html','matrix.html','ai_chat.html',
 'email.html','downloads.html','sms.html','cms.html','social.html',
 'contentfactory.html','automation.html','analytics.html','health.html',
 'i18n_translations.html','comments.html','admins.html','themes.html','headernav.html',
 'brand.html','tm_brand.html','token_monitoring.html','notifications.html',
 'reward_rules.html','model_providers.html','media_library.html','cleaner.html',
 'deploy.html','aliases.html','tail.html']

all_js = []
for fname in ORDER:
    fp = os.path.join(DIR, fname)
    if not os.path.exists(fp):
        print(f'MISSING: {fname}')
        continue
    with open(fp, 'r', encoding='utf-8') as f:
        txt = f.read()
    # For tail.html, only take content UP TO </script>
    if fname == 'tail.html':
        close_idx = txt.find('</script>')
        if close_idx >= 0:
            txt = txt[:close_idx]
    # Remove <script> and </script> tags
    txt = txt.replace('<script>', '').replace('</script>', '')
    all_js.append(txt)

js = '\n'.join(all_js)

# Replace Jinja2 with valid JS — key for node --check to not choke
# {{ sso_token | tojson }}  →  "test_token"
js = re.sub(r'\{\{\s*sso_token\s*\|\s*tojson\s*\}\}', '"test_token_abc123"', js)
# {{ _('...') }} or {{ _("...") }} → text WITHOUT extra quotes (it's inside JS strings)
def replace_gettext(m):
    return m.group(1)  # just the inner text
js = re.sub(r'\{\{\s*_\s*\(\s*[\'"](.+?)[\'"]\s*\)\s*\}\}', replace_gettext, js)
# {% trans %}...{% endtrans %} → take inner text
js = re.sub(r'\{%\s*trans\s*%\}', '', js)
js = re.sub(r'\{%\s*endtrans\s*%\}', '', js)
# {% if ... %}...{% else %}...{% endif %} → take first branch
js = re.sub(r'\{%\s*if\s+.*?%\}', '', js)
js = re.sub(r'\{%\s*else\s*%\}', '', js)
js = re.sub(r'\{%\s*endif\s*%\}', '', js)
# {% for ... %}...{% endfor %} → take body once
js = re.sub(r'\{%\s*for\s+.*?%\}', '', js)
js = re.sub(r'\{%\s*endfor\s*%\}', '', js)
# Any remaining {% ... %} blocks
js = re.sub(r'\{%[^%]*%\}', '', js)
# Any remaining {{ ... }}
js = re.sub(r'\{\{[^}]*\}\}', '"replaced"', js)

op = os.path.join(os.path.dirname(__file__), 'admin_combined.cjs')
with open(op, 'w', encoding='utf-8') as f:
    f.write(js)
print(f'Wrote {len(js)} bytes to {op}')

r = subprocess.run(['node', '--check', op], capture_output=True, text=True)
if r.returncode == 0:
    print('✓ NO SYNTAX ERRORS')
    os.remove(op)
else:
    print('✗ SYNTAX ERRORS:')
    # Parse error to get line number
    for line in r.stderr.split('\n'):
        line = line.strip()
        if 'SyntaxError' in line or line.startswith('SyntaxError'):
            print(f'  {line}')
        elif '.cjs:' in line and 'SyntaxError' not in line:
            # Extract line number
            parts = line.split('.cjs:')
            if len(parts) > 1:
                lineno = parts[1].split(':')[0]
                print(f'  Line {lineno}: {line.strip()}')
    # Show context around first error
    for line in r.stderr.split('\n'):
        if '.cjs:' in line:
            parts = line.split('.cjs:')
            if len(parts) > 1:
                try:
                    lineno = int(parts[1].split(':')[0])
                    ctx = js.split('\n')
                    print(f'\n--- Context near line {lineno} ---')
                    for i in range(max(0,lineno-3), min(len(ctx), lineno+2)):
                        mark = '>>' if i == lineno-1 else '  '
                        print(f'  {mark} {i+1}: {ctx[i][:200]}')
                    break
                except:
                    pass
    print(f'\nFile: {op}')
