#!/usr/bin/env python3
# VeroRon 维洛智能 (verorun.com / verorun.cn)
# 版权所有 (c) 2026 樊聚民 (fanjumin). All Rights Reserved.

"""Site — Official Website Portal (端口 8081)"""

import sys, os
# ═══ ENSURE stdlib platform is cached BEFORE project platform/ dir shadows it ═══
import platform as _stdlib_platform
_ = _stdlib_platform.system
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'auth-center'))
from services.deployment_config import deploy
from services.brand_service import get_brand_settings
from services.notification_service import get_unread_count, mark_read
# ══ routes 包名冲突处理 ══
from auth_blueprint import register_auth
from routes.subscription import sub_bp
from routes.douyin_miniprogram import douyin_mp_bp

# 移除 auth-center sys.path
_auth_center_norm = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'auth-center'))
sys.path = [p for p in sys.path if os.path.normpath(p) != _auth_center_norm]
_platform_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'platform')
if _platform_dir not in sys.path:
    sys.path.insert(0, _platform_dir)
sys.modules.pop('routes', None)

from routes.shop_public import shop_public_bp

import logging
logging.basicConfig(level=logging.DEBUG, filename='F:\\Sites\\VeroRun\\site\\site_error.log', filemode='w',
                    format='%(asctime)s %(levelname)s %(message)s')
_werk_handler = logging.FileHandler('F:\\Sites\\VeroRun\\site\\site_error.log', mode='a')
_werk_handler.setLevel(logging.DEBUG)
logging.getLogger('werkzeug').addHandler(_werk_handler)

from flask import (Flask, request, jsonify, render_template,
                   send_from_directory, redirect, Response, make_response, abort)
from cms_public import cms_bp
from models.cms import init_cms_tables
from models import get_db
import json
import time as _time
import secrets

app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

# 扩展模板搜索路径，支持插件模板
import jinja2
SITE_ADS_STATIC = os.path.join(os.path.dirname(__file__), '..', 'plugins', 'ads', 'static')
app.jinja_loader = jinja2.ChoiceLoader([
    app.jinja_loader,
    jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), '..', 'plugins', 'ads', 'templates')),
])

# ══ 子域名识别中间件 ══
from middleware.site_domain_middleware import resolve_current_site
app.before_request(resolve_current_site)


@app.context_processor
def inject_deploy():
    return dict(deploy=deploy)


@app.context_processor
def inject_site_context():
    """注入 current_site / current_domain 到所有模板"""
    return {
        'current_site': getattr(g, 'current_site', None),
        'current_domain': getattr(g, 'current_domain', None),
    }


# ══ i18n ══
from i18n import _, get_lang, get_all_translations

@app.context_processor
def inject_i18n():
    return {'_': _, 'LANG': get_lang(), 'translations': get_all_translations()}
app.jinja_env.globals['_'] = _


# ══ Rate limiter for captcha ══
_captcha_rate_limit = {}

def _check_rate_limit(key, max_per_minute=10):
    now = _time.time()
    window = 60.0
    if key not in _captcha_rate_limit:
        _captcha_rate_limit[key] = []
    _captcha_rate_limit[key] = [t for t in _captcha_rate_limit[key] if now - t < window]
    if len(_captcha_rate_limit[key]) >= max_per_minute:
        return False
    _captcha_rate_limit[key].append(now)
    return True


# ══ CSP ══
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https://cdn.jsdelivr.net; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none';"
    )
    return response


# AnalyticsMiddleware 仅在 Admin 服务启用，避免多进程 SQLite 写锁竞争
# from analytics.middleware import AnalyticsMiddleware
# AnalyticsMiddleware(app, service_name="site")
app.config['TEMPLATES_AUTO_RELOAD'] = True

import traceback as _tb

@app.errorhandler(500)
def handle_500(e):
    app.logger.error('500 ERROR on %s: %s', request.path, e)
    app.logger.error('Traceback:\n%s', ''.join(_tb.format_exc()))
    return "500 Error: " + str(e) + "\n\n" + ''.join(_tb.format_exc()), 500

