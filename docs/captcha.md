# 验证码服务（Captcha Service）

> **易站智能建站系统** 独立验证码服务，基于 FastAPI 构建，提供行为式形状匹配拼图验证码。

---

## 1. 架构总览

Captcha Service 是一个**独立部署**的 FastAPI 应用，运行在 **`127.0.0.1:8090`**，不依赖主站 Flask 进程。

```
                          ┌──────────────────────────┐
                          │   Nginx (:443)           │
                          │  /api/captcha/* → :8090  │
                          └──────┬───────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
   Platform (:8083)         Admin (:8084)        Captcha (:8090)
   (proxy /api/captcha/*)   (proxy /api/captcha/*)  FastAPI 独立进程
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                                 ▼
                          Redis (存储 + 限流)
```

请求链路有三种方式：

1. **Nginx 直连** — `location /api/captcha/ { proxy_pass http://127.0.0.1:8090; }`
2. **Platform/Admin 代理** — Flask 端用 `_proxy_captcha()` 转发给 8090（带路径白名单安全过滤）
3. **Auth-Center 内联** — `/auth/captcha/gen` 和 `/auth/captcha/verify` 由 `auth-center/services/captcha_service.py` 进程内处理（**旧版**，纯 Python stdlib 实现）

---

## 2. 验证码类型

### 2.1 形状匹配拼图（Shape-Matching Puzzle）— 新版

当前 Captcha Service v2.0.0 的主要验证方式。

- **形状**：随机从五种形状中选取 — `circle` / `triangle` / `square` / `diamond` / `ellipse`
- **背景**：每请求随机选取实景图（`captcha-service/images/` 目录下 26 张 Unsplash 图片），若无可用图片则降级为合成渐变背景
- **挑战**：背景图上挖出一个形状孔洞，前端需将匹配形状拖拽到正确位置
- **干扰**：额外生成 1~3 个干扰形状（decoy pieces）
- **形状可旋转**：随机 `0°/90°/180°/270°` 增加安全性

### 2.2 水平滑块（Horizontal Slider）— 旧版

`auth-center/services/captcha_service.py` 内联实现的水平滑动拼图：

- **Track**：280px 宽，随机偏移量（10~214px）
- **验证**：位置匹配（±4px 容差）+ 行为轨迹分析（拖拽时间、速度曲线、加速度、停顿检测）
- **无外部依赖**：纯 Python stdlib，无 Redis / Pillow 需求

---

## 3. 核心组件

| 组件 | 文件 | 说明 |
|------|------|------|
| 入口 | `captcha-service/server.py` | FastAPI 应用，挂载路由 + CORS + 静态文件端点 |
| 配置 | `captcha-service/config.py` | 端口、Redis URL、容差、安全密钥、风险阈值 |
| 拼图生成 | `captcha-service/captcha/generator.py` | Pillow + NumPy 生成形状孔洞拼图 |
| 行为分析 | `captcha-service/captcha/behavior.py` | 拖拽轨迹分析：速度、加速度、人类行为评分 |
| 安全签名 | `captcha-service/captcha/security.py` | HMAC-SHA256 Token 签发与验证（防止篡改/重放） |
| 存储 | `captcha-service/captcha/store.py` | Redis 存储层：challenge 缓存、IP 限流、失败计数、统计 |
| 数据模型 | `captcha-service/models/schemas.py` | Pydantic 模型：ChallengeResponse / VerifyRequest / TracePoint |
| 管理路由 | `captcha-service/routes/admin.py` | 统计面板（需 Bearer token 鉴权） |

---

## 4. API 端点

### 公开端点（`/api/captcha`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/captcha/generate` | 生成新挑战，返回 `token` + `background`(base64) + `hole` + `pieces` |
| `POST` | `/api/captcha/verify` | 验证阶段一：校验位置 + 行为分析，返回 `success` + `risk_score` |
| `POST` | `/api/captcha/consume` | 验证阶段二：消费 token，登录/注册表单提交时调用 |

### 静态文件端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/puzzle-captcha.js` | 前端交互 JS（Vue3 widget） |
| `GET` | `/puzzle-captcha.css` | 前端样式 |
| `GET` | `/captcha-widget.js` | 备选 widget script |
| `GET` | `/captcha-widget.css` | 备选 widget styles |

