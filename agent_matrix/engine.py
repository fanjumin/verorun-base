#!/usr/bin/env python3
"""
Agent Matrix — AI 引擎
=====================
支持 DashScope Qwen / OpenAI / DeepSeek / OpenRouter。
复用 system_config 中的 API Key，无需额外配置。
"""
from i18n import _
import json, logging, sys, os, threading
from collections import deque
import time as _time

logger = logging.getLogger(__name__)

# 供应商默认配置
PROVIDER_CONFIGS = {
    'dashscope': {
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'default_model': 'qwen-turbo',
        'key_ref': 'dashscope_text_key',
    },
    'openai': {
        'base_url': 'https://api.openai.com/v1',
        'default_model': 'gpt-4o-mini',
        'key_ref': '',
    },
    'deepseek': {
        'base_url': 'https://api.deepseek.com',
        'default_model': 'deepseek-chat',
        'key_ref': '',
    },
    'openrouter': {
        'base_url': 'https://openrouter.ai/api/v1',
        'default_model': 'openai/gpt-4o-mini',
        'key_ref': '',
    },
    'ollama': {
        'base_url': 'http://localhost:11434/v1',
        'default_model': 'llama3',
        'key_ref': '',
    },
    'siliconflow': {
        'base_url': 'https://api.siliconflow.cn/v1',
        'default_model': 'deepseek-ai/DeepSeek-V3',
        'key_ref': 'siliconflow_api_key',
    },
}