# ── PluginManager ──
try:
    from plugin_manager.manager import PluginManager
    app.plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plugins')
    PluginManager(app)
    print('[PluginManager] ✅ Site 服务插件管理器已初始化')
except Exception as e:
    print(f'[PluginManager] ⚠️ Site 服务初始化失败: {e}')

# ── Blueprint 注册 ──
register_auth(app, exclude_blueprints=['admin', 'cms_admin'])
app.register_blueprint(cms_bp)
app.register_blueprint(sub_bp, name='site_subscription')
app.register_blueprint(shop_public_bp)
app.register_blueprint(douyin_mp_bp)

from routes.site_routes import site_bp, init_site_seeds
app.register_blueprint(site_bp)

init_cms_tables()
init_site_seeds()


# ══ Captcha proxy → admin:8084 (captcha embedded) ══
import urllib.request as _ur

def _proxy_captcha(path, data=None, method='GET'):
    ALLOWED_PATHS = ['/api/captcha/generate', '/api/captcha/verify', '/api/captcha/consume']
    if path not in ALLOWED_PATHS:
        raise ValueError(f'Disallowed captcha proxy path: {path}')
    url = 'http://127.0.0.1:8084' + path
    req = _ur.Request(url, data=data, method=method)
    if data:
        req.add_header('Content-Type', 'application/json')
    resp = _ur.urlopen(req, timeout=5)
    body = resp.read()
    safe_headers = {
        'Content-Type': resp.headers.get('Content-Type', 'application/json'),
    }
    return body, resp.status, safe_headers


@app.route('/api/captcha/generate', methods=['GET'])
def captcha_proxy_generate():
    try:
        return _proxy_captcha('/api/captcha/generate')
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.route('/api/captcha/verify', methods=['POST'])
def captcha_proxy_verify():
    try:
        return _proxy_captcha('/api/captcha/verify', request.get_data())
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.route('/api/captcha/consume', methods=['POST'])
def captcha_proxy_consume():
    try:
        return _proxy_captcha('/api/captcha/consume', request.get_data())
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.route('/puzzle-captcha.js')
def site_puzzle_js():
    try:
        req = _ur.Request('http://127.0.0.1:8084/puzzle-captcha.js')
        resp = _ur.urlopen(req, timeout=5)
        return resp.read(), resp.status, {'Content-Type': 'application/javascript'}
    except:
        return '', 404


@app.route('/puzzle-captcha.css')
def site_puzzle_css():
    try:
        req = _ur.Request('http://127.0.0.1:8084/puzzle-captcha.css')
        resp = _ur.urlopen(req, timeout=5)
        return resp.read(), resp.status, {'Content-Type': 'text/css'}
    except:
        return '', 404


# ══════════════════════════════════════════════════════════════
# Helper functions
# ══════════════════════════════════════════════════════════════

def get_domain_config():
    """获取域名和Cookie配置信息"""
    host = request.headers.get('Host', '')
    try:
        brand = get_brand_settings()
        site_domain = brand.get('site_domain', '').strip()
    except Exception:
        site_domain = ''
    if not site_domain:
        site_domain = os.environ.get('DEPLOY_DOMAIN', '')
    host_name = host.split(':')[0].lower()
    cookie_domain = ('.' + site_domain) if site_domain else ('.' + host_name)
    platform_domain = f'platform.{site_domain}' if site_domain else f'platform.{host_name}'
    is_platform_host = (host_name == platform_domain or host_name == 'localhost'
                        or host_name.startswith('127.0.0.1') or host_name.startswith('192.168.'))
    return {
        'host_name': host_name,
        'site_domain': site_domain,
        'cookie_domain': cookie_domain,
        'platform_domain': platform_domain,
        'is_platform_host': is_platform_host,
    }


