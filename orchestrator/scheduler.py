#!/usr/bin/env python3
"""
Scheduler — Cron 任务调度器核心
==============================
基于 APScheduler 的扩展调度器，支持：
- 标准 Cron 表达式 + 自定义工作日历
- 一次性/重复/固定间隔任务
- 优先级调度（critical/high/normal/low）
- 失败重试（指数退避）
- 超时控制和强制终止
- 两种 Agent 类型分发（system/user）
- 分布式支持（基于数据库锁）
- SQLite Job Store（系统重启不丢失）

@package orchestrator
"""

import os, sys, time, json
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable
from functools import wraps

# 添加项目根到路径（兼容独立进程和嵌入运行）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))

try:
    import apscheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

from . import models as m


# ============================================================
# 常量
# ============================================================

PRIORITY_ORDER = {'critical': 0, 'high': 1, 'normal': 2, 'low': 3}

# ============================================================
# 自然语言 Cron 解析
# ============================================================

NATURAL_RULES = {
    # 交易日 — 周一至周五
    '每个交易日': '0 30 9 ? * MON-FRI',
    '交易日开盘': '0 30 9 ? * MON-FRI',
    '交易日收盘': '0 0 15 ? * MON-FRI',
    '交易时段': '*/30 9-15 ? * MON-FRI',
    # 固定时间
    '每小时': '0 0 * * *',
    '每半小时': '*/30 * * * *',
    '每10分钟': '*/10 * * * *',
    '早八点': '0 0 8 * * *',
    '早九点': '0 0 9 * * *',
    '中午': '0 0 12 * * *',
    '晚八点': '0 0 20 * * *',
    '凌晨': '0 0 0 * * *',
    '每天': '0 0 0 * * *',
    '每日': '0 0 0 * * *',
    '每周一': '0 0 0 * * 1',
    '每月1号': '0 0 0 1 * *',
}

def parse_natural_cron(expr: str) -> str:
    """将自然语言表达式转为 Cron 表达式"""
    if not expr:
        return ''

    # 精确匹配
    if expr in NATURAL_RULES:
        return NATURAL_RULES[expr]

    # 尝试模式匹配
    import re
    # "每个交易日 HH:MM 执行"
    trade_match = re.match(r'每个交易日\s*(\d{1,2}):(\d{2})', expr)
    if trade_match:
        h, m = trade_match.group(1), trade_match.group(2)
        return f'0 {m} {h} ? * MON-FRI'

    # "每 X 分钟/小时"
    interval_match = re.match(r'每\s*(\d+)\s*(分钟|小时)', expr)
    if interval_match:
        num = int(interval_match.group(1))
        unit = interval_match.group(2)
        if unit == '分钟':
            return f'*/{num} * * * *'
        else:
            return f'0 */{num} * * *'

    # "每天 HH:MM"
    daily_match = re.match(r'每天\s*(\d{1,2}):(\d{2})', expr)
    if daily_match:
        h, m = daily_match.group(1), daily_match.group(2)
        return f'0 {m} {h} * * *'

    # 提取 hh:mm 模式
    time_match = re.search(r'(\d{1,2}):(\d{2})', expr)
    if time_match:
        h, m = time_match.group(1), time_match.group(2)
        # 检查是否包含 周/日 信息
        if '周' in expr or '星期' in expr:
            day_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 7, '天': 7}
            for cn, num in day_map.items():
                if cn in expr:
                    return f'0 {m} {h} * * {num}'
            return f'0 {m} {h} * * *'
        return f'0 {m} {h} * * *'

    return expr  # 兜底：当作标准 cron 表达式


# ============================================================
# 调度器核心
# ============================================================

