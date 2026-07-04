# Product Sourcing Plugin (AliApiPlugin v0.2.0)

1688 supply chain sourcing plugin — product search, AI optimization, local marketplace publishing.

## Features

- **Product Sourcing** — Search / browse / batch-collect 1688 products
- **AI Optimization** — Multi-version title generation, description rewrite, selling point extraction
- **Local Publishing** — Sync to marketplace `products` table with SKU support
- **OAuth Authorization** — URL generation / callback / refresh / revoke
- **Rate Limiting** — Frequency control, concurrency control, quota management
- **Cache Service** — In-memory two-level cache
- **Audit Logging** — API call logging and statistics

## Configuration

Configuration is stored in the plugin's own `ali_api_config` table, with sensitive fields encrypted.

| Key | Description | Required |
|-----|-------------|----------|
| `alibaba_app_key` | 1688 App Key | Yes |
| `alibaba_app_secret` | 1688 App Secret | Yes |
| `alibaba_api_gateway` | API Gateway URL | No (has default) |

Can be overridden by environment variables: `ALIBABA_APP_KEY`, `ALIBABA_APP_SECRET`, `ALIBABA_API_GATEWAY`

## Uninstall

On uninstall, the following is automatically cleaned up:

- Delete plugin directory
- Drop all 6 `ali_api_*` tables
- Delete legacy config from `system_config`

## i18n

All user-facing text uses `self.t()` for translation. Translation files are in the `i18n/` directory:

```
plugins/ali_api/i18n/
├── zh-CN.yml    # Chinese translations
└── en.yml       # English translations
```

Language follows the system environment variable `DEPLOY_LANG`.
