# 抖音小程序接口实现指南

本文档为另一个Agent提供实现抖音小程序前端接口的详细指南，基于易站智能的后端API。

## 后端API概述

易站智能已提供以下抖音相关API端点（均需要JWT认证）：

### 已有认证端点
1. `GET /auth/douyin/qr` - 获取抖音登录授权URL
2. `GET /auth/douyin/callback` - 抖音OAuth回调处理（自动完成）

### 新增小程序专用端点
1. `GET /douyin_mp/user/info` - 获取当前用户信息
2. `POST /douyin_mp/user/unbind_douyin` - 解绑抖音账号
3. `GET /douyin_mp/user/bind_status` - 检查抖音绑定状态

所有端点基础URL：`https://您的域名`（需替换为实际部署域名）

## 认证流程

抖音小程序应使用以下认证流程：

1. **获取登录授权**
   - 调用 `/auth/douyin/qr` 获取抖音授权URL
   - 或者直接构建授权URL（参考后端实现）
   - 使用抖音小程序的 `wx.login()` 和 `wx.request()` 配合后端完成OAuth流程

2. **存储和使用Token**
   - 登录成功后，后端会通过回调重定向返回JWT token
   - 小程序应将token存储在 `wx.getStorageSync()` 或类似持久化存储中
   - 每次API请求在Header中携带：`Authorization: Bearer <token>`

## API实现示例

以下是使用微信小程序框架的API调用示例：

### 1. 检查抖音绑定状态
```javascript
/**
 * 检查用户是否已绑定抖音账号
 * @returns {Promise<Object>} 返回 { bound: boolean }
 */
function checkDouyinBindStatus() {
  const token = wx.getStorageSync('jwt_token') || '';
  if (!token) {
    return Promise.reject(new Error('未登录'));
  }
  
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getBaseUrl()}/douyin_mp/user/bind_status`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.success) {
          resolve(res.data);
        } else {
          reject(new Error(res.data.error || '检查绑定状态失败'));
        }
      },
      fail: (err) => {
        reject(new Error(`网络请求失败: ${err.errMsg}`));
      }
    });
  });
}
```

### 2. 获取用户信息
```javascript
/**
 * 获取当前用户的详细信息
 * @returns {Promise<Object>} 用户信息对象
 */
function getUserInfo() {
  const token = wx.getStorageSync('jwt_token') || '';
  if (!token) {
    return Promise.reject(new Error('未登录'));
  }
  
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getBaseUrl()}/douyin_mp/user/info`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.success) {
          resolve(res.data.data);
        } else {
          reject(new Error(res.data.error || '获取用户信息失败'));
        }
      },
      fail: (err) => {
        reject(new Error(`网络请求失败: ${err.errMsg}`));
      }
    });
  });
}
```

### 3. 解绑抖音账号
```javascript
/**
 * 解绑当前用户的抖音账号
 * @returns {Promise<Object>} 返回操作结果
 */
function unbindDouyin() {
  const token = wx.getStorageSync('jwt_token') || '';
  if (!token) {
    return Promise.reject(new Error('未登录'));
  }
  
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getBaseUrl()}/douyin_mp/user/unbind_douyin`,
      method: 'POST',
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.success) {
          // 清除可能存储的抖音相关信息
          wx.removeStorageSync('douyin_info');
          resolve(res.data);
        } else {
          reject(new Error(res.data.error || '解绑抖音账号失败'));
        }
      },
      fail: (err) => {
        reject(new Error(`网络请求失败: ${err.errMsg}`));
      }
    });
  });
}
```

### 辅助函数
```javascript
/**
 * 获取API基础URL
 * 在实际使用中应替换为您的域名
 * @returns {string} API基础URL
 */
function getBaseUrl() {
  // 生产环境应替换为实际域名
  // 例如：return 'https://api.yourdomain.com';
  // 开发/测试环境可使用相对路径或配置
  return getApp().globalData.apiBaseUrl || '';
}

/**
 * 初始化全局数据（在App.onLaunch中调用）
 */