def _get_system_key(key_name):
    """从 system_config 读取 API Key"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from models import get_db
    with get_db() as conn:
        row = conn.execute("SELECT value FROM system_config WHERE key=%s", (key_name,)).fetchone()
    val = row['value'] if row and row['value'] else ''
    return val


def _resolve_agent_model_config(config: dict) -> dict:
    """
    统一解析 Agent 的模型配置。
    优先级: provider_model_id → model_provider_id(旧) → 旧字段兼容
    """
    # 优先用新字段 provider_model_id，回退到旧 model_provider_id
    pm_id = config.get('provider_model_id') or config.get('model_provider_id')
    if pm_id:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from models import get_db
        with get_db() as conn:
            pm = conn.execute(
                "SELECT pm.*, p.slug as provider_slug FROM provider_models pm "
                "JOIN providers p ON p.id=pm.provider_id "
                "WHERE pm.id=%s AND pm.is_active=1 AND p.is_active=1",
                (pm_id,)
            ).fetchone()
        if pm:
            pm = dict(pm)
            config['provider'] = pm['provider_slug']
            config['model_name'] = pm['model_name']
            config['base_url'] = pm['endpoint_url']
            config['api_key_ref'] = pm['api_key_ref']
            if 'capabilities' not in config or not config.get('capabilities'):
                config['capabilities'] = pm['capabilities']
            return config
    # 回退：使用 agent 自身旧字段
    return config


class AIEngine:
    """统一 AI 引擎，支持多个供应商"""

    def __init__(self, config: dict):
        """
        config: agent_matrix 行字典
          provider, model_name, api_key_ref, base_url, system_prompt
        """
        # 统一解析模型配置（model_provider_id 优先）
        config = _resolve_agent_model_config(config)

        self.provider = config.get('provider', 'deepseek')
        self.model = config.get('model_name', 'deepseek-chat')
        self.api_key_ref = config.get('api_key_ref', 'deepseek_api_key')
        self.base_url = config.get('base_url', '')
        self.system_prompt = config.get('system_prompt', '')
        self.agent_id = config.get('id') or config.get('agent_id')
        self.agent_name = config.get('name') or config.get('agent_name', 'Unknown')

        # 解析基础 URL
        if not self.base_url:
            # 先从 system_config 读取用户可配置的调用链接
            db_base_url = _get_system_key(f'model_{self.provider}_base_url')
            if db_base_url:
                self.base_url = db_base_url
            else:
                pcfg = PROVIDER_CONFIGS.get(self.provider, {})
                self.base_url = pcfg.get('base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
                if not self.api_key_ref:
                    self.api_key_ref = pcfg.get('key_ref', '')
                if self.model == 'qwen-turbo':
                    self.model = pcfg.get('default_model', 'qwen-turbo')

        # 获取 API Key
        if self.provider == 'dashscope':
            self.api_key = _get_system_key(self.api_key_ref)
            if not self.api_key:
                # dashscope 可能用 env 变量
                self.api_key = os.environ.get('DASHSCOPE_API_KEY', '')
        else:
            # 其他供应商：尝试从 api_key_ref 读取，否则走加密存储
            self.api_key = _get_system_key(self.api_key_ref) if self.api_key_ref else ''
            if not self.api_key:
                # 尝试从 agents 表的 api_key_enc 解密
                enc_key = config.get('api_key_enc', '')
                if enc_key:
                    from services.crypto import decrypt
                    self.api_key = decrypt(enc_key)
            # 最后回退到环境变量
            if not self.api_key:
                provider_upper = self.provider.upper()
                self.api_key = os.environ.get(f'{provider_upper}_API_KEY', '')
        # 最后回退到 DB 可配置的模型 API Key（最高优先级最低，仅当其他途径都未找到时使用）
        if not self.api_key:
            self.api_key = _get_system_key(f'model_{self.provider}_api_key')

        # 初始化 OpenAI 客户端
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                logger.error("openai package not installed")
        else:
            logger.warning(f"[AIEngine] {self.provider}/{self.model}: 没有 API Key")

    def chat(self, messages, temperature=0.7, max_tokens=4096):
        """调用 LLM，返回 text"""
        if not self.client:
            return _("Error: AI engine not initialized (missing API Key)")

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            # 异步记录 token 消耗
            if hasattr(resp, 'usage') and resp.usage:
                threading.Thread(target=_log_token_usage, args=(
                    self.agent_id, self.agent_name, self.model, self.provider,
                    resp.usage.prompt_tokens or 0,
                    resp.usage.completion_tokens or 0,
                    resp.usage.total_tokens or 0,
                    'chat'
                ), daemon=True).start()
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"[AIEngine] {self.provider}/{self.model} 调用失败: {e}")
            return f"Error: {e}"

    def chat_with_tools(self, messages, tools, temperature=0.7, max_tokens=4096):
        """支持原生 function calling 的调用。

        返回完整的 message 对象（含 .content 与 .tool_calls），
        由调用方（AgentRunner 的 ReAct 循环）决定是否执行工具。
        出错时返回 None。
        """
        if not self.client:
            return None
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens
            )
            # 异步记录 token 消耗（与 chat() 保持一致）
            if hasattr(resp, 'usage') and resp.usage:
                threading.Thread(target=_log_token_usage, args=(
                    self.agent_id, self.agent_name, self.model, self.provider,
                    resp.usage.prompt_tokens or 0,
                    resp.usage.completion_tokens or 0,
                    resp.usage.total_tokens or 0,
                    'tool_call'
                ), daemon=True).start()
            return resp.choices[0].message
        except Exception as e:
            logger.error(f"[AIEngine] {self.provider}/{self.model} 工具调用失败: {e}")
            return None

    def ask(self, user_query, temperature=0.7):
        """简单一问一答"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]
        return self.chat(messages, temperature)

    def ask_with_history(self, history, user_query, temperature=0.7):
        """带历史的多轮对话"""
        messages = [{"role": "system", "content": self.system_prompt}]
        for h in history:
            role = 'user' if h['role'] in ('user',) else 'assistant'
            messages.append({"role": role, "content": h['content']})
        messages.append({"role": "user", "content": user_query})
        return self.chat(messages, temperature)

    # ========================================
    # 流式输出 (SSE)
    # ========================================

    def chat_stream(self, messages, temperature=0.7, max_tokens=4096):
        """流式调用 LLM，逐段 yield 文本内容"""
        if not self.client:
            yield _("Error: AI engine not initialized (missing API Key)")
            return

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            accumulated = ''
            for chunk in resp:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    accumulated += delta.content
                    yield delta.content
            # Stream 结束后异步记录 token（基于字符估算）
            est_prompt = sum(len(m.get('content','')) for m in messages) / 4
            est_completion = len(accumulated) / 4
            threading.Thread(target=_log_token_usage, args=(
                self.agent_id, self.agent_name, self.model, self.provider,
                int(est_prompt), int(est_completion), int(est_prompt + est_completion),
                'chat', 'text'
            ), daemon=True).start()
        except Exception as e:
            logger.error(f"[AIEngine] {self.provider}/{self.model} 流式调用失败: {e}")
            yield f"Error: {e}"

    def ask_stream(self, user_query, temperature=0.7):
        """流式一问一答"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]
        yield from self.chat_stream(messages, temperature)

    def ask_with_history_stream(self, history, user_query, temperature=0.7):
        """流式多轮对话"""
        messages = [{"role": "system", "content": self.system_prompt}]
        for h in history:
            role = 'user' if h['role'] in ('user',) else 'assistant'
            messages.append({"role": role, "content": h['content']})
        messages.append({"role": "user", "content": user_query})
        yield from self.chat_stream(messages, temperature)

    def is_ready(self):
        return self.client is not None

    # ========================================
    # 媒体生成能力（声音克隆 / TTS / 数字人视频）
    # ========================================

    def voice_clone(self, audio_url: str, voice_name: str) -> dict:
        """声音复刻：上传样本 → 训练声音模型"""
        try:
            from services.volcengine_client import voice_clone as vc_clone
            result = vc_clone(audio_url, voice_name)
            return result
        except Exception as e:
            logger.error(f"[AIEngine] voice_clone 失败: {e}")
            return {'success': False, 'error': str(e)}

    def tts(self, text: str, voice_id: str, output_path: str | None = None) -> dict:
        """Text to speech"""
        try:
            from services.volcengine_client import tts as vc_tts
            result = vc_tts(text, voice_id, output_path)
            return result
        except Exception as e:
            logger.error(f"[AIEngine] tts 失败: {e}")
            return {'success': False, 'error': str(e)}

    def avatar_video(self, text: str, voice_id: str, image_url: str) -> dict:
        """数字人口播视频"""
        try:
            from services.volcengine_client import avatar_video as vc_avatar
            result = vc_avatar(text, voice_id, image_url)
            return result
        except Exception as e:
            logger.error(f"[AIEngine] avatar_video 失败: {e}")
            return {'success': False, 'error': str(e)}

    def query_media_task(self, task_id: str) -> dict:
        """查询媒体任务状态"""
        try:
            from services.volcengine_client import query_avatar_task
            result = query_avatar_task(task_id)
            return result
        except Exception as e:
            logger.error(f"[AIEngine] query_media_task 失败: {e}")
            return {'success': False, 'status': 'failed', 'error': str(e)}

    def execute_media_action(self, action: str, params: dict) -> dict:
        """统一媒体能力路由：根据 action 分发到具体方法"""
        if action == 'voice_clone':
            return self.voice_clone(
                audio_url=params.get('audio_url', ''),
                voice_name=params.get('voice_name', _('Default Sound'))
            )
        elif action == 'tts':
            return self.tts(
                text=params.get('text', ''),
                voice_id=params.get('voice_id', ''),
                output_path=params.get('output_path')
            )
        elif action == 'avatar_video':
            return self.avatar_video(
                text=params.get('text', ''),
                voice_id=params.get('voice_id', ''),
                image_url=params.get('image_url', '')
            )
        elif action == 'query':
            return self.query_media_task(
                task_id=params.get('task_id', '')
            )
        else:
            return {'success': False, 'error': f'Unsupported media action: {action}'}


# ============================================================
# Token 异步记录（供 AIEngine 内部调用）
# ============================================================

def _log_token_usage(agent_id, agent_name, model_name, provider,
                     prompt_tokens, completion_tokens, total_tokens,
                     call_type='chat', dimension='text', user_id=None, task_id=None, session_id=None):
    """异步写入 token 消耗到 agent_token_logs + agent_token_daily。静默失败。"""
    try:
        from agent_matrix.models import get_db
        with get_db() as conn:
            conn.execute("""
                INSERT INTO agent_token_logs
                (agent_id, agent_name, model_name, provider,
                 prompt_tokens, completion_tokens, total_tokens,
                 call_type, dimension, user_id, task_id, session_id, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            """, (agent_id, agent_name, model_name, provider,
                  prompt_tokens, completion_tokens, total_tokens,
                  call_type, dimension, user_id, task_id, session_id))
            conn.execute("""
                INSERT INTO agent_token_daily
                (agent_id, agent_name, stat_date,
                 prompt_tokens, completion_tokens, total_tokens, call_count, updated_at)
                VALUES (%s,%s,CURRENT_DATE,%s,%s,%s,1,NOW())
                ON CONFLICT(agent_id, stat_date) DO UPDATE SET
                    prompt_tokens      = prompt_tokens + excluded.prompt_tokens,
                    completion_tokens  = completion_tokens + excluded.completion_tokens,
                    total_tokens       = total_tokens + excluded.total_tokens,
                    call_count         = call_count + 1,
                    updated_at         = NOW()
            """, (agent_id, agent_name, prompt_tokens, completion_tokens, total_tokens))
            conn.commit()
    except Exception:
        pass


# ============================================================
# AI 费用闸门（日预算熔断 + 速率限制）
# ============================================================
# 复用现有 agent_token_daily（算当日消耗）+ system_config（存阈值），
# 不新建表/库/文件。任一维度超限即拒绝；读库异常时 fail-open 放行，
# 避免闸门自身故障阻断正常业务。

# 速率限制：进程内滑动窗口时间戳队列
_AI_CALL_TIMES = deque()
_AI_RATE_LOCK = threading.Lock()

# 阈值默认值（system_config 无对应 key 时生效）
_AI_BUDGET_DEFAULTS = {
    'ai_budget_daily_tokens': 2000000,   # 全站每日 token 上限，0=不限
    'ai_rate_max_calls': 30,             # 速率窗口内最大调用次数，0=不限
    'ai_rate_window_sec': 60,            # 速率窗口秒数
}


def _get_ai_budget_config() -> dict:
    """从 system_config 读取 AI 闸门阈值，缺失则用默认值。"""
    cfg = dict(_AI_BUDGET_DEFAULTS)
    try:
        from models import get_db as _main_get_db
        with _main_get_db() as conn:
            rows = conn.execute(
                "SELECT key, value FROM system_config WHERE key IN "
                "('ai_budget_daily_tokens','ai_rate_max_calls','ai_rate_window_sec')"
            ).fetchall()
        for r in rows:
            key = r['key'] if not isinstance(r, tuple) else r[0]
            val = r['value'] if not isinstance(r, tuple) else r[1]
            if val is None or str(val).strip() == '':
                continue
            try:
                cfg[key] = int(val)
            except (ValueError, TypeError):
                pass
    except Exception as e:
        logger.warning("[AIBudget] read config failed, using defaults: %s", e)
    return cfg


def _today_token_usage() -> int:
    """读取全站今日已消耗 token 总数（来自 agent_token_daily 汇总表）。"""
    try:
        from agent_matrix.models import get_db
        with get_db() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(total_tokens),0) AS c "
                "FROM agent_token_daily WHERE stat_date = CURRENT_DATE"
            ).fetchone()
        if row is None:
            return 0
        return int(row['c'] if not isinstance(row, tuple) else row[0])
    except Exception as e:
        logger.warning("[AIBudget] read daily usage failed: %s", e)
        return -1  # -1 表示读取失败，交由调用方 fail-open


def check_ai_budget(scene: str = '') -> tuple:
    """AI 调用前的费用闸门检查。

    Args:
        scene: 调用场景标识（仅用于日志）

    Returns:
        (allowed: bool, reason: str)
        allowed=True 放行；False 拒绝，reason 为原因。
        读库/配置异常时 fail-open（放行）。
    """
    cfg = _get_ai_budget_config()

    # 1) 速率限制（进程内滑动窗口）
    max_calls = cfg.get('ai_rate_max_calls', 0) or 0
    window = cfg.get('ai_rate_window_sec', 60) or 60
    if max_calls > 0:
        now = _time.time()
        with _AI_RATE_LOCK:
            while _AI_CALL_TIMES and now - _AI_CALL_TIMES[0] > window:
                _AI_CALL_TIMES.popleft()
            if len(_AI_CALL_TIMES) >= max_calls:
                logger.warning("[AIBudget] rate limit hit (scene=%s): %d/%ds",
                               scene, max_calls, window)
                return False, f'AI 调用速率超限（{max_calls} 次/{window} 秒），请稍后再试'
            _AI_CALL_TIMES.append(now)

    # 2) 日预算熔断
    daily_limit = cfg.get('ai_budget_daily_tokens', 0) or 0
    if daily_limit > 0:
        used = _today_token_usage()
        if used >= 0 and used >= daily_limit:
            logger.warning("[AIBudget] daily budget exhausted (scene=%s): %d/%d",
                           scene, used, daily_limit)
            return False, f"Today's AI budget is exhausted ({used}/{daily_limit} tokens)"

    return True, ''