def handle_oauth_callback(domain_config):
    """处理OAuth登录回调：验证token、设置Cookie、重定向"""
    url_token = request.args.get('token')
    if not url_token:
        return None
    from services.jwt_service import validate_token
    payload = validate_token(url_token)
    if not payload:
        return None
    from urllib.parse import urlencode
    other_params = {k: v for k, v in request.args.items() if k != 'token'}
    target = request.path
    if other_params:
        target += '?' + urlencode(other_params, doseq=True)
    resp = make_response(redirect(target))
    is_secure = request.scheme == 'https'
    resp.set_cookie('sso_token', url_token, domain=domain_config['cookie_domain'],
                    path='/', max_age=604800, samesite='Lax', secure=is_secure, httponly=True)
    return resp


def get_site_plans():
    """加载定价方案（site_% 或 deploy_%）"""
    site_plans = []
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT plan_key, name, description, price_year, price_month, tier, features_json, sort_order "
                "FROM subscription_plans WHERE is_active=1 "
                "AND (plan_key LIKE 'site_%' OR plan_key LIKE 'deploy_%') ORDER BY sort_order ASC"
            ).fetchall()
        for r in rows:
            d = dict(r)
            d['price_year'] = d['price_year'] // 100
            d['price_month'] = d['price_month'] // 100
            try:
                d['features'] = json.loads(d.get('features_json', '[]'))
            except Exception:
                d['features'] = []
            site_plans.append(d)
    except Exception as e:
        print(f'[Site plans loading] error: {e}')
    return site_plans


def get_live_stats():
    """获取实时统计数据（代理、用户、文章、动态、公会）"""
    live_stats = {'agents': 0, 'users': 0, 'posts': 0, 'feeds': 0, 'guilds': 0}
    try:
        with get_db() as conn:
            live_stats['agents'] = conn.execute("SELECT COUNT(*) FROM agent_profiles").fetchone()[0]
            live_stats['users'] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            live_stats['posts'] = conn.execute("SELECT COUNT(*) FROM cms_posts WHERE is_published=1").fetchone()[0]
            live_stats['feeds'] = conn.execute("SELECT COUNT(*) FROM agent_feeds").fetchone()[0]
            live_stats['guilds'] = conn.execute("SELECT COUNT(*) FROM guilds").fetchone()[0]
    except Exception as e:
        print(f'[Live stats loading] error: {e}')
    return live_stats


def get_header_nav(site='platform'):
    """加载头部导航菜单"""
    nav_items = []
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT title, url FROM header_nav WHERE site=? AND is_enabled=1 ORDER BY sort_order ASC",
                (site,)
            ).fetchall()
            nav_items = [dict(r) for r in rows]
    except Exception as e:
        print(f'[Header nav loading] error: {e}')
    return nav_items


def check_login_state():
    """检查用户登录状态（从Cookie或URL token）"""
    try:
        from services.jwt_service import validate_token
        token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token')
        if token and validate_token(token):
            return True
    except Exception as e:
        print(f'[CMS auth check] error: {e}')
    return False


def load_footer_data():
    """加载页脚数据：社交媒体链接、联系邮箱、页脚导航、合作伙伴链接"""
    social_links = []
    contact_email = ''
    footer_sections = {}
    footer_nav = []
    footer_articles = []
    partner_links = []

    try:
        with get_db() as conn:
            rows = conn.execute(
                'SELECT platform_name, icon_type, icon_value, url, hover_text '
                'FROM social_media_links WHERE is_enabled=1 ORDER BY display_order ASC'
            ).fetchall()
            social_links = [dict(r) for r in rows]

            email_row = conn.execute(
                "SELECT value FROM system_config WHERE key='contact_email'"
            ).fetchone()
            if email_row and email_row['value']:
                contact_email = email_row['value'].strip()

            rows = conn.execute(
                "SELECT section, title, url FROM footer_links WHERE is_enabled=1 ORDER BY section ASC, sort_order ASC"
            ).fetchall()
            for r in rows:
                sec = r['section']
                if sec not in footer_sections:
                    footer_sections[sec] = []
                footer_sections[sec].append({'title': r['title'], 'url': r['url']})

            rows = conn.execute(
                "SELECT title, url FROM footer_nav WHERE is_enabled=1 ORDER BY sort_order ASC"
            ).fetchall()
            footer_nav = [dict(r) for r in rows]

            rows = conn.execute(
                "SELECT title, url FROM footer_articles WHERE is_enabled=1 ORDER BY sort_order ASC"
            ).fetchall()
            footer_articles = [dict(r) for r in rows]

            rows = conn.execute(
                "SELECT name, url, icon_url FROM partner_links WHERE is_enabled=1 ORDER BY sort_order ASC"
            ).fetchall()
            partner_links = [dict(r) for r in rows]
    except Exception as e:
        print(f'[Footer data loading] error: {e}')

    return {
        'social_links': social_links,
        'contact_email': contact_email,
        'footer_sections': footer_sections,
        'footer_nav': footer_nav,
        'footer_articles': footer_articles,
        'partner_links': partner_links,
    }


