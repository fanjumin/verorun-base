#!/usr/bin/env python3
"""
Orchestrator — 自动化调度中心数据库模型
=======================================
Cron 任务调度系统 + Workflow 工作流引擎的 SQLite 数据模型。

两种 智能体 区分：
- system_agents: 平台内置的系统 Agent，用于执行平台自动化任务
- agents (现有 users 表): 用户配置的 AI 分身 Agent

@package orchestrator
"""

import json, time
from datetime import datetime
from contextlib import contextmanager
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
DB_PATH = os.environ.get('DB_PATH', os.path.join(DATA_DIR, 'x7k2m9a4.db'))
os.makedirs(DATA_DIR, exist_ok=True)


@contextmanager
def get_db():
    """获取数据库连接（复用 easykai 主库连接模式）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
    finally:
        conn.close()


def init_orchestrator_tables():
    """初始化调度器所有表（幂等：IF NOT EXISTS）"""
    with get_db() as conn:
        conn.executescript("""
            -- =====================================================
            -- 1. 系统 Agent 配置表（平台自己的 AI 执行者）
            -- =====================================================
            CREATE TABLE IF NOT EXISTS system_agents (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL UNIQUE,
                description     TEXT DEFAULT '',
                provider        TEXT NOT NULL DEFAULT 'dashscope',
                model           TEXT NOT NULL DEFAULT 'qwen-turbo',
                api_key_ref     TEXT DEFAULT 'dashscope_text_key',
                base_url        TEXT DEFAULT '',
                system_prompt   TEXT DEFAULT '',
                capabilities    TEXT DEFAULT '[]',       -- JSON array
                max_concurrency INTEGER DEFAULT 1,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            -- =====================================================
            -- 2. Cron 任务定义表
            -- =====================================================
            CREATE TABLE IF NOT EXISTS cron_jobs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                description     TEXT DEFAULT '',

                -- 调度方式
                job_type        TEXT NOT NULL DEFAULT 'cron'
                                CHECK(job_type IN ('cron','interval','once')),
                cron_expr       TEXT DEFAULT '',          -- 标准Cron: '0 30 9 * * 1-5'
                natural_expr    TEXT DEFAULT '',          -- 自然语言: '每个交易日 9:30'
                interval_seconds INTEGER DEFAULT 0,       -- 固定间隔（秒）
                timezone        TEXT DEFAULT 'Asia/Shanghai',
                calendar        TEXT DEFAULT '{}',        -- JSON: {workdays_only, exclude_holidays, trade_days_only}

                -- 执行规划
                start_at        TEXT DEFAULT '',
                end_at          TEXT DEFAULT '',
                next_run_at     TEXT DEFAULT '',
                max_runs        INTEGER DEFAULT 0,        -- 0 = 无限制

                -- Agent 配置（两种 Agent 区分）
                agent_type      TEXT NOT NULL DEFAULT 'system'
                                CHECK(agent_type IN ('system','user')),
                agent_id        INTEGER DEFAULT NULL,     -- system: system_agents.id | user: agents.id

                -- 目标配置
                target_type     TEXT NOT NULL DEFAULT 'workflow'
                                CHECK(target_type IN ('workflow','api','script','agent_task')),
                target_config   TEXT NOT NULL DEFAULT '{}', -- JSON: 根据target_type不同

                -- 优先级与资源
                priority        TEXT NOT NULL DEFAULT 'normal'
                                CHECK(priority IN ('critical','high','normal','low')),
                worker_pool     TEXT DEFAULT 'shared',    -- 'shared' | 'dedicated'

                -- 重试策略
                max_retries     INTEGER DEFAULT 3,
                retry_delay     INTEGER DEFAULT 10,       -- 初次重试延迟（秒）
                retry_backoff   REAL DEFAULT 2.0,         -- 指数退避因子
                timeout_seconds INTEGER DEFAULT 300,

                -- 状态
                is_active       INTEGER DEFAULT 1,
                last_run_at     TEXT DEFAULT '',
                last_status     TEXT DEFAULT ''
                                CHECK(last_status IN ('','success','failed','running','timeout','cancelled')),
                last_duration_ms INTEGER DEFAULT 0,
                run_count       INTEGER DEFAULT 0,
                fail_count      INTEGER DEFAULT 0,

                -- 审计
                created_by      INTEGER DEFAULT 0,        -- users.id
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_cron_jobs_active
                ON cron_jobs(is_active, next_run_at);
            CREATE INDEX IF NOT EXISTS idx_cron_jobs_type
                ON cron_jobs(job_type, priority);

            -- =====================================================
            -- 3. 任务依赖关系表（DAG 边）
            -- =====================================================
            CREATE TABLE IF NOT EXISTS job_dependencies (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id          INTEGER NOT NULL REFERENCES cron_jobs(id) ON DELETE CASCADE,
                depends_on_job_id INTEGER NOT NULL REFERENCES cron_jobs(id) ON DELETE CASCADE,
                condition       TEXT NOT NULL DEFAULT 'success'
                                CHECK(condition IN ('success','failure','any','completed')),
                UNIQUE(job_id, depends_on_job_id)
            );

            -- =====================================================
            -- 4. 工作流定义表
            -- =====================================================
            CREATE TABLE IF NOT EXISTS workflow_definitions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                description     TEXT DEFAULT '',
                version         INTEGER DEFAULT 1,
                is_active       INTEGER DEFAULT 1,

                -- Agent 配置
                agent_type      TEXT NOT NULL DEFAULT 'system'
                                CHECK(agent_type IN ('system','user')),
                agent_id        INTEGER DEFAULT NULL,

                -- DAG 定义（JSON）
                -- 结构: {
                --   "nodes": [{
                --     "id": "node_1",
                --     "type": "ai_agent|data_collect|ai_process|condition|approval|publish|notify|wait|sub_workflow|market_check",
                --     "name": "采集36氪",
                --     "config": {...},   -- 节点类型特定配置
                --     "position": {x, y}  -- 可视化编辑器坐标
                --   }],
                --   "edges": [{
                --     "from": "node_1",
                --     "to": "node_2",
                --     "condition": ""  -- 条件分支: "success"|"failure"|"${var} > 0.05"
                --   }]
                -- }
                definition      TEXT NOT NULL DEFAULT '{"nodes":[],"edges":[]}',

                -- 版本控制
                change_log      TEXT DEFAULT '',

                -- 触发方式（可多选）
                triggers        TEXT DEFAULT '[]',        -- JSON: [{type:"cron",config:{...}}]

                -- 并发控制
                max_concurrency INTEGER DEFAULT 1,
                timeout_minutes INTEGER DEFAULT 60,

                -- 错误处理
                on_error        TEXT DEFAULT 'pause'
                                CHECK(on_error IN ('pause','skip','retry','abort')),

                -- 审计
                created_by      INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_wf_active
                ON workflow_definitions(is_active, version);

            -- =====================================================
            -- 5. 工作流运行实例表
            -- =====================================================
            CREATE TABLE IF NOT EXISTS workflow_instances (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id     INTEGER NOT NULL REFERENCES workflow_definitions(id),
                version         INTEGER DEFAULT 1,

                -- 状态机
                status          TEXT NOT NULL DEFAULT 'pending'
                                CHECK(status IN ('pending','running','paused',
                                                 'completed','failed','cancelled','timeout')),

                -- 触发信息
                trigger_type    TEXT NOT NULL DEFAULT 'manual'
                                CHECK(trigger_type IN ('cron','manual','webhook','event','dependency')),
                trigger_config  TEXT DEFAULT '{}',

                -- 运行时数据
                current_node_id TEXT DEFAULT '',
                context_data    TEXT DEFAULT '{}',        -- 全局上下文（JSON），节点间传递数据
                error_message   TEXT DEFAULT '',
                error_detail    TEXT DEFAULT '',

                -- 时间
                started_at      TEXT DEFAULT '',
                finished_at     TEXT DEFAULT '',
                duration_ms     INTEGER DEFAULT 0,

                -- Agent 实际执行者
                executed_by_agent TEXT DEFAULT '',
                executed_by_agent_id INTEGER DEFAULT NULL,

                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_wfi_status
                ON workflow_instances(status, started_at);
            CREATE INDEX IF NOT EXISTS idx_wfi_wf
                ON workflow_instances(workflow_id, status);

            -- =====================================================
            -- 6. 工作流节点运行实例表
            -- =====================================================
            CREATE TABLE IF NOT EXISTS workflow_node_instances (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_instance_id INTEGER NOT NULL
                                    REFERENCES workflow_instances(id) ON DELETE CASCADE,
                node_id         TEXT NOT NULL,            -- 对应 definition 中的 node.id
                node_type       TEXT NOT NULL,
                node_name       TEXT DEFAULT '',

                -- 状态机
                status          TEXT NOT NULL DEFAULT 'pending'
                                CHECK(status IN ('pending','running','completed',
                                                 'failed','skipped','waiting_approval',
                                                 'waiting','timeout')),

                -- 输入输出
                input_data      TEXT DEFAULT '{}',        -- JSON
                output_data     TEXT DEFAULT '{}',        -- JSON
                error_message   TEXT DEFAULT '',
                error_detail    TEXT DEFAULT '',

                -- 重试
                retry_count     INTEGER DEFAULT 0,
                max_retries     INTEGER DEFAULT 3,

                -- 审批
                approval_status TEXT DEFAULT ''
                                CHECK(approval_status IN ('','pending','approved','rejected')),
                approved_by     INTEGER DEFAULT NULL,
                approved_at     TEXT DEFAULT '',

                -- 时间
                started_at      TEXT DEFAULT '',
                finished_at     TEXT DEFAULT '',
                duration_ms     INTEGER DEFAULT 0,

                -- 执行上下文（用于调试）
                log_snippet     TEXT DEFAULT '',

                FOREIGN KEY (workflow_instance_id) REFERENCES workflow_instances(id)
            );

            CREATE INDEX IF NOT EXISTS idx_wni_instance
                ON workflow_node_instances(workflow_instance_id, node_id);
            CREATE INDEX IF NOT EXISTS idx_wni_status
                ON workflow_node_instances(status);

            -- =====================================================
            -- 7. 执行日志表
            -- =====================================================
            CREATE TABLE IF NOT EXISTS execution_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type     TEXT NOT NULL
                                CHECK(source_type IN ('cron','workflow','node','system')),
                source_id       INTEGER DEFAULT 0,        -- cron_jobs.id / workflow_instances.id / workflow_node_instances.id
                level           TEXT NOT NULL DEFAULT 'info'
                                CHECK(level IN ('debug','info','warn','error','fatal')),
                message         TEXT NOT NULL,
                details         TEXT DEFAULT '{}',         -- JSON
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_el_source
                ON execution_logs(source_type, source_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_el_level
                ON execution_logs(level, created_at);

            -- =====================================================
            -- 8. 告警配置表
            -- =====================================================
            CREATE TABLE IF NOT EXISTS alerts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                description     TEXT DEFAULT '',
                rule_type       TEXT NOT NULL
                                CHECK(rule_type IN ('job_failed','workflow_failed',
                                                    'timeout','node_failed','custom')),
                rule_config     TEXT DEFAULT '{}',         -- JSON: {source_type, source_id, threshold, ...}
                channel         TEXT NOT NULL DEFAULT 'notification'
                                CHECK(channel IN ('email','webhook','sms','notification','all')),
                channel_config  TEXT DEFAULT '{}',         -- JSON: {webhook_url, email_to, ...}
                is_active       INTEGER DEFAULT 1,
                throttle_minutes INTEGER DEFAULT 5,        -- 防重复
                last_triggered_at TEXT DEFAULT '',
                trigger_count   INTEGER DEFAULT 0,
                created_by      INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            -- =====================================================
            -- 9. 调度器节点状态表（分布式支持）
            -- =====================================================
            CREATE TABLE IF NOT EXISTS scheduler_state (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                scheduler_id    TEXT NOT NULL UNIQUE,      -- 实例唯一标识
                hostname        TEXT DEFAULT '',
                is_leader       INTEGER DEFAULT 0,
                last_heartbeat  TEXT DEFAULT (datetime('now')),
                running_jobs    INTEGER DEFAULT 0,
                running_workflows INTEGER DEFAULT 0,
                state_json      TEXT DEFAULT '{}',
                started_at      TEXT DEFAULT (datetime('now'))
            );

            -- =====================================================
            -- 10. 工作流触发器表（事件驱动：发布即触发工作流）
            -- =====================================================
            CREATE TABLE IF NOT EXISTS workflow_triggers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                trigger_event   TEXT NOT NULL,             -- 事件名, 如 'cms.published'/'content_factory.approved'
                workflow_id     INTEGER NOT NULL,          -- 要执行的 workflow_definitions.id
                match_condition TEXT DEFAULT '{}',         -- JSON 匹配条件, 空=无条件. 如 {"category":"news","source":"factory"}
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_wt_event
                ON workflow_triggers(trigger_event, is_active);

            -- 预置默认系统 Agent（仅当没有数据时插入）
            INSERT OR IGNORE INTO system_agents (name, description, provider, model, api_key_ref, system_prompt, capabilities)
            VALUES ('default-system-agent', '平台默认自动调度 Agent，执行内容工厂、市场监控等自动化任务',
                    'dashscope', 'qwen-turbo', 'dashscope_text_key',
                    '你是平台的自动化调度助手。你的职责是执行定时任务、处理工作流、生成内容、监控市场数据。请严格按照任务要求输出结果。',
                    '["content_factory","market_monitor","data_analysis","report_generation"]');
        """)
        conn.commit()


# ========== 辅助函数 ==========

def now_str():
    """当前时间字符串"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def to_json(obj):
    """序列化到 JSON 字符串"""
    return json.dumps(obj, ensure_ascii=False, default=str)


def from_json(s, default=None):
    """从 JSON 字符串反序列化"""
    if not s:
        return default or {}
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default or {}


# ========== CRON 任务 CRUD ==========

def create_cron_job(data):
    """创建 Cron 任务"""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO cron_jobs
                (name, description, job_type, cron_expr, natural_expr,
                 interval_seconds, timezone, calendar, start_at, end_at,
                 next_run_at, max_runs, agent_type, agent_id,
                 target_type, target_config, priority, worker_pool,
                 max_retries, retry_delay, retry_backoff, timeout_seconds,
                 is_active, created_by)
            VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?)
        """, (
            data.get('name'), data.get('description', ''),
            data.get('job_type', 'cron'), data.get('cron_expr', ''),
            data.get('natural_expr', ''),
            data.get('interval_seconds', 0),
            data.get('timezone', 'Asia/Shanghai'),
            to_json(data.get('calendar', {})),
            data.get('start_at', ''), data.get('end_at', ''),
            data.get('next_run_at', ''), data.get('max_runs', 0),
            data.get('agent_type', 'system'), data.get('agent_id'),
            data.get('target_type', 'workflow'),
            to_json(data.get('target_config', {})),
            data.get('priority', 'normal'),
            data.get('worker_pool', 'shared'),
            data.get('max_retries', 3), data.get('retry_delay', 10),
            data.get('retry_backoff', 2.0), data.get('timeout_seconds', 300),
            data.get('is_active', 1), data.get('created_by', 0)
        ))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def update_cron_job(job_id, data):
    """更新 Cron 任务"""
    fields = []
    values = []
    for key in ('name','description','job_type','cron_expr','natural_expr',
                'interval_seconds','timezone','calendar','start_at','end_at',
                'next_run_at','max_runs','agent_type','agent_id',
                'target_type','target_config','priority','worker_pool',
                'max_retries','retry_delay','retry_backoff','timeout_seconds',
                'is_active'):
        if key in data:
            fields.append(f"{key}=?")
            v = data[key]
            if key in ('calendar', 'target_config') and isinstance(v, dict):
                v = to_json(v)
            values.append(v)
    if not fields:
        return False
    values.append(job_id)
    with get_db() as conn:
        fields.append("updated_at=datetime('now')")
        conn.execute(
            f"UPDATE cron_jobs SET {', '.join(fields)} WHERE id=?",
            values
        )
        return conn.execute('SELECT changes()').fetchone()[0] > 0


def get_cron_job(job_id):
    """获取单个任务"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM cron_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_cron_jobs(active_only=False, page=1, limit=50, priority=None):
    """列出 Cron 任务"""
    where = ["1=1"]
    params = []
    if active_only:
        where.append("is_active=1")
    if priority:
        where.append("priority=?")
        params.append(priority)
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM cron_jobs WHERE {' AND '.join(where)}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM cron_jobs WHERE {' AND '.join(where)} "
            f"ORDER BY priority DESC, created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "jobs": [dict(r) for r in rows]
        }


def delete_cron_job(job_id):
    """删除任务（级联删除依赖）"""
    with get_db() as conn:
        conn.execute("DELETE FROM job_dependencies WHERE job_id=? OR depends_on_job_id=?", (job_id, job_id))
        conn.execute("DELETE FROM cron_jobs WHERE id=?", (job_id,))
        return conn.execute('SELECT changes()').fetchone()[0] > 0


# ========== 工作流 CRUD ==========

def create_workflow(data):
    """创建工作流定义"""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO workflow_definitions
                (name, description, version, is_active,
                 agent_type, agent_id, definition, change_log,
                 triggers, max_concurrency, timeout_minutes, on_error,
                 created_by)
            VALUES (?,?,?,?, ?,?,?,?, ?,?,?,?, ?)
        """, (
            data.get('name'), data.get('description', ''),
            data.get('version', 1), data.get('is_active', 1),
            data.get('agent_type', 'system'), data.get('agent_id'),
            data.get('definition', '{"nodes":[],"edges":[]}'),
            data.get('change_log', ''),
            to_json(data.get('triggers', [])),
            data.get('max_concurrency', 1),
            data.get('timeout_minutes', 60),
            data.get('on_error', 'pause'),
            data.get('created_by', 0)
        ))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def update_workflow(wf_id, data):
    """更新工作流定义（版本递增）"""
    fields = []
    values = []
    for key in ('name','description','is_active','agent_type','agent_id',
                'definition','change_log','triggers','max_concurrency',
                'timeout_minutes','on_error'):
        if key in data:
            fields.append(f"{key}=?")
            v = data[key]
            if isinstance(v, (dict, list)):
                v = to_json(v)
            values.append(v)
    if not fields:
        return False
    fields.append("version=version+1")
    fields.append("updated_at=datetime('now')")
    values.append(wf_id)
    with get_db() as conn:
        conn.execute(
            f"UPDATE workflow_definitions SET {', '.join(fields)} WHERE id=?",
            values
        )
        return conn.execute('SELECT changes()').fetchone()[0] > 0


def get_workflow(wf_id):
    """获取工作流定义"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM workflow_definitions WHERE id=?", (wf_id,)
        ).fetchone()
        return dict(row) if row else None


