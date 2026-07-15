#!/usr/bin/env python3
"""
Agent Matrix — 工具注册中心 (Tool Registry)
===========================================
为子 Agent 提供原生 function calling 可调用的工具集。

设计原则：
  - 首批仅内置「只读、安全」工具，不给写库/删除类能力。
  - 工具执行统一带 try/except 兜底，失败返回字符串错误信息而非抛异常，
    保证 ReAct 循环不会因单个工具出错而崩溃。
  - 按 Agent 的 allowed_tools 白名单过滤，未授权工具不下发给模型。

对外接口：
  - get_tools_for_agent(allowed_tools) -> list[schema]
  - execute_tool(name, args) -> str
"""
import json, os, sys, logging

logger = logging.getLogger(__name__)

# ============================================================
# 工具 Schema（OpenAI function calling 格式）
# ============================================================

TOOL_SCHEMAS = {
    "get_system_health": {
        "type": "function",
        "function": {
            "name": "get_system_health",
            "description": "获取系统最近一次健康巡检的结果汇总，包括健康分、通过/警告/错误数量，以及各检查项状态。用于回答系统运行状态、服务健康、告警相关问题。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    "query_stats": {
        "type": "function",
        "function": {
            "name": "query_stats",
            "description": "查询站点访问统计报告（PV/UV/会话/趋势/来源/热门页面），返回可读的文字洞察。用于回答流量、访问量、数据趋势相关问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "统计周期天数，默认 7 天",
                        "default": 7
                    }
                },
                "required": []
            }
        }
    },
    "search_knowledge": {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "在平台知识库中检索与关键词相关的内容片段。用于回答产品功能、FAQ、使用帮助相关问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "检索关键词"
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    "ads_list": {
        "type": "function",
        "function": {
            "name": "ads_list",
            "description": "列出广告管理系统中的广告位，可按站点、位置、是否启用筛选。",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_key": {"type": "string", "description": "站点标识，默认 default"},
                    "position": {"type": "string", "description": "广告位置，例如 sidebar"},
                    "active_only": {"type": "boolean", "description": "是否只返回启用状态的广告", "default": False}
                },
                "required": []
            }
        }
    },
    "ads_create": {
        "type": "function",
        "function": {
            "name": "ads_create",
            "description": "创建一个新的广告位。支持图片广告或广告代码，可设置投放位置、时间、定向规则、权重等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "广告名称（必填）"},
                    "site_key": {"type": "string", "description": "站点标识，默认 default"},
                    "zone_id": {"type": "integer", "description": "广告区域 ID，默认 0"},
                    "position": {"type": "string", "description": "广告位置标识，默认 sidebar"},
                    "page": {"type": "string", "description": "展示页面，默认 * 表示全站"},
                    "ad_type": {"type": "string", "enum": ["image", "code"], "description": "广告类型"},
                    "image_url": {"type": "string", "description": "图片广告 URL"},
                    "link_url": {"type": "string", "description": "图片广告跳转链接"},
                    "ad_code": {"type": "string", "description": "广告代码（HTML/JS）"},
                    "width": {"type": "integer", "description": "宽度（px）"},
                    "height": {"type": "integer", "description": "高度（px）"},
                    "targeting_rules": {"type": "object", "description": "定向规则 JSON 对象"},
                    "schedule_start": {"type": "string", "description": "投放开始时间 ISO 格式"},
                    "schedule_end": {"type": "string", "description": "投放结束时间 ISO 格式"},
                    "weight": {"type": "integer", "description": "权重，默认 1"},
                    "freq_cap": {"type": "integer", "description": "每用户每日频次上限，0 表示无限制"},
                    "click_tag": {"type": "string", "description": "点击追踪标记"},
                    "utm_source": {"type": "string", "description": "UTM 来源"},
                    "is_active": {"type": "integer", "description": "是否启用，1=启用，0=禁用"},
                    "sort_order": {"type": "integer", "description": "排序，默认 0"}
                },
                "required": ["name"]
            }
        }
    },
    "ads_update": {
        "type": "function",
        "function": {
            "name": "ads_update",
            "description": "更新指定广告位的字段，例如启用/禁用、修改代码、调整权重等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "ad_id": {"type": "integer", "description": "广告 ID"},
                    "updates": {"type": "object", "description": "要更新的字段键值对，字段含义同 ads_create"}
                },
                "required": ["ad_id", "updates"]
            }
        }
    },
    "ads_delete": {
        "type": "function",
        "function": {
            "name": "ads_delete",
            "description": "删除指定广告位。",
            "parameters": {
                "type": "object",
                "properties": {
                    "ad_id": {"type": "integer", "description": "广告 ID"}
                },
                "required": ["ad_id"]
            }
        }
    },
    "ads_get_stats": {
        "type": "function",
        "function": {
            "name": "ads_get_stats",
            "description": "查询广告统计数据，包括展示量、点击量、CTR 及每日趋势。",
            "parameters": {
                "type": "object",
                "properties": {
                    "ad_id": {"type": "integer", "description": "广告 ID，不传则统计全部广告"},
                    "days": {"type": "integer", "description": "统计天数，默认 7", "default": 7}
                },
                "required": []
            }
        }
    },
    "ads_analyze": {
        "type": "function",
        "function": {
            "name": "ads_analyze",
            "description": "分析广告效果，返回高点击、低 CTR、趋势等文字洞察与优化建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "统计天数，默认 7", "default": 7}
                },
                "required": []
            }
        }
    },
    "ads_render_snippet": {
        "type": "function",
        "function": {
            "name": "ads_render_snippet",
            "description": "生成一段 Jinja2 模板代码，用于在页面指定位置渲染广告位。",
            "parameters": {
                "type": "object",
                "properties": {
                    "position": {"type": "string", "description": "广告位置标识，默认 sidebar"},
                    "page": {"type": "string", "description": "展示页面，默认 *"},
                    "site_key": {"type": "string", "description": "站点标识，默认 default"},
                    "zone_id": {"type": "integer", "description": "广告区域 ID"}
                },
                "required": ["position"]
            }
        }
    },
    "generate_ppt": {
        "type": "function",
        "function": {
            "name": "generate_ppt",
            "description": "使用 AI 生成 PowerPoint 演示文稿（PPTX）。用户提供主题、页数和风格即可生成一份可直接下载的 PPT 文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "PPT 主题（必填）"},
                    "pages": {"type": "integer", "description": "页数，默认 10，范围 3-20", "default": 10},
                    "style": {"type": "string", "description": "风格描述，如'Dark 科技风'、'简约商务'、'教育风格'等", "default": "Dark 科技风，16:9"}
                },
                "required": ["topic"]
            }
        }
    },
}


