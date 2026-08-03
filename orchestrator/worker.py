#!/usr/bin/env python3
"""
Worker Pool — 任务执行工作池
=============================
管理并发 Worker 执行调度任务和工作流节点。
支持优先级队列、资源隔离、超时控制。

@package orchestrator
"""

from i18n import _
import os, sys, time, json, threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import PriorityQueue
from enum import IntEnum

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))

from . import models as m
from . import nodes as node_handlers
from .workflow_engine import WorkflowEngine


class Priority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class WorkerPool:
    """
    多级 Worker 池
    - 高优先级任务：专用 Worker
    - 普通/低优先级：共享 Worker
    """

    def __init__(self):
        self._engines = {}            # pool_name -> ThreadPoolExecutor
        self._workflow_engine = WorkflowEngine()
        self._lock = threading.Lock()

        # 两个 Worker 池
        self._dedicated_pool = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix='dedicated'
        )
        self._shared_pool = ThreadPoolExecutor(
            max_workers=8,
            thread_name_prefix='shared'
        )

        # 注册节点处理器
        node_handlers.register_all(self._workflow_engine)

        # 注册回调到调度器
        self._scheduler_callbacks_registered = False

        # 运行状态
        self._running = True
        self._active_tasks: dict = {}

    # ---- 注册到调度器 ----

    def register_scheduler_callbacks(self, scheduler):
        """注册调度器回调（使 scheduler 能通过 WorkerPool 执行任务）"""
        scheduler.register_callback('workflow', self._execute_workflow_job)
        scheduler.register_callback('api', self._execute_api_job)
        scheduler.register_callback('script', self._execute_script_job)
        scheduler.register_callback('agent_task', self._execute_agent_job)
        scheduler.set_workflow_runner(self._execute_workflow_job)
        self._scheduler_callbacks_registered = True

    # ---- 任务执行入口 ----

    def submit(self, task_type: str, task_data: dict,
               priority: str = 'normal') -> str:
        """
        提交任务到 Worker 池。

        Args:
            task_type: 'workflow' | 'cron' | 'node' | 'script'
            task_data: 任务参数
            priority: 'critical' | 'high' | 'normal' | 'low'

        Returns:
            task_id: 任务唯一标识
        """
        task_id = f"{task_type}_{int(time.time()*1000)}_{id(task_data)}"
        prio = Priority.__members__.get(priority.upper(), Priority.NORMAL).value

        with self._lock:
            if prio <= Priority.HIGH:
                future = self._dedicated_pool.submit(
                    self._run_task, task_id, task_type, task_data
                )
            else:
                future = self._shared_pool.submit(
                    self._run_task, task_id, task_type, task_data
                )
            self._active_tasks[task_id] = {
                'future': future,
                'type': task_type,
                'priority': priority,
                'started_at': time.time(),
                'status': 'running'
            }

        m.add_log('system', 0, 'info',
                   f'📤 Task Submitted: [{task_type}] {task_id} (Priority: {priority})')
        return task_id

    def _run_task(self, task_id: str, task_type: str, task_data: dict):
        """实际运行任务"""
        try:
            if task_type == 'workflow':
                self._execute_workflow_job(task_data)
            elif task_type == 'cron':
                self._execute_cron_job(task_data)
            elif task_type == 'node':
                self._execute_node(task_data)
            elif task_type == 'script':
                self._execute_script_job(task_data)

            with self._lock:
                if task_id in self._active_tasks:
                    self._active_tasks[task_id]['status'] = 'completed'
                    self._active_tasks[task_id]['finished_at'] = time.time()

        except Exception as e:
            m.add_log('system', 0, 'error',
                       f'❌ Task Execution Failed [{task_id}]: {str(e)}')
            with self._lock:
                if task_id in self._active_tasks:
                    self._active_tasks[task_id]['status'] = 'failed'
                    self._active_tasks[task_id]['error'] = str(e)

    # ---- 具体任务执行器 ----

    def _execute_workflow_job(self, job_data: dict) -> dict:
        """执行工作流任务（作为 Cron 任务的回调）"""
        if isinstance(job_data, dict):
            wf_id = job_data.get('workflow_id')
            trigger_config = job_data.get('trigger_config', {})
        else:
            wf_id = job_data
            trigger_config = {}

        if not wf_id:
            return {'success': False, 'error': _('Missing workflow_id')}

        try:
            inst_id = self._workflow_engine.run_workflow(
                wf_id, trigger_type='cron',
                trigger_config=trigger_config
            )
            return {'success': True, 'instance_id': inst_id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_cron_job(self, job_data: dict) -> dict:
        """执行直接的 Cron 任务"""
        job_id = job_data.get('job_id')
        target_type = job_data.get('target_type', 'api')
        target_config = job_data.get('target_config', {})

        if target_type == 'api':
            return self._execute_api_target(target_config)
        elif target_type == 'script':
            return self._execute_script_target(target_config)

        return {'success': False, 'error': f'Unsupported target type: {target_type}'}

    def _execute_api_job(self, job: dict, target_config: dict,
                          timeout: int = 300) -> dict:
        """执行 API 类型的任务"""
        return self._execute_api_target(target_config)

    def _execute_api_target(self, config: dict) -> dict:
        """执行 API 调用"""
        import urllib.request

        url = config.get('url', '')
        method = config.get('method', 'GET').upper()
        headers = config.get('headers', {})
        body = config.get('body')

        if not url:
            return {'success': False, 'error': _('URL is empty')}

        req = urllib.request.Request(url, method=method)
        for k, v in headers.items():
            req.add_header(k, v)
        if body:
            import json as _json
            req.data = _json.dumps(body).encode('utf-8')
            if 'Content-Type' not in headers:
                req.add_header('Content-Type', 'application/json')

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')[:10000]
                return {
                    'success': resp.status < 400,
                    'status': resp.status,
                    'body': resp_body
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_script_job(self, job: dict, target_config: dict = None,
                             timeout: int = 300) -> dict:
        """执行脚本类型的任务"""
        config = target_config or (job.get('target_config', {}) if isinstance(job, dict) else {})
        script_path = config.get('script_path', '')
        script_args = config.get('args', [])

        if script_path:
            import subprocess
            # 安全校验：script_path 必须在 SCRIPTS_DIR 内
            SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
            real_script = os.path.realpath(os.path.join(SCRIPTS_DIR, os.path.basename(script_path)))
            if not real_script.startswith(os.path.realpath(SCRIPTS_DIR)):
                return {'success': False, 'error': f'Script path rejected: {script_path}'}
            if not os.path.isfile(real_script):
                return {'success': False, 'error': f'Script not found: {script_path}'}
            try:
                result = subprocess.run(
                    [sys.executable, real_script] + script_args,
                    capture_output=True, text=True, timeout=timeout
                )
                return {
                    'success': result.returncode == 0,
                    'stdout': result.stdout[-2000:],
                    'stderr': result.stderr[-1000:],
                    'returncode': result.returncode
                }
            except subprocess.TimeoutExpired:
                return {'success': False, 'error': f'Script Execution Timeout ({timeout}s)'}
            except Exception as e:
                return {'success': False, 'error': str(e)}

        return {'success': True, 'message': _('No Script Path, Skip')}

    def _execute_agent_job(self, job: dict, target_config: dict = None,
                            timeout: int = 300) -> dict:
        """执行 Agent 任务（调用 智能体）"""
        config = target_config or job.get('target_config', {}) if isinstance(job, dict) else {}
        prompt = config.get('prompt', '')
        if not prompt:
            return {'success': False, 'error': _('Prompt is empty')}
        return node_handlers.handle_ai_agent({'config': config}, {'context': {}})

    def _execute_node(self, task_data: dict):
        """执行单个工作流节点（给外部直接调用用）"""
        node_def = task_data.get('node_def', {})
        input_data = task_data.get('input_data', {})
        return self._workflow_engine.execute_node(
            node_def, task_data.get('node_inst', {}),
            task_data.get('inst_id', 0), input_data.get('node_outputs', {})
        )

    # ---- 状态和监控 ----

    def get_active_tasks(self) -> list:
        """获取当前活跃任务"""
        with self._lock:
            now = time.time()
            tasks = []
            for tid, tdata in self._active_tasks.items():
                duration = now - tdata.get('started_at', now)
                tasks.append({
                    'task_id': tid,
                    'type': tdata['type'],
                    'priority': tdata['priority'],
                    'status': tdata['status'],
                    'duration_s': round(duration, 1),
                    'error': tdata.get('error', '')
                })
            tasks.sort(key=lambda t: t.get('duration_s', 0), reverse=True)
            return tasks[:50]

    def get_pool_stats(self) -> dict:
        """获取 Worker 池统计"""
        return {
            'dedicated_pool': {
                'max_workers': 4,
                'active': sum(1 for t in self._active_tasks.values()
                              if t['status'] == 'running' and t['priority'] in ('critical', 'high'))
            },
            'shared_pool': {
                'max_workers': 8,
                'active': sum(1 for t in self._active_tasks.values()
                              if t['status'] == 'running' and t['priority'] in ('normal', 'low'))
            },
            'total_active': sum(1 for t in self._active_tasks.values()
                                if t['status'] == 'running'),
            'total_queued': sum(1 for t in self._active_tasks.values()
                                if t['status'] != 'running')
        }

    def shutdown(self):
        """关闭 Worker 池"""
        self._running = False
        self._dedicated_pool.shutdown(wait=False)
        self._shared_pool.shutdown(wait=False)
        m.add_log('system', 0, 'info', _('🔴 Worker pool is closed'))

    @property
    def workflow_engine(self) -> WorkflowEngine:
        return self._workflow_engine
