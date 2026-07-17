#!/usr/bin/env python3
"""Seed NovaTech AI site via DeepSeek API using direct psycopg2."""
import os, sys, json, urllib.request

API_KEY = "sk-b527bcba292c4ffc8caf10d148bb5b23"
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "verorun",
    "user": "easykai",
    "password": "***REMOVED***",
}

PROMPT = """Generate a complete single-page website design for a modern tech startup called 'NovaTech AI'. 

Return ONLY valid JSON with this exact structure:
{
  "tokens": {
    "brand": {"site_name": "NovaTech AI", "slogan": "Build the Future with AI", "brand_story": "Enterprise-grade AI solutions for modern businesses", "company_name": "NovaTech Inc."},
    "colors": {"primary": "#0891b2", "secondary": "#06b6d4", "accent": "#f59e0b", "background": "#ffffff", "surface": "#f0f9ff", "text_primary": "#0f172a", "text_secondary": "#475569", "border": "#e2e8f0", "error": "#ef4444", "success": "#10b981"},
    "typography": {"heading_font": "Inter, sans-serif", "body_font": "Inter, sans-serif", "h1_size": "3rem", "h2_size": "2rem", "h3_size": "1.5rem", "body_size": "1rem"},
    "spacing": {"section_gap": "80px", "card_padding": "24px"},
    "navigation": {"items": [{"id": 1, "title": "Home", "url": "#hero"}, {"id": 2, "title": "Services", "url": "#services"}, {"id": 3, "title": "Pricing", "url": "#pricing"}, {"id": 4, "title": "FAQ", "url": "#faq"}, {"id": 5, "title": "Contact", "url": "#contact"}]},
    "footer": {"copyright": "\u00a9 2026 NovaTech AI. All rights reserved."}
  },
  "blocks": [
    {"page": "home", "position": 0, "block_type": "hero", "title": "Build the Future with AI", "subtitle": "Enterprise-grade AI solutions that transform your business operations and drive growth.", "content": "", "icon": "", "image_url": ""},
    {"page": "home", "position": 1, "block_type": "features", "title": "Our Services", "subtitle": "Comprehensive AI solutions tailored to your needs", "content": "", "icon": "", "image_url": ""},
    {"page": "home", "position": 2, "block_type": "cta", "title": "Ready to Transform Your Business?", "subtitle": "Get started with NovaTech AI today", "content": "Join hundreds of companies already using our platform.", "icon": "", "image_url": ""},
    {"page": "home", "position": 3, "block_type": "pricing", "title": "Pricing Plans", "subtitle": "Choose the plan that fits your needs", "content": "", "icon": "", "image_url": ""},
    {"page": "home", "position": 4, "block_type": "faq", "title": "Frequently Asked Questions", "subtitle": "Everything you need to know", "content": "", "icon": "", "image_url": ""},
    {"page": "home", "position": 5, "block_type": "contact", "title": "Get in Touch", "subtitle": "We'd love to hear from you", "content": "Contact our team for a personalized demo.", "icon": "", "image_url": ""}
  ]
}"""

def call_deepseek():
    print("[DeepSeek] Calling API...")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps({
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": PROMPT}],
            "temperature": 0.7,
            "max_tokens": 4096
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
    )
    resp = urllib.request.urlopen(req, timeout=120)
    body = json.loads(resp.read())
    content = body["choices"][0]["message"]["content"]
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)

def seed_db(data):
    import psycopg2
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 1. Write draft tokens
    tokens_json = json.dumps(data["tokens"], ensure_ascii=False)
    cur.execute("SELECT id FROM design_tokens WHERE site_key='platform'")
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE design_tokens SET draft_json=%s, updated_at=NOW() WHERE site_key='platform'", (tokens_json,))
    else:
        cur.execute("INSERT INTO design_tokens (site_key, token_json, draft_json, generated_by) VALUES ('platform', '{}', %s, 'ai_draft')", (tokens_json,))
    print(f"[DB] Tokens saved: {list(data['tokens'].keys())}")

    # 2. Replace draft blocks
    cur.execute("DELETE FROM cms_blocks WHERE is_published=0")
    for b in data['blocks']:
        cur.execute(
            "INSERT INTO cms_blocks (page, section, position, block_type, title, subtitle, content, icon, image_url, is_published, created_at, updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,NOW(),NOW())",
            (b.get('page','home'), b.get('section', b.get('block_type', 'section')),
             b.get('position',0), b.get('block_type','section'),
             b.get('title',''), b.get('subtitle',''), b.get('content',''),
             b.get('icon',''), b.get('image_url',''))
        )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM cms_blocks WHERE is_published=0")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    print(f"[DB] {count} draft blocks inserted")
    return count

if __name__ == "__main__":
    data = call_deepseek()
    print(f"[DeepSeek] Got {len(data.get('blocks',[]))} blocks")
    count = seed_db(data)
    print(f"[Done] Seeded {count} draft blocks.")
