# Regression Log — 性能回归与修复记录

> 记录 agent.easykai.cn 管理后台的性能问题及其根因、修复方案与验证结果。
> 最新更新: 2026-07-14

---

## 1. Dashboard 无限 Loading

### 症状
进入后台后 Dashboard 区域卡在 Loading 状态，数据无法加载。

### 根因
`l_dashboard()` 函数在 `init()` 调用时被执行，但此时 `l_dashboard` 变量尚未定义。JavaScript 的 `function hoisting` 仅提升函数声明，`const l_dashboard = async () => {...}` 表达式不会被提升，导致调用时 `l_dashboard` 为 `undefined`。

### 修复
- `setTimeout(init, 100)` 将初始化推迟 100ms，确保所有函数定义完成
- 添加 `tail` 大按钮兜底加载逻辑

### 状态
✅ 已修复

---

## 2. Gunicorn Worker 冷启动

### 症状
第一次访问时响应极慢（6-7 秒），后续访问正常（<200ms）。这是所有性能问题的**根本瓶颈**。

### 根因
`gunicorn` 没有 `--preload` 参数。每个 worker 在接收第一个请求时才加载整个应用（20+ 蓝图/插件/自动化系统等），阻塞当前请求 6-7 秒。

更严重的是：4 个 worker 并发加载慢查询会全部被 hang 住，导致 **ERR_TIMED_OUT**。

### 修复
```diff
- ExecStart=/usr/bin/python3 -m gunicorn -w 4
+ ExecStart=/usr/bin/python3 -m gunicorn --preload -w 4
```

### 影响范围
`/etc/systemd/system/admin.service`

### 状态
✅ 已修复，部署后即刻生效

---

## 3. ERR_TIMED_OUT

### 症状
浏览器地址栏输入 `agent.easykai.cn` 后长时间无响应，最终显示 `ERR_TIMED_OUT`。

### 根因
**非网络问题**（ping 到阿里云 25ms，0% 丢包）。根因是 Gunicorn 冷启动（见 #2），worker 全被慢查询 hang 住，nginx 等不到后端响应。

辅助因素：`ssl_session_tickets off` 导致每个新连接做完整 TLS 握手。

### 修复
| 改动 | 文件 | 效果 |
|------|------|------|
| `--preload` | admin.service | 冷启动消除 |
| `ssl_session_tickets on` | easykai.conf | TLS 复用（66ms） |
| `ssl_session_cache shared:SSL:10m` | easykai.conf | 共享会话缓存 |
| 统一 HTTP 80 server block | easykai.conf | 简化重定向逻辑 |

### 状态
✅ 已修复。用户确认 ERR_TIMED_OUT 不再出现。

---

## 4. nginx 配置冗余

### 症状
nginx reload 报 `conflicting server name` 警告。

### 根因
`sites-enabled/` 下同时存在 `.conf` 和 `.bak` 文件，配置被重复加载。

### 修复
```bash
rm /etc/nginx/sites-enabled/easykai.conf.bak
```
HTTP 80 端口由 3 个独立 server block（含 if 条件）合并为统一 block。

### 状态
✅ 已清理

---

## 5. 登录成功后的 Toast 延时

### 症状
登录成功后页面无响应约 600ms，然后才跳转到后台。

### 根因
前端 `setTimeout` 设置为 600ms（为了显示 Toast 动画），实际等待过长。

### 修复
```diff
- setTimeout(() => { window.location.href = ... }, 600);
+ setTimeout(() => { window.location.href = ... }, 100);
```

### 影响文件
- `admin/templates/login.html`
- `admin/templates/admin_login.html`（3 处）

### 状态
✅ 已部署

---

## 6. Jinja2 模板编译慢

### 症状
首次请求 `/admin` 页面耗时 1.16s，后续请求 0.11s。

### 根因
`app.config['TEMPLATES_AUTO_RELOAD'] = True` 导致 Jinja2 每次渲染都检查 62 个 template 文件的时间戳。Worker 重启后所有模板需重新编译。

### 修复
```python
app.config['TEMPLATES_AUTO_RELOAD'] = False
app.jinja_env.auto_reload = False
app.jinja_env.bytecode_cache = jinja2.FileSystemBytecodeCache(...)
```

### 效果
- 冷 worker 首次渲染: **1.16s → 0.19s**
- 字节码缓存命中后: **0.11s**

### 状态
✅ 已部署

---

## 7. Analytics 中国城市数据缺失