# ══════════════════════════════════════════════════════════════
# Routes — Official Website
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """营销首页 — 未登录显示官网首页，已登录重定向到平台控制台"""
    # 1. 处理 OAuth 回调
    if request.args.get('code'):
        domain_config = get_domain_config()
        oauth_response = handle_oauth_callback(domain_config)
        if oauth_response:
            return oauth_response

    # 2. 检查是否已登录
    from services.jwt_service import validate_token
    token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    if token:
        payload = validate_token(token)
        if payload:
            # 已登录 → 重定向到平台控制台
            platform_url = deploy.url('platform')
            return redirect(f'{platform_url}/?token={token}')

    # 3. 未登录 → 官网首页
    site_plans = get_site_plans()
    return render_template('public_home.html', site_plans=site_plans)


@app.route('/ai-matrix')
def ai_matrix_page():
    """AI矩阵介绍页"""
    site_plans = get_site_plans()
    return render_template('services.html', site_plans=site_plans)


@app.route('/docs')
def docs_page():
    """帮助文档页"""
    return redirect('/knowledge')


@app.route('/contact')
def contact_page():
    """联系我们 — 跳转关于页"""
    return redirect('/about')


@app.route('/privacy')
def privacy_page():
    """隐私政策页"""
    return redirect('/')


@app.route('/insights')
def insights_page():
    """知识中心/洞察页"""
    return redirect('/knowledge')


@app.route('/start')
def start_page():
    """快速开始页"""
    return render_template('start.html')


@app.route('/api/pricing/calculator-config')
def calculator_config():
    """返回价格计算器配置（从DB读取，零硬编码）"""
    base_setup = 0
    base_renewal = 0
    base_total = 0
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT price_month, price_year FROM subscription_plans WHERE plan_key='deploy_basic' AND is_active=1"
            ).fetchone()
        if row:
            base_renewal = row['price_month'] // 100
            base_total = row['price_year'] // 100
            base_setup = base_total - base_renewal
    except:
        pass

    rules = []
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT rule_key, label, rule_type, options_json FROM pricing_rules WHERE is_active=1 ORDER BY sort_order"
            ).fetchall()
        for r in rows:
            opts = json.loads(r['options_json'])
            for o in opts:
                o['price'] = o['price'] // 100
            rules.append({
                'key': r['rule_key'],
                'label': r['label'],
                'type': r['rule_type'],
                'options': opts,
            })
    except:
        pass

    plan_thresholds = []
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT plan_key, name, price_year FROM subscription_plans "
                "WHERE plan_key LIKE 'site_%' AND is_active=1 ORDER BY sort_order"
            ).fetchall()
        for r in rows:
            plan_thresholds.append({
                'key': r['plan_key'],
                'name': r['name'],
                'max_addon': r['price_year'] // 100 - base_total if base_total else 0,
            })
    except:
        pass

    return jsonify({
        'base': {'setup': base_setup, 'renewal': base_renewal, 'total': base_total},
        'rules': rules,
        'plan_thresholds': plan_thresholds,
    })


