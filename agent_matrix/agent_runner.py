#!/usr/bin/env python3
"""Agent Matrix — Agent 执行器

加载 Agent 配置 → 注入 System Prompt → 执行 LLM 调用 → 自检。
"""
import json, os, sys, logging

from i18n import _

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
            from agent_matrix.engine import AIEngine
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
        self._log(task_id, 'info', 'execution', _('🤖 {name} 开始执行任务', name=self.name))
        logs.append(_('[{name}] 接收任务: {title}', name=self.name, title=task.get("title", "")))

        # 2. 构建完整的 Prompt
        user_query = self._build_query(task)
        logs.append(_('[Prompt] 构造完成'))

        # 3. 调用 LLM
        engine = self._get_engine()
        if not engine or not engine.is_ready():
            err_msg = _('AI 引擎未就绪（{provider}/{model}）', provider=self.config.get("provider", "?"), model=self.config.get("model_name", "?"))
            self._log(task_id, 'error', 'execution', err_msg)
            return self._fail(err_msg, logs)

        self._log(task_id, 'info', 'api_call',
                   _('调用 {provider}/{model}', provider=self.config.get("provider"), model=self.config.get("model_name")))

        # 按 allowed_tools 白名单决定是否启用 ReAct 工具循环
        tools = self._get_tools()
        if tools:
            logs.append(_('[Tools] 启用 {count} 个工具，进入 ReAct 循环', count=len(tools)))
            response = self._run_react_loop(engine, user_query, history, tools, logs, task_id)
        elif history:
            response = engine.ask_with_history(history, user_query)
        else:
            response = engine.ask(user_query)

        if response.startswith('Error:'):
            self._log(task_id, 'error', 'execution', response)
            return self._fail(response, logs)

        logs.append(_('[LLM] 响应长度: {length} 字符', length=len(response)))
        self._log(task_id, 'info', 'execution', _('LLM 响应完成（{length} 字符）', length=len(response)))

        # 4. 自检 (Self-Critique)
        self_review = self._self_critique(response, task)
        logs.append(_('[Self-Critique] {review}', review=self_review.get("review", _("无"))))

        confidence = self_review.get('confidence', 0.85)
        self._log(task_id, 'info', 'self_review',
                   _('自检完成: confidence={confidence}, review={review}', confidence=confidence, review=self_review.get("review", "")[:100]))

        # 5. 如果置信度过低，重试
        retries = 0
        max_retries = task.get('max_retries', 2)
        while confidence < 0.7 and retries < max_retries:
            retries += 1
            logs.append(_('[Retry #{retry}] confidence={confidence} < 0.7，重新执行', retry=retries, confidence=confidence))
            self._log(task_id, 'warn', 'execution',
                       _('重试 #{retry}: confidence={confidence} < 0.7', retry=retries, confidence=confidence))

            # 用更明确的 prompt 重试，带入自检发现的问题点
            issues = self_review.get('issues', [])
            issues_str = ('\n'.join(f'- {i}' for i in issues)) if issues else _('（无具体问题清单）')
            retry_query = (
                _('之前的结果不理想（置信度: {confidence}）。\n', confidence=confidence)
                + _('自检反馈: {review}\n', review=self_review.get('review', ''))
                + _('需改进的问题:\n')
                + issues_str + '\n'
                + _('改进建议: {suggestion}\n\n', suggestion=self_review.get('suggestion', '') or _('无'))
                + _('请针对上述问题重新执行任务。\n\n')
                + _('原任务: {query}', query=user_query)
            )
            response = engine.ask(retry_query)
            if response.startswith('Error:'):
                break
            self_review = self._self_critique(response, task)
            confidence = self_review.get('confidence', 0.85)
            logs.append(_('[Retry #{retry}] 新 confidence={confidence}', retry=retries, confidence=confidence))
            self._log(task_id, 'info', 'self_review',
                       _('重试 #{retry} 后 confidence={confidence}', retry=retries, confidence=confidence))

        # 6. 更新统计
        if self.models:
            self.models.update_agent_stats(self.agent_id, success=(confidence >= 0.7))

        if confidence >= 0.7:
            self._log(task_id, 'info', 'execution', _('✅ 任务完成, confidence={confidence}', confidence=confidence))
            return {
                'status': 'completed',
                'response': response,
                'confidence': confidence,
                'self_review': self_review.get('review', ''),
                'logs': logs,
                'retries': retries
            }
        else:
            err_msg = _('重试 {retries} 次后 confidence={confidence} 仍低于阈值', retries=retries, confidence=confidence)
            self._log(task_id, 'error', 'execution', err_msg)
            return self._fail(err_msg, logs, confidence)

    def _get_tools(self):
        """按 Agent 的 allowed_tools 返回可用工具 schema，无则返回 []"""
        try:
            from agent_matrix.tools import get_tools_for_agent
            return get_tools_for_agent(self.config.get('allowed_tools'))
        except Exception as e:
            logger.warning(_('[{name}] 加载工具失败，退回单轮: {e}', name=self.name, e=e))
            return []

    def _run_react_loop(self, engine, user_query, history, tools, logs, task_id,
                        max_rounds=5):
        """ReAct 工具循环：思考→调用工具→观察→再思考，直到模型给出终态答复。

        任何异常/达到轮次上限均安全收尾，返回已有的文本（或错误字符串）。
        """
        from agent_matrix.tools import execute_tool

        # 构建初始消息
        messages = [{"role": "system", "content": self.config.get('system_prompt', '')}]
        if history:
            for h in history:
                role = 'user' if h.get('role') == 'user' else 'assistant'
                messages.append({"role": role, "content": h.get('content', '')})
        messages.append({"role": "user", "content": user_query})

        last_text = ''
        for round_i in range(1, max_rounds + 1):
            msg = engine.chat_with_tools(messages, tools)
            if msg is None:
                logs.append(_('[ReAct #{round_i}] 工具调用返回空，退回普通对话', round_i=round_i))
                fallback = engine.ask(user_query)
                return fallback if not last_text else last_text

            tool_calls = getattr(msg, 'tool_calls', None)
            if msg.content:
                last_text = msg.content

            # 模型未请求工具 → 终态答复
            if not tool_calls:
                self._log(task_id, 'info', 'execution',
                           _('ReAct 于第 {round_i} 轮结束（无更多工具调用）', round_i=round_i))
                return last_text or ''

            # 把 assistant 的 tool_calls 消息追加回上下文
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in tool_calls
                ]
            })

            # 逐个执行工具，把结果作为 tool 消息回灌
            for tc in tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except (json.JSONDecodeError, TypeError):
                    args = {}
                self._log(task_id, 'info', 'tool_call', _('调用工具 {name} args={args}', name=name, args=args))
                logs.append(_('[ReAct #{round_i}] 调用工具 {name}', round_i=round_i, name=name))
                result = execute_tool(name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)[:4000]
                })

        # 达到轮次上限，做最后一次无工具收尾
        logs.append(_('[ReAct] 达到最大轮次 {max_rounds}，强制收尾', max_rounds=max_rounds))
        final = engine.chat_with_tools(messages, tools)
        if final is not None and final.content:
            return final.content
        return last_text or _('（工具循环达到上限，未产出最终答复）')

    def _build_query(self, task):
        """构造发给 LLM 的用户消息"""
        parts = [_("## 任务: {title}", title=task.get('title', ''))]

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
            parts.append(_("\n### 输入参数:"))
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
            parts.append(_("\n### 期望输出:\n{data}", data=json.dumps(expected, ensure_ascii=False, indent=2)))

        parts.append(_("\n请严格按照要求执行，完成后输出结果。"))
        return '\n'.join(parts)

    def _self_critique(self, response, task):
        """自检：先做规则初判，灰区(0.5~0.8)时再让 LLM 做结构化自评"""
        expected = task.get('expected_output', {})
        if isinstance(expected, str):
            try:
                expected = json.loads(expected)
            except (json.JSONDecodeError, TypeError):
                expected = {}

        # 1. 规则初判：检查输出长度和格式
        review_parts = []
        confidence = 0.85

        if len(response) < 50:
            review_parts.append(_("输出过短 (<50字符)"))
            confidence = max(0.3, confidence - 0.3)
        else:
            review_parts.append(_("输出长度合理 ({length}字符)", length=len(response)))

        if isinstance(expected, dict) and expected.get('fields'):
            # 检查是否包含期望字段
            matched = sum(1 for f in expected['fields'] if f in response.lower())
            field_ratio = matched / len(expected['fields'])
            if field_ratio < 0.5:
                review_parts.append(_("期望字段匹配率低（{matched}/{total}）", matched=matched, total=len(expected['fields'])))
                confidence = max(0.4, confidence - 0.2)

        if 'Error' in response or '错误' in response or '失败' in response:
            review_parts.append(_("输出包含错误/失败信息"))
            confidence = max(0.2, confidence - 0.3)

        confidence = round(confidence, 2)
        result = {
            'confidence': confidence,
            'review': '; '.join(review_parts),
            'issues': [],
            'suggestion': ''
        }

        # 2. 灰区触发 LLM 结构化自评（仅 0.5~0.8 之间，控制成本）
        if 0.5 <= confidence <= 0.8:
            llm_review = self._llm_critique(response, task)
            if llm_review:
                result.update(llm_review)

        return result

    def _llm_critique(self, response, task):
        """让 LLM 对输出做结构化自评，失败时返回 None 由规则结果兜底"""
        engine = self._get_engine()
        if not engine or not engine.is_ready():
            return None

        critique_prompt = (
            "你是严格的质量审查员。请评估下面的【任务】与【输出】是否达标，"
            "只输出纯 JSON（不要 markdown 代码块），格式：\n"
            '{"confidence": 0.0-1.0 的浮点数, "issues": ["问题1", ...], "suggestion": "改进建议"}\n\n'
            f"【任务】{task.get('title', '')}\n{task.get('description', '')}\n\n"
            f"【输出】\n{response[:2000]}"
        )
        try:
            raw = engine.ask(critique_prompt, temperature=0.2)
            if not raw or raw.startswith('Error:'):
                return None
            import re as _re
            match = _re.search(r'\{[\s\S]*\}', raw)
            if not match:
                return None
            data = json.loads(match.group())
            conf = float(data.get('confidence', 0.85))
            conf = round(max(0.0, min(1.0, conf)), 2)
            issues = data.get('issues', []) or []
            suggestion = data.get('suggestion', '') or ''
            review = _('LLM自评: ') + (suggestion or _('通过'))
            if issues:
                review += _(' | 问题: ') + '; '.join(str(i) for i in issues)
            return {
                'confidence': conf,
                'review': review,
                'issues': issues,
                'suggestion': suggestion
            }
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(_('[{name}] LLM 自评解析失败，回退规则结果: {e}', name=self.name, e=e))
            return None

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
