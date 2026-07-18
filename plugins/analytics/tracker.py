#!/usr/bin/env python3
"""
analytics/tracker.py — 自定义事件追踪 + 告警管理

用于记录业务事件（如_("Launch Agent")、_("View Stock Details")、_("Create Workflow")等）
可通过 API 调用或 Workflow 节点触发。

用法:
  from analytics.tracker import track_event
  track_event('launch_agent', visitor_hash='xxx', category='agent', label='hermes')
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from . import models as am


def track_event(event_name: str,
                visitor_hash: str = '',
                category: str = '',
                label: str = '',
                value: int = 0,
                path: str = '',
                service_name: str = '',
                metadata: dict = None,
                conn=None):
    """
    记录自定义业务事件

    参数:
        event_name:  事件名，如 "launch_agent", "view_stock", "create_workflow"
        visitor_hash: 访客哈希（可为空，用于关联用户行为）
        category:    事件分类，如 "agent", "stock", "workflow"
        label:       事件标签，如 "hermes", "000001.SH"
        value:       事件数值（可选），如价格、数量
        path:        发生路径
        service_name: 来源服务
        metadata:    额外 JSON 数据

    返回:
        事件 ID 或 None
    """
    if not event_name:
        return None

    should_close = False
    if conn is None:
        conn = am.get_db()
        should_close = True

    try:
        event_id = am.insert_event(conn, {
            'timestamp': int(time.time()),
            'visitor_hash': visitor_hash,
            'event_name': event_name,
            'event_category': category or '',
            'event_label': label or '',
            'event_value': value,
            'path': path,
            'service_name': service_name,
            'metadata': metadata or {},
        })
        return event_id
    finally:
        if should_close:
            conn.close()


def track_page_view_extra(conn, visitor_hash: str, path: str,
                          event_label: str = '', payload: dict = None):
    """
    追踪特定页面的额外信息（扩展 Page View 事件）
    用于股票详情页、Agent 档案页等
    """
    return track_event(
        event_name='page_view_detail',
        visitor_hash=visitor_hash,
        category='page',
        label=event_label or path,
        path=path,
        metadata=payload,
        conn=conn,
    )


def track_agent_action(conn, visitor_hash: str, agent_name: str,
                       action: str = 'launch', metadata: dict = None):
    """
    追踪 智能体 操作
    action: launch / stop / configure / feedback
    """
    return track_event(
        event_name=f'agent_{action}',
        visitor_hash=visitor_hash,
        category='agent',
        label=agent_name,
        metadata=metadata,
        conn=conn,
    )


def track_workflow_action(conn, visitor_hash: str, workflow_name: str,
                          action: str = 'run', metadata: dict = None):
    """
    追踪 Workflow 操作
    action: run / complete / fail
    """
    return track_event(
        event_name=f'workflow_{action}',
        visitor_hash=visitor_hash,
        category='workflow',
        label=workflow_name,
        metadata=metadata,
        conn=conn,
    )


def track_content_action(conn, visitor_hash: str, content_id: str,
                         action: str = 'view', metadata: dict = None):
    """
    追踪内容操作（内容工厂产出）
    action: view / share / bookmark
    """
    return track_event(
        event_name=f'content_{action}',
        visitor_hash=visitor_hash,
        category='content',
        label=content_id,
        metadata=metadata,
        conn=conn,
    )


# ─── 告警管理 ──────────────────────────────────────────────────────────────────

def create_alert(name: str, metric: str, operator: str,
                 threshold: float, time_window: str = '1h',
                 channels: list = None) -> int:
    """
    创建告警规则

    参数:
        name:        告警名称
        metric:      指标 (uv/pv/bounce_rate/error_rate/response_time)
        operator:    操作符 (gt/lt/gte/lte/eq/change_pct)
        threshold:   阈值
        time_window: 时间窗口 (1h/24h/7d)
        channels:    通知渠道 ["notification", "email", "webhook"]

    返回: 告警 ID
    """
    conn = am.get_db()
    try:
        channels_json = json.dumps(channels or ['notification'], ensure_ascii=False)
        cur = conn.execute("""
            INSERT INTO analytics_alerts
            (name, enabled, metric, operator, threshold, time_window, channels, created_at, updated_at)
            VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?) RETURNING id
        """, (name, metric, operator, threshold, time_window, channels_json,
              int(time.time()), int(time.time())))
        conn.commit()
        return cur.fetchone()['id']
    finally:
        conn.close()


def list_alerts(enabled_only: bool = False) -> list:
    """获取告警规则列表"""
    conn = am.get_db()
    try:
        query = "SELECT * FROM analytics_alerts"
        if enabled_only:
            query += " WHERE enabled=1"
        rows = conn.execute(query + " ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_alert(alert_id: int, **kwargs) -> bool:
    """更新告警规则"""
    allowed = {'name', 'enabled', 'metric', 'operator', 'threshold',
               'time_window', 'channels'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    updates['updated_at'] = int(time.time())
    set_clause = ', '.join(f'{k}=?' for k in updates)
    conn = am.get_db()
    try:
        conn.execute(
            f"UPDATE analytics_alerts SET {set_clause} WHERE id=?",
            list(updates.values()) + [alert_id]
        )
        conn.commit()
        return conn.execute("SELECT changes()").fetchone()['changes'] > 0
    finally:
        conn.close()


def delete_alert(alert_id: int) -> bool:
    """删除告警规则"""
    conn = am.get_db()
    try:
        cur = conn.execute("DELETE FROM analytics_alerts WHERE id=?", (alert_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ─── 报告生成 ──────────────────────────────────────────────────────────────────

def generate_report(days: int = 7, include_charts: bool = False) -> dict:
    """
    生成分析报告（用于日报/周报）
    可被 Workflow 引擎调用
    """
    conn = am.get_db()
    try:
        report = {
            'generated_at': datetime.now().isoformat(),
            'period': f'past_{days}_days',
            'summary': {},
            'trend': am.get_trend(conn, days),
            'sources': am.get_source_analysis(conn, days),
            'devices': am.get_device_distribution(conn, days)['by_device'],
            'geo': am.get_geo_distribution(conn, days),
            'hot_pages': am.get_page_rank(conn, days, 10),
            'events': [dict(r) for r in
                       conn.execute(
                           "SELECT event_name, event_category, COUNT(*) count "
                           "FROM analytics_events WHERE timestamp>=? "
                           "GROUP BY event_name ORDER BY count DESC LIMIT 10",
                           (int(time.time()) - days * 86400,)
                       ).fetchall()],
        }

        # 汇总
        totals = conn.execute("""
            SELECT COALESCE(SUM(pv),0) pv, COALESCE(SUM(uv),0) uv,
                   COALESCE(SUM(total_sessions),0) sessions
            FROM analytics_daily_stats
            WHERE date >= ?
        """, ((datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),)).fetchone()

        report['summary'] = {
            'total_pv': totals['pv'],
            'total_uv': totals['uv'],
            'total_sessions': totals['sessions'],
            'avg_daily_pv': round(totals['pv'] / days, 1) if days > 0 else 0,
            'avg_daily_uv': round(totals['uv'] / days, 1) if days > 0 else 0,
        }
        return report
    finally:
        conn.close()


def generate_insight_text(report: dict) -> str:
    """
    将报告数据转为可读的文字洞察
    适合 智能体 解读后生成报告
    """
    lines = []
    s = report['summary']
    lines.append(f"📊 Statistics Analysis Report ({report['period']})")
    lines.append(f"━━━━━━━━━━━━━━━━━━")
    lines.append(f"Total Views (PV): {s['total_pv']}")
    lines.append(f"Unique Visitors (UV): {s['total_uv']}")
    lines.append(f"Total Sessions: {s['total_sessions']}")
    lines.append(f"Daily PV: {s['avg_daily_pv']}  |  Daily UV: {s['avg_daily_uv']}")
    lines.append("")

    # 趋势
    if report['trend']:
        last = report['trend'][-1] if report['trend'] else {}
        first = report['trend'][0] if report['trend'] else {}
        if last and first:
            pv_change = ((last['pv'] - first['pv']) / max(first['pv'], 1)) * 100
            lines.append(f"📈 Traffic Change: {pv_change:+.1f}%")
            lines.append(f"  Bounce Rate: {last.get('bounce_rate', 0):.1f}%")
            lines.append(f"  Average Session Duration: {last.get('avg_duration', 0):.0f}s")
    lines.append("")

    # 热门来源
    if report['sources']:
        lines.append(_("🔗 Top Sources:"))
        for src in report['sources'][:5]:
            lines.append(f"  • {src['source_name']}: {src['pv']} PV ({src.get('pct', 0):.1f}%)")
    lines.append("")

    # 热门页面
    if report['hot_pages']:
        lines.append(_("📄 Popular Pages:"))
        for pg in report['hot_pages'][:5]:
            lines.append(f"  • {pg['path']}: {pg['pv']} PV / {pg['uv']} UV")
    lines.append("")

    return '\n'.join(lines)