@app.route('/pricing', strict_slashes=False)
@app.route('/subscribe')
@app.route('/subscribe/success')
def pricing_page():
    """套餐订阅页面 — /pricing 和 /subscribe 共享"""
    from services.jwt_service import validate_token
    import json

    token = request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    user_info = None
    if token:
        payload = validate_token(token)
        if payload:
            user_info = payload

    try:
        brand = get_brand_settings()
    except:
        brand = None

    plans = []
    try:
        with get_db() as conn:
            rows = conn.execute('SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY sort_order').fetchall()
        for r in rows:
            p = dict(r)
            p['price_month'] = p['price_month'] // 100
            p['price_quarter'] = (p.get('price_quarter', 0) or 0) // 100
            p['price_semi_annual'] = (p.get('price_semi_annual', 0) or 0) // 100
            p['price_year'] = p['price_year'] // 100
            try:
                p['features'] = json.loads(p.get('features_json', '[]'))
            except:
                p['features'] = []
            plans.append(p)
    except Exception as e:
        print(f'[pricing] Error loading plans: {e}')

    return render_template('subscribe.html', plans_json=json.dumps(plans, ensure_ascii=False),
                           brand=brand, user_info=user_info, page='pricing')


@app.route('/login')
def login_page():
    """登录页 — 双栏布局：左=订阅服务 | 右=登录表单"""
    from services.jwt_service import validate_token
    from flask import make_response
    import json

    try:
        brand = get_brand_settings()
        site_domain = brand.get('site_domain', '').strip()
    except:
        site_domain = request.headers.get('Host', '').split(':')[0].lower()
    cd = ('.' + site_domain) if site_domain else ''

    existing_token = request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    if existing_token:
        payload = validate_token(existing_token)
        if payload:
            target = request.args.get('redirect', '')
            if target and target != '/':
                return redirect(target)

    url_token = request.args.get('token')
    if url_token:
        payload = validate_token(url_token)
        if payload:
            target = request.args.get('redirect', '') or '/'
            resp = make_response(redirect(target))
            if cd:
                resp.set_cookie('sso_token', url_token, domain=cd, path='/',
                                max_age=604800, samesite='Lax', secure=True, httponly=True)
            else:
                resp.set_cookie('sso_token', url_token, path='/',
                                max_age=604800, samesite='Lax', secure=True, httponly=True)
            return resp

    plans = []
    try:
        with get_db() as conn:
            rows = conn.execute('SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY sort_order').fetchall()
        for r in rows:
            p = dict(r)
            p['price_month'] = p['price_month'] // 100
            p['price_quarter'] = (p.get('price_quarter', 0) or 0) // 100
            p['price_semi_annual'] = (p.get('price_semi_annual', 0) or 0) // 100
            p['price_year'] = p['price_year'] // 100
            try:
                p['features'] = json.loads(p.get('features_json', '[]'))
            except:
                p['features'] = []
            plans.append(p)
    except:
        pass

    return render_template('login.html', plans=plans, brand=brand)


@app.route('/register')
def register_page():
    return render_template('register.html')


@app.route('/reset-password')
def reset_password_page():
    return render_template('reset_password.html')


@app.route('/enterprise-verify')
def enterprise_verify_page():
    """企业认证页面"""
    brand = get_brand_settings()
    site_name = brand.get('site_name_cn', '') if brand else ''
    return render_template('user_enterprise_verify.html', site_name=site_name)


@app.route('/preview/<slug>')
def preview_article(slug):
    """文章预览路由"""
    from services.jwt_service import validate_token
    from models.cms import get_post_by_slug_preview

    post = get_post_by_slug_preview(slug)
    if not post:
        abort(404)

    if not post.get('is_published'):
        token = request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
        payload = validate_token(token) if token else None
        if not payload:
            return redirect(f'/login?redirect=/preview/{slug}')

    brand = None
    try:
        brand = get_brand_settings()
    except:
        pass

    theme_css_url = None
    try:
        site_domain = brand.get('site_domain', '').strip() if brand else ''
        if site_domain:
            row = get_db().execute("SELECT value FROM cms_settings WHERE key='theme'").fetchone()
            if row and row['value']:
                theme_css_url = f'/static/themes/{row["value"]}/theme.css'
    except:
        pass

    if isinstance(post.get('tags'), str):
        try:
            post['tags'] = json.loads(post['tags'])
        except:
            post['tags'] = []

    return render_template('cms_preview.html', post=post, brand=brand, theme_css_url=theme_css_url)