function initGlobalData() {
  getApp().globalData = {
    apiBaseUrl: 'https://您的实际域名', // 请替换为实际部署域名
    // 其他全局数据...
  };
}
```

## 数据结构说明

### 用户信息响应（`/douyin_mp/user/info`）
成功响应格式：
```json
{
  "success": true,
  "data": {
    "id": 123,
    "phone": "13800138000",
    "username": "用户名",
    "display_name": "显示名称",
    "is_admin": false,
    "douyin_bound": true,
    "douyin_nickname": "抖音昵称",
    "douyin_avatar": "https://example.com/avatar.jpg",
    "agent_id": "agent_123",
    "agent_nickname": "Agent名称",
    "agent_avatar_url": "https://example.com/agent_avatar.jpg"
  }
}
```

### 绑定状态响应（`/douyin_mp/user/bind_status`）
成功响应格式 Bolivar:
```json
{
  "success": true,
  "data": {
    "bound": true
  }
}
```

### 解绑响应（`/douyin_mp/user/unbind_douyin`）
成功响应格式:
```json
{
  "success": true,
  "data": {
    "message": "抖音账号已成功解绑"
  }
}
```

## 错误处理

所有API端点在失败时返回统一格式：
```json
{
  "success": false,
  "error": "错误描述信息"
}
```

常见错误码：
- 401: 未提供有效的Token / 无效或过期的Token
- 400: 当前用户未绑定抖音账号（仅在解绑时可能）
- 404: 用户不存在
- 500: 服务器内部错误

## 安全建议

1. **Token管理**
   - 不要在URL或日志中暴露token
   - 定期检查token过期状态，实现刷新机制
   - 考虑使用微信小程序的加密存储（如有需求）

2. **请求安全**
   - 所有请求必须使用HTTPS
   - 实现请求超时处理（建议10-15秒）
   - 考虑实现请求重试机制（网络波动时）

3. **数据验证**
   - 对后端返回的数据进行基本验证和类型检查
   - 对于关键操作（如解绑），考虑添加二次确认

## 与现有系统集成

如果小程序需要与易站智能的其他功能集成：

1. **用户中心**
   - 可通过 `/douyin_mp/user/info` 获取用户基本信息
   - 结合 Agent 信息展示用户的AI助理

2. **认证状态同步**
   - 建议在小程序启动时检查登录状态
   - 如果token过期，引导用户重新通过抖音登录

3. **Agent相关功能**
   - 用户信息中包含 `agent_id`、`agent_nickname` 等字段
   - 可用于展示用户绑定的AI助理信息

## 测试建议

1. **单元测试**
   - 模拟各种响应状态（成功、不同错误码、网络失败）
   - 测试token存储和检索逻辑

2. **集成测试**
   - 使用真实的测试域名完成端到端流程
   - 测试从抖音登录到获取用户信息的完整链路
   - 测试解绑功能及状态同步

3. **边界情况**
   - 未登录状态下调用受保护端点
   - token过期后的处理
   - 网络中断和恢复的情况

## 文件结构建议

对于微信小程序项目，建议的文件组织：
```
/miniprogram/
  /utils/
    api.js          // 包含上面的所有API函数
    auth.js         // 认证相关工具函数
    config.js       // 配置文件（域名等）
  /pages/
    /bind-douyin/   // 绑定/解绑抖音页面
    /profile/       // 用户资料页面（展示从API获取的信息）
  /app.js           // 小程序入口，初始化全局数据
  /app.json         // 小程序配置
```

## 注意事项

1. **域名替换**：所有代码中的 `https://您的实际域名` 必须替换为您实际部署易站智能的域名
2. **端口**：如果系统不是运行在标准80/443端口，需要在URL中包含端口号
3. **环境区分**：建议开发、测试、生产环境使用不同的配置
4. **版本控制**：建议将API版本号写入URL中（如 `/api/v1/douyin_mp/user/info`），但当前实现未包含版本号
5. **更新维护**：后端API可能会更新，保持此文档与实际实现同步

此指南为另一个Agent提供了完整的抖音小程序前端接口实现蓝照。Agent可以根据此文档直接编写小程序代码，实现与易站智能的抖音功能对接。