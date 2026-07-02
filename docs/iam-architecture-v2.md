# IAM 重构方案 v2 — 用户身份与访问管理

> 基于现有 easykai-auth 体系重构，充分复用 user_agents、agent_api_keys、user_sessions 等已建表

---

## 一、整体架构

### 实体关系

```
        ┌─────────────────────────────────────────────────┐
        │                 Human User (users)              │
        │  id | username* | phone | email | password_hash │
        │  display_name | avatar_url | active | is_admin  │
        └───────────┬────────────────────────┬────────────┘
                    │                        │
          ┌─────────▼────────┐     ┌─────────▼──────────┐
          │  Login Methods   │     │  Security Settings  │
          │  • SMS (手机号)    │     │  • 密码 (pbkdf2)    │
          │  • 密码 (用户名/手机)│     │  • 2FA (可选)      │
          │  • 邮箱 (未来)     │     │  • 会话管理         │
          │  • 微信 (未来)     │     │  • 登录记录         │
          └──────────────────┘     └────────────────────┘
                    │
          ┌─────────▼──────────────────────────┐
          │       User Agents (user_agents)    │
          │  1 Human : N Agents                │
          │  id | agent_name | avatar_url      │
          │  status | default_scopes           │
          └─────────┬──────────────────────────┘
                    │
          ┌─────────▼──────────────────────────┐
          │    Agent API Keys (agent_api_keys) │
          │  id | agent_id | key_hash          │
          │  name | scopes | expire_at         │
          │  status | rotated_from_key_id      │
          └────────────────────────────────────┘
```

### 双账号设计原则

| 属性 | Human User | Agent |
|------|-----------|-------|
| 认证方式 | 手机/密码/未来邮箱+社交 | API Key only |
| 登录态 | JWT token | API Key (Bearer) |
| 可创建角色 | 注册即有人类账号 | Human 主动创建 |
| 操作者 | 人类自己 | AI / 自动化脚本 |
| Scope 控制 | 套餐 (tier) 决定调用限额 | 细粒度 scope 控制 |
| 审计 | 管理员操作日志 (admin_logs) | Agent 操作日志 (agent_logs) |

### 现有复用表 (不动/可扩展)

| 表名 | 现状 | 复用方式 |
|------|------|---------|
| `users` | ✅ 核心用户表 | 加 `username` 字段, `email` 已有但未启用 |
| `user_agents` | ✅ 已建 | 保持, 扩展 scope 列表 |
| `agent_api_keys` | ✅ 已建 | 保持, 加 `expire_at` 已存在 |
| `agent_logs` | ✅ 已建 | 保持 |
| `user_sessions` | ✅ 已建但未启 | 改造为真正会话管理 |
| `login_attempts` | ✅ 已建 | 保持 |
| `sms_codes` | ✅ 已建 | 保持 |
| `admin_profiles` | ✅ 已建 | 保持 |
| `admin_logs` | ✅ 已建 | 保持 |
| `api_keys` | ⚠️ 旧表 | 废弃, 迁移到 agent_api_keys |

---

## 二、数据库表结构变更

### users 表 — 扩展字段

```sql
-- 现有字段保留, 新增以下:
ALTER TABLE users ADD COLUMN username TEXT UNIQUE;       -- 登录名（唯一、不可修改）
ALTER TABLE users ADD COLUMN display_name TEXT DEFAULT ''; -- 显示名（可随时改）
ALTER TABLE users ADD COLUMN email TEXT UNIQUE;            -- 已有但未启用
ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN password_changed_at TEXT;    -- 密码最后修改时间
ALTER TABLE users ADD COLUMN totp_secret TEXT DEFAULT '';  -- 2FA 密钥
ALTER TABLE users ADD COLUMN totp_enabled INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN security_level INTEGER DEFAULT 0; -- 安全等级 0=低 1=中 2=高
```

**现有 nickname 字段** → 映射为 `display_name`（注册时 nickname 填入 display_name）
**现有 phone** → 保持为主要注册/登录方式
**现有 username** → 新逻辑: 登录时可选手机号或用户名

### user_sessions 表 — 激活会话管理

```sql
-- 现有表已建, 激活使用
-- 每次登录创建, 密码修改后清除所有
```

### agent_api_keys — 完善字段（已基本完备）

```sql
-- 现有字段已覆盖: id, agent_id, user_id, key_hash, key_prefix, name, scopes, status,
-- expire_at, last_used_at, rotated_at, rotated_from_key_id, calls_today, calls_total
```

---

## 三、API 端点设计

### 认证 (routes/auth.py)

