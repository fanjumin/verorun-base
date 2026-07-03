#!/usr/bin/env python3
# VeroRon 维洛智能 (verorun.com / verorun.cn)
# 版权所有 (c) 2026 樊聚民 (fanjumin). All Rights Reserved.

"""
Health Monitor — Flask API 路由
================================
提供健康巡检的 REST API + 管理后台页面。

注册方式：
    from easykai_health import health_bp
    app.register_blueprint(health_bp)

API 端点:
  GET   /admin/health/              — 管理后台页面
  GET   /admin/health/api/status    — 当前状态仪表盘
  POST  /admin/health/api/run       — 触发手动巡检
  GET   /admin/health/api/history   — 巡检历史列表
  GET   /admin/health/api/history/<run_id> — 某次巡检详情
  GET   /admin/health/api/checks    — 检查项列表
  PUT   /admin/health/api/checks/<id> — 更新检查项配置
  GET   /admin/health/api/trend     — 健康趋势数据
  GET   /admin/health/api/alerts    — 告警历史
  POST  /admin/health/api/alerts/read — 标记告警已读
  GET   /admin/health/api/export    — 导出巡检报告JSON
"""

import os, sys, json, time, threading
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))
sys.path.insert(0, os.path.join(BASE_DIR, '..'))
from i18n import _

from . import models as m
from .checkers import CheckerRegistry
from .alerter import evaluate_and_alert

health_bp = Blueprint('health', __name__,
                      url_prefix='/admin/health',
                      template_folder='templates',
                      static_folder='static',
                      static_url_path='/admin/health/static')


# ─── 鉴权辅助 ──────────────────────────────────────────────────────────────

def _require_admin():
    from services.jwt_service import validate_token
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('sso_token') or request.headers.get('X-Token')
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        return None
    return payload


# ─── 巡检执行引擎 ──────────────────────────────────────────────────────────

def run_health_check(trigger_type='manual', trigger_info='', check_keys=None):
    """
    执行一次完整巡检。
    check_keys: 如果指定，只运行特定的检查项（如 ['core_api', 'database']）
    返回 run_id
    """
    with m.get_db() as conn:
        # 获取所有启用的检查项
        if check_keys:
            rows = conn.execute(
                'SELECT * FROM health_checks WHERE is_active=1 AND check_key IN ({})'.format(
                    ','.join('?' * len(check_keys))
                ), check_keys
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM health_checks WHERE is_active=1 ORDER BY sort_order'
            ).fetchall()

        total = len(rows)
        # 创建巡检批次
        conn.execute(
            "INSERT INTO check_runs (trigger_type, trigger_info, total_checks, status) VALUES (?,?,?,'running')",
            (trigger_type, trigger_info, total)
        )
        run_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']
        conn.commit()

    # 逐个执行检查
    results = []
    passed = warnings = errors = 0
    total_duration = 0

    for row in rows:
        check = dict(row)
        config = json.loads(check.get('config', '{}'))
        checker = CheckerRegistry.get_instance(check['check_key'], config)

        if not checker:
            # 无对应检查器，标记为警告
            result = {
                'check_id': check['id'],
                'check_key': check['check_key'],
                'check_name': _(check['name']),
                'category': check['category'],
                'status': 'warning',
                'response_time_ms': 0,
                'message': _('无检查器实现: {key}').format(key=check['check_key']),
                'detail': '{}',
            }
        else:
            try:
                cr = checker.run()
                result = {
                    'check_id': check['id'],
                    'check_key': check['check_key'],
                    'check_name': _(check['name']),
                    'category': check['category'],
                    'status': cr.status,
                    'response_time_ms': cr.response_time_ms,
                    'message': cr.message,
                    'detail': json.dumps(cr.detail, ensure_ascii=False),
                }
            except Exception as e:
                result = {
                    'check_id': check['id'],
                    'check_key': check['check_key'],
                    'check_name': _(check['name']),
                    'category': check['category'],
                    'status': 'error',
                    'response_time_ms': 0,
                    'message': _('检查器异常: {err}').format(err=e),
                    'detail': json.dumps({'error': str(e)}, ensure_ascii=False),
                }

        total_duration += result['response_time_ms']
        if result['status'] == 'passed':
            passed += 1
        elif result['status'] == 'warning':
            warnings += 1
        else:
            errors += 1
        results.append(result)

    # 保存结果到数据库
    with m.get_db() as conn:
        for r in results:
            conn.execute(
                'INSERT INTO check_history (run_id, check_id, check_key, check_name, category, '
                'status, response_time_ms, message, detail) VALUES (?,?,?,?,?,?,?,?,?)',
                (run_id, r['check_id'], r['check_key'], r['check_name'], r['category'],
                 r['status'], r['response_time_ms'], r['message'], r['detail'])
            )
        # 更新批次
        conn.execute(
            'UPDATE check_runs SET passed=?, warnings=?, errors=?, duration_ms=?, '
            "status='completed', summary=? WHERE id=?",
            (passed, warnings, errors, total_duration,
             f'✅ {passed} ⚠️ {warnings} ❌ {errors}', run_id)
        )
        conn.commit()

    # 告警评估
    try:
        evaluate_and_alert(run_id, results)
    except Exception as e:
        print(f'[HealthCheck] 告警评估失败: {e}')

    # 更新每日趋势
    _update_daily_trend()

    return run_id


