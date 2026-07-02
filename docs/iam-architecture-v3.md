# IAM 重构方案 v3 — 用户身份与访问管理（终版）

> 对标 OpenAI / Anthropic / Perplexity / Cursor 2026 年用户体验标准
> 基于 easykai-auth 现有体系重构，充分复用已有表和代码

---

## 一、整体架构（Mermaid 图）

```mermaid
graph TB
    subgraph "Human User"
        U[users<br/>id | username | phone | email | display_name<br/>password_hash | totp_secret | security_level]
    end

    subgraph "认证方式"
        A1[短信验证码登录<br/>手机号 + 6位动态码]
        A2[密码登录<br/>用户名/手机号 + 密码]
        A3[邮箱登录<br/>未来扩展]
        A4[社交登录<br/>微信/Google 未来扩展]
    end

    subgraph "Agent 身份"
        UA[user_agents<br/>id | agent_name | avatar_url<br/>status | default_scopes<br/>1 Human : N Agents]
        AK[agent_api_keys<br/>id | key_hash | key_prefix | name<br/>scopes | expire_at | status<br/>last_used_ip | rotated_from]
    end

    subgraph "安全体系"
        S1[user_sessions<br/>登录设备管理]
        S2[login_attempts<br/>速率限制+暴力防护]
        S3[agent_logs<br/>Agent操作审计]
        S4[2FA / TOTP<br/>可选增强保护]
    end

    U --> A1 & A2 & A3 & A4
    U --> UA
    UA --> AK
    U --> S1 & S2
    UA --> S3
    U --> S4
```

---

## 二、数据库表结构（完整 DDL）

### users — 核心用户表

```sql
CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    -- ── 登录凭证 ──
    username        TEXT UNIQUE,              -- 登录名（唯一、注册后不可修改）
    phone           TEXT UNIQUE,              -- 手机号（主要注册方式）
    phone_verified  INTEGER DEFAULT 0,
    email           TEXT UNIQUE,              -- 邮箱（可选，用于找回密码/通知）
    email_verified  INTEGER DEFAULT 0,
    password_hash   TEXT,                     -- pbkdf2:sha256:100000:{salt}:{hash}
    -- ── 身份信息 ──
    display_name    TEXT DEFAULT '',          -- 显示名（可随时修改，用于界面展示）
    nickname        TEXT,                     -- 旧字段保留兼容，映射为 display_name
    avatar_url      TEXT DEFAULT '',
    wechat_openid   TEXT UNIQUE,
    wechat_unionid  TEXT,
    wechat_nickname TEXT,
    -- ── 安全设置 ──
    totp_secret     TEXT DEFAULT '',          -- TOTP 密钥（2FA）
    totp_enabled    INTEGER DEFAULT 0,       -- 是否启用 2FA
    password_changed_at TEXT,                -- 密码最后修改时间
    security_level  INTEGER DEFAULT 0,       -- 安全等级 0=基本 1=增强 2=最高
    -- ── 状态 ──
    is_admin        INTEGER DEFAULT 0,
    active          INTEGER DEFAULT 1,
    last_login      TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

### 新增迁移

```sql
-- 2026-05-11: v2 IAM 重构
ALTER TABLE users ADD COLUMN username TEXT UNIQUE;
ALTER TABLE users ADD COLUMN display_name TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN password_changed_at TEXT;
ALTER TABLE users ADD COLUMN totp_secret TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN totp_enabled INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN security_level INTEGER DEFAULT 0;

-- 回填现有用户: username = phone, display_name = nickname or phone
UPDATE users SET username = phone WHERE username IS NULL;
UPDATE users SET display_name = COALESCE(nickname, phone) WHERE display_name = '';
```

### user_agents — 用户 Agent

```sql
CREATE TABLE user_agents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    agent_name      TEXT NOT NULL DEFAULT '',
    agent_type      TEXT DEFAULT 'personal',   -- personal / community / trading
    avatar_url      TEXT DEFAULT '',
    status          TEXT DEFAULT 'active',      -- active / inactive / suspended
    default_scopes  TEXT DEFAULT '[]',          -- JSON: 继承默认权限
    metadata        TEXT DEFAULT '{}',          -- JSON
    last_active_ip  TEXT DEFAULT '',
    last_active_at  TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