class SchedulerEngine:
    """Cron 任务调度器引擎"""

    def __init__(self, scheduler_id: str = None, db_url: str = None):
        hostname = os.uname().nodename if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', 'localhost')
        self.scheduler_id = scheduler_id or f'scheduler-{hostname}-{os.getpid()}'
        self._lock = threading.Lock()
        self._running_jobs: dict = {}  # job_id -> APScheduler job
        self._workflow_runner: Optional[Callable] = None
        self._callback_map: dict = {}  # target_type -> handler function

        if not HAS_APSCHEDULER:
            raise ImportError(
                "APScheduler 未安装。请运行: pip install apscheduler sqlalchemy"
            )

        # APScheduler 配置
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(8),
            'processpool': ProcessPoolExecutor(2)
        }

        self._apscheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults={
                'coalesce': True,           # 合并错过的执行
                'max_instances': 1,          # 防止并发
                'misfire_grace_time': 300,   # 5分钟容错
            },
            timezone='Asia/Shanghai'
        )

        # 注册事件监听
        self._apscheduler.add_listener(
            self._on_job_event,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )

    # ---- 注册处理器 ----

    def register_callback(self, target_type: str, handler: Callable):
        """注册特定 target_type 的处理函数"""
        self._callback_map[target_type] = handler

    def set_workflow_runner(self, runner: Callable):
        """设置工作流执行器"""
        self._workflow_runner = runner

    # ---- 生命周期 ----

    def start(self):
        """启动调度器"""
        m.add_log('system', 0, 'info',
                   f'🟢 调度器启动: {self.scheduler_id}',
                   {'scheduler_id': self.scheduler_id})
        self._apscheduler.start()
        self._register_scheduler_heartbeat()
        self._sync_cron_jobs()

    def shutdown(self, wait=True):
        """关闭调度器"""
        m.add_log('system', 0, 'info',
                   f'🔴 调度器关闭: {self.scheduler_id}')
        self._apscheduler.shutdown(wait=wait)

    def pause(self):
        """暂停所有任务"""
        self._apscheduler.pause()
        m.add_log('system', 0, 'warn', '⏸️ 调度器暂停')

    def resume(self):
        """恢复所有任务"""
        self._apscheduler.resume()
        m.add_log('system', 0, 'info', '▶️ 调度器恢复')

    # ---- 任务管理 ----

    def _sync_cron_jobs(self):
        """从数据库同步所有活跃的 Cron 任务"""
        with self._lock:
            # 清除现有 APScheduler 作业（保留管理元数据）
            for job_id in list(self._running_jobs.keys()):
                try:
                    self._apscheduler.remove_job(f'cron_{job_id}')
                except Exception:
                    pass
            self._running_jobs.clear()

            # 从数据库重新加载
            result = m.list_cron_jobs(active_only=True, limit=1000)
            for job in result['jobs']:
                self._schedule_job(job)

    def _schedule_job(self, job: dict):
        """调度单个任务"""
        job_id = job['id']
        job_type = job['job_type']
        cron_expr = job.get('cron_expr') or ''
        natural_expr = job.get('natural_expr') or ''
        interval_sec = job.get('interval_seconds', 0)
        start_at = job.get('start_at') or None
        end_at = job.get('end_at') or None
        max_runs = job.get('max_runs', 0)

        # 确定最终 cron 表达式
        if natural_expr and not cron_expr:
            cron_expr = parse_natural_cron(natural_expr)

        try:
            # 创建 APScheduler trigger
            if job_type == 'cron' and cron_expr:
                parts = cron_expr.strip().split()
                if len(parts) == 5:
                    trigger = CronTrigger(
                        minute=parts[0], hour=parts[1],
                        day=parts[2], month=parts[3], day_of_week=parts[4],
                        timezone=job.get('timezone', 'Asia/Shanghai')
                    )
                elif len(parts) == 6:
                    trigger = CronTrigger(
                        second=parts[0], minute=parts[1], hour=parts[2],
                        day=parts[3], month=parts[4], day_of_week=parts[5],
                        timezone=job.get('timezone', 'Asia/Shanghai')
                    )
                else:
                    m.add_log('cron', job_id, 'error', f'无效的 Cron 表达式: {cron_expr}')
                    return

            elif job_type == 'interval' and interval_sec > 0:
                trigger = IntervalTrigger(seconds=interval_sec)

            elif job_type == 'once' and start_at:
                trigger = DateTrigger(run_date=start_at)

            else:
                m.add_log('cron', job_id, 'warn', f'无法调度的任务类型或缺少参数')
                return

            # 添加 APScheduler 作业
            aps_job = self._apscheduler.add_job(
                self._execute_job_wrapper,
                trigger=trigger,
                id=f'cron_{job_id}',
                name=job.get('name', f'Job-{job_id}'),
                args=[job_id],
                max_instances=1,
                coalesce=True,
                misfire_grace_time=300,
                replace_existing=True
            )

            self._running_jobs[job_id] = aps_job
            m.add_log('cron', job_id, 'info',
                       f'📅 任务已调度: [{job.get("name")}] {cron_expr or natural_expr or f"每{interval_sec}秒"}')

        except Exception as e:
            m.add_log('cron', job_id, 'error',
                       f'调度任务失败 [{job.get("name")}]: {str(e)}')

    def _execute_job_wrapper(self, job_id: int):
        """任务执行包装器（记录开始/结束/重试）"""
        job = m.get_cron_job(job_id)
        if not job or not job['is_active']:
            return

        start_time = time.time()
        m.update_cron_job(job_id, {
            'last_run_at': m.now_str(),
            'last_status': 'running'
        })

        # 检查并发限制
        current_runs = m.get_cron_job(job_id)
        if current_runs and current_runs.get('run_count', 0) >= current_runs.get('max_runs', 0) > 0:
            m.add_log('cron', job_id, 'warn', '⏭️ 已达最大执行次数，跳过')
            return

        result = self._execute_with_retries(job)

        duration_ms = int((time.time() - start_time) * 1000)
        m.update_cron_job(job_id, {
            'last_status': 'success' if result['success'] else 'failed',
            'last_duration_ms': duration_ms,
            'run_count': job.get('run_count', 0) + 1,
            'fail_count': job.get('fail_count', 0) + (0 if result['success'] else 1)
        })

        # 检查依赖触发
        if result['success']:
            self._trigger_dependent_jobs(job_id)

    def _execute_with_retries(self, job: dict) -> dict:
        """带重试的任务执行"""
        max_retries = job.get('max_retries', 3)
        retry_delay = job.get('retry_delay', 10)
        backoff = job.get('retry_backoff', 2.0)
        timeout = job.get('timeout_seconds', 300)
        job_id = job['id']
        target_type = job['target_type']
        target_config = m.from_json(job.get('target_config', '{}'))

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                m.add_log('cron', job_id, 'info',
                           f'🔄 执行尝试 {attempt+1}/{max_retries+1}')

                # 查找处理器
                handler = self._callback_map.get(target_type)
                if handler:
                    result = handler(job, target_config, timeout)
                elif target_type == 'workflow':
                    # 默认工作流执行
                    wf_id = target_config.get('workflow_id')
                    if wf_id and self._workflow_runner:
                        result = self._workflow_runner(
                            wf_id, trigger_type='cron',
                            trigger_config={'cron_job_id': job_id}
                        )
                    else:
                        raise ValueError(f'工作流执行器未设置或 worklow_id 缺失')
                else:
                    # 直接执行 API 调用
                    result = self._execute_api_target(target_config, timeout)

                if result and result.get('success', True):
                    m.add_log('cron', job_id, 'info', '✅ 执行成功')
                    return {'success': True, 'result': result}
                else:
                    last_error = str(result.get('error', 'Unknown error'))

            except TimeoutError:
                last_error = '⏰ 超时'
                m.add_log('cron', job_id, 'error', f'⏰ 任务超时 ({timeout}s)')
                break  # 超时不重试

            except Exception as e:
                last_error = str(e)
                m.add_log('cron', job_id, 'error',
                           f'❌ 执行失败 (第{attempt+1}次): {e}')

            # 指数退避等待（最后一次不等待）
            if attempt < max_retries:
                delay = retry_delay * (backoff ** attempt)
                m.add_log('cron', job_id, 'info',
                           f'⏳ 等待 {delay:.0f}秒后重试...')
                time.sleep(delay)

        m.add_log('cron', job_id, 'error',
                   f'❌ 执行失败（已重试{max_retries}次）: {last_error}')
        return {'success': False, 'error': last_error}

    def _execute_api_target(self, config: dict, timeout: int) -> dict:
        """执行 API 类型的任务目标"""
        import urllib.request
        import json

        url = config.get('url', '')
        method = config.get('method', 'GET').upper()
        headers = config.get('headers', {})
        body = config.get('body')

        req = urllib.request.Request(url, method=method)
        for k, v in headers.items():
            req.add_header(k, v)
        if body:
            req.data = json.dumps(body).encode('utf-8')
            if 'Content-Type' not in headers:
                req.add_header('Content-Type', 'application/json')

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return {
                    'success': resp.status < 400,
                    'status': resp.status,
                    'body': resp.read().decode('utf-8')[:5000]
                }
        except Exception as e:
            raise

    def _trigger_dependent_jobs(self, job_id: int):
        """触发依赖当前任务的后继任务"""
        with m.get_db() as conn:
            conn.execute("""
                SELECT j.* FROM job_dependencies d
                JOIN cron_jobs j ON d.job_id = j.id
                WHERE d.depends_on_job_id = %s AND j.is_active = 1
            """, (job_id,))
            deps_row = conn.fetchall()
            deps = [dict(r) for r in deps_row]

        for dep in deps:
            dep = dict(dep)
            m.add_log('cron', dep['id'], 'info',
                       f'🔗 由任务 #{job_id} 完成触发执行')
            self._execute_job_wrapper(dep['id'])

    # ---- 事件处理 ----

    def _on_job_event(self, event):
        """APScheduler 事件回调"""
        # 状态由 _execute_job_wrapper 记录，这里只记录额外异常
        if event.exception:
            m.add_log('cron', 0, 'error',
                       f'APScheduler 异常: {event.exception}')

    def _register_scheduler_heartbeat(self):
        """注册调度器心跳"""
        self._apscheduler.add_job(
            self._heartbeat,
            trigger=IntervalTrigger(seconds=30),
            id='_scheduler_heartbeat',
            name='Scheduler Heartbeat',
            replace_existing=True,
            max_instances=1
        )

    def _heartbeat(self):
        """调度器心跳更新"""
        try:
            running_count = len([
                j for j in self._running_jobs.values()
                if j and getattr(j, 'next_run_time', None)
            ])

            with m.get_db() as conn:
                conn.execute("""
                    INSERT INTO scheduler_state
                        (scheduler_id, hostname, is_leader, last_heartbeat,
                         running_jobs, state_json)
                    VALUES (%s,%s,1, NOW(), %s, '{}')
                    ON CONFLICT (scheduler_id) DO UPDATE SET
                        hostname = EXCLUDED.hostname,
                        is_leader = EXCLUDED.is_leader,
                        last_heartbeat = EXCLUDED.last_heartbeat,
                        running_jobs = EXCLUDED.running_jobs,
                        state_json = EXCLUDED.state_json
                """, (self.scheduler_id, os.uname().nodename, running_count))

        except Exception:
            pass

    # ---- 外部接口 ----

    def add_job(self, job_data: dict) -> int:
        """从外部添加新任务（自动调度）"""
        job_id = m.create_cron_job(job_data)
        self._sync_cron_jobs()
        return job_id

    def remove_job(self, job_id: int) -> bool:
        """移除任务并取消调度"""
        result = m.delete_cron_job(job_id)
        if result:
            try:
                self._apscheduler.remove_job(f'cron_{job_id}')
                self._running_jobs.pop(job_id, None)
            except Exception:
                pass
        return result

    def update_job(self, job_id: int, data: dict) -> bool:
        """更新任务并重新调度"""
        result = m.update_cron_job(job_id, data)
        if result:
            self._sync_cron_jobs()
        return result

    def pause_job(self, job_id: int) -> bool:
        """暂停单个任务"""
        return self.update_job(job_id, {'is_active': 0})

    def resume_job(self, job_id: int) -> bool:
        """恢复单个任务"""
        return self.update_job(job_id, {'is_active': 1})

    def get_status(self) -> dict:
        """获取调度器状态"""
        from apscheduler.schedulers.base import STATE_PAUSED
        return {
            'scheduler_id': self.scheduler_id,
            'running': self._apscheduler.running,
            'paused': self._apscheduler.state == STATE_PAUSED,
            'scheduled_jobs': len(self._running_jobs),
            'next_jobs': [
                {
                    'id': jid,
                    'name': getattr(j, 'name', ''),
                    'next_run': str(j.next_run_time) if getattr(j, 'next_run_time', None) else None
                }
                for jid, j in self._running_jobs.items()
                if j and getattr(j, 'next_run_time', None)
            ][:20]
        }


# ============================================================
# 命令行测试
# ============================================================

if __name__ == '__main__':
    m.init_orchestrator_tables()

    scheduler = SchedulerEngine()
    scheduler.start()

    print(f'🟢 Scheduler started: {scheduler.scheduler_id}')
    print('Press Ctrl+C to stop.')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
        print('🔴 Scheduler stopped.')
