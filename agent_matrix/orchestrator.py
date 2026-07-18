#!/usr/bin/env python3
"""
Agent Matrix — 任务协调核心 (Orchestrator)
========================================
负责任务分解 → Agent 选择 → 任务下发 → 结果收集 → 报告生成。
"""
import json, os, sys, logging, time
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    AgentOrchestrator — 主协调器

    核心流程:
      1. decompose_task(instruction) → Task分解方案
      2. dispatch_sub_tasks(decomposed) → 并行下发子任务
      3. collect_results() → 等待并收集
      4. aggregate_report(results) → 生成汇总报告
    """

    def __init__(self, models_module=None, engine_module=None, runner_class=None):
        self.models = models_module
        self._engine_module = engine_module
        self._runner_class = runner_class

    # -------------------------------------------------------
    # 外部入口
    # -------------------------------------------------------

    def process_instruction(self, instruction: str, master_agent_id: int, session_id: str = None, mode: str = 'fast'):
        """
        处理用户指令的完整流程（同步版本）

        返回: {
            'master_task_id': 'AT-...',
            'decomposition': [...],
            'sub_task_results': [...],
            'status': 'completed' | 'failed',
            'summary': '汇总报告',
            'all_completed': bool
        }
        """
        startup = time.time()

        # 注入模式指令
        mode_prefixes = {
            'deep': '【深度思考模式】请进行深入、全面、细致的分析，尽可能给出最详尽的回答。',
            'image': '【图像处理模式】请优先将任务委派给内容管理Agent（CMS域），由负责图像生成，包括文生图、图生图、配图等操作。',
        }
        if mode in mode_prefixes:
            instruction = mode_prefixes[mode] + '\n\n' + instruction

        # 图像模式：派发给 CMS Agent（含图像能力）
        if mode == 'image':
            cms_agents = [a for a in self.models.list_agents(role_type='sub', active_only=True)
                          if a.get('domain') == 'cms']
            if cms_agents:
                cms_agent = cms_agents[0]
                instruction = (f'请将以下任务委派给内容管理Agent（ID={cms_agent["id"]}, '
                               f'名称={cms_agent["name"]}），由其执行图像相关操作：\n\n{instruction}')

        # 1. 创建 Master 任务
        master_task_id = self.models.create_task({
            'source_agent_id': master_agent_id,
            'target_agent_id': master_agent_id,
            'task_type': 'composite',
            'title': instruction[:100],
            'description': instruction,
            'input_data': {'raw_instruction': instruction},
            'max_retries': 1,
            'timeout_seconds': 600,
        })
        self.models.update_task_status(master_task_id, 'running')

        # 2. 获取 Master Agent 配置
        master_config = self.models.get_agent(master_agent_id)
        if not master_config:
            self.models.update_task_status(master_task_id, 'failed', error_message='Master Agent 不存在')
            return {'status': 'failed', 'error': 'Master Agent 不存在'}

        self._add_task_log(master_task_id, master_agent_id, 'info', 'execution',
                           f'开始处理指令: {instruction[:80]}...')

        # 3. 任务分解
        try:
            decomposed = self.decompose_task(instruction, master_config)
        except Exception as e:
            self.models.update_task_status(master_task_id, 'failed', error_message=str(e))
            self._add_task_log(master_task_id, master_agent_id, 'error', 'execution',
                               f'任务分解失败: {e}')
            return {'status': 'failed', 'error': f'任务分解失败: {e}', 'master_task_id': master_task_id}

        self._add_task_log(master_task_id, master_agent_id, 'info', 'execution',
                           f'任务分解完成: {len(decomposed)} 个子任务')

        # 4. 保存会话消息
        if session_id:
            self.models.add_message(session_id, 'user', instruction, master_task_id=master_task_id)

        # 5. 下发子任务（传入原始指令用于参考图识别）
        sub_results = self.dispatch_sub_tasks(decomposed, master_task_id, session_id, original_instruction=instruction)

        # 6. 汇总结果
        all_completed = all(r.get('status') == 'completed' for r in sub_results)
        total_time = round(time.time() - startup, 2)

        # 7. 更新 Master 任务
        if all_completed:
            self.models.update_task_status(master_task_id, 'completed',
                                           confidence=1.0,
                                           self_review=f'所有子任务完成 ({total_time}s)')
        else:
            failed_count = sum(1 for r in sub_results if r.get('status') == 'failed')
            self.models.update_task_status(
                master_task_id,
                'completed' if failed_count < len(sub_results) else 'failed',
                self_review=f'{len(sub_results)}个子任务, {failed_count}个失败 ({total_time}s)'
            )

        self._add_task_log(master_task_id, master_agent_id, 'info', 'execution',
                           f'任务完成 ({total_time}s), 状态: {"全部完成" if all_completed else "部分失败"}')

        # 8. 保存会话回复
        summary = self._build_summary(decomposed, sub_results, total_time, all_completed)
        if session_id:
            self.models.add_message(
                session_id, 'master', summary,
                agent_id=master_agent_id, agent_name='Athena',
                master_task_id=master_task_id
            )

        return {
            'master_task_id': master_task_id,
            'decomposition': decomposed,
            'sub_task_results': sub_results,
            'status': 'completed' if all_completed else 'partial',
            'summary': summary,
            'all_completed': all_completed,
            'duration_s': total_time
        }

    # -------------------------------------------------------
    # 智能记忆：对话结束自动提取（Write 层）
    # -------------------------------------------------------
    _extraction_executor = None

    @classmethod
    def _get_executor(cls):
        """延迟创建 ThreadPoolExecutor（避免多进程问题）"""
        import concurrent.futures
        if cls._extraction_executor is None:
            cls._extraction_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=2, thread_name_prefix='kb_extract_'
            )
        return cls._extraction_executor

    def _on_task_complete(self, conversation_text: str, user_id: int, task_result: dict):
        """对话结束 → 异步判断 → 送 Cleaner（不阻塞响应）"""
        try:
            self._get_executor().submit(
                self._async_extract_and_store, conversation_text, user_id, task_result
            )
        except Exception as e:
            logger.warning(f"提交知识提取任务失败 user={user_id}: {e}")

    def _async_extract_and_store(self, conversation_text: str, user_id: int, task_result: dict):
        """后台线程执行提取+入库（不阻塞对话响应）"""
        try:
            if not self._should_extract(conversation_text, task_result):
                return

            facts = self._extract_facts(conversation_text)
            if not facts:
                return

            from auth_center.routes.cleaner_agent import process_clean_content
            for fact in facts:
                try:
                    process_clean_content(fact, admin_id=user_id)
                except Exception as e:
                    logger.warning(f"单条知识入库失败 user={user_id}: {e}")
        except Exception as e:
            logger.error(f"自动知识提取失败 user={user_id}: {e}")

    def _should_extract(self, conversation_text: str, task_result: dict) -> bool:
        """判断对话是否值得提取知识"""
        import hashlib

        conv = (conversation_text or '').strip()
        if not conv:
            return False

        # 纯寒暄过滤：太短的跳过
        if len(conv) < 20:
            return False

        # 敏感信息过滤
        import re
        sensitive_patterns = [
            r'\b1[3-9]\d{9}\b',           # 手机号
            r'\b\d{6}(19|20)\d{8}[\dXx]\b',  # 身份证
            r'(password|密码|secret|密钥|AKSK|access_key)',  # 密钥类
        ]
        for pat in sensitive_patterns:
            if re.search(pat, conv, re.IGNORECASE):
                return False

        # 幂等保护：已处理过的跳过
        try:
            conv_hash = hashlib.md5(conv.encode()).hexdigest()
            from models import get_db
            with get_db() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM knowledge_queue WHERE processed_hash = %s LIMIT 1",
                    (conv_hash,)
                ).fetchone()
                if exists:
                    return False
                # 标记为已处理
                conn.execute(
                    "INSERT INTO knowledge_queue (source, raw_content, status, processed_hash) VALUES (%s,%s,%s,%s)",
                    ('auto_extract', conv[:500], 'processed', conv_hash)
                )
                conn.commit()
        except Exception:
            pass  # 幂等检查失败不影响提取

        # 必须有实质内容才提取
        return True

    def _extract_facts(self, conversation_text: str) -> list:
        """
        用轻量 LLM 调用从对话中提取关键事实。
        返回事实列表，每条为简洁陈述句。
        失败返回空列表，不影响对话响应。
        """
        import requests, json as _json

        prompt = (
            "从以下对话中提取关键事实，每条一行，简洁陈述。只提取客观事实，不推测。\n"
            "格式：每行一条事实，以 '- ' 开头。\n"
            "跳过寒暄和闲聊。如果对话中没有任何值得记录的事实，输出 '无'。\n\n"
            "对话：\n" + conversation_text[:4000] + "\n\n"
            "输出示例：\n"
            "- 用户经营餐饮品牌\n"
            "- 用户偏好暖色调设计\n"
            "- 用户上次建了名为XX餐厅的官网\n"
        )

        try:
            # 使用与 orchestrator 相同的 AI 配置
            agent = self.models.get_agent(1)  # Master Agent 配置
            if not agent:
                return []

            api_url = os.environ.get(
                'EASYKAI_LLM_URL',
                agent.get('api_url', 'https://api.deepseek.com/v1/chat/completions')
            )
            api_key = os.environ.get(
                'EASYKAI_LLM_KEY',
                agent.get('api_key', '')
            )
            model = os.environ.get(
                'EASYKAI_LLM_MODEL',
                agent.get('model_name', 'deepseek-chat')
            )

            resp = requests.post(
                api_url,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 500,
                    'temperature': 0.3,
                },
                timeout=10,
            )
            resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content']

            # 解析事实列表
            facts = []
            for line in content.strip().split('\n'):
                line = line.strip()
                if line.startswith('- ') and len(line) > 3:
                    fact = line[2:].strip()
                    if fact and fact != '无':
                        facts.append(fact)

            logger.info(f"提取事实 {len(facts)} 条: {facts}")
            return facts

        except Exception as e:
            logger.warning(f"事实提取 LLM 调用失败: {e}")
            return []

    # -------------------------------------------------------
    # 任务分解
    # -------------------------------------------------------

    def decompose_task(self, instruction: str, master_config: dict):
        """
        任务分解：让 Master Agent 将指令拆分为子任务

        返回: [{
            'title': str,
            'description': str,
            'target_agent_name': str,
            'task_type': 'execute' | 'review',
            'priority': int,
            'input_data': dict,
            'expected_output': dict
        }, ...]
        """
        # 获取可用 Sub Agents 列表
        all_agents = self.models.list_agents(active_only=True)
        sub_agents = [a for a in all_agents if a['role_type'] == 'sub']

        # 构建系统提示：注入可用 Agent 列表
        agent_list_str = json.dumps(
            [{'name': a['name'], 'domain': a['domain'],
              'managed_modules': a['managed_modules'],
              'description': a['description']}
             for a in sub_agents],
            ensure_ascii=False, indent=2
        )

        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from agent_matrix.engine import AIEngine

        engine = AIEngine(master_config)

        if not engine.is_ready():
            logger.warning("Master Agent AI 引擎未就绪，使用模板分解")
            return self._template_decompose(instruction, sub_agents)

        # 加载 Master Agent 的 System Prompt（从文件）
        master_prompt = self._load_prompt(master_config.get('system_prompt', ''))

        decompose_prompt = f"""{master_prompt}