# ============================================================
# 工具执行器（均为只读）
# ============================================================

def _get_matrix_db():
    """获取 agent_matrix 所在主库连接（复用项目 models.get_db）"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from models import get_db
    return get_db()


def _tool_get_system_health(args):
    """读取最近一次健康巡检结果汇总（只读）"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from plugins.health_check.models import get_db as health_db
        with health_db() as conn:
            run = conn.execute(
                "SELECT * FROM check_runs WHERE status='completed' "
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if not run:
                return "暂无健康巡检记录。"
            run = dict(run)
            total = run.get('total_checks', 0) or 0
            passed = run.get('passed', 0) or 0
            warnings = run.get('warnings', 0) or 0
            errors = run.get('errors', 0) or 0
            denom = passed + warnings + errors
            score = round((passed + warnings * 0.5) * 100 / denom, 1) if denom else 100.0

            items = conn.execute(
                "SELECT check_name, status, message FROM check_history "
                "WHERE run_id=? ORDER BY status DESC",
                (run['id'],)
            ).fetchall()
        lines = [
            f"健康分: {score}/100",
            f"检查总数: {total}, 通过: {passed}, 警告: {warnings}, 错误: {errors}",
            f"巡检时间: {run.get('created_at', '')}",
        ]
        abnormal = [dict(i) for i in items if i['status'] != 'passed']
        if abnormal:
            lines.append("异常项:")
            for i in abnormal[:15]:
                lines.append(f"  - [{i['status']}] {i['check_name']}: {(i['message'] or '')[:80]}")
        else:
            lines.append("所有检查项均通过。")
        return '\n'.join(lines)
    except Exception as e:
        logger.warning(f"[tool:get_system_health] 执行失败: {e}")
        return f"获取健康状态失败: {e}"


def _tool_query_stats(args):
    """生成站点统计报告的文字洞察（只读）"""
    try:
        days = int(args.get('days', 7) or 7)
        days = max(1, min(days, 90))
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from plugins.analytics.tracker import generate_report, generate_insight_text
        report = generate_report(days=days)
        return generate_insight_text(report)
    except Exception as e:
        logger.warning(f"[tool:query_stats] 执行失败: {e}")
        return f"查询统计数据失败: {e}"


def _tool_search_knowledge(args):
    """在知识库中检索关键词（只读）"""
    try:
        keyword = str(args.get('keyword', '')).strip()
        if not keyword:
            return "未提供检索关键词。"
        with _get_matrix_db() as conn:
            row = conn.execute(
                "SELECT value FROM system_config WHERE key='chatbot_knowledge_base'"
            ).fetchone()
        content = (row['value'] if row and row['value'] else '') or ''
        if not content:
            return "知识库为空。"
        # 简单按段落匹配，返回命中片段
        blocks = [b.strip() for b in content.split('\n\n') if b.strip()]
        hits = [b for b in blocks if keyword.lower() in b.lower()]
        if not hits:
            return f"知识库中未找到与「{keyword}」相关的内容。"
        return '\n---\n'.join(hits[:5])[:2000]
    except Exception as e:
        logger.warning(f"[tool:search_knowledge] 执行失败: {e}")
        return f"检索知识库失败: {e}"


def _tool_ads_list(args):
    """列出广告"""
    try:
        import plugins.ads.ai_tools as ads_tools
        res = ads_tools.list_ads(
            site_key=args.get('site_key'),
            position=args.get('position'),
            active_only=args.get('active_only', False)
        )
        if not res['success']:
            return f"获取广告列表失败: {res.get('error')}"
        ads = res.get('data', [])
        if not ads:
            return "暂无广告位。"
        lines = [f"共 {len(ads)} 个广告位："]
        for a in ads:
            status = '启用' if a.get('is_active') else '停用'
            lines.append(
                f"ID {a['id']}: {a['name']} | 站点 {a.get('site_key','default')} | "
                f"位置 {a.get('position','-')} | 类型 {a.get('ad_type','image')} | {status}"
            )
        return '\n'.join(lines)
    except Exception as e:
        logger.warning(f"[tool:ads_list] 执行失败: {e}")
        return f"获取广告列表失败: {e}"


def _tool_ads_create(args):
    """创建广告"""
    try:
        import plugins.ads.ai_tools as ads_tools
        res = ads_tools.create_ad(args)
        if res['success']:
            return f"✅ 广告已创建，ID: {res['data']['id']}"
        return f"❌ 创建失败: {res.get('error')}"
    except Exception as e:
        logger.warning(f"[tool:ads_create] 执行失败: {e}")
        return f"创建广告失败: {e}"


def _tool_ads_update(args):
    """更新广告"""
    try:
        import plugins.ads.ai_tools as ads_tools
        ad_id = args.get('ad_id')
        updates = args.get('updates', {})
        res = ads_tools.update_ad(ad_id, updates)
        if res['success']:
            return f"✅ 广告 {ad_id} 已更新"
        return f"❌ 更新失败: {res.get('error')}"
    except Exception as e:
        logger.warning(f"[tool:ads_update] 执行失败: {e}")
        return f"更新广告失败: {e}"


def _tool_ads_delete(args):
    """删除广告"""
    try:
        import plugins.ads.ai_tools as ads_tools
        res = ads_tools.delete_ad(args.get('ad_id'))
        if res['success']:
            return f"✅ 广告 {args.get('ad_id')} 已删除"
        return f"❌ 删除失败: {res.get('error')}"
    except Exception as e:
        logger.warning(f"[tool:ads_delete] 执行失败: {e}")
        return f"删除广告失败: {e}"


def _tool_ads_get_stats(args):
    """查询广告统计"""
    try:
        import plugins.ads.ai_tools as ads_tools
        res = ads_tools.get_stats(
            ad_id=args.get('ad_id'),
            site_key=args.get('site_key'),
            days=int(args.get('days', 7))
        )
        if not res['success']:
            return f"查询统计失败: {res.get('error')}"
        data = res.get('data', {})
        total = data.get('total', {})
        daily = data.get('daily', [])
        lines = [
            f"=== 广告统计（最近 {args.get('days',7)} 天）===",
            f"展示量: {total.get('impressions', 0)}",
            f"点击量: {total.get('clicks', 0)}",
            f"CTR: {total.get('ctr', 0)}%",
        ]
        if daily:
            lines.append("每日趋势:")
            for r in daily[-10:]:
                lines.append(f"  {r['stat_date']}: 展示 {r.get('impressions',0)} 点击 {r.get('clicks',0)}")
        return '\n'.join(lines)
    except Exception as e:
        logger.warning(f"[tool:ads_get_stats] 执行失败: {e}")
        return f"查询广告统计失败: {e}"


def _tool_ads_analyze(args):
    """分析广告效果"""
    try:
        import plugins.ads.ai_tools as ads_tools
        res = ads_tools.analyze_ads(days=int(args.get('days', 7)))
        if res['success']:
            return res['data']
        return f"分析失败: {res.get('error')}"
    except Exception as e:
        logger.warning(f"[tool:ads_analyze] 执行失败: {e}")
        return f"广告分析失败: {e}"


def _tool_ads_render_snippet(args):
    """生成广告渲染代码片段"""
    try:
        import plugins.ads.ai_tools as ads_tools
        res = ads_tools.generate_render_snippet(
            position=args.get('position', 'sidebar'),
            page=args.get('page', '*'),
            site_key=args.get('site_key', 'default'),
            zone_id=args.get('zone_id')
        )
        if res['success']:
            return "在模板中加入以下代码即可渲染广告位：\n```jinja2\n" + res['data'] + "\n```"
        return f"生成代码失败: {res.get('error')}"
    except Exception as e:
        logger.warning(f"[tool:ads_render_snippet] 执行失败: {e}")
        return f"生成广告渲染代码失败: {e}"


def _tool_generate_ppt(args):
    """使用 AI 生成 PPT 文件"""
    try:
        topic = str(args.get('topic', '未命名主题')).strip()
        if not topic:
            return '❌ 请提供 PPT 主题'
        pages = max(3, min(int(args.get('pages', 10) or 10), 20))
        style = str(args.get('style', 'Dark 科技风，16:9'))
        from agent_matrix.routes import _generate_ppt_file
        filename = _generate_ppt_file(topic, pages, style)
        if filename:
            return f'✅ PPT 已生成："{topic}"（{pages}页）\n下载链接：/admin/agent-matrix/media/download/{filename}'
        return '❌ PPT 生成失败，请检查后端日志'
    except Exception as e:
        logger.warning(f"[tool:generate_ppt] 执行失败: {e}")
        return f'❌ PPT 生成异常: {e}'


TOOL_EXECUTORS = {
    "get_system_health": _tool_get_system_health,
    "query_stats": _tool_query_stats,
    "search_knowledge": _tool_search_knowledge,
    "ads_list": _tool_ads_list,
    "ads_create": _tool_ads_create,
    "ads_update": _tool_ads_update,
    "ads_delete": _tool_ads_delete,
    "ads_get_stats": _tool_ads_get_stats,
    "ads_analyze": _tool_ads_analyze,
    "ads_render_snippet": _tool_ads_render_snippet,
    "generate_ppt": _tool_generate_ppt,
}


# ============================================================
# 对外接口
# ============================================================

def get_tools_for_agent(allowed_tools):
    """按 Agent 的 allowed_tools 白名单返回可用工具 schema 列表。

    allowed_tools 可为 JSON 字符串或 list；为空/无效时返回空列表
    （即该 Agent 不启用工具，走原单轮逻辑）。
    """
    if not allowed_tools:
        return []
    if isinstance(allowed_tools, str):
        try:
            allowed_tools = json.loads(allowed_tools)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(allowed_tools, list):
        return []
    return [TOOL_SCHEMAS[name] for name in allowed_tools if name in TOOL_SCHEMAS]


def execute_tool(name, args):
    """执行指定工具，返回字符串结果。未知工具或异常均返回错误字符串。"""
    executor = TOOL_EXECUTORS.get(name)
    if not executor:
        return f"未知工具: {name}"
    if not isinstance(args, dict):
        args = {}
    try:
        return executor(args)
    except Exception as e:
        logger.warning(f"[tool:{name}] 未捕获异常: {e}")
        return f"工具 {name} 执行异常: {e}"