| 端点 | 方法 | 说明 | 安全提示 |
|------|------|------|---------|
| `/auth/sms/send` | POST | 发送验证码 (purpose: register/login/reset_password) | "验证码5分钟内有效" |
| `/auth/sms/register` | POST | 手机+验证码注册 | "注册即表示同意服务条款" |
| `/auth/sms/login` | POST | 手机验证码登录 | "端到端加密保护账号" |
| `/auth/password/login` | POST | 用户名/手机+密码登录 | "密码管理器建议" |
| `/auth/username/check` | GET | 检查用户名是否可用 | — |
| `/auth/email/send-code` | POST | 发送邮箱验证码 | "5分钟内有效" |
| `/auth/email/bind` | POST | 绑定邮箱 | "用于找回密码" |

### 用户中心 (routes/user.py)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/user/profile` | GET | 当前用户信息 |
| `/user/profile` | PUT | 更新显示名等 |
| `/user/display-name` | PUT | 单独更新显示名 |
| `/user/password/set` | POST | 设置/修改密码 (需短信验证) |
| `/user/email/bind` | POST | 绑定邮箱 (需邮箱验证码) |
| `/user/2fa/totp` | POST | 开启/关闭 2FA |
| `/user/sessions` | GET | 当前登录设备列表 |
| `/user/sessions/<id>` | DELETE | 登出指定设备 |
| `/user/sessions/logout-all` | POST | 登出所有设备 |

### Agent & API Key (routes/agents.py — 现有增强)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/agent/list` | GET | Agent 列表 |
| `/agent/create` | POST | 创建 Agent |
| `/agent/<id>` | GET/PUT/DELETE | 详情/更新/删除 |
| `/agent/<id>/keys` | GET | API Key 列表 |
| `/agent/<id>/keys/create` | POST | 创建 Key |
| `/agent/<id>/keys/<kid>` | PUT/DELETE | 更新名称/撤销 |
| `/agent/<id>/keys/<kid>/rotate` | POST | 轮换 |
| `/agent/<id>/stats` | GET | 统计 |

---

## 四、API Key 管理（详细设计）

### 现状

Agent 体系 (`agent_api_keys`) 已有完善的 Key 生命周期管理：
- ✅ 创建时命名 + 一次性展示完整 Key
- ✅ 列表显示名称/前缀/状态/最后使用/创建时间
- ✅ 撤销 (status='revoked')
- ✅ 轮换 (rotated_from_key_id 溯源)
- ✅ Scope 权限控制 (scopes JSON 字段)
- ✅ 过期时间 (expire_at)

### 需要增强

#### 1. 创建 Key 时的权限范围选择

前端 UI 需要支持：
- 可选预设 scope 集合（community:read, community:write, skills:analysis, stock:read, market:alert 等）
- 自定义 scope 输入
- scope 列表从后端获取（未来可扩展）

```python
SCOPE_CATALOG = {
    'community': {
        'read':  '读取社区内容',
        'write': '发布社区内容',
    },
    'skills': {
        'analysis': '运行分析 Skill',
        'execute':  '执行交易 Skill',
    },
    'stock': {
        'read': '查询股票数据',
    },
    'market': {
        'alert': '获取市场提醒',
    },
    'admin': {
        'agent': '管理 Agent',
    },
}
```

#### 2. 创建 Key 的安全提示

```
┌─────────────────────────────────────┐
│ 🔑 创建新 API Key                   │
│                                      │
│ 名称: [____________________________] │
│                                      │
│ 过期时间: [30天▾]                     │
│                                      │
│ 权限范围:                             │
│ ☑ community:read   ☑ community:write │
│ ☑ skills:analysis  ☐ stock:read      │
│ ☐ market:alert     ☐ admin:agent     │
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ ⚠️ 安全提示                      │ │
│ │ • API Key 有完整访问权限，请妥善保管│ │
│ │ • 泄露将导致严重后果              │ │
│ │ • 建议定期轮换                   │ │
│ │ • 最小权限原则：只勾选需要的权限   │ │
│ └──────────────────────────────────┘ │
│                                      │
│           [取消]  [生成密钥]          │
└─────────────────────────────────────┘
```

#### 3. Key 展示页（创建成功后）

```
┌─────────────────────────────────────┐
│ 🎉 API Key 创建成功！                │
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ sk-easykai-a3f8b2...7c1d        │ │
│ └──────────────────────────────────┘ │
│        [📋 复制]                      │
│                                      │
│ ⚠️ 请立即复制保存！关闭后将无法再次查看 │
│                                      │
│           [我已保存，关闭]            │
└─────────────────────────────────────┘
```

#### 4. Key 管理页面

