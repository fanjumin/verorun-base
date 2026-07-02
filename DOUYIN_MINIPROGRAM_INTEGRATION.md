# 易站智能 - 抖音小程序对接说明

## 概述
本文档说明如何将抖音小程序与易站智能对接，包括数据库结构、API端点以及使用方法。

## 数据库结构
系统使用SQLite数据库，位于 `/data/easykai.db`，与抖音相关的关键字段在 `users` 表中：

- `douyin_open_id` TEXT UNIQUE - 抖音 open ID（唯一标识）
- `douyin_nickname` TEXT - 抖音昵称
- `douyin_avatar` TEXT - 抖音头像URL
- `phone` TEXT UNIQUE - 手机号（登录使用）
- `is_admin` INTEGER DEFAULT 0 - 是否为管理员
- `id` INTEGER PRIMARY KEY - 用户ID

## API端点

### 已有端点（抖音登录认证）
这些端点已存在于 `auth-center/routes/auth.py` 中：

1. **GET `/auth/douyin/qr`**
   - 显示抖音QR登录页面或重定向到抖音OAuth授权页
   - 使用 `douyin_service.get_oauth_url()` 生成授权URL

2. **GET `/auth/douyin/callback`**
   - 处理抖音OAuth回调
   - 用授权码换取access token
   - 获取用户资料并创建/更新用户记录
   - 生成JWT token并重定向到 `/douyin-success?token={token}`

### 新增端点（抖音小程序专用）
新增的Blueprint位于 `/home/***REMOVED***/projects/easykai.cn/auth-center/routes/douyin_miniprogram.py`，已注册到 admin 应用中：

1. **GET `/douyin_mp/user/info`**
   - 获取当前用户的详细信息
   - 需要JWT认证：`Authorization: Bearer <token>`
   - 返回用户基本信息、抖音绑定状态、Agent信息等

2. **POST `/douyin_mp/user/unbind_douyin`**
   - 解绑当前用户的抖音账号
   - 需要JWT认证：`Authorization: Bearer <token>`
   - 将抖音相关字段设置为NULL

3. **GET `/douyin_mp/user/bind_status`**
   - 检查当前用户是否已绑定抖音账号
   - 需要JWT认证：`Authorization: Bearer <token>`
   - 返回 `{ "bound": true/false }`

## 使用流程

### 1. 用户登录获取Token
小程序应引导用户通过抖音登录流程：
- 跳转到抖音授权页（可通过现有 `/auth/douyin/qr` 获取URL）
- 用户授权后，抖音会回调到 `/auth/douyin/callback`
- 从回调URL中提交的token参数获取JWT token
- 将token存储在小程序中（如localStorage）用于后续请求

### 2. 调用小程序专用API
获取到token后，小程序可以调用新增的API端点：

```javascript
// 示例：获取用户信息
wx.request({
  url: 'https://您的域名/douyin_mp/user/info',
  header: {
    'Authorization': 'Bearer ' + token
  },
  success: function(res) {
    if (res.data.success) {
      console.log('用户信息:', res.data.data);
    }
  }
});
```

### 3. 解绑抖音账号
当用户需要解绑抖音账号时：
```javascript
wx.request({
  url: 'https://您的域名/douyin_mp/user/unbind_douyin',
  method: 'POST',
  header: {
    'Authorization': 'Bearer ' + token
  },
  success: function(res) {
    if (res.data.success) {
      // 解绑成功，清除本地存储的抖音相关信息
    }
  }
});
```

## 安全考虑

1. **Token安全**：
   - JWT token应安全存储，避免在日志或URL中泄露
   - 建议使用HTTPS传输
   - 实现token过期刷新机制

2. **权限控制**：
   - 新增端点仅验证用户身份，不检查管理员权限
   - 如需发布内容等敏感操作，应考虑额外的权限验证
   - 当前发布功能仍需要管理员权限（通过 `/social/publish` 端点）

3. **速率限制**：
   - 建议在小程序端实现基本的请求频率限制
   - 后端已有基础的速率限制机制（如短信发送）

## 部署说明

1. **环境配置**：
   - 确保环境变量 `DOUYIN_CALLBACK` 正确设置为您的域名下的 `/auth/douyin/callback` 路径
   - 在抖音开放平台后台配置的回调域名必须与实际域名一致

2. **域名验证**：
   - 完成抖音开放平台的域名校验流程
   - 确保服务器可公开访问，且端口正确映射（通常是80或443端口）

3. **测试建议**：
   - 首先使用现有的抖音登录流程测试Token获取
   - 然后测试新增的 `/douyin_mp/user/info` 端点
   - 最后测试解绑功能

## 文件修改摘要

### 新增文件：
- `/home/***REMOVED***/projects/easykai.cn/auth-center/routes/douyin_miniprogram.py`

### 修改文件：
- `/home/***REMOVED***/projects/easykai.cn/admin/app.py`
  - 添加导入: `from routes.douyin_miniprogram import douyin_mp_bp`
  - 添加注册: `app.register_blueprint(douyin_mp_bp)`

## 注意事项

1. 当前实现侧重于用户信息查询和账号解绑
2. 如需小程序直接发布内容到抖音，需要：
   - 评估安全风险（防止滥用）
   - 可能需要额外的权限验证或审批流程
   - 考虑异步处理以避免请求超时
3. 建议监控API使用情况，防止恶意刷取

## 联系和支持
如有疑问，请参考系统其他认证端点的实现方式，或联系系统管理员。

文档生成时间: 2026-06-05T11:50:44+08:00