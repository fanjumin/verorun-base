#!/usr/bin/env python3
"""
Seed draft data using DeepSeek API, then deploy and insert on the server.
Usage: python tools/seed_draft_from_deepseek.py
"""
import os, sys, json, subprocess, tempfile

# ── Config ────────────────────────────────────────────
DEEPSEEK_KEY = 'sk-b527bcba292c4ffc8caf10d148bb5b23'
DEEPSEEK_MODEL = 'deepseek-chat'
SERVER = '***REMOVED***'
SSH_USER = 'easykai'
SSH_PASS = '***REMOVED***'
REMOTE_DIR = '/home/easykai/easykai-workspace/easykai.cn/'

# ── Step 1: Call DeepSeek to generate content ─────────

def call_deepseek(prompt, system_msg="You are a website content generator. Output ONLY valid JSON."):
    import urllib.request
    payload = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.deepseek.com/chat/completions',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {DEEPSEEK_KEY}',
        }
    )
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read().decode())
    return result['choices'][0]['message']['content']


print('=' * 60)
print('Step 1: Generating website content via DeepSeek...')
print('=' * 60)

# Generate draft_tokens (brand, colors, typography, navigation, footer, spacing)
tokens_prompt = """Generate a complete website design tokens JSON for a business website.
The website should be about "CloudAI Solutions" - a tech company selling AI-powered cloud services.

Return a valid JSON object with this EXACT structure (fill in meaningful values):
{
  "brand": {
    "site_name": "CloudAI Solutions",
    "slogan": "string, a compelling tagline",
    "industry": "Technology / Cloud Computing",
    "brand_story": "string, 2-3 sentences about the company",
    "company_name": "CloudAI Solutions Inc.",
    "contact_email": "contact@cloudai.example.com"
  },
  "colors": {
    "primary": "#...", "secondary": "#...", "accent": "#...",
    "background": "#ffffff", "surface": "#f8fafc",
    "text_primary": "#1a202c", "text_secondary": "#64748b",
    "border": "#e2e8f0", "error": "#ef4444", "success": "#10b981"
  },
  "typography": {
    "heading_font": "Inter, sans-serif", "body_font": "Inter, -apple-system, sans-serif",
    "h1_size": "2.5rem", "h2_size": "1.875rem", "h3_size": "1.5rem",
    "body_size": "1rem", "small_size": "0.875rem", "line_height": 1.75
  },
  "navigation": {
    "items": [
      {"id": 1, "title": "Home", "url": "/", "icon": "", "target": "_self", "children": []},
      {"id": 2, "title": "Products", "url": "/products", "icon": "", "target": "_self", "children": []},
      {"id": 3, "title": "Pricing", "url": "/pricing", "icon": "", "target": "_self", "children": []},
      {"id": 4, "title": "About", "url": "/about", "icon": "", "target": "_self", "children": []},
      {"id": 5, "title": "Contact", "url": "/contact", "icon": "", "target": "_self", "children": []}
    ]
  },
  "footer": {
    "sections": [], "articles": [],
    "copyright": "2026 CloudAI Solutions. All rights reserved.",
    "icp_number": "", "security_number": ""
  },
  "spacing": {
    "xs": "4px", "sm": "8px", "md": "16px", "lg": "32px", "xl": "64px",
    "section_gap": "64px", "card_padding": "24px"
  }
}

Use a modern tech blue/indigo color scheme for primary colors.
Reply with ONLY the JSON object, no markdown, no explanation."""

try:
    tokens_raw = call_deepseek(tokens_prompt)
    # Extract JSON from response
    match = __import__('re').search(r'\{[\s\S]*\}', tokens_raw)
    if match:
        draft_tokens = json.loads(match.group(0))
    else:
        draft_tokens = json.loads(tokens_raw)
    print(f'  Tokens generated: brand={draft_tokens["brand"]["site_name"]}')
except Exception as e:
    print(f'  Token generation failed: {e}')
    sys.exit(1)

# Generate cms_blocks content
blocks_prompt = """Generate website page content as a JSON array of CMS blocks for the "home" page.
The website is "CloudAI Solutions" - AI-powered cloud services company.

Each block has these fields: page, section, position, block_type, title, subtitle, content, icon, image_url.

block_type must be one of: hero, feature-card, cta, faq, contact, stats, testimonial, pricing-card

Generate 6 blocks for the home page:
1. Hero section (block_type: hero) - with a strong headline and subtitle
2. Features section - 3 feature cards (block_type: feature-card) about AI cloud services
3. Stats section (block_type: stats) - key metrics
4. Pricing section - 3 pricing tiers (block_type: pricing-card)
5. FAQ section - 3 common questions (block_type: faq)
6. CTA section (block_type: cta) - call to action

Return a JSON array ONLY, like:
[
  {"page": "home", "section": "hero", "position": 0, "block_type": "hero", "title": "...", "subtitle": "...", "content": "...", "icon": "", "image_url": ""},
  ...
]

Use meaningful business content. Reply with ONLY the JSON array."""

