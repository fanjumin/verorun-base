# 商品采集插件 (AliApiPlugin v0.2.0)

1688 供应链采集插件 — 商品搜索、AI 优化、本地商城发布。

## 功能

- **商品采集** — 搜索 / 分类浏览 / 批量采集 1688 商品
- **AI 优化** — 多版本标题生成、描述重写、卖点提炼
- **本地发布** — 同步到商城 `products` 表，支持 SKU
- **OAuth 授权** — URL 生成 / 回调 / 刷新 / 解除
- **风控系统** — 频率限制、并发控制、配额管理
- **缓存服务** — 内存二级缓存
- **日志审计** — API 调用日志与统计

## 配置

配置存储在插件自有的 `ali_api_config` 表中，密钥字段加密存储。

| 键 | 说明 | 是否必填 |
|----|------|---------|
| `alibaba_app_key` | 1688 App Key | 是 |
| `alibaba_app_secret` | 1688 App Secret | 是 |
| `alibaba_api_gateway` | API 网关地址 | 否（有默认值） |

环境变量可覆盖：`ALIBABA_APP_KEY`、`ALIBABA_APP_SECRET`、`ALIBABA_API_GATEWAY`

## 卸载

卸载时自动清理以下内容：

- 删除插件目录
- 删除全部 6 张 `ali_api_*` 表
- 删除 `system_config` 中的旧配置记录

## i18n

插件所有面向用户的文本使用 `self.t()` 方法翻译，翻译文件位于 `i18n/` 目录：

```
plugins/ali_api/i18n/
├── zh-CN.yml    # 中文翻译
└── en.yml       # 英文翻译
```

语言自动跟随系统环境变量 `DEPLOY_LANG`。