def _update_daily_trend():
    """更新每日健康趋势统计"""
    today = datetime.now().strftime('%Y-%m-%d')
    with m.get_db() as conn:
        stats = conn.execute(
            "SELECT COUNT(*) as total, "
            "COALESCE(SUM(CASE WHEN status='passed' THEN 1 ELSE 0 END), 0) as passed, "
            "COALESCE(SUM(CASE WHEN status='warning' THEN 1 ELSE 0 END), 0) as warnings, "
            "COALESCE(SUM(CASE WHEN status='error' THEN 1 ELSE 0 END), 0) as errors, "
            "COALESCE(AVG(response_time_ms), 0) as avg_ms "
            "FROM check_history WHERE date(checked_at)=?",
            (today,)
        ).fetchone()

        if stats and stats['total'] > 0:
            total = stats['total']
            score = 100.0
            if total > 0:
                score = ((stats['passed'] * 100) + (stats['warnings'] * 60)) / total
                score = round(score, 1)

            conn.execute(
                "INSERT OR REPLACE INTO health_trend (date, total_checks, passed, warnings, errors, avg_response_ms, health_score) "
                "VALUES (?,?,?,?,?,?,?)",
                (today, stats['total'], stats['passed'], stats['warnings'], stats['errors'],
                 int(stats['avg_ms']), score)
            )
            conn.commit()


# ═════════════════════════════════════════════════════════════════════════
# API 端点
# ═════════════════════════════════════════════════════════════════════════

@health_bp.route('/')
def health_page():
    """管理后台页面（iframe 嵌入模式，同 analytics）"""
    admin = _require_admin()
    if not admin:
        return '', 401
    return render_template('health.html')


@health_bp.route('/api/status')
def api_status():
    """获取当前巡检状态（最新一次巡检结果 + 总览统计）"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    latest = m.get_latest_status()
    unread_alerts = m.get_unread_alert_count()

    # 各分类状态统计
    categories = {}
    if latest and latest.get('items'):
        for item in latest['items']:
            cat = item.get('category', 'other')
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0, 'warning': 0, 'error': 0}
            categories[cat]['total'] += 1
            categories[cat][item['status']] += 1

    return jsonify({
        'success': True,
        'data': {
            'latest_run': latest,
            'categories': categories,
            'unread_alerts': unread_alerts,
        }
    })


@health_bp.route('/api/run', methods=['POST'])
def api_run():
    """触发手动巡检"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    check_keys = request.json.get('checks') if request.is_json else None

    # 异步执行（避免客户端等待）
    def _async_run():
        run_health_check(trigger_type='manual', trigger_info=f'admin:{admin["user_id"]}',
                         check_keys=check_keys)

    t = threading.Thread(target=_async_run, daemon=True)
    t.start()

    return jsonify({'success': True, 'message': _('巡检已启动，请稍后查看结果')})