### 症状
Analytics → Region 页面显示 "No China city data"，无中国城市数据。

### 根因
双重问题：
1. `ip2region_v4.xdb` 数据库文件在服务器上完全缺失（`plugins/analytics/data/` 下只有 `analytics.db`），所有中国 IP 城市定位回退到 `ip-api.com`，但该服务在大陆不可达/限流
2. 文件后来被上传到服务器，但 **admin 服务从未重启**，`_ip2region_searcher` 始终保持 `None`

### 修复
| 步骤 | 说明 |
|------|------|
| 本地定位 xdb 文件 | `F:\Sites\easykai.cn\analytics\data\ip2region_v4.xdb`（10.6MB） |
| 复制到项目路径 | `F:\Sites\VeroRun\plugins\analytics\data\` |
| 部署到服务器 | `/home/.../analytics/data/` |
| **重启 admin 服务** | `systemctl restart admin.service` |

### 验证
```sql
-- analytics_logs 中的地理数据
CN / 蚌埠市 / 223.242.130.x → /admin/

-- API 响应
GET /admin/analytics/api/v1/geo/china-cities?days=30
→ {"data":[{"city":"蚌埠市","pv":2,"uv":1}],"success":true}
```

### 状态
✅ 已修复。新访问数据持续累积中。

---

## 8. Admin 页面 "Verifying Identity..." 永久卡死

### 症状
访问 `https://agent.easykai.cn/admin` 后页面永久显示 "Verifying Identity..."（加载动画），无法进入后台。整个 admin 页面的所有模块（Dashboard、用户管理、CMS 等）全部不可用。

### 根因
**`f5d03e3`**（"merge remote i18n changes into memory system"）合并时，`admin/templates/partials/subscriptions.html` 第 56 行混入了一个多余的 `};`：

```javascript
// 第 55 行：forceCancel 函数正常结束
}).catch(function(){showToast("{{ _('Request Failed') }}","error")});
}
};   // ← 多余的垃圾！merge 残留
```

admin 页面由 60+ 个 partial 模板拼接成一个约 12000 行的 `<script>` 标签串行执行。一个多余的 `};` 导致整个脚本解析失败（`SyntaxError: Unexpected token '}'`），所有后续代码不执行。`tail.html` 中的 `init()` 调用永远不会到达，页面永久停留在 head.html 中的初始 "Verifying Identity..." HTML。

### 修复
```diff
 }).catch(function(){showToast("{{ _('Request Failed') }}","error")});
-}
-};
+}
```

仅影响 1 个文件、1 行代码。

### 预防
新增 `tools/check_templates.py` 预检脚本，每次提交前自动扫描：
- ① 嵌套/断裂 `_()` 模式正则扫描
- ② Jinja2 `env.parse()` 编译检测

用法：`python tools/check_templates.py`，返回 0=通过，1=阻止。

### 状态
✅ 已修复。本地 `preview_admin.html` 渲染验证通过，`new Function()` 解析无错误。

---

## 总结

| # | 问题 | 优先级 | 时间 | 状态 |
|---|------|--------|------|------|
| 1 | Dashboard 卡死 | P0 | 07-13 | ✅ |
| 2 | Worker 冷启动 | **P0 根因** | 07-14 | ✅ |
| 3 | ERR_TIMED_OUT | P0 | 07-14 | ✅ |
| 4 | nginx 配置冗余 | P2 | 07-14 | ✅ |
| 5 | Toast 延时 600ms | P1 | 07-14 | ✅ |
| 6 | 模板编译 1.16s | P1 | 07-14 | ✅ |
| 7 | Analytics 中国城市 | P0 | 07-14 | ✅ |
| 8 | Verifying Identity 卡死 | P0 | 07-19 | ✅ |

### 关键教训

1. **Gunicorn `--preload` 应始终开启** — 特别是应用有大量导入/初始化时，这是最容易被忽略的性能陷阱
2. **文件部署后务必重启服务** — 这次 xdb 文件上传了但服务没重启，绕了一大圈才定位到
3. **在服务器复现问题比代码审查更高效** — #2 的问题静态代码根本看不出来，只有看 `ps` 才能在 5 秒内定位
4. **Merge 后必须逐文件检查** — `f5d03e3` 合并了 2000+ 文件，一个字节的残留字符就能让整个系统瘫痪。`check_templates.py` 应作为 pre-commit hook 集成，防止此类问题再次发生
