# VeroRon 维洛智能 — SDK 使用参考文档

> 版本: v1.0  
> 最后更新: 2026-07-07  
> 适用平台: Python 3.10+, JavaScript (浏览器/Node.js)

---

## 目录

1. [概述](#1-概述)
2. [Python SDK](#2-python-sdk)
3. [JavaScript SDK](#3-javascript-sdk)
4. [API Key 管理](#4-api-key-管理)
5. [认证与 JWT](#5-认证与-jwt)
6. [错误处理](#6-错误处理)
7. [最佳实践](#7-最佳实践)

---

## 1. 概述

### 1.1 什么是 SDK

SDK（Software Development Kit）是为开发者提供的代码库封装，用于简化与 VeroRon 维洛智能 平台 API 的交互。当前系统**不提供独立安装的 SDK 包**，但提供了可直接集成到项目中的 Python 和 JavaScript 客户端示例代码。

### 1.2 架构概览

```
你的应用
  │
  ├── Python SDK ─── REST API ─── 易站 AI 平台
  │       │                          │
  │       ├── AuthClient             ├── 认证中心
  │       ├── UserClient            ├── 用户服务
  │       ├── KnowledgeClient       ├── 知识库
  │       ├── AgentClient           ├── AI 矩阵
  │       ├── ChatClient            ├── 对话
  │       ├── ShopClient            ├── 商城
  │       ├── AgentMatrixClient     ├── Agent Matrix 管理
  │       ├── CouponClient          ├── 优惠券
  │       └── SubscriptionClient    └── 订阅
  │
  └── JavaScript SDK ─── REST API ─── 同上
          │
          ├── VeroRunClient（浏览器）
          ├── fetch/axios 封装
          ├── SSE 流式聊天支持
          └── 滑块验证码组件
```

### 1.3 依赖

**Python**: `requests` (HTTP 客户端)

**JavaScript**: `fetch` (浏览器原生) 或 `axios`

---

## 2. Python SDK

### 2.1 基础客户端

所有客户端继承自同一个 `BaseClient`，提供统一的认证和请求处理。

```python
import requests
import json

class VeroRunClient:
    """易站 AI Python SDK 基础客户端"""

    def __init__(self, base_url="https://platform.easykai.cn", api_key=None, token=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def set_token(self, token):
        """设置 JWT Token"""
        self.token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def set_api_key(self, api_key):
        """设置 API Key"""
        self.api_key = api_key
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, **kwargs)
        return resp.json()
```

**使用示例**:
```python
client = VeroRunClient()

# 或者使用 API Key
client = VeroRunClient(api_key="tm-abc123...")
```

### 2.2 认证客户端

处理登录、注册、Token 管理。

```python
class AuthClient:
    """认证 API 封装"""

    def __init__(self, client: VeroRunClient):
        self.client = client

    def login_by_password(self, phone, password, captcha_id=None):
        """密码登录"""
        data = {"phone": phone, "password": password}
        if captcha_id:
            data["captcha_id"] = captcha_id
        result = self.client._request("POST", "/user/password/login", json=data)
        if result.get("success"):
            self.client.set_token(result["data"]["token"])
        return result

    def login_by_sms(self, phone, code):
        """短信验证码登录"""
        result = self.client._request("POST", "/auth/sms/login",
                                       json={"phone": phone, "code": code})
        if result.get("success"):
            self.client.set_token(result["data"]["token"])
        return result

    def register(self, phone, code, password, username, display_name=""):
        """短信验证码注册"""
        result = self.client._request("POST", "/auth/sms/register", json={
            "phone": phone, "code": code, "password": password,
            "username": username, "display_name": display_name
        })
        if result.get("success"):
            self.client.set_token(result["data"]["token"])
        return result

    def refresh_token(self, old_token):
        """刷新 Token"""
        return self.client._request("POST", "/auth/refresh",
                                     json={"token": old_token})

    def logout(self):
        """退出登录"""
        return self.client._request("POST", "/auth/logout")
```

**使用示例**:
```python
client = VeroRunClient()
auth = AuthClient(client)

# 密码登录
result = auth.login_by_password("13800138000", "mypassword")
if result["success"]:
    print(f"登录成功，用户ID: {result['data']['user']['id']}")

# 注册
result = auth.register("13800138000", "123456", "mypass", "myuser", "My Name")
```

### 2.3 用户客户端

```python
class UserClient:
    """用户 API 封装"""

    def __init__(self, client: VeroRunClient):
        self.client = client

    def get_profile(self):
        """获取当前用户资料"""
        return self.client._request("GET", "/user/profile")

    def update_profile(self, nickname=None, display_name=None):
        """更新用户资料"""
        data = {}
        if nickname: data["nickname"] = nickname
        if display_name: data["display_name"] = display_name
        return self.client._request("PUT", "/user/profile", json=data)

    def list_api_keys(self):
        """列出 API Key"""
        return self.client._request("GET", "/user/keys")

    def create_api_key(self, name=""):
        """创建新的 API Key"""
        return self.client._request("POST", "/user/keys/generate",
                                     json={"name": name})

    def revoke_api_key(self, key_id):
        """撤销 API Key"""
        return self.client._request("DELETE", f"/user/keys/{key_id}")

    def get_notifications(self, page=1, page_size=20):
        """获取通知列表"""
        return self.client._request(
            "GET", f"/user/notifications?page={page}&pageSize={page_size}")

    def create_ticket(self, title, content, ticket_type="aftersale"):
        """创建工单"""
        return self.client._request("POST", "/user/tickets", json={
            "title": title, "content": content, "type": ticket_type
        })

    def get_addresses(self):
        """获取收货地址"""
        return self.client._request("GET", "/user/addresses")

    def create_address(self, address_data):
        """创建收货地址"""
        return self.client._request("POST", "/user/addresses", json=address_data)

    def get_tiers(self):
        """获取套餐列表"""
        return self.client._request("GET", "/user/tiers")

    def get_usage_history(self):
        """获取使用历史"""
        return self.client._request("GET", "/user/usage-history")
```

**使用示例**:
```python
user = UserClient(client)
profile = user.get_profile()
print(f"用户: {profile['data']['display_name']}")
print(f"套餐: {profile['data']['tier_name']}")
print(f"剩余调用: {profile['data']['calls_remaining']}")

# 创建 API Key
key_result = user.create_api_key("我的应用Key")
print(f"新 Key: {key_result['data']['key']}")  # ⚠️ 只显示一次
```

### 2.4 AI 聊天客户端

```python
class ChatClient:
    """AI 对话 API 封装"""

    def __init__(self, client: VeroRunClient):
        self.client = client

    def chat_public(self, messages, source="api"):
        """公开 AI 对话（无需登录，带限流）"""
        return self.client._request("POST", "/api/v1/chat/public", json={
            "messages": messages, "source": source
        })

    def chat_authenticated(self, messages, temperature=0.7, skip_rag=False):
        """非流式 AI 对话（需登录）"""
        return self.client._request("POST", "/api/v1/chat/request", json={
            "messages": messages, "temperature": temperature, "skip_rag": skip_rag
        })

    def chat_stream(self, messages):
        """流式 AI 对话（返回 SSE 生成器）"""
        import json as _json
        resp = self.client.session.post(
            f"{self.client.base_url}/api/v1/chat",
            json={"messages": messages},
            stream=True
        )
        for line in resp.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    yield _json.loads(line[6:])
```

**使用示例**:
```python
chat = ChatClient(client)

# 非流式对话
result = chat.chat_authenticated([
    {"role": "user", "content": "什么是易站AI？"}
])
print(f"AI回复: {result['data']['content']}")

# 流式对话
for event in chat.chat_stream([
    {"role": "user", "content": "给我推荐一些建站方案"}
]):
    if event["type"] == "token":
        print(event["content"], end="", flush=True)
    elif event["type"] == "done":
        print(f"\n\n完整回复: {event['reply']}")
```

### 2.5 知识库客户端

```python
class KnowledgeClient:
    """知识库/RAG API 封装"""

    def __init__(self, client: VeroRunClient):
        self.client = client

    def search(self, query, top_k=5, category=None):
        """RAG 检索"""
        data = {"query": query, "topK": top_k}
        if category: data["category"] = category
        return self.client._request("POST", "/api/v1/rag/search", json=data)

    def list_knowledge(self, keyword=None, category=None, page=1, page_size=10):
        """知识库列表"""
        return self.client._request("POST", "/api/v1/knowledge/list", json={
            "keyword": keyword, "category": category,
            "page": page, "pageSize": page_size
        })

    def save_knowledge(self, kb_id, title, content, keywords=None, category=None):
        """新增/更新知识块"""
        return self.client._request("POST", "/api/v1/knowledge/save", json={
            "id": kb_id, "title": title, "content": content,
            "keywords": keywords or [], "category": category
        })

    def delete_knowledge(self, kb_id):
        """删除知识块"""
        return self.client._request("POST", "/api/v1/knowledge/delete",
                                     json={"id": kb_id})
```

**使用示例**:
```python
kb = KnowledgeClient(client)

# RAG 检索
results = kb.search("如何进行网站SEO优化", top_k=3)
for item in results["data"]:
    print(f"[{item['score']}] {item['block']['title']}")
    print(f"  {item['block']['content'][:100]}...")
```

### 2.6 Agent 客户端

```python
class AgentClient:
    """用户 Agent API 封装"""

    def __init__(self, client: VeroRunClient):
        self.client = client

    def list_agents(self):
        """Agent 列表"""
        return self.client._request("GET", "/agent/list")

    def create_agent(self, name, agent_type="personal"):
        """创建 Agent"""
        return self.client._request("POST", "/agent/create", json={
            "agent_name": name, "agent_type": agent_type
        })

    def get_agent(self, agent_id):
        """Agent 详情"""
        return self.client._request("GET", f"/agent/{agent_id}")

    def delete_agent(self, agent_id):
        """删除 Agent"""
        return self.client._request("DELETE", f"/agent/{agent_id}")

    def create_agent_key(self, agent_id, name="", expire_days=365):
        """为 Agent 生成 API Key"""
        return self.client._request("POST", f"/agent/{agent_id}/keys/create",
                                     json={"name": name, "expire_days": expire_days})

    def revoke_agent_key(self, agent_id, key_id):
        """撤销 Agent 的 Key"""
        return self.client._request("DELETE", f"/agent/{agent_id}/keys/{key_id}")

    def get_agent_stats(self, agent_id):
        """Agent 使用统计"""
        return self.client._request("GET", f"/agent/{agent_id}/stats")
```

**使用示例**:
```python
agent = AgentClient(client)

# 创建 Agent
result = agent.create_agent("我的数据分析助手")
print(f"Agent ID: {result['data']['id']}")

# 生成 Agent API Key（以 ek- 开头）
key_result = agent.create_agent_key(result['data']['id'], "数据分析Key")
print(f"Agent Key: {key_result['data']['key']}")
```

### 2.7 商城客户端

```python
class ShopClient:
    """商城 API 封装"""

    def __init__(self, client: VeroRunClient):
        self.client = client

    def list_products(self, page=1, page_size=20):
        """商品列表（前端）"""
        return self.client._request("GET",
            f"/shop/api/products?page={page}&pageSize={page_size}")

    def get_product(self, product_id):
        """商品详情"""
        return self.client._request("GET", f"/shop/api/products/{product_id}")

    def add_to_cart(self, sku_id, quantity=1):
        """加入购物车"""
        return self.client._request("POST", "/shop/api/cart/add",
                                     json={"sku_id": sku_id, "quantity": quantity})

    def checkout(self, address_id, remark=""):
        """结算下单"""
        return self.client._request("POST", "/shop/api/checkout",
                                     json={"address_id": address_id, "remark": remark})

    def list_orders(self, page=1, page_size=10):
        """订单列表"""
        return self.client._request("GET",
            f"/shop/api/orders?page={page}&pageSize={page_size}")
```

### 2.8 Agent Matrix 管理客户端

```python
class AgentMatrixClient:
    """Agent Matrix 管理 API 封装（需管理员 JWT）"""

    def __init__(self, client: VeroRunClient):
        self.client = client

    def list_agents(self, role=None, domain=None, active_only=True):
        """Agent 列表"""
        params = []
        if role: params.append(f"role={role}")
        if domain: params.append(f"domain={domain}")
        if active_only: params.append("active_only=1")
        qs = "&" + "&".join(params) if params else ""
        return self.client._request("GET", f"/admin/agent-matrix/agents?{qs}")

    def create_agent(self, data):
        """创建 Agent"""
        return self.client._request("POST", "/admin/agent-matrix/agents", json=data)

    def get_agent(self, agent_id):
        """Agent 详情"""
        return self.client._request("GET", f"/admin/agent-matrix/agents/{agent_id}")

    def update_agent(self, agent_id, data):
        """更新 Agent"""
        return self.client._request("PUT", f"/admin/agent-matrix/agents/{agent_id}", json=data)

    def delete_agent(self, agent_id):
        """删除 Agent"""
        return self.client._request("DELETE", f"/admin/agent-matrix/agents/{agent_id}")

    def toggle_agent(self, agent_id):
        """启用/禁用 Agent"""
        return self.client._request("POST", f"/admin/agent-matrix/agents/{agent_id}/toggle")

    def test_agent(self, agent_id, message):
        """测试 Agent"""
        return self.client._request("POST", f"/admin/agent-matrix/agents/{agent_id}/test",
                                     json={"message": message})

    def chat(self, messages, session_id=None):
        """向 Master Agent 发送指令"""
        data = {"messages": messages}
        if session_id: data["session_id"] = session_id
        return self.client._request("POST", "/admin/agent-matrix/chat", json=data)

    def chat_stream(self, messages, session_id=None):
        """SSE 流式聊天"""
        import json as _json
        data = {"messages": messages}
        if session_id: data["session_id"] = session_id
        resp = self.client.session.post(
            f"{self.client.base_url}/admin/agent-matrix/chat/stream",
            json=data, stream=True
        )
        for line in resp.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    yield _json.loads(line[6:])

    def dispatch_task(self, agent_id, task_type, params):
        """直接下发任务给 Sub Agent"""
        return self.client._request("POST", "/admin/agent-matrix/dispatch", json={
            "agent_id": agent_id, "task_type": task_type, "params": params
        })

    def list_tasks(self, status=None, agent_id=None):
        """任务列表"""
        params = []
        if status: params.append(f"status={status}")
        if agent_id: params.append(f"agent_id={agent_id}")
        qs = "&" + "&".join(params) if params else ""
        return self.client._request("GET", f"/admin/agent-matrix/tasks?{qs}")

    def get_token_stats(self, period="7d", dimension="agent", agent_id=None):
        """Token 消耗统计"""
        p = f"period={period}&dimension={dimension}"
        if agent_id: p += f"&agent_id={agent_id}"
        return self.client._request("GET", f"/admin/agent-matrix/token-stats?{p}")

    def generate_image(self, prompt, model=None):
        """AI 生成图片"""
        data = {"prompt": prompt}
        if model: data["model"] = model
        return self.client._request("POST", "/admin/agent-matrix/generate-image", json=data)
```

### 2.9 优惠券客户端

```python
class CouponClient:
    """优惠券插件 API 封装"""

    def __init__(self, client: VeroRunClient):
        self.client = client

    def list_coupons(self, page=1, page_size=20):
        """优惠券列表（用户端）"""
        return self.client._request("GET",
            f"/plugin/coupons/coupons?page={page}&pageSize={page_size}")

    def validate_coupon(self, code, cart_amount):
        """验证优惠券"""
        return self.client._request("POST", "/plugin/coupons/validate",
                                     json={"code": code, "cart_amount": cart_amount})

    def get_recommendations(self, cart_items=None):
        """AI 推荐最优优惠券"""
        data = {}
        if cart_items: data["cart_items"] = cart_items
        return self.client._request("POST", "/plugin/coupons/recommend", json=data)
```

### 2.10 订阅客户端

```python
class SubscriptionClient:
    """订阅与部署 API 封装"""

    def __init__(self, client: VeroRunClient):
        self.client = client

    def list_plans(self):
        """获取套餐列表"""
        return self.client._request("GET", "/subscription/plans")

    def my_subscription(self):
        """我的订阅"""
        return self.client._request("GET", "/subscription/my")

    def create_subscription(self, plan_id, payment_channel="alipay"):
        """创建订阅订单"""
        return self.client._request("POST", "/subscription/create",
                                     json={"plan_id": plan_id,
                                           "payment_channel": payment_channel})

    # ── 部署码验证（独立部署场景）──

    def heartbeat(self, deploy_code, hostname="", version=""):
        """部署实例心跳验证"""
        return self.client._request("POST", "/api/subscription/heartbeat", json={
            "code": deploy_code, "hostname": hostname, "version": version
        })

    def check_subscription(self, deploy_code):
        """公共查询订阅状态"""
        return self.client._request("GET",
            f"/api/subscription/check?code={deploy_code}")
```

**部署心跳使用示例**:
```python
# 在客户部署环境中
sub = SubscriptionClient(client)
result = sub.heartbeat("DC-20260701-XXXXXX", hostname="server1")
if result["success"] and result["data"]["valid"]:
    print(f"订阅有效，剩余 {result['data']['days_remaining']} 天")
else:
    print("订阅已过期！")
```

---

## 3. JavaScript SDK

### 3.1 基础客户端

```javascript
/**
 * 易站 AI JavaScript SDK
 * 浏览器环境使用
 */
class VeroRunClient {
  constructor(baseURL = 'https://platform.easykai.cn') {
    this.baseURL = baseURL.replace(/\/+$/, '');
    this.token = null;
  }

  setToken(token) {
    this.token = token;
  }

  async request(method, path, body = null, options = {}) {
    const url = `${this.baseURL}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers,
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const config = { method, headers };
    if (body) {
      config.body = JSON.stringify(body);
    }

    const response = await fetch(url, config);
    return response.json();
  }

  // 快捷方法
  get(path) { return this.request('GET', path); }
  post(path, body) { return this.request('POST', path, body); }
  put(path, body) { return this.request('PUT', path, body); }
  del(path) { return this.request('DELETE', path); }
}
```

**使用**:
```javascript
const client = new VeroRunClient('https://platform.easykai.cn');

// 登录
const loginResult = await client.post('/user/password/login', {
  phone: '13800138000',
  password: 'mypassword'
});
if (loginResult.success) {
  client.setToken(loginResult.data.token);
}

// 获取用户信息
const profile = await client.get('/user/profile');
console.log(profile.data.display_name);
```

### 3.2 用户 API 封装

```javascript
class UserAPI {
  constructor(client) {
    this.client = client;
  }

  getProfile() { return this.client.get('/user/profile'); }

  updateProfile(data) { return this.client.put('/user/profile', data); }

  listKeys() { return this.client.get('/user/keys'); }

  generateKey(name) { return this.client.post('/user/keys/generate', { name }); }

  revokeKey(keyId) { return this.client.del(`/user/keys/${keyId}`); }

  getNotifications(page = 1) {
    return this.client.get(`/user/notifications?page=${page}&pageSize=20`);
  }

  createTicket(title, content, type = 'aftersale') {
    return this.client.post('/user/tickets', { title, content, type });
  }
}

// 使用示例
const userAPI = new UserAPI(client);
const profile = await userAPI.getProfile();
```

### 3.3 AI 聊天（含 SSE 流式）

```javascript
class ChatAPI {
  constructor(client) {
    this.client = client;
  }

  /**
   * 非流式对话
   */
  async chat(messages, options = {}) {
    return this.client.post('/api/v1/chat/request', {
      messages,
      temperature: options.temperature ?? 0.7,
      skip_rag: options.skipRag ?? false,
    });
  }

  /**
   * 流式对话（SSE）
   * @param {Array} messages - 消息数组
   * @param {Function} onToken - 收到 token 回调 (content) => void
   * @param {Function} onDone - 完成回调 (reply, knowledge) => void
   * @param {Function} onError - 错误回调 (error) => void
   */
  async chatStream(messages, { onToken, onDone, onError } = {}) {
    const url = `${this.client.baseURL}/api/v1/chat`;
    const headers = { 'Content-Type': 'application/json' };
    if (this.client.token) {
      headers['Authorization'] = `Bearer ${this.client.token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ messages }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            switch (event.type) {
              case 'token':
                onToken?.(event.content);
                break;
              case 'done':
                onDone?.(event.reply, event.retrievedKnowledge);
                break;
              case 'error':
                onError?.(event.content);
                break;
            }
          } catch (e) {
            console.warn('SSE parse error:', e);
          }
        }
      }
    }
  }

  /**
   * RAG 检索
   */
  ragSearch(query, topK = 5, category = null) {
    const body = { query, topK };
    if (category) body.category = category;
    return this.client.post('/api/v1/rag/search', body);
  }
}

// 使用示例
const chatAPI = new ChatAPI(client);

// 非流式
const result = await chatAPI.chat([
  { role: 'user', content: '易站AI有哪些功能？' }
]);
console.log(result.data.content);

// 流式
await chatAPI.chatStream(
  [{ role: 'user', content: '帮我写一段 Python 代码' }],
  {
    onToken: (content) => process.stdout.write(content),
    onDone: (reply) => console.log('\n--- 完成 ---'),
    onError: (error) => console.error('错误:', error),
  }
);
```

### 3.4 滑块验证码组件

```javascript
class CaptchaService {
  constructor(captchaServiceURL = 'http://127.0.0.1:8090') {
    this.url = captchaServiceURL;
  }

  /**
   * 生成滑块验证码
   */
  async generate() {
    const resp = await fetch(`${this.url}/api/captcha/generate`);
    return resp.json();
  }

  /**
   * 验证滑块
   */
  async verify(token, dragDistance, dragTrace) {
    const resp = await fetch(`${this.url}/api/captcha/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, drag_distance: dragDistance, drag_trace: dragTrace }),
    });
    return resp.json();
  }

  /**
   * 消费验证码（一次性）
   */
  async consume(token) {
    const resp = await fetch(`${this.url}/api/captcha/consume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });
    return resp.json();
  }
}
```

### 3.5 前端错误拦截器

```javascript
class VeroRunClientWithInterceptor extends VeroRunClient {
  constructor(baseURL) {
    super(baseURL);
    this.onError = null;
  }

  async request(method, path, body = null, options = {}) {
    const result = await super.request(method, path, body, options);

    if (!result.success) {
      // Token 过期自动跳转登录
      if (result.error?.includes('Token') || result.error?.includes('未登录')) {
        window.location.href = '/login';
        return result;
      }

      // 限流提示
      if (result.status === 429) {
        console.warn('请求过于频繁，请稍后再试');
      }

      // 自定义错误回调
      this.onError?.(result);
    }

    return result;
  }
}
```

---

## 4. API Key 管理

### 4.1 Key 类型

| 类型 | 前缀 | 用途 | 创建位置 |
|------|------|------|----------|
| 平台 API Key | `tm-` | 调用平台 API | `POST /user/keys/generate` |
| Agent API Key | `ek-` | 调用 Agent 能力 | `POST /agent/<aid>/keys/create` |
| JWT Token | - | 用户认证 | 登录/注册时返回 |

### 4.2 API Key 使用

```python
# 通过 API Key 认证
client = VeroRunClient(api_key="tm-abc123...")

# 通过 JWT 认证
client = VeroRunClient(token="jwt-token...")

# Agent Key 认证（用于 Agent 级别的 API 调用）
agent_client = VeroRunClient(api_key="ek-abc123...")
```

### 4.3 Key 安全建议

- ⚠️ **完整 Key 只在创建时返回一次**，创建后立即复制保存
- 定期轮换（rotate）Key，降低泄露风险
- 不同服务使用不同 Key，方便隔离和审计
- Agent Key 支持设置 scopes（权限范围）和过期时间

---

## 5. 认证与 JWT

### 5.1 JWT 规格

| 项目 | 值 |
|------|-----|
| 算法 | HS256 |
| Access Token 有效期 | 7 天 |
| Refresh Token 有效期 | 30 天 |
| 密钥来源 | 环境变量 `JWT_SECRET` |

### 5.2 SSO 单点登录

平台使用 JWT SSO + 跨子域 Cookie 实现单点登录：

```
Cookie: sso_token=<jwt>; Domain=.easykai.cn; Path=/; HttpOnly; Secure
```

所有子域名（platform.easykai.cn、admin.easykai.cn）共享此 Cookie，实现全局登录态。

### 5.3 Token 刷新策略

```python
# 检测 Token 即将过期时，调用刷新接口
def refresh_if_needed(client, auth_client):
    # 这里可以用简单的过期时间判断
    # 实际场景中可解析 JWT payload 中的 exp 字段
    try:
        result = auth_client.refresh_token(client.token)
        if result.get("success"):
            client.set_token(result["data"]["token"])
            return True
    except Exception:
        pass
    return False
```

### 5.4 密码登录（含验证码防刷）

```python
def secure_login(client, phone, password):
    """
    密码登录（自动处理验证码防刷）
    """
    result = client.post("/user/password/login", {
        "phone": phone,
        "password": password
    })

    if not result.success and "验证码" in (result.error or ""):
        # 需要滑块验证码
        captcha = await generate_captcha()  # 调用 GET /auth/captcha/gen
        # 用户拖动滑块...
        user_x = await show_captcha_and_wait(captcha)
        # 验证滑块
        verify_result = await client.post("/auth/captcha/verify", {
            "captcha_id": captcha.captcha_id,
            "user_x": user_x,
            "trajectory: [...]
        })
        if verify_result.success:
            result = client.post("/user/password/login", {
                "phone": phone,
                "password": password,
                "captcha_id": captcha.captcha_id
            })

    return result
```

---

## 6. 错误处理

### 6.1 错误码对照表

| HTTP | error 值 | 含义 | 处理建议 |
|------|----------|------|----------|
| 400 | 缺少必填字段 | 请求参数不完整 | 检查请求体 |
| 400 | 验证码错误 | 短信/滑块验证失败 | 重新获取验证码 |
| 400 | 用户名已存在 | 用户名被占用 | 更换用户名 |
| 401 | 未提供有效的 Token | 未登录 | 调用登录接口获取 Token |
| 401 | 无效或过期的 Token | Token 过期/错误 | 调用 `/auth/refresh` 刷新 |
| 403 | 需要管理员权限 | 非管理员操作 | 使用管理员账号 |
| 404 | 资源不存在 | 访问的资源不存在 | 检查资源 ID |
| 429 | 请求太频繁 | IP 限流 | 降低请求频率，等待 1 分钟 |
| 500 | 服务器错误 | 服务端异常 | 稍后重试或联系管理员 |

### 6.2 重试策略

```python
import time
import logging

def api_call_with_retry(client_func, max_retries=3, base_delay=1):
    """带指数退避的 API 调用重试"""
    for attempt in range(max_retries):
        try:
            result = client_func()
            if result.get("success"):
                return result

            # 非服务器错误不重试
            status = result.get("status", 400)
            if status < 500:
                return result

        except Exception as e:
            logging.warning(f"API 调用失败 (attempt {attempt+1}): {e}")

        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt)
            logging.info(f"等待 {delay}s 后重试...")
            time.sleep(delay)

    return {"success": False, "error": "Max retries exceeded"}
```

### 6.3 限流处理

公开 API（`/api/v1/chat/public`、`/api/v1/chat`）有 IP 限流：
- 每 IP 每分钟 **10 次**（公开对话）
- 超过返回 429

**本地缓存 Token 减少重复登录请求**：
```python
import time
from functools import wraps

def token_cache(ttl_seconds=3600):
    """Token 缓存装饰器"""
    cache = {}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            key = f"{func.__name__}:{args}:{kwargs}"

            if key in cache:
                token, expires = cache[key]
                if now < expires:
                    return token

            result = func(*args, **kwargs)
            if result.get("success"):
                token = result.get("data", {}).get("token")
                if token:
                    cache[key] = (token, now + ttl_seconds)
            return result
        return wrapper
    return decorator
```

---

## 7. 最佳实践

### 7.1 安全建议

1. **不要硬编码 API Key**：使用环境变量或密钥管理服务
   ```python
   import os
   api_key = os.environ.get("EASYKAI_API_KEY")
   ```

2. **HTTPS 始终开启**：所有 API 调用必须使用 HTTPS

3. **最小权限原则**：Agent Key 设置最小必要 scopes

4. **定期轮换密钥**：
   ```python
   # 每 90 天轮换一次
   def rotate_keys(client, user_api):
       keys = user_api.list_api_keys()
       for key in keys["data"]:
           if key["active"]:
               # 创建新 Key 后删除旧的
               new_key = user_api.create_api_key(f"{key['name']}-rotated")
               user_api.revoke_api_key(key["id"])
   ```

### 7.2 性能优化

1. **使用持久连接**（Session）：
   ```python
   # Python requests.Session 自动保持连接池
   session = requests.Session()
   ```

2. **批量操作**：尽量使用批量接口而非循环调用

3. **分页控制**：合理设置 pageSize（建议 20-50）

4. **缓存 RAG 结果**：
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=128)
   def cached_rag_search(kb_client, query, top_k=5):
       return kb_client.search(query, top_k)
   ```

### 7.3 完整集成示例

```python
"""
VeroRon 维洛智能 SDK 完整集成示例
"""

import os
import requests
import json

class EasyKaiSDK:
    """一键集成——封装所有客户端"""

    def __init__(self, base_url="https://platform.easykai.cn", api_key=None, token=None):
        self._client = VeroRunClient(base_url, api_key=api_key, token=token)
        self.auth = AuthClient(self._client)
        self.user = UserClient(self._client)
        self.chat = ChatClient(self._client)
        self.kb = KnowledgeClient(self._client)
        self.agent = AgentClient(self._client)
        self.shop = ShopClient(self._client)
        self.matrix = AgentMatrixClient(self._client)
        self.coupon = CouponClient(self._client)
        self.sub = SubscriptionClient(self._client)

    def login(self, phone=None, password=None, token=None):
        """一键登录"""
        if token:
            self._client.set_token(token)
            return {"success": True}

        if phone and password:
            return self.auth.login_by_password(phone, password)

        raise ValueError("必须提供 token 或 phone+password")

    def get_summary(self):
        """获取用户概览"""
        profile = self.user.get_profile()
        if not profile.get("success"):
            return profile
        data = profile["data"]
        return {
            "success": True,
            "data": {
                "user": f"{data['display_name']} ({data['username']})",
                "tier": data["tier_name"],
                "calls_remaining": data["calls_remaining"],
                "keys": len(self.user.list_api_keys().get("data", [])),
            }
        }


# ── 使用示例 ──
if __name__ == "__main__":
    sdk = EasyKaiSDK()
    sdk.login(phone="13800138000", password="mypassword")
    summary = sdk.get_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
```

---

> **文档维护说明**  
> 本文档基于 v2026.07 代码生成。SDK 客户端代码是参考实现，实际使用时可根据项目需求调整。  
> 所有方法签名和响应格式以 [API 参考文档](./api-reference.md) 为准。