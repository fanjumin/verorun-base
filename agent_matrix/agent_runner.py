#!/usr/bin/env python3
"""Agent Matrix — Agent 执行器

加载 Agent 配置 → 注入 System Prompt → 执行 LLM 调用 → 自检。
"""
import json, os, sys, logging
logger = logging.getLogger(__name__)


class AgentRunner:
    """Agent 执行器：负责一次 Agent 对话的完整生命周期"""

    def __init__(self, agent_config: dict, db_models=None):
        """
        agent_config: agent_matrix 行字典
        db_models: models 模块引用（用于日志记录）
        """
        self.config = agent_config
        self.agent_id = agent_config.get('id', 0)
        self.name = agent_config.get('name', 'Unnamed Agent')
        self.role_type = agent_config.get('role_type', 'sub')
        self.domain = agent_config.get('domain', 'general')

        # 延迟加载 engine，避免循环依赖
        self._engine = None
        self._engine_ready = False
        self.models = db_models

    def _get_engine(self):
        if not self._engine:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
            import traceback
            with open('/tmp/hermes_runner_debug.log', 'a') as f:
                f.write(f"AgentRunner._get_engine called for agent_id={self.agent_id}, name={self.name}, "
                       f"provider={self.config.get('provider','?')}, model={self.config.get('model_name','?')}, "
                       f"api_key_ref={self.config.get('api_key_ref','?')}\n")
                traceback.print_stack(file=f)
            from agent_matrix.engine import AIEngine, _get_system_key
            with open('/tmp/hermes_runner_debug.log', 'a') as f:
                test_key = _get_system_key(self.config.get('api_key_ref', ''))
                f.write(f"  -> _get_system_key returned: last_8={test_key[-8:] if test_key else 'N/A'}\n")
            self._engine = AIEngine(self.config)
            self._engine_ready = self._engine.is_ready()
        return self._engine

    def is_ready(self):
        self._get_engine()
        return self._engine_ready

    def execute(self, task: dict, history: list = None):
        """
        执行一次 Agent 任务

        task: {
            'task_id': 'AT-...',
            'title': '...',
            'description': '...',
            'input_data': {...},
        }
        history: 可选的历史对话 (用于多轮)

        Returns: {
            'status': 'completed' | 'failed',
            'response': '...',
            'confidence': 0.0-1.0,
            'self_review': '...',
            'logs': [...]
        }
        """
        logs = []
        task_id = task.get('task_id', 'unknown')

        # 1. 日志：开始执行
        self._log(task_id, 'info', 'execution', f'🤖 {self.name} 开始执行任务')
        logs.append(f'[{self.name}] 接收任务: {task.get("title", "")}')

        # 2. 构建完整的 Prompt
        user_query = self._build_query(task)
        logs.append(f'[Prompt] 构造完成')

        # 3. 调用 LLM
        engine = self._get_engine()
        if not engine or not engine.is_ready():
            err_msg = f'AI 引擎未就绪（{self.config.get("provider", "?")}/{self.config.get("model_name", "?")}）'
            self._log(task_id, 'error', 'execution', err_msg)
            return self._fail(err_msg, logs)

        self._log(task_id, 'info', 'api_call',
                   f'调用 {self.config.get("provider")}/{self.config.get("model_name")}')

        if history:
            response = engine.ask_with_history(history, user_query)
        else:
            response = engine.ask(user_query)

        if response.startswith('Error:'):
            self._log(task_id, 'error', 'execution', response)
            return self._fail(response, logs)

        logs.append(f'[LLM] 响应长度: {len(response)} 字符')
        self._log(task_id, 'info', 'execution', f'LLM 响应完成 ({len(response)} 字符)')

        # 4. 自检 (Self-Critique)
        self_review = self._self_critique(response, task)
        logs.append(f'[Self-Critique] {self_review.get("review", "无")}')

        confidence = self_review.get('confidence', 0.85)
        self._log(task_id, 'info', 'self_review',
                   f'自检完成: confidence={confidence}, review={self_review.get("review", "")[:100]}')

        # 5. 如果置信度过低，重试
        retries = 0
        max_retries = task.get('max_retries', 2)
        while confidence < 0.7 and retries < max_retries:
            retries += 1
            logs.append(f'[Retry #{retries}] confidence={confidence} < 0.7，重新执行')
            self._log(task_id, 'warn', 'execution',
                       f'重试 #{retries}: confidence={confidence} < 0.7')

            # 用更明确的 prompt 重试
            retry_query = (
                f"之前的结果不理想（置信度: {confidence}）。\n"
                f"自检反馈: {self_review.get('review', '')}\n\n"
                f"请重新执行任务，特别注意以下改进点。\n\n"
                f"原任务: {user_query}"
            )
            response = engine.ask(retry_query)
            if response.startswith('Error:'):
                break
            self_review = self._self_critique(response, task)
            confidence = self_review.get('confidence', 0.85)
            logs.append(f'[Retry #{retries}] 新 confidence={confidence}')
            self._log(task_id, 'info', 'self_review',
                       f'重试 #{retries} 后 confidence={confidence}')

        # 6. 更新统计
        if self.models:
            self.models.update_agent_stats(self.agent_id, success=(confidence >= 0.7))

        if confidence >= 0.7:
            self._log(task_id, 'info', 'execution', f'✅ 任务完成, confidence={confidence}')
            return {
                'status': 'completed',
                'response': response,
                'confidence': confidence,
                'self_review': self_review.get('review', ''),
                'logs': logs,
                'retries': retries
            }
        else:
            err_msg = f'重试 {retries} 次后 confidence={confidence} 仍低于阈值'
            self._log(task_id, 'error', 'execution', err_msg)
            return self._fail(err_msg, logs, confidence)

    def _build_query(self, task):
        """构造发给 LLM 的用户消息"""
        parts = [f"## 任务: {task.get('title', '')}"]

        description = task.get('description', '')
        if description:
            parts.append(f"\n{description}")

        input_data = task.get('input_data', {})
        if isinstance(input_data, str):
            try:
                input_data = json.loads(input_data)
            except (json.JSONDecodeError, TypeError):
                pass
        if isinstance(input_data, dict) and input_data:
            parts.append("\n### 输入参数:")
            for k, v in input_data.items():
                if isinstance(v, str) and len(v) > 500:
                    parts.append(f"- {k}: {v[:500]}...")
                else:
                    parts.append(f"- {k}: {v}")

        expected = task.get('expected_output', {})
        if isinstance(expected, str):
            try:
                expected = json.loads(expected)
            except (json.JSONDecodeError, TypeError):
                pass
        if expected:
            parts.append(f"\n### 期望输出:\n{json.dumps(expected, ensure_ascii=False, indent=2)}")

        parts.append("\n请严格按照要求执行，完成后输出结果。")
        return '\n'.join(parts)

    def _self_critique(self, response, task):
        """自检：让 LLM 对自己的输出打分"""
        title = task.get('title', '')
        expected = task.get('expected_output', {})
        if isinstance(expected, str):
            try:
                expected = json.loads(expected)
            except (json.JSONDecodeError, TypeError):
                expected = {}

        # 简单自检：检查输出长度和格式
        review_parts = []
        confidence = 0.85

        if len(response) < 50:
            review_parts.append("输出过短 (<50字符)")
            confidence = max(0.3, confidence - 0.3)
        else:
            review_parts.append(f"输出长度合理 ({len(response)}字符)")

        if isinstance(expected, dict) and expected.get('fields'):
            # 检查是否包含期望字段
            matched = sum(1 for f in expected['fields'] if f in response.lower())
            field_ratio = matched / len(expected['fields'])
            if field_ratio < 0.5:
                review_parts.append(f"期望字段匹配率低 ({matched}/{len(expected['fields'])})")
                confidence = max(0.4, confidence - 0.2)

        if 'Error' in response or '错误' in response or '失败' in response:
            review_parts.append("输出包含错误/失败信息")
            confidence = max(0.2, confidence - 0.3)

        if not review_parts:
            review_parts.append("基本质量通过")
            confidence = min(1.0, confidence + 0.1)

        return {
            'confidence': round(confidence, 2),
            'review': '; '.join(review_parts)
        }

    def _log(self, task_id, level, log_type, message):
        if self.models:
            try:
                self.models.add_log(task_id, self.agent_id, level, log_type, message)
            except Exception:
                pass

    def _fail(self, error, logs, confidence=0.0):
        return {
            'status': 'failed',
            'response': error,
            'confidence': confidence,
            'self_review': '',
            'logs': logs + [f'[FAIL] {error}']
        }