现在，用户下达了以下指令：

<instruction>
{instruction}
</instruction>

当前可用的 Sub Agent 团队：
{agent_list_str}

请按以下 JSON 格式输出任务分解方案（不要加 markdown 代码块标记，只输出纯 JSON）：

{{
  "tasks": [
    {{
      "title": "子任务简要标题",
      "description": "子任务详细描述，包含执行要求",
      "target_agent_name": "目标 Agent 名称（必须在上面的列表中）",
      "task_type": "execute",
      "priority": 5,
      "input_data": {{"action": "具体操作", "params": {{...}}}},
      "expected_output": {{"fields": ["期望输出的字段名"]}}
    }}
  ]
}}

注意：
- 如果没有合适的 Sub Agent，设 target_agent_name 为 "none" 说明原因
- 如果指令可以直接回复（无需子任务），输出一个空 tasks 数组并设置 direct_reply
- 任务之间如果有依赖关系，在 description 中注明
- 每个任务必须能独立执行"""

        response = engine.ask(decompose_prompt, temperature=0.3)

        # 解析 JSON 响应
        try:
            # 尝试直接解析
            data = json.loads(response)
            tasks = data.get('tasks', [])
        except (json.JSONDecodeError, TypeError):
            # 尝试提取 JSON 块
            import re
            match = re.search(r'\{[\s\S]*"tasks"[\s\S]*\}', response)
            if match:
                try:
                    data = json.loads(match.group())
                    tasks = data.get('tasks', [])
                except (json.JSONDecodeError, TypeError):
                    tasks = []
            else:
                tasks = []

        if not tasks:
            logger.info("Master Agent 未分解出子任务，使用模板分解作为 fallback")
            return self._template_decompose(instruction, sub_agents)

        # 图像关键词集合（与 _template_decompose 同步）
        _ai_image_kw = {'图片', '图像', '配图', '封面', '海报', '生成图片', '文生图',
                        '画图', '裁剪', '压缩', '格式转换', '图库', '社交媒体配图'}

        # 将 Agent 名称映射为 ID
        agent_map = {a['name']: a for a in sub_agents}
        result = []
        for t in tasks:
            agent_name = t.get('target_agent_name', '')
            if agent_name and agent_name in agent_map:
                agent = agent_map[agent_name]
                title_desc = (t.get('title', '') + ' ' + t.get('description', '')).lower()
                target_module = 'image' if any(kw in title_desc for kw in _ai_image_kw) else agent.get('domain', '')
                result.append({
                    'title': t.get('title', ''),
                    'description': t.get('description', ''),
                    'target_agent_id': agent['id'],
                    'target_agent_name': agent['name'],
                    'target_module': target_module,
                    'task_type': t.get('task_type', 'execute'),
                    'priority': t.get('priority', 5),
                    'input_data': t.get('input_data', {}),
                    'expected_output': t.get('expected_output', {}),
                })
            else:
                logger.warning(f"任务 '{t.get('title')}' 指向未知 Agent: {agent_name}")

        return result if result else self._template_decompose(instruction, sub_agents)

    def _template_decompose(self, instruction, sub_agents):
        """模板分解：AI 不可用时，根据关键词匹配。
        关键词自动从每个角色的 domain + managed_modules 动态生成。
        """
        instruction_lower = instruction.lower()
        matched = []

        # 图像关键词集合（始终匹配）
        _image_kw = {'图片', '图像', '配图', '封面', '海报', '生成图片', '文生图',
                     '画图', '裁剪', '压缩', '格式转换', '图库', '社交媒体配图'}

        # 从 sub_agents 动态构建关键词映射
        agent_keywords = {}
        for a in sub_agents:
            name = a['name']
            kws = set()
            # 1. domain 关键词
            domain = (a.get('domain') or '').lower()
            if domain and domain != 'general':
                kws.add(domain)
            # 2. managed_modules 关键词
            modules = []
            try:
                modules = json.loads(a.get('managed_modules') or '[]')
            except (json.JSONDecodeError, TypeError):
                pass
            for mod in modules:
                if isinstance(mod, str):
                    kws.add(mod.lower())
                    # 模块名拆分（site_builder → site, builder）
                    for part in mod.replace('-', '_').split('_'):
                        if len(part) > 2:
                            kws.add(part)
            # 3. name 拆分关键词
            for part in name.replace('-', ' ').replace('_', ' ').split():
                w = part.lower().strip()
                if len(w) > 2:
                    kws.add(w)
            agent_keywords[name] = list(kws)

        agent_map = {a['name']: a for a in sub_agents}
        found_agents = set()

        for agent_name, keywords in agent_keywords.items():
            if agent_name not in agent_map:
                continue
            for kw in keywords:
                if kw in instruction_lower:
                    if agent_name not in found_agents:
                        a = agent_map[agent_name]
                        target_module = 'image' if kw in _image_kw else a.get('domain', '')
                        matched.append({
                            'title': f'{a["description"].split("—")[0] if "—" in a["description"] else a["name"]} — 指令相关操作',
                            'description': instruction[:200],
                            'target_agent_id': a['id'],
                            'target_agent_name': a['name'],
                            'target_module': target_module,
                            'task_type': 'execute',
                            'priority': 5,
                            'input_data': {'raw_instruction': instruction},
                            'expected_output': {'fields': ['result']},
                        })
                        found_agents.add(agent_name)
                    break

        return matched

    # -------------------------------------------------------
    # 任务分发与执行
    # -------------------------------------------------------

    def dispatch_sub_tasks(self, tasks: list, master_task_id: str, session_id: str = None, original_instruction: str = ''):
        """
        并行分发并执行子任务（ThreadPoolExecutor + 超时熔断）

        返回: [{
            'sub_task_id': 'AT-...',
            'agent_name': '...',
            'status': 'completed' | 'failed',
            'response': '...',
            'confidence': 0.0,
            'self_review': '...',
            'logs': [...]
        }, ...]
        """
        from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
        import threading

        results = []
        futures = {}
        completed_count = 0
        total = len(tasks)
        results_lock = threading.Lock()

        def _run_single(task_def):
            """在线程池中执行单个子任务"""
            target_id = task_def['target_agent_id']
            agent_config = self.models.get_agent(target_id)
            if not agent_config:
                return {
                    'sub_task_id': None,
                    'agent_name': task_def.get('target_agent_name', '?'),
                    'status': 'failed',
                    'error': 'Agent 配置不存在',
                    'title': task_def.get('title', ''),
                }

            # 创建子任务记录
            sub_task_id = self.models.create_task({
                'source_agent_id': agent_config.get('id', 0),
                'target_agent_id': target_id,
                'parent_task_id': master_task_id,
                'master_task_id': master_task_id,
                'task_type': task_def.get('task_type', 'execute'),
                'title': task_def.get('title', ''),
                'description': task_def.get('description', ''),
                'input_data': task_def.get('input_data', {}),
                'expected_output': task_def.get('expected_output', {}),
                'target_module': task_def.get('target_module', ''),
                'priority': task_def.get('priority', 5),
                'max_retries': 2,
                'timeout_seconds': 300,
            })
            self.models.update_task_status(sub_task_id, 'running')

            target_module = task_def.get('target_module', '')
            if target_module == 'image':
                exec_result = self._execute_image_agent(
                    task_def, agent_config, sub_task_id, target_id,
                    session_id, original_instruction
                )
            else:
                exec_result = self._execute_standard_agent(
                    task_def, agent_config, sub_task_id, target_id,
                    session_id, master_task_id
                )

            # 更新结果状态
            if exec_result['status'] == 'completed':
                self.models.update_task_status(
                    sub_task_id, 'completed',
                    result_data=exec_result.get('response', ''),
                    confidence=exec_result.get('confidence', 0.9),
                    self_review=exec_result.get('self_review', '')
                )
                self.models.update_agent_stats(target_id, success=True)
            else:
                self.models.update_task_status(
                    sub_task_id, 'failed',
                    error_message=exec_result.get('response', ''),
                    confidence=0.0
                )

            if session_id:
                status_icon = 'completed' if exec_result['status'] == 'completed' else 'failed'
                self.models.add_message(
                    session_id, 'system',
                    f"[{status_icon}] {task_def.get('title', '')}: {exec_result['status']} (confidence={exec_result.get('confidence', 0)})",
                    metadata={'sub_task_id': sub_task_id, 'status': exec_result['status']},
                    master_task_id=master_task_id
                )

            self._add_task_log(sub_task_id, target_id, 'info', 'execution',
                               f'{exec_result["status"]}: confidence={exec_result.get("confidence", 0)}')

            return {
                'sub_task_id': sub_task_id,
                'agent_name': agent_config.get('name', ''),
                'agent_id': target_id,
                'status': exec_result['status'],
                'response': exec_result.get('response', ''),
                'confidence': exec_result.get('confidence', 0),
                'self_review': exec_result.get('self_review', ''),
                'logs': exec_result.get('logs', []),
                'title': task_def.get('title', ''),
                'image_url': exec_result.get('image_url', ''),
            }

        # 用 ThreadPoolExecutor 并行提交所有任务
        max_workers = min(len(tasks), 5)  # 最多5个并行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for task_def in tasks:
                future = executor.submit(_run_single, task_def)
                futures[future] = task_def

            # 等待完成（带超时）
            timeout_per_task = 300  # 每个任务最多300秒
            try:
                for future in as_completed(futures, timeout=timeout_per_task):
                    try:
                        result = future.result()
                        with results_lock:
                            results.append(result)
                            completed_count += 1
                    except Exception as e:
                        task_def = futures[future]
                        with results_lock:
                            results.append({
                                'sub_task_id': None,
                                'agent_name': task_def.get('target_agent_name', '?'),
                                'status': 'failed',
                                'error': str(e),
                                'title': task_def.get('title', ''),
                            })
                            completed_count += 1
            except TimeoutError:
                # 超时未完成的任务标记为 failed
                for future in futures:
                    if not future.done():
                        task_def = futures[future]
                        with results_lock:
                            results.append({
                                'sub_task_id': None,
                                'agent_name': task_def.get('target_agent_name', '?'),
                                'status': 'failed',
                                'error': '任务执行超时（300s）',
                                'title': task_def.get('title', ''),
                            })
                            completed_count += 1

        return results

    def _compress_history(self, conv, agent_config):
        """构建注入 Agent 的历史消息。

        - 会话 <= 8 条：直接返回原文。
        - 会话 > 8 条：保留最近 6 条原文，对更早消息用 LLM 生成一段摘要，
          作为一条 assistant 记忆消息插到最前。LLM 不可用/失败时回退为 conv[-6:]。
        """
        recent_n = 6
        threshold = 8
        if not conv:
            return None
        if len(conv) <= threshold:
            return [{'role': m['role'], 'content': m['content']} for m in conv]

        older = conv[:-recent_n]
        recent = conv[-recent_n:]
        recent_msgs = [{'role': m['role'], 'content': m['content']} for m in recent]

        summary = self._summarize_messages(older, agent_config)
        if not summary:
            # 摘要失败，回退为最近 6 条原文
            return recent_msgs

        memory_msg = {'role': 'assistant', 'content': f'[历史对话摘要]\n{summary}'}
        return [memory_msg] + recent_msgs

    def _summarize_messages(self, messages, agent_config):
        """用 LLM 把较早的历史消息压缩成摘要，失败返回 None"""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
            from agent_matrix.engine import AIEngine
            engine = AIEngine(agent_config)
            if not engine.is_ready():
                return None
            convo_text = '\n'.join(
                f"{m['role']}: {m['content']}" for m in messages
            )[:4000]
            prompt = (
                "请把下面的多轮对话压缩成简洁摘要，保留关键事实、结论与未完成事项，"
                "用要点列出，不要寒暄：\n\n" + convo_text
            )
            summary = engine.ask(prompt, temperature=0.3)
            if not summary or summary.startswith('Error:'):
                return None
            return summary.strip()
        except Exception as e:
            logger.warning(f"历史摘要压缩失败，回退最近消息: {e}")
            return None

    def _execute_standard_agent(self, task_def, agent_config, sub_task_id, target_id,
                                 session_id, master_task_id):
        """执行标准 LLM Agent"""
        from agent_matrix.agent_runner import AgentRunner
        prompt = self._load_prompt(agent_config.get('system_prompt', ''))
        if prompt:
            agent_config['system_prompt'] = prompt
        runner = AgentRunner(agent_config, db_models=self.models)
        history = None
        if session_id:
            conv = self.models.get_conversation(session_id)
            history = self._compress_history(conv, agent_config)
        if session_id:
            self.models.add_message(
                session_id, 'sub', f"开始执行: {task_def.get('title', '')}",
                agent_id=target_id, agent_name=agent_config.get('name', ''),
                master_task_id=master_task_id
            )
        return runner.execute({
            'task_id': sub_task_id,
            'title': task_def.get('title', ''),
            'description': task_def.get('description', ''),
            'input_data': task_def.get('input_data', {}),
            'expected_output': task_def.get('expected_output', {}),
            'max_retries': 2,
        }, history=history)

    def _execute_image_agent(self, task_def, agent_config, sub_task_id, target_id,
                              session_id, original_instruction):
        """执行图片处理 Agent（Wan2.7 / PIL）"""
        import os, re as _re, uuid, json as _json
        exec_result = {'status': 'completed', 'response': '', 'image_url': '', 'confidence': 0.95}
        try:
            prompt = task_def.get('description', '') or task_def.get('title', '')
            ref_image_url = None
            ref_local_path = None

            # 从指令中提取参考图 URL
            urls = _re.findall(r'/static/uploads/temp/[^\s]+', original_instruction)
            if urls:
                rel_path = urls[0]
                from services.deployment_config import deploy
                ref_image_url = deploy.url('agent') + rel_path
                ref_local_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    '..', 'admin', 'static', 'uploads', 'temp',
                    os.path.basename(rel_path)
                )
            else:
                try:
                    conv = self.models.get_conversation(session_id) if session_id else []
                    for msg in reversed(conv):
                        content = str(msg.get('content', ''))
                        old_urls = _re.findall(r'/static/uploads/temp/[^\s]+', content)
                        if old_urls:
                            rel_path = old_urls[0]
                            from services.deployment_config import deploy
                            ref_image_url = deploy.url('agent') + rel_path
                            ref_local_path = os.path.join(
                                os.path.dirname(os.path.abspath(__file__)),
                                '..', 'admin', 'static', 'uploads', 'temp',
                                os.path.basename(rel_path)
                            )
                            break
                except:
                    pass
            self._add_task_log(sub_task_id, target_id, 'info', 'image_gen',
                               f'参考图: {ref_image_url or "无"}')

            # 视觉识别
            vision_analysis = ''
            if ref_image_url and prompt:
                try:
                    from services.ai_content_generator import analyze_image
                    if any(kw in prompt for kw in ['提取','裁剪','截取','抠图','取出']):
                        vq = f'用户要求: {prompt}\n请分析这张图片中用户想要提取的区域的精确位置坐标(x,y,width,height)，只返回JSON: {{"x":数字,"y":数字,"w":数字,"h":数字}}'
                    elif any(kw in prompt for kw in ['添加文字','写文字','加文字']):
                        vq = f'用户要求: {prompt}\n请描述图片的布局，建议文字添加的最佳位置'
                    else:
                        vq = f'用户要求: {prompt}\n请详细描述这张图片的内容、风格、颜色、布局'
                    vision_analysis = analyze_image(ref_image_url, question=vq)
                except:
                    pass

            TEMP_DIR = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..', 'admin', 'static', 'uploads', 'temp'
            )
            os.makedirs(TEMP_DIR, exist_ok=True)

            # 解析裁剪坐标
            crop_coords = None
            if vision_analysis:
                j_match = _re.search(r'\{[^}]+\}', vision_analysis)
                if j_match:
                    try:
                        jd = _json.loads(j_match.group())
                        if all(k in jd for k in ['x','y','w','h']):
                            crop_coords = (jd['x'], jd['y'], jd['x']+jd['w'], jd['y']+jd['h'])
                    except:
                        pass

            # 操作路由表
            def _op_crop(p, ref_path):
                from PIL import Image as _PIL
                img = _PIL.open(ref_path)
                w, h = img.size
                if crop_coords: box = crop_coords
                elif '左上角' in p: box = (0, 0, min(int(w*0.20),400), min(int(h*0.15),200))
                elif '右上角' in p: box = (max(0,w-min(int(w*0.20),400)), 0, w, min(int(h*0.15),200))
                elif '左下角' in p: box = (0, max(0,h-min(int(h*0.15),200)), min(int(w*0.20),400), h)
                elif '右下角' in p: box = (max(0,w-min(int(w*0.20),400)), max(0,h-min(int(h*0.15),200)), w, h)
                elif '中间' in p: box = (int(w*0.25), int(h*0.25), int(w*0.75), int(h*0.75))
                else: box = (0, 0, min(int(w*0.20),400), min(int(h*0.15),200))
                cr = img.crop(box)
                fn = f'{uuid.uuid4().hex}.png'
                cr.save(os.path.join(TEMP_DIR, fn))
                return f'/static/uploads/temp/{fn}', f'已裁剪区域 {box}'

            def _op_resize(p, ref_path):
                from PIL import Image as _PIL
                img = _PIL.open(ref_path)
                nums = _re.findall(r'(\d+)\s*[xX*]\s*(\d+)', p)
                nw, nh = (int(nums[0][0]), int(nums[0][1])) if nums else (img.width//2, img.height//2)
                img.resize((nw, nh)).save(os.path.join(TEMP_DIR, fn := f'{uuid.uuid4().hex}.png'))
                return f'/static/uploads/temp/{fn}', f'已缩放至 {nw}x{nh}'

            def _op_add_text(p, ref_path):
                from PIL import Image, ImageDraw, ImageFont
                img = Image.open(ref_path).convert('RGBA')
                txt = Image.new('RGBA', img.size, (0,0,0,0))
                draw = ImageDraw.Draw(txt)
                text = p.replace('添加文字','').replace('写文字','').replace('加文字','').replace('加水印','').strip().strip('，,') or 'EasyKai'
                try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 36)
                except: font = ImageFont.load_default()
                bbox = draw.textbbox((0,0), text, font=font)
                x, y = (img.width-(bbox[2]-bbox[0]))//2, img.height-(bbox[3]-bbox[1])-20
                draw.text((x,y), text, fill=(255,255,255,255), font=font)
                Image.alpha_composite(img, txt).convert('RGB').save(os.path.join(TEMP_DIR, fn := f'{uuid.uuid4().hex}.png'))
                return f'/static/uploads/temp/{fn}', f'已添加文字"{text}"'

            def _op_rotate(p, ref_path):
                from PIL import Image as _PIL
                deg = _re.findall(r'(\d+)', p)
                _PIL.open(ref_path).rotate(int(deg[0]) if deg else 90, expand=True).save(
                    os.path.join(TEMP_DIR, fn := f'{uuid.uuid4().hex}.png'))
                return f'/static/uploads/temp/{fn}', f'已旋转 {deg[0] if deg else 90}度'

            def _op_compress(p, ref_path):
                from PIL import Image as _PIL
                fn = f'{uuid.uuid4().hex}.jpg'
                _PIL.open(ref_path).convert('RGB').save(os.path.join(TEMP_DIR, fn), quality=60)
                return f'/static/uploads/temp/{fn}', '已压缩(quality=60)'

            action_map = [
                (['提取','裁剪','截取','抠图','取出','扣图'], _op_crop),
                (['添加文字','写文字','加文字','加水印'], _op_add_text),
                (['压缩','减小'], _op_compress),
                (['缩放','调整大小','放大','缩小'], _op_resize),
                (['旋转','翻转'], _op_rotate),
            ]

            op_result = None
            if ref_local_path and os.path.exists(ref_local_path):
                for keywords, handler in action_map:
                    if any(kw in prompt for kw in keywords):
                        op_result = handler(prompt, ref_local_path)
                        break

            if op_result:
                local_url, msg = op_result
                exec_result['image_url'] = local_url
                exec_result['response'] = msg
            elif ref_image_url:
                from services.ai_content_generator import generate_image
                import urllib.request as _urlreq
                gen_prompt = f'{prompt}\n\n参考图分析: {vision_analysis[:500]}' if vision_analysis else prompt
                oss_url = generate_image(gen_prompt, size='1280x720', reference_image_url=ref_image_url)
                if oss_url:
                    img_data = _urlreq.urlopen(oss_url, timeout=30).read()
                    ext = '.jpg' if ('jpg' in oss_url or 'jpeg' in oss_url) else '.webp' if 'webp' in oss_url else '.png'
                    fn = f'{uuid.uuid4().hex}{ext}'
                    with open(os.path.join(TEMP_DIR, fn), 'wb') as f: f.write(img_data)
                    exec_result['image_url'] = f'/static/uploads/temp/{fn}'
                    exec_result['response'] = '图片已生成'
            elif prompt:
                from services.ai_content_generator import generate_image
                import urllib.request as _urlreq
                oss_url = generate_image(prompt, size='1280x720')
                if oss_url:
                    img_data = _urlreq.urlopen(oss_url, timeout=30).read()
                    ext = '.jpg' if ('jpg' in oss_url or 'jpeg' in oss_url) else '.webp' if 'webp' in oss_url else '.png'
                    fn = f'{uuid.uuid4().hex}{ext}'
                    with open(os.path.join(TEMP_DIR, fn), 'wb') as f: f.write(img_data)
                    exec_result['image_url'] = f'/static/uploads/temp/{fn}'
                    exec_result['response'] = '图片已生成'
        except Exception as img_err:
            exec_result['status'] = 'failed'
            exec_result['response'] = f'图片生成失败: {str(img_err)}'
            self._add_task_log(sub_task_id, target_id, 'error', 'image_gen', str(img_err))

        return exec_result

    # -------------------------------------------------------
    # 报告生成
    # -------------------------------------------------------

    def _build_summary(self, decomposed, sub_results, total_time, all_completed):
        """构建人类可读的汇总报告"""
        parts = []
        parts.append(f"📋 **任务执行报告**\n")
        parts.append(f"共 {len(decomposed)} 个子任务 | 耗时 {total_time}s\n")

        for i, (task, result) in enumerate(zip(decomposed, sub_results), 1):
            icon = '✅' if result.get('status') == 'completed' else '❌'
            agent = task.get('target_agent_name', '?')
            conf = result.get('confidence', 0)
            title = task.get('title', '')
            parts.append(f"{icon} #{i} [{agent}] {title}")
            parts.append(f"   ├ 置信度: {conf}")
            if result.get('self_review'):
                parts.append(f"   └ 自检: {result['self_review']}")
            if result.get('status') == 'failed':
                parts.append(f"   └ 错误: {result.get('response', '')[:200]}")
            # 添加子任务的实际产出内容
            resp = result.get('response', '')
            if resp and result.get('status') == 'completed' and len(resp) > 5:
                # 截取合理长度显示
                display = resp[:1500]
                if len(resp) > 1500:
                    display += '\n...（内容较长，已截断）'
                parts.append(f"   └ 产出:\n{display}")

        if all_completed:
            parts.append(f"\n✅ **全部 {len(decomposed)} 个子任务完成**")
        else:
            failed = sum(1 for r in sub_results if r.get('status') == 'failed')
            parts.append(f"\n⚠️ **{failed}/{len(decomposed)} 个子任务失败**")

        return '\n'.join(parts)

    # -------------------------------------------------------
    # 辅助方法
    # -------------------------------------------------------

    def _load_prompt(self, prompt_source):
        """加载 System Prompt（支持文件路径或直接文本）"""
        if not prompt_source:
            return ''
        # 如果是文件路径（以 prompts/ 开头）
        if prompt_source.startswith('prompts/'):
            base_dir = os.path.dirname(__file__)
            file_path = os.path.join(base_dir, prompt_source)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            logger.warning(f"Prompt 文件不存在: {file_path}")
            return ''
        return prompt_source

    def _add_task_log(self, task_id, agent_id, level, log_type, message):
        if self.models:
            try:
                self.models.add_log(task_id, agent_id, level, log_type, message)
            except Exception:
                pass


# ============================================================
# 更新 Agent 统计的辅助函数
# ============================================================

def update_agent_stats(agent_id, success=True):
    """更新 Agent 的任务统计"""
    try:
        from agent_matrix import models as m
        with m.get_db() as conn:
            field = 'tasks_success' if success else 'tasks_failed'
            conn.execute(f"""
                UPDATE agent_matrix
                SET tasks_total = tasks_total + 1,
                    {field} = {field} + 1,
                    last_run_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (agent_id,))
            conn.commit()
    except Exception:
        pass
