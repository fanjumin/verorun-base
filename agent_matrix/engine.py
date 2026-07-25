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
from concurrent.futures import ThreadPoolExecutor
import time as _time

logger = logging.getLogger(__name__)

# 模块级 sys.path 设置（只执行一次，避免函数内重复插入）
_PARENT_DIR = os.path.join(os.path.dirname(__file__), '..')
_AUTH_CENTER_DIR = os.path.join(os.path.dirname(__file__), '..', 'auth-center')
for _d in (_AUTH_CENTER_DIR, _PARENT_DIR):
    if _d not in sys.path:
        sys.path.append(_d)

# 统一日志线程池（避免每次调用创建新线程）
_LOG_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix='token-log')

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
        'base_url': 'https://api.deepseek.com/v1',
        'default_model': None,
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
    from models import get_db
    with get_db() as conn:
        row = conn.execute("SELECT value FROM system_config WHERE key=%s", (key_name,)).fetchone()
    val = row['value'] if row and row['value'] else ''
    return val


def _resolve_key_from_provider_api_keys(provider_slug):
    """从 provider_api_keys 表读取并解密 API Key"""
    try:
        from models import get_db as _get_db
        from services.crypto import decrypt as _decrypt
        with _get_db() as conn:
            row = conn.execute(
                "SELECT key_value_enc FROM provider_api_keys "
                "WHERE provider=%s AND is_active=1 AND key_value_enc != '' "
                "ORDER BY id LIMIT 1",
                (provider_slug,)
            ).fetchone()
        if row and row['key_value_enc']:
            return _decrypt(row['key_value_enc'])
    except Exception as e:
        logger.warning(f"[KeyResolver] provider_api_keys lookup failed for {provider_slug}: {e}")
    return ''