@health_bp.route('/api/history')
def api_history():
    """巡检历史列表"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 20, type=int), 100)
    offset = (page - 1) * limit
    trigger_filter = request.args.get('trigger', '')

    with m.get_db() as conn:
        where = ''
        params = []
        if trigger_filter:
            where = 'WHERE trigger_type=?'
            params.append(trigger_filter)

        total = conn.execute(
            f'SELECT COUNT(*) as c FROM check_runs {where}', params
        ).fetchone()['c']

        rows = conn.execute(
            f'SELECT * FROM check_runs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?',
            params + [limit, offset]
        ).fetchall()

    return jsonify({
        'success': True,
        'data': {
            'total': total,
            'page': page,
            'limit': limit,
            'runs': [dict(r) for r in rows],
        }
    })


@health_bp.route('/api/history/<int:run_id>')
def api_history_detail(run_id):
    """某次巡检的详细结果"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    with m.get_db() as conn:
        run = conn.execute('SELECT * FROM check_runs WHERE id=?', (run_id,)).fetchone()
        if not run:
            return jsonify({'success': False, 'error': _('巡检记录不存在')}), 404
        items = m.get_history_for_run(run_id)

    return jsonify({
        'success': True,
        'data': {
            'run': dict(run),
            'items': items,
        }
    })


@health_bp.route('/api/checks')
def api_checks():
    """获取检查项列表"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    with m.get_db() as conn:
        rows = conn.execute('SELECT * FROM health_checks ORDER BY sort_order').fetchall()

    return jsonify({
        'success': True,
        'data': {
            'checks': [dict(r) for r in rows],
        }
    })


@health_bp.route('/api/checks/<int:check_id>', methods=['PUT', 'DELETE'])
def api_update_check(check_id):
    """更新或删除检查项配置"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    if request.method == 'DELETE':
        with m.get_db() as conn:
            conn.execute('DELETE FROM health_checks WHERE id=?', (check_id,))
            conn.commit()
        return jsonify({'success': True, 'message': '已删除'})

    data = request.json
    if not data:
        return jsonify({'success': False, 'error': _('无效数据')}), 400

    with m.get_db() as conn:
        check = conn.execute('SELECT * FROM health_checks WHERE id=?', (check_id,)).fetchone()
        if not check:
            return jsonify({'success': False, 'error': _('检查项不存在')}), 404

        updates = []
        params = []
        for field in ('is_active', 'name', 'description', 'severity', 'sort_order'):
            if field in data:
                updates.append(f'{field}=?')
                params.append(data[field])
        if 'config' in data and isinstance(data['config'], dict):
            updates.append('config=?')
            params.append(json.dumps(data['config'], ensure_ascii=False))

        updates.append("updated_at=datetime('now')")
        params.append(check_id)

        conn.execute(
            f'UPDATE health_checks SET {", ".join(updates)} WHERE id=?',
            params
        )
        conn.commit()

    return jsonify({'success': True, 'message': _('已更新')})


@health_bp.route('/api/trend')
def api_trend():
    """健康趋势数据"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    days = request.args.get('days', 7, type=int)
    if days not in (7, 14, 30):
        days = 7

    trend = m.get_health_trend(days)

    return jsonify({
        'success': True,
        'data': {
            'days': days,
            'trend': trend,
        }
    })


@health_bp.route('/api/checkers/registry')
def api_checkers_registry():
    """获取所有已注册检查器元数据（用于管理界面）"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    registered = CheckerRegistry.list_registered()

    # 获取当前 DB 中的检查项配置
    with m.get_db() as conn:
        db_checks = conn.execute('SELECT check_key, is_active, config, sort_order FROM health_checks').fetchall()
    db_map = {r['check_key']: dict(r) for r in db_checks}

    # 合并信息
    merged = []
    for info in registered:
        ck = info['check_key']
        db_info = db_map.get(ck, {})
        merged.append({
            **info,
            'is_active': db_info.get('is_active', 1) if db_info else 0,
            'in_db': ck in db_map,
        })

    # 也标记已注册但未在 DB 中的
    registered_keys = {r['check_key'] for r in registered}
    for ck, db_info in db_map.items():
        if ck not in registered_keys:
            merged.append({
                'check_key': ck,
                'name': db_info.get('name', ck),
                'category': 'unknown',
                'severity': 'warning',
                'description': '已在数据库中但无对应检查器实现',
                'in_db': True,
                'is_active': db_info.get('is_active', 0),
            })

    return jsonify({
        'success': True,
        'data': {
            'registered': merged,
            'total': len(merged),
            'registry_count': len(registered),
        }
    })


