# 抖音小程序 API 文档

基于easykai.cn代码库，以下是可供抖音小程序调用的标准API接口：

## 一、抖音小程序专用API（需Authorization: Bearer <token>）

### 1. 用户信息接口
**GET** `/douyin_mp/user/info`  
获取当前用户的详细信息（包括是否绑定抖音账号）

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "phone": "13800138000",
    "username": "user123",
    "display_name": "张三",
    "is_admin": false,
    "douyin_bound": true,
    "douyin_nickname": "抖音用户",
    "douyin_avatar": "https://example.com/avatar.jpg",
    "agent_id": "agent_001",
    "agent_nickname": "AI助手",
    "agent_avatar_url": "https://example.com/agent.jpg"
  }
}
```

### 2. 抖音绑定状态检查
**GET** `/douyin_mp/user/bind_status`  
检查当前用户是否已绑定抖音账号

**响应示例：**
```json
{
  "success": true,
  "data": {
    "bound": true
  }
}
```

### 3. 解绑抖音账号
**POST** `/douyin_mp/user/unbind_douyin`  
解除当前用户与抖音账号的绑定关系

**响应示例：**
```json
{
  "success": true,
  "data": {
    "message": "抖音账号已成功解绑"
  }
}
```

## 二、聊天机器人API

### 1. 聊天机器人状态检查
**GET** `/api/v1/chat/status`  
检查聊天机器人服务状态和配置信息

**响应示例：**
```json
{
  "ok": true,
  "engine": "agent_matrix",
  "provider": "deepseek",
  "model": "deepseek-chat",
  "agent_id": "agent_001",
  "is_active": 1,
  "faq": true
}
```

### 2. 聊天对话接口
**POST** `/api/v1/chat`  
发送消息并获取AI回复（流式响应）

**请求示例：**
```json
{
  "message": "我想了解产品价格",
  "history": [],
  "unanswered_count": 0
}
```

**响应格式（Server-Sent Events）：**
```
data: {"role":"assistant"}

data: "您好！我是易站智能的智能客服Kai Assistant。"
data: "关于产品价格，我们有多种套餐可选..."
data: [DONE]
```

### 3. 转人工客服
**POST** `/api/v1/chat/escalate`  
将对话转接给人工客服

**请求示例：**
```json
{
  "contact": "13800138000",
  "message": "我想咨询产品定制方案",
  "type": "presale",
  "category": "",
  "priority": "normal"
}
```

**响应示例：**
```json
{
  "success": true,
  "ticket_id": "ES-20260609-0001",
  "message": "已转人工，工作人员尽快联系您"
}
```

## 三、认证相关API（获取Token所需）

### 1. 发送验证码
**POST** `/auth/sms/send`  
发送短信验证码

**请求示例：**
```json
{
  "phone": "13800138000",
  "purpose": "login",
  "captcha_id": "从验证码接口获取"
}
```

### 2. 登录/注册
**POST** `/auth/sms/login`  
使用验证码登录（如用户不存在则自动注册）

**请求示例：**
```json
{
  "phone": "13800138000",
  "code": "123456"
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 123,
      "phone": "13800138000",
      "nickname": "张三"
    }
  }
}
```

## 四、产品展示相关API（通过CMS系统）

### 1. 获取首页内容块
**GET** `/api/social-media`  
获取社交媒体链接（用于页脚展示）

**GET** `/api/interests`  
获取兴趣标签列表

### 2. CMS内容获取（通用接口）
平台应用提供内容管理系统，可通过以下方式获取产品展示内容：
- 主页内容：`GET /` （返回渲染后的HTML）
- 特定页面：`GET /brand`、`GET /services` 等
- 文章列表：`GET /insights`、`GET /insights/<slug>`

> **注意**：产品展示通常通过CMS块系统实现。后台可在`cms_blocks`表中创建产品展示块，前端通过页面渲染获取。如果需要专门的产品API，建议在`platform/routes/cms_public.py`或新建路由中添加。

## 五、使用流程示例

1. **用户登录流程**：
   - 调用 `/auth/sms/send` 发送验证码
   - 用户输入验证码后调用 `/auth/sms/login` 获取token
   - 将token存储至本地（如Storage）

2. **抖音绑定检查**：
   - 调用 `/douyin_mp/user/bind_status` 检查绑定状态
   - 如未绑定，引导用户进行抖音授权（通过`/auth/douyin/qr`和`/auth/douyin/callback`完成）

3. **使用聊天机器人**：
   - 调用 `/api/v1/chat/status` 确认服务可用
   - 通过 `/api/v1/chat` 发送消息获取AI回复
   - 必要时调用 `/api/v1/chat/escalate` 转人工

4. **展示产品信息**：
   - 通过平台首页或专题页获取产品展示内容（CMS系统）
   - 或调用专门的产品展示接口（需后台补充）

## 六、重要说明

1. **认证方式**：除特别说明外，所有需要用户身份验证的API均需在请求头中携带：
   ```
   Authorization: Bearer <your_token_here>
   ```

2. **响应格式**：
   - 成功响应：`{"success": true, "data": {...}}`
   - 错误响应：`{"success": false, "error": "错误信息"}`, 并附带相应HTTP状态码

3. **流式响应**：聊天机器人API使用Server-Sent Events（SSE）格式，前端需适当处理事件流

4. **错误码参考**：
   - 400: 请求参数错误
   - 401: 未授权/token无效
   - 403: 禁止访问
   - 404: 资源不存在
   - 429: 请求过于频繁
   - 500: 服务器内部错误
   - 503: 服务暂不可用（如客服离线）

以上接口均来自当前代码库的实际实现，可直接用于抖音小程序开发。如需其他具体功能的API，请提供更详细的需求描述。