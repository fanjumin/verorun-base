"""AI Advisor 对话统计与报表"""
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_db():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
    from models import get_db
    return get_db()


INTENT_CATEGORIES = ['purchase', 'aftersale', 'complaint', 'consult', 'technical', 'other']
SENTIMENT_LABELS = ['positive', 'neutral', 'negative', 'urgent']


def classify_intent(user_query):
    """轻量级 LLM 调用，将用户消息分类为意图+情绪。
    
    返回 (intent, sentiment)
    intent ∈ ['purchase','aftersale','complaint','consult','technical','other']
    sentiment ∈ ['positive','neutral','negative','urgent']
    """
    if not user_query or not user_query.strip():
        return 'other', 'neutral'
    try:
        import sys as _sys, os as _os
        _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..'))
        from agent_matrix.engine import AIEngine

        prompt = f"""分析以下用户消息，输出 JSON，不要多余文字：
{{
  "intent": "分类（purchase=购买意向, aftersale=售后, complaint=投诉, consult=咨询, technical=技术支持, other=其他）",
  "sentiment": "情绪（positive=正面, neutral=中性, negative=负面, urgent=紧急）"
}}

消息：{user_query[:500]}"""

        engine = AIEngine({'provider': 'dashscope', 'model_name': 'qwen-turbo'})
        reply = ''
        for token in engine.chat_stream([
            {'role': 'system', 'content': '你是一个精准的分类器。只输出 JSON。'},
            {'role': 'user', 'content': prompt}
        ], temperature=0.1, max_tokens=128):
            if not token.startswith('Error:'):
                reply += token

        data = json.loads(reply.strip())
        intent = data.get('intent', 'other')
        sentiment = data.get('sentiment', 'neutral')
        if intent not in INTENT_CATEGORIES:
            intent = 'other'
        if sentiment not in SENTIMENT_LABELS:
            sentiment = 'neutral'
        return intent, sentiment
    except Exception as e:
        logger.warning(f"[Chatbot] classify_intent failed, using defaults: {e}")
        return 'other', 'neutral'


def log_session(session_id, user_query='', ai_reply='', escalated=False,
                source='chatbot', intent='', sentiment=''):
    """记录一次 AI 对话回合到 chatbot_sessions。"""
    try:
        with _get_db() as conn:
            conn.execute(
                """INSERT INTO chatbot_sessions
                   (session_id, user_query, ai_reply, escalated, source,
                    intent, sentiment, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (session_id, user_query, ai_reply, 1 if escalated else 0, source,
                 intent, sentiment)
            )
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"[Chatbot Stats] log_session failed: {e}")
        return False


def get_today_stats():
    """获取今日统计概览，含意图分布。"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        with _get_db() as conn:
            # 今日对话数（唯一 session）
            total = conn.execute(
                "SELECT COUNT(DISTINCT session_id) as cnt FROM chatbot_sessions "
                "WHERE source='chatbot' AND date(created_at)=?",
                (today,)
            ).fetchone()['cnt'] or 0

            # 今日转人工数
            escalated = conn.execute(
                "SELECT COUNT(DISTINCT session_id) as cnt FROM chatbot_sessions "
                "WHERE source='chatbot' AND escalated=1 AND date(created_at)=?",
                (today,)
            ).fetchone()['cnt'] or 0

            # 今日工单数
            tickets = conn.execute(
                "SELECT COUNT(*) as cnt FROM user_tickets "
                "WHERE category='chatbot_escalation' AND date(created_at)=date('now')"
            ).fetchone()['cnt'] or 0

            # 工单中已解决的
            resolved = conn.execute(
                "SELECT COUNT(*) as cnt FROM user_tickets "
                "WHERE category='chatbot_escalation' AND status='closed' "
                "AND date(created_at)=date('now')"
            ).fetchone()['cnt'] or 0

            # 今日 CSAT 平均分
            avg_csat = conn.execute(
                "SELECT COALESCE(AVG(csat_score),0) as avg FROM chatbot_sessions "
                "WHERE source='chatbot' AND csat_score>0 AND date(created_at)=?",
                (today,)
            ).fetchone()['avg'] or 0

            # 意图分布
            intent_raw = conn.execute(
                "SELECT intent, COUNT(*) as cnt FROM chatbot_sessions "
                "WHERE source='chatbot' AND date(created_at)=? AND intent!='' "
                "GROUP BY intent ORDER BY cnt DESC",
                (today,)
            ).fetchall()
            intent_dist = {r['intent']: r['cnt'] for r in intent_raw}

            # 情绪分布
            sentiment_raw = conn.execute(
                "SELECT sentiment, COUNT(*) as cnt FROM chatbot_sessions "
                "WHERE source='chatbot' AND date(created_at)=? AND sentiment!='' "
                "GROUP BY sentiment ORDER BY cnt DESC",
                (today,)
            ).fetchall()
            sentiment_dist = {r['sentiment']: r['cnt'] for r in sentiment_raw}

            # 本周趋势（daily session count for last 7 days）
            trend_raw = conn.execute(
                "SELECT date(created_at) as d, COUNT(DISTINCT session_id) as cnt "
                "FROM chatbot_sessions WHERE source='chatbot' "
                "AND created_at >= datetime('now', '-7 days') "
                "GROUP BY d ORDER BY d"
            ).fetchall()

        handoff_rate = round(escalated / total * 100, 1) if total > 0 else 0
        resolve_rate = round(resolved / tickets * 100, 1) if tickets > 0 else 0
        trend = [{'date': r['d'], 'count': r['cnt']} for r in trend_raw]

        return {
            'today_sessions': total,
            'today_escalated': escalated,
            'handoff_rate': handoff_rate,
            'today_tickets': tickets,
            'resolve_rate': resolve_rate,
            'avg_csat': round(avg_csat, 1),
            'intent_distribution': intent_dist,
            'sentiment_distribution': sentiment_dist,
            'trend': trend,
        }
    except Exception as e:
        logger.error(f"[Chatbot Stats] get_today_stats failed: {e}")
        return {'today_sessions': 0, 'today_escalated': 0, 'handoff_rate': 0,
                'today_tickets': 0, 'resolve_rate': 0, 'avg_csat': 0,
                'intent_distribution': {}, 'sentiment_distribution': {},
                'trend': []}


def record_csat(session_id, score):
    """记录 CSAT 评分到会话记录。"""
    try:
        with _get_db() as conn:
            conn.execute(
                "UPDATE chatbot_sessions SET csat_score=? WHERE session_id=?",
                (score, session_id)
            )
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"[Chatbot Stats] record_csat failed: {e}")
        return False


