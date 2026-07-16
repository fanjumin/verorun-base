#!/usr/bin/env python3
"""
analytics/cli.py — 分析系统 CLI 维护工具

用法:
  python3 -m analytics.cli init                  # 初始化分析数据库表
  python3 -m analytics.cli process                # 运行一次聚合处理
  python3 -m analytics.cli daemon                 # 启动聚合守护进程
  python3 -m analytics.cli report [days=7]        # 生成文本报告
  python3 -m analytics.cli cleanup [days=30]      # 清理过期日志
  python3 -m analytics.cli stats                  # 分析系统自身统计
  python3 -m analytics.cli add-alert              # 交互式添加告警
  python3 -m analytics.cli seed-workflows         # 创建预设工作流
"""

import os
import sys
import json
import time
import signal
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from . import models as am
from .tracker import generate_report, generate_insight_text, create_alert
from .processor import AnalyticsProcessor


def cmd_init():
    """初始化分析数据库表"""
    am.init_analytics_tables()
    conn = am.get_db()
    try:
        config = am.get_privacy_config(conn)
        print(f'[Analytics] 📋 隐私配置:')
        for k, v in config.items():
            print(f'  {k}: {v}')
    finally:
        conn.close()


def cmd_process():
    """运行一次聚合处理"""
    processor = AnalyticsProcessor()
    stats = processor.process()
    print(f'[Analytics] ✅ 聚合完成')
    print(f'  处理批次: {stats["total_batches"]}')
    print(f'  PV: {stats["processed"]["pv"]}')
    print(f'  Bot: {stats["processed"]["bot"]}')
    print(f'  错误: {stats["processed"]["error"]}')


def cmd_daemon():
    """启动聚合守护进程"""
    interval = int(sys.argv[3]) if len(sys.argv) > 3 else 60

    processor = AnalyticsProcessor()
    running = True

    def handler(sig, frame):
        nonlocal running
        print('\n[Analytics Daemon] 正在停止...')
        running = False

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    print(f'[Analytics Daemon] 🚀 启动 (间隔 {interval}s)')
    while running:
        try:
            processor.process()
            time.sleep(interval)
        except Exception as e:
            print(f'[Analytics Daemon] ⚠️ {e}')
            time.sleep(interval)

    print('[Analytics Daemon] ✅ 已停止')


def cmd_report():
    """生成报告"""
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    report = generate_report(days)
    text = generate_insight_text(report)
    print(text)


def cmd_cleanup():
    """清理过期日志"""
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    conn = am.get_db()
    try:
        deleted = am.cleanup_old_logs(conn, days)
        print(f'[Analytics] 🧹 已清理 {deleted} 条日志 (保留 {days} 天)')
    finally:
        conn.close()


def cmd_stats():
    """分析系统自身统计"""
    conn = am.get_db()
    try:
        sys_info = am.get_privacy_config(conn) if hasattr(am, 'get_privacy_config') else {}

        total_logs = conn.execute("SELECT COUNT(*) c FROM analytics_logs").fetchone()['c']
        total_hourly = conn.execute("SELECT COUNT(*) c FROM analytics_hourly_stats").fetchone()['c']
        total_daily = conn.execute("SELECT COUNT(*) c FROM analytics_daily_stats").fetchone()['c']
        total_events = conn.execute("SELECT COUNT(*) c FROM analytics_events").fetchone()['c']
        total_sessions = conn.execute("SELECT COUNT(*) c FROM analytics_visitor_sessions").fetchone()['c']

        today = datetime.now().strftime('%Y-%m-%d')
        today_pv = conn.execute(
            "SELECT COUNT(*) c FROM analytics_logs WHERE date(timestamp,'unixepoch')=? AND is_bot=0",
            (today,)
        ).fetchone()['c']
        today_uv = conn.execute(
            "SELECT COUNT(DISTINCT visitor_hash) c FROM analytics_logs WHERE date(timestamp,'unixepoch')=? AND is_bot=0",
            (today,)
        ).fetchone()['c']

        # 数据库大小
        db_size = conn.execute(
            "SELECT pg_database_size(current_database()) as size"
        ).fetchone()['size']

        print('═' * 45)
        print(f'  📊 分析系统状态')
        print('═' * 45)
        print(f'  原始日志:     {total_logs:,} 条')
        print(f'  小时聚合:     {total_hourly:,} 条')
        print(f'  日聚合:       {total_daily:,} 条')
        print(f'  事件:         {total_events:,} 条')
        print(f'  会话:         {total_sessions:,} 条')
        print(f'  今日 PV:      {today_pv:,}')
        print(f'  今日 UV:      {today_uv:,}')
        print(f'  数据库大小:   {db_size/1048576:.2f} MB')
        print('─' * 45)

    except Exception as e:
        print(f'[Analytics] ❌ 查询失败: {e}')
    finally:
        conn.close()