```

### agent_api_keys — Agent 级 API Key（核心表）

```sql
CREATE TABLE agent_api_keys (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id            INTEGER NOT NULL REFERENCES user_agents(id),
    user_id             INTEGER NOT NULL REFERENCES users(id),
    -- ── 密钥数据 ──
    key_hash            TEXT UNIQUE NOT NULL,    -- SHA-256 哈希（仅存哈希）
    key_prefix          TEXT NOT NULL,           -- 前缀展示 'sk-...b2c1'
    name                TEXT DEFAULT '',         -- 用户自定义名称
    -- ── 权限与生命周期 ──
    scopes              TEXT DEFAULT '[]',       -- JSON: 权限范围列表
    status              TEXT DEFAULT 'active',   -- active / revoked / expired
    expire_at           TEXT,                    -- 过期时间（NULL=永不过期）
    -- ── 审计追踪 ──
    last_used_at        TEXT,                    -- 最后使用时间
    last_used_ip        TEXT DEFAULT '',         -- 最后使用 IP
    rotated_at          TEXT,                    -- 轮换时间
    rotated_from_key_id INTEGER DEFAULT 0,       -- 溯源：从哪个旧 Key 轮换来的
    -- ── 用量统计 ──
    calls_today         INTEGER DEFAULT 0,
    calls_total         INTEGER DEFAULT 0,
    last_reset          TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_agent_api_keys_agent ON agent_api_keys(agent_id);
CREATE INDEX idx_agent_api_keys_user ON agent_api_keys(user_id);
```

### user_sessions — 登录设备管理

```sql
CREATE TABLE user_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    token_hash  TEXT NOT NULL,
    device_name TEXT DEFAULT '',          -- "Chrome on Windows" / "Safari on iPhone"
    device_type TEXT DEFAULT '',          -- mobile / desktop / api
    ip_address  TEXT DEFAULT '',
    user_agent  TEXT DEFAULT '',
    location    TEXT DEFAULT '',          -- 地理位置（来自 IP）
    is_current  INTEGER DEFAULT 0,
    last_active TEXT,                     -- 最后活跃时间
    created_at  TEXT DEFAULT (datetime('now')),
    expired_at  TEXT
);

CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
```

---

## 三、密码策略（强制，对标主流平台）

```python
PASSWORD_POLICY = {
    'min_length': 10,
    'max_length': 128,
    'require': {
        'upper': True,      # 必须包含大写字母 A-Z
        'lower': True,      # 必须包含小写字母 a-z
        'digit': True,      # 必须包含数字 0-9
        'special': True,    # 必须包含特殊字符 !@#$%^&*()_+-=[]{}|;:,.<>?
    },
    # 上述四项中至少满足 3 项
    'min_categories': 3,    # 至少3种字符类别
    'blocked_patterns': [   # 禁止的模式
        '1234567890', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
        'password', 'Password1', 'Passw0rd', 'admin123',
        'letmein', 'welcome', 'abcdefghij', '0000000000',
    ],
    'reuse_prevention': 5,  # 不能与最近5次密码相同（需历史表）
}
```

**提示文案（注册页）**:

```
🔐 密码要求：
• 长度至少 10 位
• 必须包含大写字母、小写字母、数字、特殊字符中的至少 3 种
• 不能包含常见弱密码（如 password、1234567890）
• 建议使用密码管理器生成并保存
```

**提示文案（修改密码）**:

```
🔐 密码修改后，所有已登录设备将自动下线，需要重新登录。
```

---

## 四、注册流程（分步向导，对标 Cursor 风格）

### Step 1: 手机验证

```
┌──────────────────────────────────────────┐
│ 📝 创建你的账号                 第1步/共3步  │
│                                            │
│ 手机号     [  138 0013 8000  ] [发送验证码] │
│ 验证码     [  _  _  _  _  _  _  ]         │
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ 📱 已发送 6 位验证码，5 分钟内有效     │  │
│ │ 🔒 我们采用加密传输保护你的手机号      │  │
│ └──────────────────────────────────────┘  │
│                                            │
│               [下一步 → ]                  │
└──────────────────────────────────────────┘
```

### Step 2: 设置密码

```
┌──────────────────────────────────────────┐
│ 📝 创建你的账号                 第2步/共3步  │
│                                            │
│ 设置密码   [____________________________]  │
│ 确认密码   [____________________________]  │
│                                            │
│ [🔑 生成强密码]                             │
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ 🔐 密码要求：                          │  │
│ │ • 长度至少 10 位                      │  │
│ │ • 必须包含大写、小写、数字、特殊字符    │  │
│ │   中的至少 3 种                       │  │
│ │ • 不能使用弱密码                      │  │
│ │ 💡 建议使用密码管理器保存密码          │  │
│ └──────────────────────────────────────┘  │
│                                            │
│               [下一步 → ]                  │
└──────────────────────────────────────────┘
```

### Step 3: 设置用户名

```
┌──────────────────────────────────────────┐
│ 📝 创建你的账号                 第3步/共3步  │
│                                            │
│ 用户名  [  g u x i a o   ]                │
│         ✅ 用户名可用                       │
│                                            │
│ 显示名  [  Guxiao          ]               │
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ ℹ️ 用户名用于登录，注册后不可修改      │  │
│ │ 💡 显示名随时可改，用于页面展示        │  │
│ └──────────────────────────────────────┘  │
│                                            │
│             [🎉 完成注册]                   │
└──────────────────────────────────────────┘
```

### Step 4: 注册成功 + 引导

```
┌──────────────────────────────────────────┐
│ 🎉 注册成功！                              │
│                                            │
│ ✅ 账号安全已启用                          │
│ ✅ 端到端加密保护                          │
│                                            │
│   [创建你的第一个 Agent →]                 │
│   [进入控制台         ]                    │
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ 🛡️ 安全提醒                          │  │
│ │ • 我们不会存储你的交易数据和持仓信息   │  │
│ │ • 建议立即设置 Agent 和 API Key      │  │
│ │ • 建议启用 2FA 增强安全              │  │
│ └──────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

