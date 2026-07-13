# 易站系统全面测试报告

- 生成时间: 2026-07-12 19:57:20
- 目标服务器: easykai@***REMOVED***
- 汇总: ✅ 31  ⚠️ 3  ❌ 0  (共 34 项)

## Auth

| 状态 | 项目 | 耗时 | 详情 |
|------|------|------|------|
| ✅ | 获取 admin JWT | - | token 长度=291 |

## L0

| 状态 | 项目 | 耗时 | 详情 |
|------|------|------|------|
| ✅ | site:8081/health | 140ms | {"service":"auth-center+site","status":"ok"} |
| ✅ | platform:8083/health | 141ms | {"service":"platform","status":"ok","version":"1.0.0"} |
| ✅ | admin:8084/health | 149ms | {"port":8084,"service":"admin-panel","status":"ok"} |
| ✅ | health:8085/health | 145ms | {"service":"health-service","status":"ok"} |

## L1

| 状态 | 项目 | 耗时 | 详情 |
|------|------|------|------|
| ✅ | health-service /ready (DB 连通) | - | {"service":"health-service","status":"ready"} |

## L2

| 状态 | 项目 | 耗时 | 详情 |
|------|------|------|------|
| ✅ | 触发 health/api/run（异步） | 158ms | Health check started, results will appear shortly |
| ✅ | checker: agent_matrix | 5ms | 8 matrix configs \| 1 system agents \| 30 user agents \| 0 running |
| ✅ | checker: content_factory | 5ms | 0 channels \| 0 processing \| 0 pending review |
| ⚠️ | checker: media_integrity | 5ms | Found 5 missing files (Dry-run, no fixes applied) |
| ✅ | checker: discovery_tables | 36ms | 153 tables, 36168 total rows |
| ✅ | checker: error_logs | 4ms | 0 error logs in last 24h |
| ⚠️ | checker: external_apis | 2720ms | 1/1 abnormal: httpbin.org(503) |
| ✅ | checker: ssl_cert | - | 0/0 SSL certificates valid |
| ✅ | checker: discovery_modules | 3ms | 22 modules stable |
| ✅ | checker: discovery_endpoints | 1774ms | 654 endpoints across 41 blueprints |
| ✅ | checker: discovery_plugins | - | No plugins discovered |
| ✅ | checker: core_api | 97ms | All 3 subsite APIs OK |
| ✅ | checker: database | 5ms | Database OK (154 tables, 6.4MB) |
| ✅ | checker: redis | 15ms | Redis OK (127.0.0.1:6379, connections:1) |
| ✅ | checker: server_resources | 100ms | CPU 71.4% \| Memory 68.2% \| Disk 42.5% |
| ✅ | checker: sse_ws | - | SSE/WS connections OK |
| ✅ | checker: workflow_engine | 4ms | 7/7 Cron active \| 0 workflows |

## L3

| 状态 | 项目 | 耗时 | 详情 |
|------|------|------|------|
| ✅ | HTTPS 可达: 主站根路由 | - | HTTP 200 |
| ✅ | HTTPS 可达: admin 登录页 | - | HTTP 200 |
| ⚠️ | HTTPS 可达: auth 认证路由 | - | HTTP 404 |
| ✅ | HTTPS 可达: platform 子域 | - | HTTP 200 |
| ✅ | HTTPS 可达: agent 子域 | - | HTTP 200 |
| ✅ | SSO: platform 免登通过 | - | {"count":0,"success":true} |
| ✅ | SSO: 篡改 token 被拒 | - | HTTP 401 |

## L4

| 状态 | 项目 | 耗时 | 详情 |
|------|------|------|------|
| ✅ | 验证码代理 8081/api/captcha/generate | - | {"background":"iVBORw0KGgoAAAANSUhEUgAAAVQAAAC+CAYAAABqOvflA |
| ✅ | 插件 discover（23 个） | - | {"data":{"plugins":[{"author":"VeroRun","config":{"default_height":0,"default_width":320,"max_placem |
| ✅ | 主站首页渲染 | - | HTTP 200 |

## L5

| 状态 | 项目 | 耗时 | 详情 |
|------|------|------|------|
| ✅ | workflow_engine | - | 7/7 Cron active \| 0 workflows |