@app.route('/knowledge')
def knowledge_page():
    guides = []
    ai_tips = []
    articles = []
    insights = []

    try:
        with get_db() as conn:
            rows = conn.execute(
                'SELECT id, title, summary FROM processed_contents WHERE is_published=1 AND content_type=? ORDER BY created_at DESC LIMIT 10',
                ('article',)
            ).fetchall()
            articles = [{'title': r['title'],
                         'description': (r['summary'] or '')[:100] + '...' if r['summary'] and len(r['summary']) > 100 else (r['summary'] or ''),
                         'category': 'guide', 'category_label': '建站指南', 'read_count': 0, 'read_time': '5分钟'}
                        for r in rows]

            rows = conn.execute(
                'SELECT id, title, summary FROM processed_contents WHERE is_published=1 ORDER BY created_at DESC LIMIT 5',
            ).fetchall()
            insights = [{'title': r['title'],
                         'description': (r['summary'] or '')[:80] + '...' if r['summary'] and len(r['summary']) > 80 else (r['summary'] or ''),
                         'icon': '📈', 'category': '行业洞察', 'author': '', 'date': '', 'author_initial': 'A'}
                        for r in rows]
    except Exception as e:
        print(f'[knowledge_page] DB error: {e}')

    if not guides:
        guides = [
            {'icon': '📋', 'title': '快速开始：创建您的第一个网站', 'description': '从注册到上线，只需5分钟即可拥有专业网站'},
            {'icon': '🎨', 'title': '主题定制：打造专属品牌风格', 'description': '选择主题、调整配色、自定义布局'},
            {'icon': '🚀', 'title': 'SEO优化：提升搜索引擎排名', 'description': '关键词优化、Meta标签、内容策略'},
            {'icon': '📊', 'title': '数据分析：追踪网站流量', 'description': '访问统计、用户行为、转化分析'},
        ]

    if not ai_tips:
        ai_tips = [
            {'icon': '💡', 'title': 'AI内容生成', 'description': '利用AI自动生成高质量文章和产品描述'},
            {'icon': '🤖', 'title': '智能客服', 'description': '部署AI聊天机器人提升客户体验'},
            {'icon': '📝', 'title': '文案优化', 'description': 'AI辅助优化营销文案和标题'},
        ]

    if not articles:
        articles = [
            {'title': '2026年AI建站趋势分析', 'description': 'AI技术正在重塑网站建设方式，了解最新趋势和最佳实践',
             'category': 'insight', 'category_label': '行业洞察', 'read_count': 1250, 'read_time': '8分钟'},
            {'title': '如何选择适合的网站主题', 'description': '从行业特性、品牌风格、功能需求三个维度选择主题',
             'category': 'guide', 'category_label': '建站指南', 'read_count': 890, 'read_time': '6分钟'},
            {'title': 'SEO排名提升技巧', 'description': '深度解析搜索引擎优化策略，快速提升网站排名',
             'category': 'seo', 'category_label': 'SEO优化', 'read_count': 2100, 'read_time': '10分钟'},
            {'title': 'AI驱动的内容创作', 'description': '利用大语言模型高效生成高质量内容',
             'category': 'ai', 'category_label': 'AI应用', 'read_count': 1560, 'read_time': '7分钟'},
        ]

    if not insights:
        insights = [
            {'title': 'AI行业发展报告2026', 'description': '深度分析AI技术在各行业的应用现状与未来趋势',
             'icon': '📈', 'category': '行业报告', 'author': '', 'date': '2026-01-15', 'author_initial': ''},
            {'title': '中小企业数字化转型', 'description': '如何利用AI工具实现业务增长和效率提升',
             'icon': '💼', 'category': '企业战略', 'author': '', 'date': '2026-01-12', 'author_initial': ''},
        ]

    return render_template('knowledge.html', guides=guides, ai_tips=ai_tips,
                           articles=articles, insights=insights)