### 管理端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/admin/captcha/stats` | 统计面板（需 `Authorization: Bearer <secret>`） |
| `GET` | `/health` | 健康检查 |

### 请求示例（Verify）

```json
POST /api/captcha/verify
{
  "token": "hmac_signed_token",
  "drag_distance": 0,
  "drag_trace": [
    {"t": 100, "x": 10, "y": 80},
    {"t": 200, "x": 45, "y": 82},
    {"t": 350, "x": 90, "y": 85}
  ]
}
```

---

## 5. 两阶段验证流程（Two-Phase Verification）

验证码采用 **verify → consume** 两阶段设计，防止重放攻击：

```
┌──────────┐     ┌──────────────┐     ┌───────────┐
│  前端     │     │ Captcha API  │     │ 业务后端   │
├──────────┤     ├──────────────┤     ├───────────┤
│ 1. generate ├──▶│ return token │     │           │
│ 2. 用户拖拽  │     │              │     │           │
│ 3. verify  ├──▶│ 行为分析+位置  │     │           │
│            │◀──│ success/失败   │     │           │
│ 4. 提交表单  │     │              │     │           │
│            ├─────────────────────────▶│ consume   │
│            │     │              │     │           │
│            │◀─────────────────────────│ 登录成功   │
└──────────┘     └──────────────┘     └───────────┘
```

- **Phase 1**（`/verify`）：校验位置匹配 + 行为轨迹分析，不消耗 token
- **Phase 2**（`/consume`）：业务表单提交时，后端用 token 换取一次性消费确认
- Token 由 HMAC-SHA256 签名，内含图像 ID 和孔洞位置，防篡改

---

## 6. 集成方式

### 6.1 前端接入

前端加载 `puzzle-captcha.js` 组件：

```html
<link rel="stylesheet" href="/puzzle-captcha.css">
<script src="/puzzle-captcha.js"></script>
```

组件调用流程：
1. 调用 `GET /api/captcha/generate` 获取背景图 + 拼图碎片
2. 用户拖拽形状至匹配位置
3. 调用 `POST /api/captcha/verify` 验证
4. 验证通过后，将 token 随登录/注册表单提交

### 6.2 后端集成（Platform / Admin）

Platform（`:8083`）和 Admin（`:8084`）通过 `_proxy_captcha()` 函数将请求安全转发至 8090：

```python
@bp.route('/api/captcha/verify', methods=['POST'])
def captcha_proxy_verify():
    return _proxy_captcha('/api/captcha/verify', request.get_data())
```

代理函数包含**路径白名单**（仅允许 `/generate`、`/verify`、`/consume`）和响应头安全过滤。

### 6.3 Auth-Center 内联（旧版）

`/auth/captcha/gen` 和 `/auth/captcha/verify` 不走 8090，而是由 `auth-center/services/captcha_service.py` 在 Flask 进程内处理：

- 纯内存存储（`dict` + 线程锁），无需 Redis
- 随机偏移量水平滑块
- 行为轨迹评分 + 位置校验

---

## 7. 配置项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CAPTCHA_HOST` | `0.0.0.0` | 监听地址 |
| `CAPTCHA_PORT` | `8090` | 监听端口 |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis 连接 |
| `CAPTCHA_TTL` | `120` | Challenge 过期秒数 |
| `RATE_LIMIT_TTL` | `300` | IP 限流窗口（秒） |
| `MAX_FAILS` | `5` | 窗口内最大失败次数 |
| `TOLERANCE` | `4` | 位置容差 ±px |
| `CAPTCHA_SECRET_KEY` | `change-me-in-production` | HMAC 签名密钥 |
| `RISK_THRESHOLD` | `0.7` | 风险阈值（≥ 通过） |

---

## 8. 相关文件

- `captcha-service/server.py` — FastAPI 入口
- `captcha-service/config.py` — 配置中心
- `captcha-service/captcha/generator.py` — 拼图生成器
- `captcha-service/captcha/behavior.py` — 拖拽行为分析引擎
- `captcha-service/captcha/security.py` — HMAC-SHA256 Token 安全层
- `captcha-service/captcha/store.py` — Redis 存储适配层
- `captcha-service/routes/captcha.py` — API 路由（generate / verify / consume）
- `captcha-service/routes/admin.py` — 管理统计路由
- `auth-center/services/captcha_service.py` — 旧版内联验证码服务