def list_workflows(active_only=False, page=1, limit=50):
    """列出工作流定义"""
    where = ["1=1"]
    params = []
    if active_only:
        where.append("is_active=1")
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM workflow_definitions WHERE {' AND '.join(where)}",
            params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM workflow_definitions WHERE {' AND '.join(where)} "
            f"ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "workflows": [dict(r) for r in rows]
        }


def delete_workflow(wf_id):
    """删除工作流（级联删除关联实例和节点）"""
    with get_db() as conn:
        # 先删除节点实例
        conn.execute("""DELETE FROM workflow_node_instances WHERE workflow_instance_id IN 
                        (SELECT id FROM workflow_instances WHERE workflow_id=?)""", (wf_id,))
        # 再删除实例
        conn.execute("DELETE FROM workflow_instances WHERE workflow_id=?", (wf_id,))
        # 最后删除定义
        conn.execute("DELETE FROM workflow_definitions WHERE id=?", (wf_id,))
        return conn.execute('SELECT changes()').fetchone()[0] > 0


# ========== 工作流实例 ==========

def create_workflow_instance(workflow_id, trigger_type='manual', trigger_config=None):
    """创建工作流运行实例"""
    wf = get_workflow(workflow_id)
    if not wf:
        return None
    defn = from_json(wf.get('definition', '{}'))
    with get_db() as conn:
        conn.execute("""
            INSERT INTO workflow_instances
                (workflow_id, version, trigger_type, trigger_config,
                 status, context_data, started_at)
            VALUES (?,?,?,?, 'running', '{}', datetime('now'))
        """, (
            workflow_id, wf.get('version', 1),
            trigger_type, to_json(trigger_config or {})
        ))
        inst_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # 创建所有节点的实例记录
        nodes = defn.get('nodes', [])
        for node in nodes:
            conn.execute("""
                INSERT INTO workflow_node_instances
                    (workflow_instance_id, node_id, node_type, node_name,
                     status, input_data, max_retries)
                VALUES (?,?,?,?, 'pending', '{}', ?)
            """, (
                inst_id, node.get('id', ''),
                node.get('type', ''), node.get('name', ''),
                node.get('max_retries', 3)
            ))

        conn.commit()
        return inst_id