@health_bp.route('/api/checkers/register', methods=['POST'])
def api_register_check():
    """从管理后台注册一个新检查项（写入 DB + 检查是否已有加载的 checker 类）"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.json or {}
    check_key = data.get('check_key', '').strip()
    name = data.get('name', check_key)
    category = data.get('category', 'system')
    severity = data.get('severity', 'warning')

    if not check_key:
        return jsonify({'success': False, 'error': _('check_key 必填')}), 400

    checker_class = CheckerRegistry.get(check_key)
    if checker_class:
        # 使用检查器类中定义的元数据
        inst = checker_class({})
        name = name or inst.get_name()
        category = category or inst.get_category()
        severity = severity or inst.get_severity()
        config = json.dumps(inst.get_config_defaults(), ensure_ascii=False)
    else:
        # 只有 check_key，没有对应的 Python 检查器类
        config = '{}'

    with m.get_db() as conn:
        existing = conn.execute('SELECT id FROM health_checks WHERE check_key=?', (check_key,)).fetchone()
        if existing:
            return jsonify({'success': False, 'error': f'检查项 {check_key} 已存在 (ID={existing["id"]})'})

        # 获取最大 sort_order
        max_order = conn.execute('SELECT COALESCE(MAX(sort_order),0)+10 as o FROM health_checks').fetchone()['o']

        conn.execute(
            'INSERT INTO health_checks (check_key, name, category, description, config, severity, sort_order, is_active) '
            'VALUES (?,?,?,?,?,?,?,1)',
            (check_key, name, category, data.get('description', ''), config, severity, max_order)
        )
        conn.commit()
        new_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']

    return jsonify({
        'success': True,
        'message': _('检查项 {name} 已添加').format(name=name),
        'data': {'id': new_id, 'check_key': check_key, 'has_checker': checker_class is not None}
    })


@health_bp.route('/api/alerts')
def api_alerts():
    """告警历史"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    alerts = m.get_alerts(limit=100)

    return jsonify({
        'success': True,
        'data': {
            'alerts': alerts,
        }
    })