```
┌─────────────────────────────────────────────────────────┐
│ API 密钥管理                            [+ 创建新密钥]  │
├─────────┬──────────┬──────────┬─────────┬──────────────┤
│ 名称     │ 密钥前缀  │ 权限范围  │ 状态     │ 操作         │
├─────────┼──────────┼──────────┼─────────┼──────────────┤
│ 生产环境 │ sk-...b2 │ comm:rw  │ ✅ 启用  │ ✏️ 🔄 🗑️    │
│ 测试     │ sk-...a1 │ comm:r   │ ✅ 启用  │ ✏️ 🔄 🗑️    │
│ 脚本     │ sk-...c3 │ skill:a  │ ❌ 吊销  │              │
├─────────┼──────────┼──────────┼─────────┼──────────────┤
│ 操作: ✏️ 编辑名称  🔄 轮换(旧Key立即失效)  🗑️ 撤销     │
└─────────────────────────────────────────────────────────┘
```

---

## 五、注册与登录流程安全提示

### 注册流程

```
步骤 1: 输入手机号 → 获取验证码
  [📱 我们使用加密传输保护您的手机号]
  
步骤 2: 输入验证码 → 设置密码
  [🔐 密码要求: 10位以上, 含大写+小写+数字+特殊字符]
  [💡 建议使用密码管理器保存密码]
  
步骤 3: 设置用户名（唯一登录标识）
  [ℹ️ 用户名不可修改, 用于登录]
  
步骤 4: 注册成功
  [🎉 欢迎！我们不会存储您的交易数据和持仓信息]
```

### 登录流程

```
短信登录:
  [📱 验证码5分钟内有效, 请勿泄露给他人]
  
密码登录:
  [🔐 如果使用公共设备, 建议登录后启用2FA]
  [💡 密码管理器 > 记忆密码]
```

---

## 六、安全增强

### 密码策略（强制执行）

```python
PASSWORD_RULES = {
    'min_length': 10,
    'require_upper': True,
    'require_lower': True,
    'require_digit': True,
    'require_special': True,  # 至少3种类型
    'weak_passwords': [
        '1234567890', 'password10', 'Password10', 'qwertyuiop',
        'abc1234567', 'letmein123',
    ],
}
```

### 密码修改后强制下线

```python
# 密码修改时
conn.execute("DELETE FROM user_sessions WHERE user_id=? AND is_current=0", (uid,))
# 当前 token 的 token_hash 标记为已过期
```

### 2FA/MFA（可选，MVP后期）

- TOTP (Google Authenticator / Authy)
- 手机验证码作为备选
- 设置页面: 扫码绑定 + 验证码确认

---

## 七、迁移方案

### 100% 向后兼容

| 现有用户 | 迁移方式 |
|---------|---------|
| 已有 `phone` 且 `nickname` 非空 | 自动建立 username = phone, display_name = nickname |
| 已有 `phone` 但 `nickname` 为空 | 自动建立 username = phone, display_name = phone |
| 已有 `password_hash` | 保持不动 |
| **旧 `api_keys` 表** | 保留不删，提供 API 兼容，新 Key 全部走 `agent_api_keys` |

### 迁移步骤

```
Phase 1 (MVP): 现有功能增强
  → 加 username 字段 + 显示名分离
  → 升级密码策略
  → 完善 Agent → API Key 管理 UI
  → 前端加安全提示文案

Phase 2: 邮箱登录
  → 启用 email 登录
  → 邮箱验证码流程

Phase 3: 社交登录
  → 微信 OAuth 接入（已有 wechat_service.py）
  → 其他社交平台

Phase 4: 安全增强
  → 2FA/MFA
  → 异常登录检测
  → 安全评分
```

---

## 八、MVP 实施优先级

### Priority 1（即刻实现）

```
1. users 表加 username/display_name 字段（迁移脚本）
2. 注册页重构: 用户名+手机+密码+safety提示
3. 登录页重构: 短信/密码 tab + safety提示
4. 密码策略升级（10位+3类+禁止弱密码）
5. Agent API Key 管理 UI 增强（scope选择+过期时间+轮换）
6. 首次登录引导: 设置显示名
```

### Priority 2（MVP期）

```
7. 个人中心: 账户设置（用户名展示/显示名修改/安全设置）
8. Agent 管理页面增强（头像+状态+Key 统一管理）
9. 邮箱绑定
10. 密码修改后下线所有设备
```

### Priority 3（MVP后）

```
11. 2FA/MFA
12. 邮箱登录
13. 微信/社交登录
14. 异常登录告警
15. 数据与隐私说明页
```