def cmd_add_alert():
    """交互式添加告警规则"""
    import readline  # 增强输入体验
    print('\n=== 添加分析告警规则 ===')
    print()

    name = input('告警名称: ').strip()
    if not name:
        print('❌ 名称不能为空')
        return

    print('\n指标选项:')
    metrics = ['uv (独立访客)', 'pv (浏览量)', 'bounce_rate (跳出率%)',
               'error_rate (错误率%)', 'avg_response_time (平均响应ms)']
    for i, m in enumerate(metrics, 1):
        print(f'  {i}. {m}')
    metric_idx = int(input('选择指标 (1-5): ').strip())
    metric_map = ['', 'uv', 'pv', 'bounce_rate', 'error_rate', 'avg_response_time']
    metric = metric_map[metric_idx]

    print('\n操作符:')
    print('  1. > (大于)')
    print('  2. < (小于)')
    print('  3. >= (大于等于)')
    print('  4. <= (小于等于)')
    op_idx = int(input('选择操作符 (1-4): ').strip())
    op_map = ['', 'gt', 'lt', 'gte', 'lte']
    operator = op_map[op_idx]

    threshold = float(input('阈值: ').strip())

    print('\n时间窗口:')
    print('  1. 1h (1小时)')
    print('  2. 24h (24小时)')
    print('  3. 7d (7天)')
    tw_idx = int(input('选择 (1-3): ').strip())
    tw_map = ['', '1h', '24h', '7d']
    time_window = tw_map[tw_idx]

    alert_id = create_alert(name, metric, operator, threshold, time_window)
    print(f'\n✅ 告警规则已创建 (ID: {alert_id})')


def cmd_seed_workflows():
    """创建预设分析工作流"""
    try:
        from .workflow_nodes import create_daily_report_workflow, create_weekly_report_workflow
        from orchestrator import models as om
        om.init_orchestrator_tables()
    except ImportError:
        print('❌ 需要 orchestrator 模块 (pip install apscheduler)')
        return

    conn = om.get_db()
    try:
        daily_id = create_daily_report_workflow(conn)
        weekly_id = create_weekly_report_workflow(conn)
        print(f'✅ 预设工作流已创建:')
        print(f'  📊 每日分析报告 (ID: {daily_id})')
        print(f'  📊 每周运营报告 (ID: {weekly_id})')

        # 创建工作流绑定的 Cron 任务
        from orchestrator import models as om
        om.create_cron_job(conn, {
            'name': '每日分析报告',
            'target_type': 'workflow',
            'target_id': daily_id,
            'cron_expression': '0 8 * * *',
            'is_active': 1,
            'priority': 3,
            'timeout': 300,
        })
        om.create_cron_job(conn, {
            'name': '每周运营报告',
            'target_type': 'workflow',
            'target_id': weekly_id,
            'cron_expression': '0 9 * * 1',
            'is_active': 1,
            'priority': 3,
            'timeout': 300,
        })
        print(f'  ⏰ Cron 任务已绑定 (每日8:00 / 每周一9:00)')
    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    commands = {
        'init': cmd_init,
        'process': cmd_process,
        'daemon': cmd_daemon,
        'report': cmd_report,
        'cleanup': cmd_cleanup,
        'stats': cmd_stats,
        'add-alert': cmd_add_alert,
        'seed-workflows': cmd_seed_workflows,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f'❌ 未知命令: {cmd}')
        print(__doc__)
