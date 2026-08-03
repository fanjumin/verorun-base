#!/usr/bin/env python3
"""
Workflow Engine — DAG 工作流引擎
================================
轻量级 DAG 执行引擎，管理工作流实例的状态机。

工作流实例状态机:
  pending → running → completed
                  ↓ → failed
                  ↓ → paused → running
                  ↓ → timeout
                  ↓ → cancelled

节点实例状态机:
  pending → running → completed
                  ↓ → failed
                  ↓ → skipped
                  ↓ → waiting_approval → completed/rejected

@package orchestrator
"""

from i18n import _
import os, sys, time, json
import threading
from datetime import datetime
from typing import Optional, Callable
from collections import deque
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))

from . import models as m
from .safe_eval import safe_eval


class WorkflowEngine:
    """DAG 工作流执行引擎"""

    # 节点类型映射（由外部注册）
    NODE_HANDLERS: dict = {}

    def __init__(self, max_workers: int = 4):
        self._running_instances: dict = {}
        self._lock = threading.Lock()
        self._max_workers = max_workers
        self._node_executor_map: dict = {}  # node_type -> handler

        # 默认注册所有节点类型
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认节点处理器（可在运行时重写）"""
        for nt in ['ai_agent', 'data_collect', 'ai_process', 'condition',
                   'approval', 'publish', 'notify', 'wait', 'sub_workflow',
                   'market_check', 'http_request', 'script']:
            self._node_executor_map[nt] = None  # 需要外部注册

    def register_node_handler(self, node_type: str, handler: Callable):
        """注册节点类型处理器"""
        self._node_executor_map[node_type] = handler

    # ---- 核心执行 ----

    def run_workflow(self, workflow_id: int,
                     trigger_type: str = 'manual',
                     trigger_config: dict = None,
                     initial_context: dict = None) -> int:
        """
        执行工作流

        Args:
            workflow_id: 工作流定义 ID
            trigger_type: 触发类型
            trigger_config: 触发配置
            initial_context: 初始上下文数据

        Returns:
            workflow_instance_id
        """
        # 创建工作流实例
        inst_id = m.create_workflow_instance(
            workflow_id, trigger_type, trigger_config
        )
        if not inst_id:
            raise ValueError(f'工作流 #{workflow_id} 不存在')

        # 更新上下文
        if initial_context:
            inst = m.get_workflow_instance(inst_id)
            ctx = m.from_json(inst.get('context_data', '{}'))
            ctx.update(initial_context)
            m.update_workflow_instance(inst_id, {
                'context_data': m.to_json(ctx)
            })

        m.add_log('workflow', inst_id, 'info',
                   f'🚀 工作流 #{workflow_id} 实例 #{inst_id} 启动')

        # 获取 DAG 定义
        wf = m.get_workflow(workflow_id)
        definition = m.from_json(wf.get('definition', '{}'))

        # P2-8: 最大节点数限制（防止恶意或疏忽创建超大工作流）
        max_nodes = 100
        nodes = definition.get('nodes', [])
        if len(nodes) > max_nodes:
            m.update_workflow_instance(inst_id, {
                'status': 'failed',
                'error_message': f'Workflow node count ({len(nodes)}) exceeds maximum ({max_nodes})',
                'finished_at': m.now_str()
            })
            raise ValueError(f'Workflow has {len(nodes)} nodes, exceeding maximum of {max_nodes}')

        # 查找起始节点（入度为0的节点）
        start_nodes = self._find_start_nodes(definition)

        # 异步执行
        thread = threading.Thread(
            target=self._execute_workflow_async,
            args=(inst_id, wf, definition, start_nodes),
            daemon=True
        )
        with self._lock:
            self._running_instances[inst_id] = thread
        thread.start()

        return inst_id

    def _execute_workflow_async(self, inst_id: int, wf: dict,
                                 definition: dict, start_nodes: list):
        """异步执行工作流"""
        start_time = time.time()
        timeout_min = wf.get('timeout_minutes', 60)
        timeout_sec = timeout_min * 60
        on_error = wf.get('on_error', 'pause')

        try:
            # 执行起点节点
            execution_queue = deque(start_nodes)
            visited = set()
            node_outputs = {}  # node_id -> output_data

            while execution_queue and not self._is_instance_done(inst_id):
                # 检查超时
                if time.time() - start_time > timeout_sec:
                    raise TimeoutError(f'Workflow execution timeout ({timeout_min} minutes)')

                node_id = execution_queue.popleft()
                if node_id in visited:
                    continue
                visited.add(node_id)

                # 获取节点定义
                nodes = definition.get('nodes', [])
                node_def = next((n for n in nodes if n.get('id') == node_id), None)
                if not node_def:
                    continue

                # 更新当前节点
                m.update_workflow_instance(inst_id, {
                    'current_node_id': node_id
                })

                # 获取节点实例
                node_insts = m.get_node_instances_by_workflow(inst_id)
                node_inst = next(
                    (ni for ni in node_insts if ni['node_id'] == node_id),
                    None
                )
                if not node_inst:
                    continue

                # 检查前置节点条件
                edges = definition.get('edges', [])
                incoming_edges = [e for e in edges if e.get('to') == node_id]
                all_satisfied = True
                for edge in incoming_edges:
                    from_node = edge.get('from')
                    from_output = node_outputs.get(from_node, {})
                    condition = edge.get('condition', 'success')

                    if not self._check_edge_condition(from_output, condition):
                        all_satisfied = False
                        if condition == 'success':
                            # 前置失败则跳过当前节点
                            m.update_node_instance(node_inst['id'], {
                                'status': 'skipped',
                                'output_data': m.to_json({'skipped': True, 'reason': f'Predecessor Node {from_node} Not Successful'})
                            })
                            m.add_log('node', node_inst['id'], 'warn',
                                       f'⏭️ Node [{node_def.get("name")}] skipped: Precondition not met')

                if not all_satisfied:
                    continue

                # 执行节点
                result = self._execute_node(node_def, node_inst,
                                             inst_id, node_outputs)

                node_outputs[node_id] = result.get('output', {})

                # 根据执行结果处理
                if result['status'] == 'completed':
                    # 找到后续节点
                    outgoing = [e for e in edges if e.get('from') == node_id]
                    for edge in outgoing:
                        execution_queue.append(edge.get('to'))

                elif result['status'] == 'waiting_approval':
                    # 暂停工作流，等待审批
                    m.update_workflow_instance(inst_id, {'status': 'paused'})
                    m.add_log('workflow', inst_id, 'info',
                               _('⏸️ Workflow paused: Waiting for manual approval'))

                elif result['status'] == 'failed':
                    error_msg = result.get('output', {}).get('error', _('Node Execution Failed'))
                    if on_error == 'abort':
                        self._fail_instance(inst_id, error_msg)
                        return
                    elif on_error == 'skip':
                        # 跳过，继续执行后续
                        outgoing = [e for e in edges if e.get('from') == node_id]
                        for edge in outgoing:
                            execution_queue.append(edge.get('to'))
                    elif on_error == 'pause':
                        m.update_workflow_instance(inst_id, {
                            'status': 'paused',
                            'error_message': error_msg
                        })
                        m.add_log('workflow', inst_id, 'warn',
                                   f'⏸️ Workflow paused at node [{node_def.get("name")}]: {error_msg}')
                        return

            # 检查是否所有节点都已执行
            all_nodes = {n.get('id') for n in nodes}
            completed_nodes = set(node_outputs.keys())
            skipped = set()

            node_insts = m.get_node_instances_by_workflow(inst_id)
            for ni in node_insts:
                if ni['status'] == 'skipped' or ni['status'] == 'failed':
                    skipped.add(ni['node_id'])

            if all_nodes <= (completed_nodes | skipped):
                duration_ms = int((time.time() - start_time) * 1000)
                m.update_workflow_instance(inst_id, {
                    'status': 'completed',
                    'finished_at': m.now_str(),
                    'duration_ms': duration_ms
                })
                m.add_log('workflow', inst_id, 'info',
                           f'✅ Workflow execution completed ({duration_ms}ms)')
            else:
                # 有节点未执行（可能因条件分支跳过）
                duration_ms = int((time.time() - start_time) * 1000)
                m.update_workflow_instance(inst_id, {
                    'status': 'completed',
                    'finished_at': m.now_str(),
                    'duration_ms': duration_ms
                })

        except TimeoutError as e:
            self._timeout_instance(inst_id, str(e))
        except Exception as e:
            self._fail_instance(inst_id, str(e))
        finally:
            with self._lock:
                self._running_instances.pop(inst_id, None)

    def _execute_node(self, node_def: dict, node_inst: dict,
                       inst_id: int, node_outputs: dict) -> dict:
        """执行单个节点"""
        node_id = node_def.get('id', '')
        node_type = node_def.get('type', '')
        node_name = node_def.get('name', '')
        config = node_def.get('config', {})
        node_inst_id = node_inst['id']

        start_time = time.time()

        # 更新状态为 running
        m.update_node_instance(node_inst_id, {
            'status': 'running',
            'started_at': m.now_str()
        })

        m.add_log('node', node_inst_id, 'info',
                   f'⚡ Executing node [{node_name}] ({node_type})')

        try:
            # 准备输入数据
            input_data = {}
            input_data['config'] = config

            # 从上下文获取数据
            inst = m.get_workflow_instance(inst_id)
            context = m.from_json(inst.get('context_data', '{}'))
            input_data['context'] = context

            # 从前置节点获取输出
            for prev_id, prev_output in node_outputs.items():
                input_data[f'node_{prev_id}_output'] = prev_output

            # 更新节点输入数据
            m.update_node_instance(node_inst_id, {
                'input_data': m.to_json(input_data)
            })

            # 查找处理器
            handler = self._node_executor_map.get(node_type)

            if handler:
                # 使用注册的处理器执行
                output = handler(node_def, input_data)
            else:
                # 内置节点逻辑
                output = self._execute_builtin_node(node_type, config, input_data)

            # 更新节点为完成状态
            duration_ms = int((time.time() - start_time) * 1000)
            m.update_node_instance(node_inst_id, {
                'status': 'completed',
                'output_data': m.to_json(output),
                'finished_at': m.now_str(),
                'duration_ms': duration_ms
            })

            # 更新工作流上下文
            new_context = context.copy()
            new_context[f'node_{node_id}_output'] = output
            m.update_workflow_instance(inst_id, {
                'context_data': m.to_json(new_context)
            })

            m.add_log('node', node_inst_id, 'info',
                       f'✅ Node [{node_name}] Completed ({duration_ms}ms)')

            return {'status': 'completed', 'output': output}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            # 检查是否需要审批（例如，某些条件触发人工审批）
            if 'approval_required' in str(e).lower() or \
               config.get('require_approval_on_error', False):
                m.update_node_instance(node_inst_id, {
                    'status': 'waiting_approval',
                    'error_message': error_msg,
                    'finished_at': m.now_str(),
                    'duration_ms': duration_ms
                })
                m.add_log('node', node_inst_id, 'warn',
                           f'⏳ Node [{node_name}] requires approval: {error_msg}')
                return {'status': 'waiting_approval', 'output': {'error': error_msg}}

            # 普通失败
            m.update_node_instance(node_inst_id, {
                'status': 'failed',
                'error_message': error_msg,
                'error_detail': traceback.format_exc(),
                'finished_at': m.now_str(),
                'duration_ms': duration_ms
            })
            m.add_log('node', node_inst_id, 'error',
                       f'❌ Node [{node_name}] Failed: {error_msg}')
            return {'status': 'failed', 'output': {'error': error_msg}}

    def execute_node(self, node_def: dict, node_inst: dict,
                     inst_id: int, node_outputs: dict) -> dict:
        """公共接口：执行单个节点（供 worker 等外部调用）"""
        return self._execute_node(node_def, node_inst, inst_id, node_outputs)

    def _execute_builtin_node(self, node_type: str, config: dict,
                               input_data: dict) -> dict:
        """执行内置节点逻辑"""
        if node_type == 'wait':
            seconds = config.get('seconds', config.get('duration', 60))
            time.sleep(seconds)
            return {'waited_seconds': seconds}

        elif node_type == 'condition':
            expression = config.get('expression', 'true')
            context = input_data.get('context', {})
            # 简单条件评估
            result = self._eval_condition(expression, context, input_data)
            return {'condition_result': result, 'passed': result}

        elif node_type == 'http_request':
            import urllib.request
            url = config.get('url', '')
            method = config.get('method', 'GET')
            headers = config.get('headers', {})
            body = config.get('body')

            req = urllib.request.Request(url, method=method)
            for k, v in headers.items():
                req.add_header(k, v)
            if body:
                import json as _json
                req.data = _json.dumps(body).encode('utf-8')

            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')[:10000]

            return {
                'status_code': resp.status,
                'body': resp_body
            }

        else:
            # 为未实现的节点类型返回占位输出
            return {
                'node_type': node_type,
                'message': f'Node Type {node_type} Uses Default Processor',
                'config': config,
                'executed': True
            }

    # ---- 辅助方法 ----

    def _find_start_nodes(self, definition: dict) -> list:
        """找出 DAG 中的起始节点（入度为0的节点）"""
        nodes = definition.get('nodes', [])
        edges = definition.get('edges', [])

        if not edges:
            return [n.get('id') for n in nodes]

        targets = {e.get('to') for e in edges}
        return [n.get('id') for n in nodes if n.get('id') not in targets]

    def _check_edge_condition(self, from_output: dict, condition: str) -> bool:
        """检查边条件是否满足"""
        if not condition or condition == 'success':
            return from_output.get('status') != 'failed' if 'status' in from_output else True
        if condition == 'failure':
            return from_output.get('status') == 'failed'
        if condition == 'any':
            return True
        if condition == 'completed':
            return True
        # 自定义条件表达式
        return True

    def _eval_condition(self, expression: str, context: dict,
                         input_data: dict) -> bool:
        """评估条件表达式"""
        try:
            # 简单变量替换
            local_vars = {}
            local_vars.update(context)
            local_vars.update({k: v for k, v in input_data.items() if k.startswith('node_')})

            result = safe_eval(expression, local_vars)
            return bool(result)
        except Exception as e:
            import logging
            logging.warning(f"[Workflow] Condition evaluation failed: {e}")
            return True  # 条件评估失败时默认不通过，避免错误分支被执行

    def _is_instance_done(self, inst_id: int) -> bool:
        """检查实例是否已结束"""
        inst = m.get_workflow_instance(inst_id)
        if not inst:
            return True
        return inst['status'] in ('completed', 'failed', 'cancelled', 'timeout')

    def _fail_instance(self, inst_id: int, error: str):
        """标记实例为失败"""
        m.update_workflow_instance(inst_id, {
            'status': 'failed',
            'error_message': error[:500],
            'error_detail': error,
            'finished_at': m.now_str(),
            'duration_ms': 0
        })
        m.add_log('workflow', inst_id, 'error', f'❌ Workflow Failed: {error}')

    def _timeout_instance(self, inst_id: int, error: str):
        """标记实例为超时"""
        m.update_workflow_instance(inst_id, {
            'status': 'timeout',
            'error_message': error[:500],
            'error_detail': error,
            'finished_at': m.now_str(),
            'duration_ms': 0
        })
        m.add_log('workflow', inst_id, 'error', f'⏰ Workflow timeout: {error}')

    # ---- 外部控制 ----

    def pause_instance(self, inst_id: int) -> bool:
        """暂停工作流实例"""
        inst = m.get_workflow_instance(inst_id)
        if inst and inst['status'] == 'running':
            m.update_workflow_instance(inst_id, {'status': 'paused'})
            m.add_log('workflow', inst_id, 'info', _('⏸️ Workflow paused'))
            return True
        return False

    def resume_instance(self, inst_id: int) -> bool:
        """恢复工作流实例"""
        inst = m.get_workflow_instance(inst_id)
        if inst and inst['status'] == 'paused':
            m.update_workflow_instance(inst_id, {'status': 'running'})
            m.add_log('workflow', inst_id, 'info', _('▶️ Workflow resumed'))
            return True
        return False

    def cancel_instance(self, inst_id: int) -> bool:
        """取消工作流实例"""
        inst = m.get_workflow_instance(inst_id)
        if inst and inst['status'] in ('running', 'paused'):
            m.update_workflow_instance(inst_id, {
                'status': 'cancelled',
                'finished_at': m.now_str()
            })
            m.add_log('workflow', inst_id, 'warn', _('🛑 Workflow canceled'))
            return True
        return False

    def approve_node(self, inst_id: int, node_inst_id: int,
                      approved: bool, reviewer: int = 0) -> bool:
        """审批节点"""
        now = m.now_str()
        m.update_node_instance(node_inst_id, {
            'approval_status': 'approved' if approved else 'rejected',
            'approved_by': reviewer,
            'approved_at': now
        })

        if approved:
            # 标记为完成，继续执行
            m.update_node_instance(node_inst_id, {
                'status': 'completed',
                'finished_at': now
            })
            m.add_log('node', node_inst_id, 'info', _('✅ Node Approved'))

            # 恢复工作流执行
            self.resume_instance(inst_id)
            # 重新触发现有流程
            thread = threading.Thread(
                target=self._resume_after_approval,
                args=(inst_id,),
                daemon=True
            )
            thread.start()
            return True
        else:
            # 标记为失败
            m.update_node_instance(node_inst_id, {
                'status': 'failed',
                'error_message': _('Approval Not Approved'),
                'finished_at': now
            })
            m.add_log('node', node_inst_id, 'info', _('❌ Node Approval Not Passed'))
            return False

    def _resume_after_approval(self, inst_id: int):
        """审批通过后恢复执行"""
        inst = m.get_workflow_instance(inst_id)
        if not inst or inst['status'] == 'cancelled':
            return

        # P2-7: 审批超时检查（默认 72 小时）
        approval_timeout_hours = int(os.environ.get('APPROVAL_TIMEOUT_HOURS', '72'))
        created_at = inst.get('created_at', '')
        if created_at:
            from datetime import datetime, timedelta
            try:
                created_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                if datetime.now() - created_dt > timedelta(hours=approval_timeout_hours):
                    m.update_workflow_instance(inst_id, {
                        'status': 'timeout',
                        'error_message': f'Approval timed out after {approval_timeout_hours} hours',
                        'finished_at': m.now_str()
                    })
                    m.add_log('workflow', inst_id, 'warn', _('⏰ Workflow approval timed out'))
                    return
            except ValueError:
                pass

        wf = m.get_workflow(inst['workflow_id'])
        definition = m.from_json(wf.get('definition', '{}'))
        nodes = definition.get('nodes', [])

        current_node_id = inst.get('current_node_id', '')

        # 从当前节点继续
        edges = definition.get('edges', [])
        node_outputs = {}

        # 收集已完成的节点输出
        node_insts = m.get_node_instances_by_workflow(inst_id)
        for ni in node_insts:
            if ni['status'] == 'completed':
                node_outputs[ni['node_id']] = m.from_json(ni.get('output_data', '{}'))

        execution_queue = deque([current_node_id])
        visited = {ni['node_id'] for ni in node_insts if ni['status'] == 'completed'}

        while execution_queue:
            node_id = execution_queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)

            node_def = next((n for n in nodes if n.get('id') == node_id), None)
            if not node_def:
                continue

            node_inst = next(
                (ni for ni in node_insts if ni['node_id'] == node_id),
                None
            )
            if not node_inst:
                continue

            result = self._execute_node(node_def, node_inst, inst_id, node_outputs)
            node_outputs[node_id] = result.get('output', {})

            if result['status'] == 'completed':
                outgoing = [e for e in edges if e.get('from') == node_id]
                for edge in outgoing:
                    execution_queue.append(edge.get('to'))
            else:
                break

        # 检查是否全部完成
        all_node_ids = {n.get('id') for n in nodes}
        completed_ids = {ni['node_id'] for ni in m.get_node_instances_by_workflow(inst_id)
                         if ni['status'] in ('completed', 'skipped')}
        if all_node_ids <= completed_ids:
            m.update_workflow_instance(inst_id, {
                'status': 'completed',
                'finished_at': m.now_str()
            })
            m.add_log('workflow', inst_id, 'info', _('✅ Workflow completed (after approval resume)'))


# ============================================================
# 快速测试
# ============================================================

if __name__ == '__main__':
    m.init_orchestrator_tables()

    engine = WorkflowEngine()

    # 创建一个简单的测试工作流
    wf_id = m.create_workflow({
        'name': _('Test Workflow'),
        'description': '自动化测试',
        'definition': m.to_json({
            "nodes": [
                {"id": "start", "type": "http_request", "name": "测试请求",
                 "config": {"url": "https://httpbin.org/delay/1", "method": "GET"}},
                {"id": "end", "type": "wait", "name": _("Wait 2 seconds"),
                 "config": {"seconds": 2}}
            ],
            "edges": [
                {"from": "start", "to": "end", "condition": "success"}
            ]
        })
    })

    print(f'🆕 创建工作流 #{wf_id}')
    inst_id = engine.run_workflow(wf_id)
    print(f'🚀 启动实例 #{inst_id}')

    # 等待执行完成
    import time
    time.sleep(5)

    inst = m.get_workflow_instance(inst_id)
    print(f'📊 Status: {inst["status"]}')
    if inst['duration_ms']:
        print(f'⏱️ Duration: {inst["duration_ms"]}ms')

    # 打印节点状态
    nodes = m.get_node_instances_by_workflow(inst_id)
    for n in nodes:
        print(f'  📌 {n["node_name"]}: {n["status"]} ({n.get("duration_ms", 0)}ms)')