def get_hot_topics(limit=10):
    """热门问题分析：按 user_query 聚合，取最热门的前 N 条。"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT user_query, COUNT(*) as cnt FROM chatbot_sessions "
                "WHERE source='chatbot' AND date(created_at)=? "
                "AND user_query!='' "
                "GROUP BY user_query ORDER BY cnt DESC LIMIT ?",
                (today, limit)
            ).fetchall()
        return [{'query': r['user_query'], 'count': r['cnt']} for r in rows]
    except Exception as e:
        logger.error(f"[Chatbot Stats] get_hot_topics failed: {e}")
        return []


def get_agent_performance():
    """座席绩效：工单处理量、解决率。"""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                """SELECT
                    assigned_name,
                    assigned_to,
                    COUNT(*) as total_tickets,
                    SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) as resolved,
                    ROUND(AVG(
                        CASE WHEN replied_at IS NOT NULL AND replied_at!=''
                        THEN (julianday(replied_at) - julianday(created_at)) * 86400
                        ELSE NULL END
                    ), 0) as avg_response_sec
                  FROM user_tickets
                  WHERE assigned_to > 0
                  GROUP BY assigned_to
                  ORDER BY total_tickets DESC"""
            ).fetchall()
        result = []
        for r in rows:
            resolve_rate = round(r['resolved'] / r['total_tickets'] * 100, 1) if r['total_tickets'] > 0 else 0
            avg_resp = f"{round(r['avg_response_sec'] / 60, 1)}min" if r['avg_response_sec'] else '--'
            result.append({
                'agent_name': r['assigned_name'] or f"Agent #{r['assigned_to']}",
                'agent_id': r['assigned_to'],
                'total_tickets': r['total_tickets'],
                'resolved': r['resolved'],
                'resolve_rate': resolve_rate,
                'avg_response': avg_resp,
            })
        return result
    except Exception as e:
        logger.error(f"[Chatbot Stats] get_agent_performance failed: {e}")
        return []


def qa_check_conversation(session_id, user_query, ai_reply):
    """对话质检：用 LLM 分析一轮对话的质量。
    
    返回 {score, suggestion} 或 None
    """
    if not user_query or not ai_reply:
        return None
    try:
        import sys as _sys, os as _os, json as _json
        _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..'))
        from agent_matrix.engine import AIEngine

        prompt = f"""分析以下 AI 客服对话，从以下维度打分（1-5），输出 JSON：

{{
  "score": "总体评分 1-5",
  "accuracy": "准确性 1-5",
  "helpfulness": "有帮助程度 1-5",
  "politeness": "礼貌程度 1-5",
  "suggestion": "改进建议（一句话）"
}}

用户：{user_query[:300]}
AI：{ai_reply[:500]}"""

        engine = AIEngine({'provider': 'dashscope', 'model_name': 'qwen-turbo'})
        reply = ''
        for token in engine.chat_stream([
            {'role': 'system', 'content': '你是一个对话质量评审员。只输出 JSON。'},
            {'role': 'user', 'content': prompt}
        ], temperature=0.1, max_tokens=256):
            if not token.startswith('Error:'):
                reply += token

        data = _json.loads(reply.strip())
        return {
            'score': min(5, max(1, int(data.get('score', 3)))),
            'accuracy': min(5, max(1, int(data.get('accuracy', 3)))),
            'helpfulness': min(5, max(1, int(data.get('helpfulness', 3)))),
            'politeness': min(5, max(1, int(data.get('politeness', 3)))),
            'suggestion': str(data.get('suggestion', ''))[:200],
        }
    except Exception as e:
        logger.warning(f"[Chatbot] QA check failed: {e}")
        return None