@app.route('/about')
def about_page():
    company = {}
    stats = {}
    values = []
    team = {'members': []}
    process = {'steps': []}
    contact = {'entries': []}

    try:
        brand = get_brand_settings()
        company = {
            'name': brand.get('company_name', ''),
            'description': brand.get('description', ''),
            'story_intro': '我们致力于用AI技术赋能每一个企业',
            'story_title': '创新驱动，智能未来',
            'story_paragraphs': [
                'VeroRon 维洛智能成立于2026年，是一家专注于AI驱动的网站建设和内容管理平台。',
                '通过多智能体协作系统，我们为用户提供从网站搭建、内容生成、SEO优化到数据分析的一站式解决方案。',
                '我们的使命是让AI技术普惠大众，帮助中小企业和个人创业者在数字化时代获得更大的竞争优势。',
            ],
            'copyright': brand.get('copyright', '') or '© 2026 VeroRon 维洛智能 版权所有'
        }

        with get_db() as conn:
            stats['clients'] = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            stats['projects'] = conn.execute('SELECT COUNT(*) FROM cms_posts WHERE is_published=1').fetchone()[0]
            stats['satisfaction'] = 98
            stats['years'] = 1

            contact_email = brand.get('contact_email', '')
            contact['intro'] = '如有任何问题或合作意向，请随时联系我们'
            contact['entries'] = [
                {'icon': '📧', 'label': '电子邮箱', 'val': [contact_email] if contact_email else [deploy.email('support')]},
                {'icon': '📱', 'label': '联系电话', 'val': ['400-888-8888']},
                {'icon': '📍', 'label': '公司地址', 'val': ['江苏省徐州市泉山区软件园']},
            ]
    except Exception as e:
        print(f'[about_page] error: {e}')

    if not values:
        values = [
            {'key': 'innovation', 'icon': '🚀', 'title': '创新引领', 'description': '持续探索AI技术边界，为用户带来前沿体验'},
            {'key': 'customer', 'icon': '💝', 'title': '客户至上', 'description': '以用户需求为核心，提供优质服务'},
            {'key': 'excellence', 'icon': '⭐', 'title': '追求卓越', 'description': '精益求精，打造高品质产品'},
            {'key': 'teamwork', 'icon': '🤝', 'title': '团队协作', 'description': '多元团队，共创价值'},
        ]

    if not team['members']:
        team['intro'] = '汇聚行业精英，打造顶尖团队'
        team['members'] = [
            {'initial': '张', 'name': '张三', 'title': '首席执行官', 'description': '10年互联网行业经验，专注AI创业'},
            {'initial': '李', 'name': '李四', 'title': '首席技术官', 'description': '前大厂技术负责人，深耕AI领域'},
            {'initial': '王', 'name': '王五', 'title': '产品总监', 'description': '产品设计专家，注重用户体验'},
            {'initial': '赵', 'name': '赵六', 'title': '市场总监', 'description': '品牌营销专家，推动增长策略'},
        ]

    if not process['steps']:
        process['intro'] = '简单四步，快速上线'
        process['steps'] = [
            {'title': '需求沟通', 'description': '了解您的业务需求和目标'},
            {'title': '方案设计', 'description': '定制专属网站建设方案'},
            {'title': '开发实施', 'description': '专业团队高效开发'},
            {'title': '上线运维', 'description': '持续优化，保驾护航'},
        ]

    return render_template('about.html', company=company, stats=stats, values=values,
                           team=team, process=process, contact=contact)


@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "site", "version": "1.0.0"})


@app.route('/avatar/gen/<path:seed>')
def generated_avatar(seed):
    """生成默认首字母头像 SVG"""
    from services.avatar_service import generate_initials_svg
    svg = generate_initials_svg(seed)
    return Response(svg, mimetype='image/svg+xml', headers={'Cache-Control': 'public, max-age=86400'})


