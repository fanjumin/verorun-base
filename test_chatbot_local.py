#!/usr/bin/env python3
"""本地测试脚本：验证 AI Advisor (chatbot) 插件完整链路

测试内容:
  1. 插件管理器初始化是否正常
  2. plugin_configs 表是否存在 + 种子配置是否写入
  3. agent_matrix 表是否存在 Kai Assistant 记录
  4. 平台聊天 API 路由是否存在
  5. Site 服务插件初始化正常
  6. chatbot 配置数据库可读取
"""

import os, sys, json, sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
os.environ['JWT_SECRET'] = 'test_secret_key_12345678901234567890'
os.environ['FLASK_SECRET_KEY'] = 'test_flask_secret_do_not_use_in_production'
os.environ['DEPLOY_LANG'] = 'zh-CN'
os.environ['DEPLOY_MARKET'] = 'cn'
os.environ['EASYKAI_MODE'] = 'main'

DB_PATH = os.path.join(BASE, 'data', 'x7k2m9a4.db')
assert os.path.exists(DB_PATH), f"数据库不存在: {DB_PATH}"
os.environ['DB_PATH'] = DB_PATH

sys.path.insert(0, os.path.join(BASE, 'auth-center'))
sys.path.insert(0, BASE)

# ── 清理插件注册表 & agent_matrix，强制新安装 ──
from plugin_manager.models import get_registry_db
with get_registry_db() as rconn:
    rconn.execute("DELETE FROM plugin_registry WHERE identifier='chatbot'")
    rconn.commit()
with sqlite3.connect(DB_PATH) as conn:
    conn.execute("DELETE FROM agent_matrix WHERE name='Kai Assistant'")
    conn.execute("DELETE FROM plugin_configs WHERE plugin_name='chatbot'")
    conn.commit()

passed = 0
failed = 0

def check(name, ok, detail=''):
    global passed, failed
    status = '✅ PASS' if ok else '❌ FAIL'
    if ok:
        passed += 1
    else:
        failed += 1
    print(f'  {status}  {name}')
    if detail:
        for line in detail.split('\n'):
            print(f'         {line}')

# ═══ 1. 插件管理器初始化 ═══
print('\n===== 1. 插件管理器初始化 =====')
try:
    from plugin_manager.manager import PluginManager
    from flask import Flask
    app = Flask(__name__)
    app.plugins_dir = os.path.join(BASE, 'plugins')
    pm = PluginManager(app)
    plugins = pm.list_plugins()
    plugin_names = [p.identifier for p in plugins]
    check('PluginManager 初始化成功', True)
    check('chatbot 插件已注册', 'chatbot' in plugin_names,
          f'已注册插件: {plugin_names}')
except Exception as e:
    import traceback
    check('PluginManager 初始化', False, f'{e}\n{traceback.format_exc()}')

# ═══ 2. plugin_configs 表 + 种子数据 ═══
print('\n===== 2. plugin_configs 表 =====')
try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    check('plugin_configs 表存在', 'plugin_configs' in tables,
          f'表列表 (前20): {tables[:20]}')
    if 'plugin_configs' in tables:
        rows = conn.execute(
            "SELECT key, value FROM plugin_configs WHERE plugin_name='chatbot'"
        ).fetchall()
        cfg = {r['key']: r['value'] for r in rows}
        check(f'chatbot 种子配置已写入', len(cfg) > 0,
              f'配置: {json.dumps(cfg, ensure_ascii=False, indent=2)}')
        if cfg:
            check('title 配置存在', 'title' in cfg,
                  f'title = {cfg.get("title", "N/A")}')
            check('enabled 配置存在', 'enabled' in cfg,
                  f'enabled = {cfg.get("enabled", "N/A")}')
    conn.close()
except Exception as e:
    check('plugin_configs 表', False, str(e))

# ═══ 3. agent_matrix 表 & Kai Assistant ═══
print('\n===== 3. Agent 矩阵 =====')
try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if 'agent_matrix' in tables:
        row = conn.execute(
            "SELECT name, role_type, domain, provider, model_name, "
            "substr(system_prompt,1,80) as prompt_preview, is_active "
            "FROM agent_matrix WHERE name=? AND role_type=?",
            ('Kai Assistant', 'sub')
        ).fetchone()
        if row:
            d = dict(row)
            check('Kai Assistant 已注册', True,
                  json.dumps(d, ensure_ascii=False, indent=2))
            check('Agent 名称正确', d['name'] == 'Kai Assistant')
            check('is_active 已启用', d['is_active'] == 1)
        else:
            check('Kai Assistant (sub 角色)', False,
                  '未找到 name="Kai Assistant" role_type="sub" 的记录')
    else:
        check('agent_matrix 表存在', False)
    conn.close()
except Exception as e:
    check('Agent 矩阵', False, str(e))

# ═══ 4. 聊天 API 路由检查 ═══
print('\n===== 4. 聊天 API 路由 =====')
try:
    from platform.routes.api_v1 import api_v1_bp
    from flask import Flask as _F
    chat_app = _F(__name__)
    chat_app.register_blueprint(api_v1_bp)
    chat_rules = [r.rule for r in chat_app.url_map.iter_rules() if 'chat' in r.rule]
    check(f'聊天 API 路由已注册', len(chat_rules) > 0,
          '\n'.join(chat_rules))
except Exception as e:
    check('聊天 API 路由', False, str(e))

# ═══ 5. Site 服务插件 Manager ═══
print('\n===== 5. Site 服务插件管理器 =====')
try:
    from flask import Flask
    from plugin_manager.manager import PluginManager
    site_app = Flask(__name__)
    site_app.plugins_dir = os.path.join(BASE, 'plugins')
    pm_site = PluginManager(site_app)
    site_plugins = pm_site.list_plugins()
    site_names = [p.identifier for p in site_plugins]
    check('Site PluginManager 初始化成功', True)
    check('chatbot 插件在 Site 中已注册', 'chatbot' in site_names,
          f'Site 已注册: {site_names}')
except Exception as e:
    import traceback
    check('Site 服务插件管理器', False, f'{e}\n{traceback.format_exc()}')

# ═══ 6. 再次确认数据库配置 ═══
print('\n===== 6. chatbot 数据库配置 =====')
try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT key, value FROM plugin_configs WHERE plugin_name='chatbot'"
    ).fetchall()
    cfg = {r['key']: r['value'] for r in rows}
    check('chatbot 数据库配置可读取', len(cfg) > 0,
          f'共 {len(cfg)} 个配置项: {json.dumps(cfg, ensure_ascii=False)}')
    conn.close()
except Exception as e:
    check('chatbot 数据库配置', False, str(e))

print('\n' + '=' * 50)
print(f'测试结果: ✅ {passed} 通过 | ❌ {failed} 失败 | 共计 {passed+failed} 项')
print('=' * 50)

sys.exit(1 if failed > 0 else 0)