---

## 五、登录流程

### 短信登录

```
┌──────────────────────────────────────────┐
│ 登录 EasyKai                    选择登录方式 │
│  [短信验证码]  [密码登录]  [邮箱登录(未来)]  │
│                                            │
│ 手机号     [  138 0013 8000  ] [发送验证码] │
│ 验证码     [  _  _  _  _  _  _  ]         │
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ 📱 验证码 5 分钟内有效                 │  │
│ │ 🔒 采用端到端加密保护您的账号安全      │  │
│ └──────────────────────────────────────┘  │
│                                            │
│               [登录]                        │
│                                            │
│ ──── 其他方式 ────                         │
│ [微信登录(未来)]  [忘记密码?]               │
└──────────────────────────────────────────┘
```

### 密码登录

```
┌──────────────────────────────────────────┐
│ 登录 EasyKai                    选择登录方式 │
│  [短信验证码]  [密码登录]  [邮箱登录(未来)]  │
│                                            │
│ 用户名/手机  [  g u x i a o     ]          │
│ 密码         [  • • • • • • •  ]  [👁]    │
│                                            │
│ [忘记密码?]                                 │
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ 🔐 安全提示                           │  │
│ │ • 如果使用公共设备，登录后请退出       │  │
│ │ • 密码建议使用密码管理器保存          │  │
│ │ • 建议启用 2FA 增强账号安全           │  │
│ └──────────────────────────────────────┘  │
│                                            │
│               [登录]                        │
└──────────────────────────────────────────┘
```

---

## 六、API Key 管理（完整功能）

### 创建 Key — 权限范围选择器

```
┌──────────────────────────────────────────────────────┐
│ 🔑 创建新 API Key                                     │
│                                                        │
│ 名称     [  生产环境 Key                       ]        │
│ 过期时间  [ 30 天 ▾ ]                                 │
│                                                        │
│ ── 权限范围 ──                                         │
│                                                        │
│ ┌ Community ──────────────────────────────────────┐   │
│ │ ☐ community:read   读取社区内容                   │   │
│ │ ☐ community:write  发布社区内容                   │   │
│ └──────────────────────────────────────────────────┘   │
│ ┌ Skills ─────────────────────────────────────────┐   │
│ │ ☑ skills:analysis 运行分析 Skill（推荐）         │   │
│ │ ☐ skills:execute  执行交易 Skill                 │   │
│ └──────────────────────────────────────────────────┘   │
│ ┌ Market ─────────────────────────────────────────┐   │
│ │ ☐ stock:read     查询股票数据                    │   │
│ │ ☐ market:alert   获取市场提醒                    │   │
│ └──────────────────────────────────────────────────┘   │
│ ┌ Admin ──────────────────────────────────────────┐   │
│ │ ☐ admin:agent    管理 Agent                      │   │
│ └──────────────────────────────────────────────────┘   │
│                                                        │
│ ┌──────────────────────────────────────────────────┐   │
│ │ ⚠️ 安全提示                                        │   │
│ │ • API Key 提供对账户资源的直接访问权限             │   │
│ │ • 泄露 API Key 可能导致严重后果                    │   │
│ │ • 请遵守最小权限原则：仅勾选需要的权限              │   │
│ │ • 建议定期轮换 Key（每 90 天）                     │   │
│ │ • 不要在代码中硬编码 API Key                       │   │
│ └──────────────────────────────────────────────────┘   │
│                                                        │
│                    [取消]    [生成密钥]                 │
└──────────────────────────────────────────────────────┘
```

