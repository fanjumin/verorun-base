# 管理员后台实施方案

## 当前架构

```
auth-center (共享)                community (独立)
┌─────────────────────┐           ┌──────────────────────┐
│ easykai.db          │           │ community.db          │
│ └─ users            │   查询    │ └─ users (映射表)     │
│ └─ app_authorizations│ ◄─────── │ └─ payment_orders     │
│ └─ api_keys         │           │ └─ recurring_subs     │
│ └─ sms_codes        │           │ └─ contact_convs      │
└─────────────────────┘           │ └─ contact_replies    │
                                  │ └─ skill_keys         │
                                  │ └─ activity_logs      │
                                  │ └─ 社区表...          │
                                  └──────────────────────┘
```

管理员后台直接挂在 **community (8082)** 上，它已经能读 easykai.db。

---

## 一、新增数据库表

在 community.db 中添加管理员专用表：

### 1.1 admin_notes — 管理员备注
```sql
CREATE TABLE IF NOT EXISTS admin_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    admin_id INTEGER NOT NULL,
    created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
);
```

### 1.2 user_tags — 用户标签
```sql
CREATE TABLE IF NOT EXISTS user_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    admin_id INTEGER NOT NULL,
    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
    UNIQUE(user_id, tag)
);
```

---

## 二、管理员认证

复用现有 `_user_auth()` + `is_admin` 字段。

```python
def _require_admin():
    user = _user_auth()
    if not user:
        return api_error("未登录", 401)
    admins = _query_auth_db(
        "SELECT id, is_admin FROM users WHERE id=? AND is_admin=1",
        (user.get("auth_user_id"),))
    if not admins:
        return api_error("无管理员权限", 403)
    return user
```

---

## 三、API 路由设计

全部挂 `/api/v1/admin/` 前缀。

### 3.1 Dashboard 总览
```
GET /api/v1/admin/dashboard
```
今日注册、今日Key、活跃调用、总用户、总订阅、开放工单、3天到期、今日收入、本月收入

### 3.2 用户列表
```
GET /api/v1/admin/users?page=1&per=20&search=&tier=&status=
```
LEFT JOIN 两个数据库，返回用户 + 套餐 + Key数 + 调用量 + 标签

### 3.3 用户详情
```
GET /api/v1/admin/users/<auth_user_id>
```
完整用户画像：基本信息 + TradeMind + 社区 + 订阅 + 订单 + 工单 + API Key + 操作日志 + 标签 + 备注

### 3.4 标签管理
```
POST /api/v1/admin/users/<id>/tags     {tag: 'high_value'}
DELETE /api/v1/admin/users/<id>/tags?tag=high_value
```

### 3.5 备注管理
```
POST /api/v1/admin/users/<id>/notes    {content: '...'}
GET  /api/v1/admin/users/<id>/notes
```

### 3.6 工单管理
```
GET  /api/v1/admin/tickets?status=open
GET  /api/v1/admin/tickets/<conv_id>
POST /api/v1/admin/tickets/<conv_id>/reply  {content}
POST /api/v1/admin/tickets/<conv_id>/close
```

### 3.7 到期预警
```
GET /api/v1/admin/expiring?days=7
GET /api/v1/admin/risk-alerts
```

### 3.8 收入统计
```
GET /api/v1/admin/revenue?range=month|quarter|year
```

---

## 四、前端页面

全部服务端渲染（Jinja2），放在 `community/templates/admin/` 下。

| 页面 | 路由 | 说明 |
|------|------|------|
| Admin 首页 | /admin | Dashboard |
| 用户列表 | /admin/users | 搜索/筛选/分页 |
| 用户详情 | /admin/users/<id> | 详细信息 |
| 工单管理 | /admin/tickets | 工单列表 |
| 工单详情 | /admin/tickets/<id> | 对话界面 |
| 到期预警 | /admin/expiring | 即将过期列表 |

管理员入口：导航栏检测到 `is_admin` 时显示「管理后台」链接。

---

## 五、实施步骤

### Phase 1 — 核心数据（新增 admin.py 文件）
1. 添加 admin_notes + user_tags 表到 models.py
2. 创建 community/admin.py — 管理员认证 + 所有 API
3. Dashboard + 用户列表 + 用户详情 API
4. 创建 templates/admin/*.html 页面

### Phase 2 — 运营功能
5. 工单管理 API + 页面
6. 用户标签 + 备注
7. 到期/风险预警

### Phase 3 — 数据洞察
8. 收入统计
9. 运营 Dashboard 卡片

---

## 六、部署

- 本地 8082 预览 → 确认后部署服务器
- 服务器：`sudo systemctl restart community`
- 不改 systemd / nginx，新 API 已走 8082 端口

---

## 七、不做的事
- ❌ 不重建用户系统
- ❌ 不做传统 CRM 字段
- ❌ 不引入新数据库
- ❌ 不做联盟/返佣
