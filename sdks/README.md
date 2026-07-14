# VeroRun SDKs

JavaScript SDKs for VeroRun social media mini-program platforms.

## Packages

| Package | Directory | Description |
|---------|-----------|-------------|
| `@verorun/sdk-common` | `common/` | Core SDK: Auth, Chat, RAG |
| `@verorun/sdk-wechat` | `wechat/` | WeChat Mini-Program (`wx.*`) wrapper |
| `@verorun/sdk-douyin` | `douyin/` | Douyin/Toutiao Mini-Program (`tt.*`) wrapper |
| `@verorun/sdk-telegram` | `telegram/` | Telegram Bot API + WebApp SDK |
| `@verorun/sdk-line` | `line/` | LINE LIFF + Messaging API SDK |

## Usage

```js
// Common SDK — works on all platforms
import { VeroAuth, VeroChat, VeroRAG } from '@verorun/sdk-common';

const auth = new VeroAuth({ baseURL: 'https://easykai.cn', platform: 'telegram' });
const { data } = await auth.login({ initData: tg.initData });
```

## Publishing

```bash
# Each package can be published independently
cd sdks/<package>
npm publish
```

## License

MIT