### Key 展示 — 一次性展示页面

```
┌──────────────────────────────────────────────────────┐
│ 🎉 API Key 创建成功！                                  │
│                                                        │
│ 名称: 生产环境 Key                                     │
│ 权限: skills:analysis                                  │
│ 过期: 30 天后 (2026-06-10)                             │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │                                                    │ │
│ │  sk-easykai-a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e  │ │
│ │                                                    │ │
│ └────────────────────────────────────────────────────┘ │
│                  [📋 复制密钥]                         │
│                                                        │
│ ┌──────────────────────────────────────────────────┐   │
│ │ ⚠️ 安全警告                                       │   │
│ │ • 这是你唯一一次看到完整密钥！                       │   │
│ │ • 关闭此弹窗后，将无法再次查看                      │   │
│ │ • 请立即复制并安全保存（密码管理器推荐）              │   │
│ │ • 如怀疑泄露，请立即撤销并重新创建                   │   │
│ └──────────────────────────────────────────────────┘   │
│                                                        │
│                   [我已保存，关闭]                       │
└──────────────────────────────────────────────────────┘
```

### Key 管理列表 — 完整信息展示

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ API 密钥管理                                                       [+ 创建]  │
├──────┬──────────────┬────────────┬───────────┬──────────┬──────────────────┤
│ 名称 │ 密钥前缀      │ 权限范围    │ 最后使用   │ 最后IP   │ 状态/过期        │
├──────┼──────────────┼────────────┼───────────┼──────────┼──────────────────┤
│ 生产  │ sk-easy...b2 │ skill:a    │ 2分钟前    │ 47.92.x  │ ✅ 启用 · 30天后  │
│       │              │            │           │          │ ✏️ 🔄 🗑️        │
├──────┼──────────────┼────────────┼───────────┼──────────┼──────────────────┤
│ 测试  │ sk-easy...a1 │ comm:rw    │ 3天前      │ 127.0.0  │ ✅ 启用 · 永不过期 │
│       │              │            │           │          │ ✏️ 🔄 🗑️        │
├──────┼──────────────┼────────────┼───────────┼──────────┼──────────────────┤
│ 脚本  │ sk-easy...c3 │ skill:a    │ 从未使用   │ -        │ ❌ 已吊销         │
│       │              │            │           │          │                  │
└──────┴──────────────┴────────────┴───────────┴──────────┴──────────────────┘