@health_bp.route('/api/alerts/read', methods=['POST'])
def api_alerts_read():
    """标记告警已读"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.json or {}
    alert_id = data.get('alert_id')

    with m.get_db() as conn:
        if alert_id:
            conn.execute('UPDATE alert_history SET is_read=1 WHERE id=?', (alert_id,))
        else:
            conn.execute('UPDATE alert_history SET is_read=1')
        conn.commit()

    return jsonify({'success': True})


@health_bp.route('/api/export')
def api_export():
    """导出巡检报告 JSON"""
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    run_id = request.args.get('run_id', type=int)
    recent = request.args.get('recent', '1', type=str)

    with m.get_db() as conn:
        if run_id:
            run = conn.execute('SELECT * FROM check_runs WHERE id=?', (run_id,)).fetchone()
        else:
            run = conn.execute(
                "SELECT * FROM check_runs WHERE status='completed' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()

        if not run:
            return jsonify({'success': False, 'error': _('无可用巡检报告')}), 404

        run = dict(run)
        items = conn.execute(
            'SELECT * FROM check_history WHERE run_id=? ORDER BY category, id',
            (run['id'],)
        ).fetchall()
        run['items'] = [dict(i) for i in items]

    return jsonify({
        'success': True,
        'data': {
            'export_time': datetime.now().isoformat(),
            'platform': '',
            'report': run,
        }
    })


# ─── 修复执行 API ─────────────────────────────────────────────────────────

@health_bp.route('/api/fix', methods=['POST'])
def api_fix():
    """
    执行修复操作（从巡检结果中的 fix_suggestions 选取并执行）。
    请求体:
    {
        "run_id": 123,                  // 巡检批次 ID
        "check_key": "media_integrity", // 检查项 key
        "indices": [0, 1, 2],           // fix_suggestions 中的索引（选填，不传则全部执行）
        "confirm": true                 // 确认执行（必须为 true）
    }
    """
    admin = _require_admin()
    if not admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.json or {}
    run_id = data.get('run_id')
    check_key = data.get('check_key', '')
    selected_indices = data.get('indices')
    confirm = data.get('confirm', False)

    if not confirm:
        return jsonify({'success': False, 'error': '请确认执行 (confirm: true)'}), 400
    if not run_id or not check_key:
        return jsonify({'success': False, 'error': 'run_id 和 check_key 必填'}), 400

    # 从数据库读取该次巡检的 check_history 记录
    with m.get_db() as conn:
        history_row = conn.execute(
            'SELECT * FROM check_history WHERE run_id=? AND check_key=?',
            (run_id, check_key)
        ).fetchone()

    if not history_row:
        return jsonify({'success': False, 'error': _('未找到对应的检查结果')}), 404

    history = dict(history_row)
    try:
        detail = json.loads(history.get('detail', '{}'))
    except (json.JSONDecodeError, TypeError):
        detail = {}

    fix_suggestions = detail.get('fix_suggestions', [])
    if not fix_suggestions:
        return jsonify({'success': True, 'message': _('没有需要修复的项目')})

    # 筛选要执行的建议
    if selected_indices is not None:
        try:
            to_apply = [fix_suggestions[i] for i in selected_indices]
        except (IndexError, TypeError):
            return jsonify({'success': False, 'error': _('无效的索引')}), 400
    else:
        to_apply = fix_suggestions

    # 执行修复
    from .checkers import FixSuggestion
    applied = 0
    errors = []
    with m.get_db() as conn:
        for s_data in to_apply:
            try:
                sug = FixSuggestion(
                    record_type=s_data.get('record_type', ''),
                    table=s_data.get('table', ''),
                    record_id=s_data.get('record_id', 0),
                    field=s_data.get('field', ''),
                    missing_path=s_data.get('missing_path', ''),
                    action=s_data.get('action', 'clear_field'),
                    reason=s_data.get('reason', ''),
                )
                ok = FixSuggestion.apply_fix(conn, sug)
                if ok:
                    applied += 1
                else:
                    errors.append(f"ID={sug.record_id}: 执行失败")
            except Exception as e:
                errors.append(f"ID={s_data.get('record_id')}: {e}")
        conn.commit()

    return jsonify({
        'success': True,
        'data': {
            'applied': applied,
            'total': len(to_apply),
            'errors': errors,
            'run_id': run_id,
        },
        'message': _('已修复 {applied}/{total} 条记录').format(applied=applied, total=len(to_apply))
    })


# ─── 内部 API：供 Workflow 引擎调用 ────────────────────────────────────────

@health_bp.route('/api/internal/run', methods=['POST'])
def api_internal_run():
    """
    被 Workflow/Cron 调用的内部 API（无需管理员登录，使用 secret token 验证）
    请求头需携带 X-Health-Secret
    """
    secret = request.headers.get('X-Health-Secret', '')
    expected = os.environ.get('HEALTH_SECRET', 'health-monitor-internal')
    if secret != expected:
        return jsonify({'success': False, 'error': 'Forbidden'}), 403

    data = request.json or {}
    trigger_type = data.get('trigger_type', 'scheduled')
    check_keys = data.get('checks')
    trigger_info = data.get('trigger_info', 'internal')

    run_id = run_health_check(trigger_type=trigger_type, trigger_info=trigger_info,
                              check_keys=check_keys)

    return jsonify({
        'success': True,
        'data': {'run_id': run_id, 'message': _('巡检已完成 (ID: {id})').format(id=run_id)}
    })