try:
    blocks_raw = call_deepseek(blocks_prompt)
    match = __import__('re').search(r'\[[\s\S]*\]', blocks_raw)
    if match:
        draft_blocks = json.loads(match.group(0))
    else:
        draft_blocks = json.loads(blocks_raw)
    print(f'  Blocks generated: {len(draft_blocks)} blocks')
except Exception as e:
    print(f'  Block generation failed: {e}')
    sys.exit(1)


# ── Step 2: Write SQL script ──────────────────────────

print('=' * 60)
print('Step 2: Preparing SQL insert script...')
print('=' * 60)

# Build the remote script
tokens_json_str = json.dumps(draft_tokens, ensure_ascii=False)
blocks_json_str = json.dumps(draft_blocks, ensure_ascii=False)

remote_script = '''#!/usr/bin/env python3
"""Seed draft data for preview-as-editor testing."""
import sys, os, json, sqlite3

# Use the project's own DB
BASE_DIR = '/home/easykai/easykai-workspace/easykai.cn'
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')  # models.py resolves to easykai-workspace/data/
DB_PATH = os.environ.get('DB_PATH', os.path.join(DATA_DIR, 'x7k2m9a4.db'))

DRAFT_TOKENS_JSON = ''' + repr(tokens_json_str) + '''

BLOCKS_JSON = ''' + repr(blocks_json_str) + '''

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Clear existing draft blocks
cur.execute("DELETE FROM cms_blocks WHERE is_published=0")
print('  Cleared existing draft blocks')

# 2. Insert design_tokens draft_json
draft_tokens = json.loads(DRAFT_TOKENS_JSON)

# Check if design_tokens record exists
cur.execute("SELECT id FROM design_tokens WHERE site_key='platform'")
row = cur.fetchone()
if row:
    cur.execute(
        "UPDATE design_tokens SET draft_json=?, updated_at=datetime('now') WHERE site_key='platform'",
        (json.dumps(draft_tokens, ensure_ascii=False),)
    )
    print('  Updated draft_json in design_tokens')
else:
    cur.execute(
        "INSERT INTO design_tokens (site_key, token_json, draft_json, generated_by, version) VALUES (?, ?, ?, ?, ?)",
        ('platform', '{}', json.dumps(draft_tokens, ensure_ascii=False), 'ai_draft', 1)
    )
    print('  Created design_tokens with draft_json')

# 3. Insert CMS blocks
blocks = json.loads(BLOCKS_JSON)
for b in blocks:
    cur.execute(
        "INSERT INTO cms_blocks (page, section, position, block_type, title, subtitle, content, icon, image_url, is_published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'), datetime('now'))",
        (b['page'], b.get('section', b['block_type']), b['position'], b['block_type'], b['title'], b.get('subtitle', ''), b.get('content', ''), b.get('icon', ''), b.get('image_url', ''))
    )
print('  Inserted ' + repr(len(blocks)) + ' draft blocks')

conn.commit()
cur.close()
conn.close()
print('Draft seeding complete!')
'''

# ── Step 3: Upload and execute on server ──────────────

print('=' * 60)
print('Step 3: Uploading and executing on server...')
print('=' * 60)

# Write script to temp file
tf = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8')
tf.write(remote_script)
tf.close()
local_path = tf.name
remote_path = '/tmp/seed_draft.py'

# Upload via paramiko
import paramiko
transport = paramiko.Transport((SERVER, 22))
transport.connect(username=SSH_USER, password=SSH_PASS)
sftp = paramiko.SFTPClient.from_transport(transport)
sftp.put(local_path, remote_path)
sftp.close()

print(f'  Uploaded script to {remote_path}')

# Execute on server
ssh = transport.open_session()
ssh.exec_command(f'cd {REMOTE_DIR} && python3 {remote_path}')
exit_code = ssh.recv_exit_status()
stdout = ssh.makefile('rb').read().decode()
stderr = ssh.makefile_stderr('rb').read().decode()
print(f'  Exit code: {exit_code}')
if stdout: print(f'  Output: {stdout}')
if stderr: print(f'  Errors: {stderr}')

transport.close()

# Cleanup temp file
os.unlink(local_path)

if exit_code == 0:
    print('=' * 60)
    print('SUCCESS! Draft data seeded.')
    print('Open https://agent.easykai.cn/admin/site-builder/preview-site')
    print('to see the editor with real content.')
    print('=' * 60)
else:
    print('=' * 60)
    print('FAILED. Check errors above.')
    print('=' * 60)
    sys.exit(1)