@app.route('/api/social-links')
def public_social_links():
    """公开 API：页脚社媒图标列表"""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id, url, icon_url, platform, sort_order '
            'FROM social_links WHERE is_active=1 ORDER BY sort_order ASC, id ASC'
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@app.route('/api/social-media')
def public_social_media():
    """公开 API：社媒图标列表（新表）"""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id, platform_name, icon_type, icon_value, url, hover_text '
            'FROM social_media_links WHERE is_enabled=1 ORDER BY display_order ASC, id ASC'
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@app.route('/api/interests')
def public_interests():
    """公开 API：兴趣标签列表"""
    search = request.args.get('search', '').strip()
    with get_db() as conn:
        if search:
            rows = conn.execute(
                'SELECT id, name, category, is_hot FROM interests WHERE is_active=1 AND is_hot=1 AND name LIKE ? ORDER BY category, sort_order, id',
                ('%'+search+'%',)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT id, name, category, is_hot FROM interests WHERE is_active=1 AND is_hot=1 ORDER BY category, sort_order, id'
            ).fetchall()
    grouped = {}
    for r in rows:
        d = dict(r)
        cat = d['category']
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(d)
    return jsonify({'success': True, 'data': grouped, 'categories': list(grouped.keys())})


@app.route('/static/media/<path:filename>')
def static_media(filename):
    """服务媒体库文件"""
    media_dir = os.path.join(os.path.dirname(__file__), '..', 'admin', 'static', 'media')
    return send_from_directory(media_dir, filename)


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), '..', 'platform', 'static'), filename)


@app.route('/static/ads/<path:filename>')
def ads_static_files(filename):
    """广告插件静态文件"""
    return send_from_directory(SITE_ADS_STATIC, filename)


# ══ 主题系统 ══
THEMES_ROOT = os.path.join(os.path.dirname(__file__), '..', 'themes')


def _get_active_theme_slug_site():
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'auth-center', 'routes'))
        from theme_admin import get_active_theme_slug_for_site
        return get_active_theme_slug_for_site('main')
    except Exception:
        return None


_theme_tpl_dir = None
_active_slug = _get_active_theme_slug_site()
if _active_slug:
    _candidate = os.path.join(THEMES_ROOT, _active_slug, 'templates')
    if os.path.isdir(_candidate):
        _theme_tpl_dir = _candidate
if _theme_tpl_dir:
    from jinja2 import ChoiceLoader, FileSystemLoader
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(_theme_tpl_dir),
        app.jinja_loader,
    ])


@app.context_processor
def inject_theme():
    slug = _get_active_theme_slug_site()
    result = {}
    if slug and slug != 'default':
        result['theme_css_url'] = '/themes/{}/theme.css'.format(slug)
    else:
        result['theme_css_url'] = None
    try:
        result['brand'] = get_brand_settings()
    except:
        result['brand'] = None
    return result


@app.route('/themes/<slug>/<path:filename>')
def serve_theme_file(slug, filename):
    import re
    safe_slug = re.sub(r'[^a-z0-9\-]', '', slug.lower())
    if safe_slug != slug:
        return 'Invalid slug', 400
    theme_static = os.path.join(THEMES_ROOT, slug)
    if not os.path.isdir(theme_static):
        return 'Theme not found', 404
    return send_from_directory(theme_static, filename)


@app.route('/chat-widget-embed')
def chat_widget_embed():
    return '<html><body style="background:#0a0a0f;color:#e0e0f0;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif">客服模块加载中...</body></html>'


@app.route('/api/video/homepage')
def api_video_homepage():
    try:
        import requests as _req
        resp = _req.get('http://127.0.0.1:8084/admin/media/video/homepage', timeout=5)
        return resp.json()
    except Exception:
        return {'success': True, 'data': None}


if __name__ == '__main__':
    import flask.cli
    flask.cli.show_server_banner = lambda *_, **__: None
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
