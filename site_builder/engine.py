#!/usr/bin/env python3
"""Site Builder — 核心引擎

职责：
1. 解析用户需求 → 结构化方案
2. 逐步执行建站 DAG（品牌→主题→导航→页面→文档）
3. 支持最小化修改（增量更新单个区块）
"""

import os, json, re, logging
import time as _time

logger = logging.getLogger(__name__)


class SiteBuilderEngine:
    """建站核心引擎"""

    def __init__(self, models_module=None):
        self._models = models_module

    # ── LLM 调用 ──────────────────────────────────────

    def _get_master_agent(self):
        """获取 Master Agent 配置"""
        from agent_matrix import models as m
        agents = m.list_agents(role_type='master', active_only=True)
        if not agents:
            raise RuntimeError('没有可用的 Master Agent')
        return agents[0]

    def _get_ai_engine(self):
        """获取 AIEngine 实例"""
        from agent_matrix.engine import AIEngine
        master = self._get_master_agent()
        return AIEngine(master)

    def _call_llm(self, system_prompt: str, user_message: str, temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """调用 LLM，返回原始文本"""
        engine = self._get_ai_engine()
        return engine.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

    def _call_llm_json(self, system_prompt: str, user_message: str) -> dict:
        """调用 LLM 并解析 JSON 返回"""
        raw = self._call_llm(system_prompt, user_message, temperature=0.3)
        # 提取 JSON
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        # 尝试提取 markdown 代码块
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        logger.warning(f'Failed to parse LLM JSON: {raw[:200]}')
        raise ValueError('LLM 返回格式无法解析为 JSON')

    # ── 关键字替换 ────────────────────────────────────

    def _fill_prompt(self, template: str, **kwargs) -> str:
        """将提示词模板中的 {关键字} 替换为实际值"""
        result = template
        for key, val in kwargs.items():
            if isinstance(val, list):
                val = ', '.join(str(v) for v in val)
            result = result.replace('{' + key + '}', str(val))
        return result

    # ── 阶段 1: 解析用户需求 ──────────────────────────

    def parse_requirement(self, prompt_template: dict, user_input: str) -> dict:
        """解析用户输入，提取结构化信息

        Returns:
            {
                "brand_name": "...",
                "tagline": "...",
                "core_services": [...],
                "target_audience": "...",
                "style_preference": "...",
                "special_requirements": "..."
            }
        """
        defaults = prompt_template.get('defaults', {})
        prompts = prompt_template.get('prompts', {})
        parse_prompt = prompts.get('parse', '')

        # 用关键字替换生成最终提示词
        filled_prompt = self._fill_prompt(
            parse_prompt,
            行业=defaults.get('industry', '通用'),
            用户输入=user_input,
        )

        result = self._call_llm_json(filled_prompt, user_input)
        return result

    # ── 阶段 2: 生成方案预览 ──────────────────────────

    def generate_plan(self, prompt_template: dict, parsed: dict, user_input: str) -> dict:
        """生成完整的建站方案（不执行，仅预览）

        Returns:
            {
                "brand": {...},
                "theme": {...},
                "navigation": {...},
                "footer": {...},
                "pages": {"home": [...], "about": [...], ...},
                "documents": [{"slug": "...", "title": "...", "content": "..."}],
                "summary": "方案摘要文本"
            }
        """
        defaults = prompt_template.get('defaults', {})
        prompts = prompt_template.get('prompts', {})
        pages = prompt_template.get('pages', [])
        documents = prompt_template.get('documents', [])

        # 提取关键字值
        brand_name = parsed.get('brand_name', '我的网站')
        industry = defaults.get('industry', '通用')
        target_audience = parsed.get('target_audience', defaults.get('target_audience', '访客'))
        style = parsed.get('style_preference', defaults.get('style', '现代'))
        page_names = [p['name'] for p in pages]
        doc_names = [d['name'] for d in documents]

        plan = {'summary': ''}

        # 1. 品牌
        brand_prompt = self._fill_prompt(
            prompts.get('brand', ''),
            品牌名称=brand_name,
            行业=industry,
            目标受众=target_audience,
            风格偏好=style,
        )
        try:
            plan['brand'] = self._call_llm_json(brand_prompt, f'品牌名称：{brand_name}')
        except Exception as e:
            logger.warning(f'Brand generation failed: {e}')
            plan['brand'] = {'site_name': brand_name, 'tagline': '', 'brand_story': ''}

        # 2. 导航
        nav_prompt = self._fill_prompt(
            prompts.get('navigation', ''),
            品牌名称=brand_name,
            行业=industry,
            目标受众=target_audience,
            页面列表=page_names,
        )
        try:
            plan['navigation'] = self._call_llm_json(nav_prompt, f'页面列表：{page_names}')
        except Exception as e:
            logger.warning(f'Navigation generation failed: {e}')
            plan['navigation'] = {'nav_items': []}

        # 3. 页脚
        footer_prompt = self._fill_prompt(
            prompts.get('footer', ''),
            品牌名称=brand_name,
            行业=industry,
            文档列表=doc_names,
        )
        try:
            plan['footer'] = self._call_llm_json(footer_prompt, f'文档列表：{doc_names}')
        except Exception as e:
            logger.warning(f'Footer generation failed: {e}')
            plan['footer'] = {'footer_groups': []}

        # 4. 各页面内容
        plan['pages'] = {}
        for page in pages:
            page_id = page['id']
            page_name = page['name']
            page_prompt_key = f'page_{page_id}'
            page_prompt = prompts.get(page_prompt_key, '')

            if not page_prompt:
                continue

            filled = self._fill_prompt(
                page_prompt,
                品牌名称=brand_name,
                行业=industry,
                目标受众=target_audience,
                风格偏好=style,
            )
            try:
                result = self._call_llm_json(filled, f'生成页面：{page_name}')
                plan['pages'][page_id] = result
            except Exception as e:
                logger.warning(f'Page {page_id} generation failed: {e}')
                plan['pages'][page_id] = {'sections': []}

        # 5. 法律文档
        plan['documents'] = []
        for doc in documents:
            doc_id = doc['id']
            doc_name = doc['name']
            doc_prompt_key = f'doc_{doc_id}'
            doc_prompt = prompts.get(doc_prompt_key, '')

            if not doc_prompt:
                continue

            filled = self._fill_prompt(
                doc_prompt,
                品牌名称=brand_name,
                行业=industry,
            )
            try:
                html_content = self._call_llm(filled, f'生成文档：{doc_name}', temperature=0.3, max_tokens=3000)
                plan['documents'].append({
                    'slug': doc_id,
                    'title': doc_name,
                    'content': html_content,
                })
            except Exception as e:
                logger.warning(f'Document {doc_id} generation failed: {e}')

        # 构建摘要
        plan['summary'] = self._build_summary(brand_name, pages, plan)
        return plan

    def _build_summary(self, brand_name: str, pages: list, plan: dict) -> str:
        """构建方案摘要文本"""
        lines = [
            f'🏷️ 品牌：{brand_name}',
            '',
            '📄 页面结构：',
        ]
        for page in pages:
            page_id = page['id']
            page_data = plan.get('pages', {}).get(page_id, {})
            section_count = len(page_data.get('sections', []))
            lines.append(f'  ├─ {page["name"]}（{section_count} 个区块）')

        lines.append('')
        lines.append('📋 法律文档：')
        for doc in plan.get('documents', []):
            lines.append(f'  ├─ {doc["title"]}')

        lines.append('')
        lines.append('⚠️ 请确认以上方案，或告诉我需要调整的地方。')
        lines.append('回复「确认执行」开始建站，或描述需要修改的内容。')
        return '\n'.join(lines)

    # ── 阶段 3: 执行建站 ──────────────────────────────

    def execute_plan(self, plan: dict, prompt_template: dict) -> dict:
        """执行建站方案，逐步写入数据库

        DAG 流程：
        1. 品牌设置
        2. 主题配置（依赖品牌配色）
        3. 导航结构 + 页脚
        4. 页面内容（并行生成各页面）
        5. 法律文档
        """
        from site_builder.generators.brand import BrandGenerator
        from site_builder.generators.navigation import NavigationGenerator
        from site_builder.generators.pages import PageGenerator
        from site_builder.generators.theme import ThemeGenerator

        results = {}
        pages = prompt_template.get('pages', [])
        documents = prompt_template.get('documents', [])

        # Step 1: 品牌设置
        try:
            BrandGenerator.apply(plan.get('brand', {}))
            results['brand'] = 'ok'
        except Exception as e:
            results['brand'] = str(e)
            logger.error(f'Brand apply failed: {e}')

        # Step 2: 主题配置
        try:
            ThemeGenerator.apply_theme(plan.get('brand', {}))
            results['theme'] = 'ok'
        except Exception as e:
            results['theme'] = str(e)
            logger.error(f'Theme apply failed: {e}')

        # Step 3: 导航 + 页脚
        try:
            NavigationGenerator.apply_nav(plan.get('navigation', {}))
            results['navigation'] = 'ok'
        except Exception as e:
            results['navigation'] = str(e)
            logger.error(f'Navigation apply failed: {e}')

        try:
            NavigationGenerator.apply_footer(plan.get('footer', {}))
            results['footer'] = 'ok'
        except Exception as e:
            results['footer'] = str(e)
            logger.error(f'Footer apply failed: {e}')

        try:
            NavigationGenerator.apply_footer_articles(documents)
            results['footer_articles'] = 'ok'
        except Exception as e:
            results['footer_articles'] = str(e)
            logger.error(f'Footer articles apply failed: {e}')

        # Step 4: 页面内容
        results['pages'] = {}
        for page in pages:
            page_id = page['id']
            page_data = plan.get('pages', {}).get(page_id, {})
            if not page_data:
                continue
            try:
                sections = page_data.get('sections', [])
                if sections:
                    PageGenerator.apply_page_blocks(page_id, sections)
                else:
                    PageGenerator.apply_page_text(page_id, page_data)
                results['pages'][page_id] = 'ok'
            except Exception as e:
                results['pages'][page_id] = str(e)
                logger.error(f'Page {page_id} apply failed: {e}')

        # Step 5: 法律文档
        results['documents'] = {}
        for doc in plan.get('documents', []):
            try:
                PageGenerator.apply_document(
                    doc['slug'],
                    doc['title'],
                    doc['content']
                )
                results['documents'][doc['slug']] = 'ok'
            except Exception as e:
                results['documents'][doc['slug']] = str(e)
                logger.error(f'Document {doc["slug"]} apply failed: {e}')

        # 统计
        total_ok = sum(
            1 for v in results.values()
            if v == 'ok' or (isinstance(v, dict) and all(vv == 'ok' for vv in v.values()))
        )
        results['_summary'] = {
            'total_steps': 5,
            'succeeded': total_ok,
            'pages_count': len(pages),
            'docs_count': len(documents),
        }
        return results

    # ── 最小化修改 ────────────────────────────────────

    def modify_block(self, user_message: str, page: str = 'home') -> dict:
        """最小化修改：分析用户意图，定位具体区块，执行修改

        Returns:
            {
                "action": "modify_block" | "add_block" | "delete_block" | "unknown",
                "target": {"block_id": N},
                "changes": {"title": "...", ...},
                "old_value": "...",
                "new_value": "..."
            }
        """
        from site_builder.generators.pages import PageGenerator

        # 获取当前页面摘要
        page_summary = PageGenerator.get_page_summary(page)
        if not page_summary:
            return {'action': 'unknown', 'error': '页面没有区块'}

        # 构建修改上下文
        modify_prompt = f"""你是一个网站内容编辑器。当前页面 [{page}] 的区块如下：

{json.dumps(page_summary, ensure_ascii=False, indent=2)}

用户要求：{user_message}

请判断用户想要修改哪个区块，只返回需要修改的字段。
**不要重新生成整个页面，只输出需要变更的部分。**

返回 JSON：
{{
  "action": "modify_block" | "add_block" | "delete_block" | "reorder" | "unknown",
  "block_id": 数字（仅 modify_block/delete_block 时需要）,
  "changes": {{"title": "新标题", "content": "新内容"}}（仅 modify_block 时需要，只包含要修改的字段）
}}

如果用户的要求无法定位到具体区块，action 返回 "unknown" 并说明原因。"""

        try:
            result = self._call_llm_json(modify_prompt, user_message)
        except Exception as e:
            return {'action': 'unknown', 'error': str(e)}

        action = result.get('action', 'unknown')

        if action == 'modify_block':
            block_id = result.get('block_id')
            changes = result.get('changes', {})
            if block_id and changes:
                # 获取旧值
                old = None
                from models import get_db
                with get_db() as conn:
                    row = conn.execute(
                        "SELECT title, content FROM cms_blocks WHERE id=?",
                        (block_id,)
                    ).fetchone()
                    if row:
                        old = dict(row)

                success = PageGenerator.modify_block(block_id, changes)
                return {
                    'action': 'modify_block',
                    'block_id': block_id,
                    'changes': changes,
                    'old_value': (old or {}).get('title', ''),
                    'new_value': changes.get('title', ''),
                    'success': success,
                }

        elif action == 'delete_block':
            block_id = result.get('block_id')
            if block_id:
                from models import get_db
                with get_db() as conn:
                    conn.execute("DELETE FROM cms_blocks WHERE id=?", (block_id,))
                    conn.commit()
                return {
                    'action': 'delete_block',
                    'block_id': block_id,
                    'success': True,
                }

        return {'action': action, 'error': result.get('reason', '无法定位需要修改的区块')}

    # ── 订阅检查 ──────────────────────────────────────

    @staticmethod
    def check_access(user_id: int = None) -> tuple:
        """检查用户是否有建站权限

        Returns:
            (allowed: bool, message: str)
        """
        # AI 底座永久免费，不检查
        # 建站功能的具体执行权限由 subscription 模块控制
        # 这里保持开放，实际限制在 routes 层处理
        return True, ''