def update_workflow_instance(inst_id, updates):
    """更新工作流实例状态"""
    fields = []
    values = []
    for key in ('status','current_node_id','context_data','error_message',
                'error_detail','finished_at','duration_ms',
                'executed_by_agent','executed_by_agent_id'):
        if key in updates:
            fields.append(f"{key}=?")
            values.append(updates[key])
    if not fields:
        return False
    values.append(inst_id)
    with get_db() as conn:
        conn.execute(
            f"UPDATE workflow_instances SET {', '.join(fields)} WHERE id=?",
            values
        )
        return conn.execute('SELECT changes()').fetchone()[0] > 0


def get_workflow_instance(inst_id):
    """获取工作流实例"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM workflow_instances WHERE id=?", (inst_id,)
        ).fetchone()
        return dict(row) if row else None


def list_workflow_instances(workflow_id=None, status=None, page=1, limit=50):
    """列出工作流运行实例"""
    where = ["1=1"]
    params = []
    if workflow_id:
        where.append("workflow_id=?")
        params.append(workflow_id)
    if status:
        where.append("status=?")
        params.append(status)
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM workflow_instances WHERE {' AND '.join(where)}",
            params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM workflow_instances WHERE {' AND '.join(where)} "
            f"ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "instances": [dict(r) for r in rows]
        }


# ========== 节点实例 ==========

def update_node_instance(node_inst_id, updates):
    """更新节点实例状态"""
    fields = []
    values = []
    for key in ('status','input_data','output_data','error_message',
                'error_detail','retry_count','started_at','finished_at',
                'duration_ms','log_snippet','approval_status',
                'approved_by','approved_at'):
        if key in updates:
            fields.append(f"{key}=?")
            v = updates[key]
            if isinstance(v, (dict, list)):
                v = to_json(v)
            values.append(v)
    if not fields:
        return False
    values.append(node_inst_id)
    with get_db() as conn:
        conn.execute(
            f"UPDATE workflow_node_instances SET {', '.join(fields)} WHERE id=?",
            values
        )
        return conn.execute('SELECT changes()').fetchone()[0] > 0


def get_node_instance(node_inst_id):
    """获取节点实例"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM workflow_node_instances WHERE id=?", (node_inst_id,)
        ).fetchone()
        return dict(row) if row else None


