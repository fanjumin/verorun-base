"""Admin 启动入口"""

import os as _os
import sys
import json

# ── 在一切之前先初始化环境 ──
# 确保根目录在路径中
_project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
_os.chdir(_project_root)

# ── 加载 i18n（必须在所有业务模块之前） ──
try:
    from i18n import init_i18n
    init_i18n()
    print(f'[i18n] ✅ 多语言初始化完成')
except Exception:
    print(f'[i18n] ⚠️ 多语言初始化失败，使用默认语言')
    import builtins
    builtins.__dict__['_'] = lambda s: s

# ── 现在导入 Flask 和全局模块 ──
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ── 导入应用模块 ──
from models import db as _db, init_db as _init_db, User, Product
from admin.routes import admin_bp
from admin.models import init_admin_db
from admin.routes.plugin import plugin_bp
from plugin_manager import PluginManager

# ===== 创建 Flask 应用 =====
app = Flask(__name__,
            template_folder=_os.path.join(_project_root, 'admin', 'templates'),
            static_folder=_os.path.join(_project_root, 'admin', 'static'))

# ===== 密钥配置 =====
app.secret_key = 'super-secret-key-12345'
app.config['SECRET_KEY'] = 'super-secret-key-12345'
app.config['SESSION_COOKIE_NAME'] = 'admin_session'
app.config['SESSION_COOKIE_PATH'] = '/admin'
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# ===== CORS =====
CORS(app, supports_credentials=True, resources={
    r'/admin/*': {
        'origins': ['https://easykai.cn', 'https://www.easykai.cn',
                    'https://platform.easykai.cn', 'https://agent.easykai.cn',
                    'http://localhost:8084', 'http://127.0.0.1:8084',
                    'http://localhost:3000', 'http://127.0.0.1:3000'],
        'supports_credentials': True
    }
})

# ===== 限流器 =====
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# ===== 数据库 =====
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{_project_root}/instance/verorun.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

_db.init_app(app)

# ===== 注册蓝图 =====
app.register_blueprint(admin_bp, url_prefix='/admin')

# ===== 静态文件 =====
@app.route('/admin/assets/<path:filename>')
def admin_assets(filename):
    return send_from_directory(
        _os.path.join(app.root_path, 'static', 'assets'), filename)

# ===== 入口页 =====
@app.route('/')
def index():
    return """
    <html><body style="background:#0f0f1a;color:#fff;font-family:sans-serif;
    display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
    <div style="text-align:center">
    <h1 style="font-size:2.5rem;margin-bottom:0.5rem;background:linear-gradient(135deg,#667eea,#764ba2);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">VeroRun Admin</h1>
    <p style="color:#888;font-size:1.1rem;">管理后台 · 版本 0.10.1</p>
    <a href="/admin" style="display:inline-block;margin-top:1.5rem;padding:0.75rem 2rem;
    background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;text-decoration:none;
    border-radius:8px;font-weight:600;">进入管理后台</a>
    </div></body></html>
    """

# ===== 健康检查 =====
@app.route('/health')
def health():
    return {'status': 'ok', 'service': 'admin', 'version': '0.10.1'}

# ===== 创建表 =====
with app.app_context():
    _init_db()
    init_admin_db()

# ===== 健康巡检 API =====
try:
    from health_check.routes import health_bp
    app.register_blueprint(health_bp, url_prefix='/admin')
    print(f'[HealthCheck] ✅ 健康巡检已注册')
    print(f'[HealthCheck] 📋 API: /admin/health/*')
except Exception as e:
    print(f'[HealthCheck] ⚠️ 健康巡检注册失败: {e}')

# ===== PluginManager（新插件系统）=====
try:
    app.version = '0.10.1'
    app.plugins_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'plugins')
    pm = PluginManager(app)
    app.register_blueprint(plugin_bp)
    print(f'[PluginManager] ✅ 管理 API 蓝图已注册 (/admin/plugins/*)')
except Exception as e:
    print(f'[PluginManager] ❌ 初始化失败: {e}')
    import traceback
    traceback.print_exc()

# ===== 自动化调度系统 (Cron + Workflow) =====
sys.path.append(_os.path.join(_os.path.dirname(__file__), '..', 'orchestrator'))
try:
    from orchestrator.routes import init_automation
    sched, worker = init_automation(app)
    app.config['AUTOMATION_SCHEDULER'] = sched
    print(f'[Automation] ✅ 调度系统已初始化')
except Exception as e:
    print(f'[Automation] ⚠️ 调度初始化失败: {e}')

# ===== 启动 =====
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8084, debug=True)
