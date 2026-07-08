# 插件系统完整测试计划

## 一、发现的问题

1. 服务器上的旧 `plugins/__init__.py` 未被删除
2. Discover API 返回空 → 原因待查（可能是旧文件干扰，或 `PluginDiscovery` 扫描逻辑问题）
3. 端口 8084 被旧进程占用 → 需 stop + restart
4. 插件发现后没有自动进入管理视野 → 需要手动"扫描→安装→启用"三步，流程太长

## 二、测试步骤（在服务器执行）

### 测试 1：基础环境修复
| # | 操作 | 命令 | 预期 |
|---|------|------|------|
| 1.1 | 杀掉所有 admin 进程 | `pkill -f admin/app.py` | 进程结束 |
| 1.2 | 删除残留旧文件 | `rm plugins/__init__.py` | 确认删除 |
| 1.3 | 重启服务 | `nohup python3 admin/app.py > /tmp/admin2.log 2>&1 &` | 无报错 |

### 测试 2：Discover API
| # | 操作 | 预期 |
|---|------|------|
| 2.1 | `curl http://localhost:8084/admin/plugins/discover` | 返回 5 个插件列表 |
| 2.2 | 检查返回的每个插件 identifier/name/version/description | 完整 |
| 2.3 | `curl http://localhost:8084/admin/plugins` | 返回空列表（未安装） |

### 测试 3：Install API
| # | 操作 | 预期 |
|---|------|------|
| 3.1 | `curl -X POST http://localhost:8084/admin/plugins/install -H 'Content-Type: application/json' -d '{"identifier":"ali_api"}'` | 返回 success |
| 3.2 | `curl -X POST ...` install coupons/reviews/wishlist/order_notify 各一次 | 全部成功 |
| 3.3 | `curl http://localhost:8084/admin/plugins` | 返回 5 个已安装列表 |

### 测试 4：Enable/Disable API
| # | 操作 | 预期 |
|---|------|------|
| 4.1 | `curl -X POST ... /plugins/enable -d '{"identifier":"ali_api"}'` | enabled=true |
| 4.2 | `curl http://localhost:8084/admin/plugins` | ali_api status=ENABLED |
| 4.3 | `curl -X POST ... /plugins/disable -d '{"identifier":"ali_api"}'` | enabled=false |
| 4.4 | `curl http://localhost:8084/admin/plugins` | ali_api status=DISABLED |

### 测试 5：事件总线
| # | 操作 | 预期 |
|---|------|------|
| 5.1 | 启用 order_notify 插件 | 成功 |
| 5.2 | 触发一次订单支付（通过系统前端） | order_notify 收到事件 |
| 5.3 | 检查日志确认事件被正确处理 | 有 Handler 执行记录 |

### 测试 6：Nginx 反向代理
| # | 操作 | 预期 |
|---|------|------|
| 6.1 | `https://easykai.cn/admin/plugins/` 浏览器访问 | 页面正常加载 |
| 6.2 | 点"扫描新插件"按钮 | 返回 5 个插件 |
| 6.3 | 逐一点"Install" | 安装成功 |
| 6.4 | 点"Enable"启用 ali_api | 1688 管理入口出现 |

## 三、已知问题清单

| 问题 | 严重度 | 说明 |
|------|--------|------|
| 端口占用导致第二条进程起不来 | 高 | 旧 `nohup` 进程未停 |
| 旧框架文件残留 | 高 | `plugins/__init__.py` 还在 |
| 管理页面没有直观的重新发现/安装按钮 | 中 | 需要用户自己点"扫描新插件" |
| 1688 功能在跑但管理入口找不到 | 中 | 原因待验证 |

## 四、如果 Discover 仍然返回空 — 需排查

1. `PluginDiscovery.__init__` 的默认 `plugins_dir`
2. `_scan_plugin_dir()` 的 glob 模式是否正确
3. 看一下 discovery.py 实际源码