def get_node_instances_by_workflow(inst_id):
    """获取工作流所有节点实例"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM workflow_node_instances WHERE workflow_instance_id=? ORDER BY id",
            (inst_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ========== 日志 ==========

def add_log(source_type, source_id, level, message, details=None):
    """添加执行日志"""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO execution_logs (source_type, source_id, level, message, details)
            VALUES (?,?,?,?,?)
        """, (source_type, source_id, level, message, to_json(details or {})))


def query_logs(source_type=None, source_id=None, level=None, page=1, limit=100):
    """查询日志"""
    where = ["1=1"]
    params = []
    if source_type:
        where.append("source_type=?")
        params.append(source_type)
    if source_id:
        where.append("source_id=?")
        params.append(source_id)
    if level:
        where.append("level=?")
        params.append(level)
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM execution_logs WHERE {' AND '.join(where)}",
            params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM execution_logs WHERE {' AND '.join(where)} "
            f"ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "logs": [dict(r) for r in rows]
        }


# ========== 统计 ==========

def get_automation_stats():
    """获取自动化系统统计概览"""
    with get_db() as conn:
        total_jobs = conn.execute("SELECT COUNT(*) FROM cron_jobs").fetchone()[0]
        active_jobs = conn.execute("SELECT COUNT(*) FROM cron_jobs WHERE is_active=1").fetchone()[0]
        total_wfs = conn.execute("SELECT COUNT(*) FROM workflow_definitions").fetchone()[0]
        running_instances = conn.execute(
            "SELECT COUNT(*) FROM workflow_instances WHERE status IN ('running','paused')"
        ).fetchone()[0]
        completed_today = conn.execute(
            "SELECT COUNT(*) FROM workflow_instances WHERE status='completed' AND date(finished_at)=date('now')"
        ).fetchone()[0]
        failed_today = conn.execute(
            "SELECT COUNT(*) FROM workflow_instances WHERE status='failed' AND date(finished_at)=date('now')"
        ).fetchone()[0]
        avg_duration = conn.execute(
            "SELECT COALESCE(AVG(duration_ms),0) FROM workflow_instances WHERE status='completed' AND date(finished_at)=date('now')"
        ).fetchone()[0]

        # 获取最近失败的
        recent_failures = conn.execute("""
            SELECT wi.id, w.name, wi.status, wi.error_message, wi.finished_at
            FROM workflow_instances wi
            LEFT JOIN workflow_definitions w ON wi.workflow_id = w.id
            WHERE wi.status IN ('failed','timeout')
            ORDER BY wi.finished_at DESC LIMIT 5
        """).fetchall()

        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "total_workflows": total_wfs,
            "running_instances": running_instances,
            "completed_today": completed_today,
            "failed_today": failed_today,
            "avg_duration_ms": avg_duration,
            "recent_failures": [dict(r) for r in recent_failures]
        }


# ========== 系统 Agent ==========

def get_default_system_agent():
    """获取默认系统 Agent"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM system_agents WHERE is_active=1 ORDER BY id LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def list_system_agents():
    """列出所有系统 Agent"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM system_agents ORDER BY id").fetchall()
        return [dict(r) for r in rows]
