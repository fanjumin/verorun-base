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
        from health_check.models import get_db as health_db
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


TOOL_EXECUTORS = {
    "get_system_health": _tool_get_system_health,
    "query_stats": _tool_query_stats,
    "search_knowledge": _tool_search_knowledge,
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