def _resolve_agent_model_config(config: dict) -> dict:
    """
    统一解析 Agent 的模型配置。
    优先级: provider_model_id → model_provider_id(旧) → 旧字段兼容
    """
    # 优先用新字段 provider_model_id，回退到旧 model_provider_id
    pm_id = config.get('provider_model_id') or config.get('model_provider_id')
    if pm_id:
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
            config['api_key_id'] = pm.get('api_key_id')
            if 'capabilities' not in config or not config.get('capabilities'):
                config['capabilities'] = pm['capabilities']
            return config
    # 回退：使用 agent 自身旧字段
    return config


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
                VALUES (%s,%s,CURRENT_DATE::text,%s,%s,%s,1,NOW())
                ON CONFLICT(agent_id, stat_date) DO UPDATE SET
                    prompt_tokens      = agent_token_daily.prompt_tokens + excluded.prompt_tokens,
                    completion_tokens  = agent_token_daily.completion_tokens + excluded.completion_tokens,
                    total_tokens       = agent_token_daily.total_tokens + excluded.total_tokens,
                    call_count         = agent_token_daily.call_count + 1,
                    updated_at         = NOW()
            """, (agent_id, agent_name, prompt_tokens, completion_tokens, total_tokens))
            conn.commit()
    except Exception as e:
        logger.error(f"[TokenLog] Failed to write token usage: {e}")


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
                "FROM agent_token_daily WHERE stat_date = CURRENT_DATE::text"
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


# ============================================================
# UnifiedLLM — 统一 LLM 调用入口
# ============================================================
# 所有模块通过 get_gateway() 或直接实例化调用 LLM。
# 从 provider_models 读取配置，支持两种寻址方式：
#   1. provider_model_id（推荐）
#   2. provider + model（兼容旧代码）
# 所有调用统一写入 agent_token_logs + agent_token_daily。

class UnifiedLLM:
    """统一 LLM 入口。
    支持实例模式：UnifiedLLM(config) 兼容 AIEngine 调用方式。
    """

    def __init__(self, config=None):
        self._clients = {}  # 缓存 OpenAI 客户端实例
        self._clients_ts = {}  # 缓存时间戳（用于 TTL 过期）
        self._clients_lock = threading.Lock()  # 线程安全
        self._rate_limiter = deque(maxlen=1000)
        self._provider = ''
        self._model = ''
        self._base_url = ''
        self._system_prompt = ''
        self._agent_id = None
        self._agent_name = 'Unknown'
        self._api_key_id = None
        if config:
            self._apply_config(config)

    def _apply_config(self, config):
        """应用 agent 配置（兼容 AIEngine 构造方式）"""
        config = _resolve_agent_model_config(config)
        self._provider = config.get('provider', '')
        self._model = config.get('model_name', '')
        self._api_key_id = config.get('api_key_id')
        import sys
        print(f"[DIAG] _apply_config: provider={self._provider}, model={self._model}, api_key_id={self._api_key_id}, pm_id={config.get('provider_model_id')}", file=sys.stderr, flush=True)
        self._base_url = config.get('base_url', '')
        self._system_prompt = config.get('system_prompt', '')
        self._agent_id = config.get('id') if config.get('id') is not None else config.get('agent_id')
        self._agent_name = config.get('name') or config.get('agent_name', 'Unknown')

    def _get_conn(self):
        """惰性获取 DB 连接（避免 init 时触发 PostgreSQL 连接）"""
        from models import get_db
        return get_db()

    def _default_base_url(self, provider):
        """供应商默认 base_url（仅当 provider_models.endpoint_url 为空时使用）"""
        defaults = {
            'dashscope': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'openai': 'https://api.openai.com/v1',
            'deepseek': 'https://api.deepseek.com/v1',
            'openrouter': 'https://openrouter.ai/api/v1',
            'ollama': 'http://localhost:11434/v1',
            'siliconflow': 'https://api.siliconflow.cn/v1',
            'gemini': 'https://generativelanguage.googleapis.com/v1beta/openai/',
            'grok': 'https://api.x.ai/v1',
        }
        return defaults.get(provider, '')

    def _fallback_key(self, provider):
        """回退到环境变量（兼容过渡期）"""
        env_map = {
            'dashscope': 'DASHSCOPE_TEXT_KEY',
            'openai': 'OPENAI_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'siliconflow': 'SILICONFLOW_API_KEY',
            'gemini': 'GEMINI_API_KEY',
            'grok': 'XAI_API_KEY',
        }
        key_name = env_map.get(provider, '')
        if key_name:
            val = os.environ.get(key_name, '')
            if val:
                return val
        # 最终回退：从 system_config 读取（使用正确 key 格式）
        key_map = {
            'dashscope': 'dashscope_text_key',
            'siliconflow': 'siliconflow_api_key',
            'deepseek': 'deepseek_api_key',
            'openai': 'openai_api_key',
            'openrouter': 'openrouter_api_key',
            'gemini': 'gemini_api_key',
            'grok': 'grok_api_key',
        }
        config_key = key_map.get(provider, f'{provider}_api_key')
        return _get_system_key(config_key)

    def _resolve_api_key(self, provider_slug, api_key_id=None):
        """优先通过 api_key_id 查 provider_api_keys，回退到 _fallback_key"""
        if api_key_id:
            try:
                with self._get_conn() as conn:
                    row = conn.execute(
                        "SELECT key_value_enc FROM provider_api_keys WHERE id=%s AND is_active=1",
                        (api_key_id,)
                    ).fetchone()
                if row and row['key_value_enc']:
                    from services.crypto import decrypt as _decrypt
                    return _decrypt(row['key_value_enc'])
            except Exception as e:
                logger.warning(f"[UnifiedLLM] api_key_id={api_key_id} lookup failed: {e}")
        # 降级路径：按 provider slug 从 provider_api_keys 查找（BUG-001 修复）
        key = _resolve_key_from_provider_api_keys(provider_slug)
        if key:
            return key
        return self._fallback_key(provider_slug)

    def _resolve_model(self, provider_model_id=None, provider=None, model=None):
        """解析模型配置。优先使用 provider_model_id"""
        if provider_model_id:
            with self._get_conn() as conn:
                pm = conn.execute(
                    """SELECT pm.model_name, pm.endpoint_url, pm.api_key_id,
                              p.slug as provider_slug
                       FROM provider_models pm
                       JOIN providers p ON p.id = pm.provider_id
                       WHERE pm.id = %s AND pm.is_active = 1 AND p.is_active = 1""",
                    (provider_model_id,)
                ).fetchone()
            if pm is None:
                raise ValueError(f'Model not found or inactive: id={provider_model_id}')
            pm = dict(pm)
            base_url = pm['endpoint_url'] or self._default_base_url(pm['provider_slug'])
            if base_url and not base_url.rstrip('/').endswith('/v1'):
                base_url = base_url.rstrip('/') + '/v1'
            return {
                'provider': pm['provider_slug'],
                'model': pm['model_name'],
                'base_url': base_url,
                'api_key': self._resolve_api_key(pm['provider_slug'], pm.get('api_key_id')),
                'model_id': provider_model_id,
            }

        # 兼容旧方式：provider + model
        if provider and model:
            with self._get_conn() as conn:
                pm = conn.execute(
                    """SELECT pm.id, pm.model_name, pm.endpoint_url, pm.api_key_id,
                              p.slug as provider_slug
                       FROM provider_models pm
                       JOIN providers p ON p.id = pm.provider_id AND p.slug = %s
                       WHERE pm.model_name = %s AND pm.is_active = 1 AND p.is_active = 1
                       LIMIT 1""",
                    (provider, model)
                ).fetchone()
            if pm:
                pm = dict(pm)
                base_url = pm['endpoint_url'] or self._default_base_url(provider)
                if base_url and not base_url.rstrip('/').endswith('/v1'):
                    base_url = base_url.rstrip('/') + '/v1'
                return {
                    'provider': pm['provider_slug'],
                    'model': pm['model_name'],
                    'base_url': base_url,
                    'api_key': self._resolve_api_key(provider, pm.get('api_key_id')),
                    'model_id': pm['id'],
                }

        raise ValueError('Cannot resolve model: provide provider_model_id or (provider + model)')

    def _get_client(self, base_url, api_key):
        """获取或创建 OpenAI 客户端（线程安全 + 5 分钟缓存 TTL）"""
        import hashlib
        cache_key = hashlib.sha256(f'{base_url}::{api_key}'.encode()).hexdigest()[:16]
        now = _time.time()
        with self._clients_lock:
            if cache_key in self._clients and now - self._clients_ts.get(cache_key, 0) < 300:
                return self._clients[cache_key]
            from openai import OpenAI
            client = OpenAI(
                base_url=base_url,
                api_key=api_key,
                timeout=120,
            )
            self._clients[cache_key] = client
            self._clients_ts[cache_key] = now
            return client

    def _check_quota(self, model_id, module, user_id=None):
        """检查 llm_quotas 精细化配额（user > model > module > global）。
        返回 (allowed: bool, reason: str)"""
        try:
            with self._get_conn() as conn:
                quotas = conn.execute(
                    """SELECT * FROM llm_quotas WHERE is_active = 1 AND (
                        (target_type = 'user' AND target_id = %s) OR
                        (target_type = 'model' AND target_id = %s) OR
                        (target_type = 'module' AND target_key = %s) OR
                        (target_type = 'global')
                    ) ORDER BY CASE target_type
                        WHEN 'user' THEN 1 WHEN 'model' THEN 2
                        WHEN 'module' THEN 3 WHEN 'global' THEN 4
                    END""",
                    (user_id or -1, model_id, module)
                ).fetchall()

                if not quotas:
                    return True, ''

                # 第一轮：检查日预算
                for q in quotas:
                    q = dict(q)
                    if q.get('daily_limit', 0) > 0:
                        today_used = conn.execute(
                            "SELECT COALESCE(SUM(total_tokens), 0) AS c FROM agent_token_logs "
                            "WHERE created_at >= CURRENT_DATE::text AND module = %s",
                            (module,)
                        ).fetchone()
                        used = today_used['c'] if isinstance(today_used, dict) else (today_used[0] or 0)
                        if used >= q['daily_limit']:
                            return False, f"Daily quota exceeded for {module}: {used}/{q['daily_limit']} tokens"

                # 第二轮：检查速率限制（先检查，全部通过后再记录）
                for q in quotas:
                    q = dict(q)
                    if q.get('rate_limit', 0) > 0:
                        now = _time.time()
                        window = q.get('rate_window_sec', 60)
                        recent = sum(1 for t in self._rate_limiter if now - t < window)
                        if recent >= q['rate_limit']:
                            return False, f"Rate limit exceeded: {recent}/{q['rate_limit']} per {window}s"

                # 所有检查通过，记录一次速率时间戳
                self._rate_limiter.append(_time.time())
                return True, ''

        except Exception as e:
            logger.warning(f'[UnifiedLLM] Quota check failed (fail-open): {e}')
            return True, ''  # fail-open

    def chat(self, messages, provider_model_id=None, provider=None, model=None,
             temperature=0.7, max_tokens=4096, module='unknown',
             raw_response=False, **kwargs):
        """统一 chat 接口
        实例模式：自动使用 self 配置
        单例模式：必须传入 provider_model_id 或 provider+model
        raw_response=False 返回 text，raw_response=True 返回 response 对象
        """
        if self._provider and not provider_model_id and not provider:
            provider = self._provider
            model = self._model

        cfg = self._resolve_model(provider_model_id, provider, model)

        # 配额检查（复用现有闸门 + llm_quotas 精细化配额）
        allowed, reason = check_ai_budget(module)
        if not allowed:
            raise RuntimeError(reason)

        quota_ok, quota_reason = self._check_quota(cfg['model_id'], module)
        if not quota_ok:
            raise RuntimeError(quota_reason)

        client = self._get_client(cfg['base_url'], cfg['api_key'])

        start_time = _time.time()
        resp = client.chat.completions.create(
            model=cfg['model'],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        elapsed = _time.time() - start_time

        usage = resp.usage
        if usage:
            self._log_usage(
                cfg['model_id'], cfg['model'], cfg['provider'],
                usage.prompt_tokens or 0,
                usage.completion_tokens or 0,
                usage.total_tokens or 0,
                'chat', module, elapsed_ms=int(elapsed * 1000),
            )

        if raw_response:
            return resp
        return resp.choices[0].message.content

    def chat_stream(self, messages, provider_model_id=None, provider=None,
                    model=None, module='unknown', **kwargs):
        """流式 chat 接口，返回生成器（自动记录 token 用量）"""
        cfg = self._resolve_model(provider_model_id, provider, model)

        allowed, reason = check_ai_budget(module)
        if not allowed:
            raise RuntimeError(reason)
        quota_ok, quota_reason = self._check_quota(cfg['model_id'], module)
        if not quota_ok:
            raise RuntimeError(quota_reason)

        client = self._get_client(cfg['base_url'], cfg['api_key'])
        start_time = _time.time()
        stream = client.chat.completions.create(
            model=cfg['model'],
            messages=messages,
            stream=True,
            stream_options={'include_usage': True},
            **kwargs
        )

        def _tracked_stream():
            final_usage = None
            try:
                for chunk in stream:
                    if chunk.usage:
                        final_usage = chunk.usage
                    yield chunk
            finally:
                if final_usage:
                    self._log_usage(
                        cfg['model_id'], cfg['model'], cfg['provider'],
                        final_usage.prompt_tokens,
                        final_usage.completion_tokens,
                        final_usage.total_tokens,
                        call_type='chat_stream', module=module,
                        elapsed_ms=int((_time.time() - start_time) * 1000)
                    )
        return _tracked_stream()

    # ── 便利方法（AIEngine 兼容） ──

    def ask(self, user_query, temperature=0.7):
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_query}
        ]
        return self.chat(messages, temperature=temperature, module='ask')

    def ask_with_history(self, history, user_query, temperature=0.7):
        messages = [{"role": "system", "content": self._system_prompt}]
        ALLOWED_ROLES = ('user', 'assistant', 'system', 'tool')
        for h in history:
            role = h['role'] if h['role'] in ALLOWED_ROLES else 'assistant'
            msg = {"role": role, "content": h.get('content', '')}
            if h.get('tool_calls'):
                msg['tool_calls'] = h['tool_calls']
            if h.get('tool_call_id'):
                msg['tool_call_id'] = h['tool_call_id']
            messages.append(msg)
        messages.append({"role": "user", "content": user_query})
        return self.chat(messages, temperature=temperature, module='ask_history')

    def chat_with_tools(self, messages, tools, temperature=0.7, max_tokens=4096):
        return self.chat(messages, temperature=temperature, max_tokens=max_tokens,
                         module='tool_call', raw_response=True, tools=tools,
                         tool_choice="auto")

    def ask_stream(self, user_query, temperature=0.7):
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_query}
        ]
        yield from self.chat_stream(messages, temperature=temperature, module='ask')

    def ask_with_history_stream(self, history, user_query, temperature=0.7):
        messages = [{"role": "system", "content": self._system_prompt}]
        ALLOWED_ROLES = ('user', 'assistant', 'system', 'tool')
        for h in history:
            role = h['role'] if h['role'] in ALLOWED_ROLES else 'assistant'
            msg = {"role": role, "content": h.get('content', '')}
            if h.get('tool_calls'):
                msg['tool_calls'] = h['tool_calls']
            if h.get('tool_call_id'):
                msg['tool_call_id'] = h['tool_call_id']
            messages.append(msg)
        messages.append({"role": "user", "content": user_query})
        yield from self.chat_stream(messages, temperature=temperature, module='ask_history')

    def is_ready(self):
        return bool(self._provider or self._clients)

    # ── 统一日志 ──

    def _log_usage(self, model_id, model_name, provider,
                   prompt_tokens, completion_tokens, total_tokens,
                   call_type='chat', module='unknown', dimension='text',
                   elapsed_ms=0):
        try:
            agent_id = self._agent_id or model_id
            agent_name = self._agent_name or f'gateway:{module}'
            _LOG_EXECUTOR.submit(_write_usage_logs,
                agent_id, agent_name, model_name, provider,
                prompt_tokens, completion_tokens, total_tokens,
                call_type, dimension, module, elapsed_ms)
        except Exception as e:
            logger.error(f"[UnifiedLLM] Failed to submit log task: {e}")


def _write_usage_logs(agent_id, agent_name, model_name, provider,
                      prompt_tokens, completion_tokens, total_tokens,
                      call_type='chat', dimension='text', module='unknown',
                      elapsed_ms=0):
    """写入 agent_token_logs + agent_token_daily。"""
    try:
        from models import get_db as _get_db
        with _get_db() as conn:
            conn.execute("""
                INSERT INTO agent_token_logs
                (agent_id, agent_name, model_name, provider,
                 prompt_tokens, completion_tokens, total_tokens,
                 call_type, dimension, module, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            """, (agent_id, agent_name, model_name, provider,
                  prompt_tokens, completion_tokens, total_tokens,
                  call_type, dimension, module))
            conn.execute("""
                INSERT INTO agent_token_daily
                (agent_id, agent_name, stat_date,
                 prompt_tokens, completion_tokens, total_tokens, call_count, updated_at)
                VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, 1, NOW())
                ON CONFLICT(agent_id, stat_date) DO UPDATE SET
                    prompt_tokens      = prompt_tokens + excluded.prompt_tokens,
                    completion_tokens  = completion_tokens + excluded.completion_tokens,
                    total_tokens       = total_tokens + excluded.total_tokens,
                    call_count         = call_count + 1,
                    updated_at         = NOW()
            """, (agent_id, agent_name, prompt_tokens, completion_tokens, total_tokens))
            conn.commit()
    except Exception as e:
        logger.error(f"[TokenLog] Failed to write token usage: {e}")


# 全局单例
_gateway = None
_gateway_lock = threading.Lock()


def get_gateway():
    global _gateway
    if _gateway is not None:
        return _gateway
    with _gateway_lock:
        if _gateway is None:
            _gateway = UnifiedLLM()
        return _gateway
