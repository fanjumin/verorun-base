# Health Check 模块升级方案

> 制定日期：2026-07-06
> 当前版本：v0.10.0

---

## 目录

1. [背景与动机](#1-背景与动机)
2. [当前模块现状 vs 行业主流对比](#2-当前模块现状-vs-行业主流对比)
3. [Bug 修复清单](#3-bug-修复清单)
4. [分阶段升级计划](#4-分阶段升级计划)
5. [文件变更总览](#5-文件变更总览)
6. [风险与注意事项](#6-风险与注意事项)

---

## 1. 背景与动机

经过近期生产事故，发现 Health Check 模块在日常运维中几乎未发挥实质作用。主要问题：

- "Check Config" 页面点击后显示 "Load failed"，无法管理检查项
- 缺乏标准化健康端点（Liveness/Readiness），无法对接外部监控
- 告警机制粗糙，无告警抑制/分组/静默，容易告警风暴
- 没有时间序列指标采集，无法接入 Grafana/Prometheus 生态
- 自动修复仅停留在分析建议阶段，无闭环执行能力

---

## 2. 当前模块现状 vs 行业主流对比

### 2.1 当前模块架构

核心文件位于 `health_check/` 目录（9个核心文件）：

| 层级 | 文件 | 功能 |
|------|------|------|
| 框架 | `checkers.py` | `BaseHealthCheck` 抽象基类 + `CheckerRegistry` + 13个内置检查器 |
| API | `routes.py` | 20+ REST API 端点（`/admin/health/api/*`） |
| 告警 | `alerter.py` | 邮件/站内信/Webhook 三种通知 |
| AI修复 | `ai_fixer.py` | 调用 LLM 分析结果并生成修复方案 |
| 发现 | `discovery.py` | 自动扫描模块/端点/表/插件 |
| 调度 | `scheduler_setup.py` | 写入 cron_jobs 表实现定时巡检 |
| 模型 | `models.py` | 6张表（checks/runs/history/alerts/trend） |
| UI | `health.html` | 6个标签页暗色仪表盘 |

### 2.2 与行业主流对比

| 维度 | 行业标准 | 当前 easykai | 差距等级 |
|------|---------|-------------|---------|
| **探测类型** | Liveness/Readiness/Startup 三种分离 | 仅有统一的 `check()` | 🔴 严重缺失 |
| **指标采集** | RED方法(Rate/Errors/Duration) + USE方法(CPU/Mem/Disk/Net) | 13个检查器覆盖基础资源+API，但无时序指标 | 🟡 中等差距 |
| **告警机制** | P0-P3四级 + 抑制/分组/静默/升级 | info/warning/critical 三级，无抑制/分组 | 🟡 中等差距 |
| **仪表盘** | Grafana 级拖拽面板/变量/SLO | 静态6标签页，无时间选择器 | 🟡 中度差距 |
| **响应格式** | IETF标准 `pass/warn/fail` / Spring Actuator 格式 | 自定义格式，不兼容 | 🟢 可接受 |
| **自动修复** | K8s重启/摘除/HPA/故障转移 | AI分析+修复建议（手动执行） | 🔴 较大差距 |
| **可观测性** | 分布式追踪/服务拓扑/SLO | 仅健康检查，无 APM | 🔴 较大差距 |
| **外部暴露** | `/health` `/health/liveness` `/health/readiness` 端点 | 无标准化端点 | 🔴 缺失 |

### 2.3 参考标准

- **Spring Boot Actuator**: 组件级深度检查，JSON格式输出
- **Kubernetes Probes**: Liveness/Readiness/Startup 三种探针，HTTP/TCP/Exec
- **Prometheus + Grafana**: 时序指标采集 + 可视化仪表盘
- **Datadog / New Relic**: 全栈可观测性（APM + Infra + Logs + RUM）

---

## 3. Bug 修复清单

### 3.1 "Check Config" Load failed（已修复）

- **根因**: `loadChecks()` 使用 `Promise.all` 并行调用两个 API，任一失败无独立错误处理
  - `JSON.parse(c.config||'{}')` 在 `config` 字段为非合法 JSON 字符串时崩溃
- **修复**: 
  - 新增 `safeFetch()` 辅助函数，每个 API 独立错误处理
  - `JSON.parse` 增加 try/catch + 类型判断保护
  - 失败时显示具体诊断信息而非通用 "Load failed"
- **文件**: `health_check/templates/health.html`

---

## 4. 分阶段升级计划

### 第一阶段：修复与加固

| 步骤 | 内容 | 涉及文件 | 产出 |
|------|------|---------|------|
| 1.1 | 修复 "Check Config" Load failed bug（✅ 已完成） | `health_check/templates/health.html` | 诊断信息明确的错误处理 |
| 1.2 | 补充 `/health/liveness` 和 `/health/readiness` 标准化端点 | `admin/app.py`、各服务 | 兼容 K8s/Nginx upstream 检查 |

**1.2 详细设计**:

```
GET /health/liveness  → HTTP 200/500, body: "ok" (仅检查进程存活)
GET /health/readiness → HTTP 200/503, body: JSON (检查 DB/Redis/关键依赖)
GET /health           → HTTP 200/503, body: JSON (综合状态)
```

### 第二阶段：告警升级

| 步骤 | 内容 | 涉及文件 | 产出 |
|------|------|---------|------|
| 2.1 | 实现 P0-P3 四级告警 + 多级阈值 + 聚合窗口 | `alerter.py`, `models.py` | 防止告警风暴 |
| 2.2 | 告警静默窗口 + 告警升级（P3→P1 自动升级） | `routes.py`, `alerter.py` | 运维窗口期不被打扰 |

**2.1 告警级别定义**:

| 级别 | 标签 | 含义 | 通知渠道 |
|------|------|------|---------|
| P0 / Critical | 🔴 CRITICAL | 服务完全不可用，影响所有用户 | 电话 + 短信 + IM + 邮件 |
| P1 / Major | 🟠 WARNING | 核心功能受损，影响大量用户 | 电话 + IM + 邮件 |
| P2 / Minor | 🟡 WARNING | 非核心功能异常或性能下降 | IM + 邮件 |
| P3 / Info | 🔵 INFO | 预警通知（磁盘85%、证书临近过期） | 邮件/工单 |

**告警最佳实践**:
- 避免告警疲劳：设置聚合窗口（如持续5分钟才触发）
- 告警抑制：高优先级触发后抑制相关低优先级
- 告警分组：同类告警合并发送
- 告警静默：计划维护期间静默已知告警

### 第三阶段：可观测性增强

| 步骤 | 内容 | 涉及文件 | 产出 |
|------|------|---------|------|
| 3.1 | 添加 Prometheus 兼容 `/metrics` 端点 | 新增 `health_check/metrics.py` | 外接 Grafana 可视化 |
| 3.2 | Dashboard 增强：时间范围选择器、类别筛选、自动刷新 | `health.html` | 运维盯屏可用 |

**3.1 采集指标**:

| 类别 | 关键指标 |
|------|---------|
| 基础设施 | CPU使用率、内存使用率、磁盘使用率、网络流量 |
| 应用层 | API QPS、延迟分位数(p50/p95/p99)、错误率(4xx/5xx) |
| 数据库 | 连接池状态、查询延迟、死锁次数 |
| 缓存 | 命中率、淘汰数、连接数 |

### 第四阶段：自动修复闭环

| 步骤 | 内容 | 涉及文件 | 产出 |
|------|------|---------|------|
| 4.1 | AI 分析结果自动执行低风险修复 | `ai_fixer.py`, `routes.py` | 减少人工介入 |
| 4.2 | 修复操作审计日志 + 回滚能力 | `models.py`, `routes.py` | 安全可控 |

**4.1 白名单操作**（仅允许自动执行以下低风险操作）:

- 清理临时文件/缓存
- 重启非核心 worker
- 调整日志级别
- 刷新 CDN 缓存

**禁止自动执行**: 数据库变更、服务重启、配置修改、文件删除

---

## 5. 文件变更总览

| 阶段 | 新增文件 | 修改文件 | 删除文件 |
|------|---------|---------|---------|
| 一 | 0 | 2（health.html, admin/app.py） | 0 |
| 二 | 0 | 3（alerter.py, models.py, routes.py） | 0 |
| 三 | 1（metrics.py） | 1（health.html） | 0 |
| 四 | 1（migration） | 3（ai_fixer.py, routes.py, models.py） | 0 |

**核心文件清单**:

```
health_check/
├── __init__.py          # 入口，蓝图注册
├── models.py            # 数据库模型（6张表）
├── checkers.py          # 检查器框架 + 13个内置检查器
├── routes.py            # Flask API 路由（20+ 端点）
├── alerter.py           # 告警模块
├── ai_fixer.py          # AI修复引擎
├── discovery.py         # 资源发现引擎
├── scheduler_setup.py   # 定时巡检配置
├── metrics.py            # [新增] Prometheus 指标端点
├── DEVELOPER.md         # 开发者指南
└── templates/
    └── health.html      # 仪表盘页面（6个标签页）
```

---

## 6. 风险与注意事项

| 风险项 | 影响 | 缓解措施 |
|--------|------|---------|
| 告警升级涉及表结构调整 | 数据迁移失败 | 迁移脚本支持回滚，先在 staging 验证 |
| Prometheus metrics 端点性能 | SQLite 不支持高并发 | 指标采集频率限制 15s+，独立线程 |
| 自动修复误操作 | 生产数据损坏 | 严格白名单机制，所有操作审计日志 |
| Dashboard 增强改动大 | 引入新的 JS 错误 | 保持向后兼容，渐进增强 |

---

**下一步**: 继续执行第一阶段 Step 1.2 — 标准化健康端点。