操作说明:
✏️ 编辑名称 — 修改密钥显示名称
🔄 轮换 Key — 生成新密钥，旧密钥立即失效（支持10分钟过渡期）
🗑️ 撤销 Key — 立即停用，不可恢复
```

### 轮换确认弹窗

```
┌──────────────────────────────────────────────┐
│ 🔄 轮换 API Key                              │
│                                              │
│ 名称: 生产环境 Key                            │
│                                              │
│ 轮换后：                                     │
│ • 当前密钥将在 10 分钟后自动失效               │
│ • 新密钥立即生效                             │
│ • 旧密钥仍可在过渡期内用于现有连接             │
│                                              │
│ ⚠️ 请确认：                                   │
│ 输入密钥名称确认: [__________________]         │
│                                              │
│           [取消]    [确认轮换]                 │
└──────────────────────────────────────────────┘
```

### Scope 权限定义表

| Scope | 名称 | 说明 | 风险等级 |
|-------|------|------|---------|
| `community:read` | 读取社区 | 查看社区帖子、评论 | 低 |
| `community:write` | 发布社区 | 发布帖子、评论 | 中 |
| `skills:analysis` | 分析 Skill | 运行市场分析、数据查询 (推荐) | 中 |
| `skills:execute` | 交易 Skill | 执行交易操作 | **高** |
| `stock:read` | 股票查询 | 查询股票行情、历史数据 | 低 |
| `market:alert` | 市场提醒 | 接收市场异动通知 | 低 |
| `admin:agent` | 管理 Agent | 创建/删除/修改 Agent | **高** |

**高风险 Scope 创建时额外提示**:
```
⚠️ 你选择了高风险权限 (skills:execute / admin:agent)
拥有此 Key 的任何人可以执行交易操作或管理你的 Agent。
强烈建议：
• 设置较短的过期时间（≤30天）
• 谨慎分享此 Key
• 定期轮换
```

---

## 七、安全与用户体验增强

### 密码修改 → 强制下线所有设备

```python
@user_bp.route('/password/set', methods=['POST'])
def set_password():
    # ... 验证验证码 + 新密码规则 ...
    
    # 更新密码
    conn.execute('UPDATE users SET password_hash=?, password_changed_at=? WHERE id=?',
                 (new_hash, now, uid))
    
    # 强制下线所有设备（当前设备除外）
    conn.execute("DELETE FROM user_sessions WHERE user_id=? AND token_hash!=?",
                 (uid, current_token_hash))
    
    # 记录安全事件
    conn.execute("INSERT INTO user_security_events (user_id, event_type, ip_address) VALUES (?,?,?)",
                 (uid, 'password_changed', ip))
    
    return jsonify({'success': True, 'message': '密码已修改，其他设备已下线'})
```

### 活跃设备管理

```
┌──────────────────────────────────────────────────────┐
│ 🔐 登录设备管理                                        │
│                                                        │
│ 当前设备  ✅ Chrome on Windows · 北京                  │
│           最后活跃: 刚刚                               │
│                                                        │
│ 其他设备:                                              │
│ ┌──────────────────────────────────────────────────┐  │
│ │ Safari on iPhone · 上海                          │  │
│ │ 最后活跃: 2 小时前                                 │  │
│ │ [下线此设备]                                       │  │
│ └──────────────────────────────────────────────────┘  │
│ ┌──────────────────────────────────────────────────┐  │
│ │ Python Requests · API                            │  │
│ │ 最后活跃: 3 天前                                  │  │
│ │ [下线此设备]                                       │  │
│ └──────────────────────────────────────────────────┘  │
│                                                        │
│ [退出所有其他设备]                                      │
└────────────────────────────────────────────────────────┘
```

### 安全事件通知

| 事件 | 通知方式 | 通知文案 |
|------|---------|---------|
| 新设备登录 | 短信 | "你的账号在 {location} 通过 {device} 登录。如非本人操作，请立即修改密码。" |
| 密码修改 | 短信 | "你的登录密码已修改。如非本人操作，请立即联系客服。" |
| API Key 创建 | 无（但 Key 列表有详细审计） | — |
| 异常登录（新IP/新设备） | 短信（可选） | "检测到来自 {location} 的新登录，已启用安全验证。" |

---

## 八、MVP 实施计划

### Phase 1 (Day 1-2) — 基础设施

```
1. DB 迁移：users 表加字段 + 回填
2. 密码验证器升级（10位 + 3类 + 弱密码库）
3. 密码修改 → 强制下线逻辑
4. 用户名检查 API
```

### Phase 2 (Day 3-5) — 注册 + 登录

```
5. 注册页重构（分步向导 + 安全提示）
6. 登录页重构（短信/密码 tab + 安全提示）
7. 首次登录引导（设置显示名）
```

### Phase 3 (Day 5-7) — API Key 管理

```
8. Agent → API Key 管理页面重构
   - Scope 选择器
   - 过期时间选择
   - 最后使用时间/IP 显示
   - 轮换确认弹窗
   - 安全提示文案
```

### Phase 4 (Day 7-9) — 安全中心

```
9. 设备管理页面
10. 安全事件日志
11. 数据与隐私说明页
```

### Phase 5 (未来)

```
12. 邮箱绑定/登录
13. 2FA / TOTP
14. 微信社交登录
15. 异常登录检测
```
