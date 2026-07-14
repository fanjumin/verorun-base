# Mini-App Generator — 小程序生成器标准

> 版本: v1.0 | 更新日期: 2026-07-14  
> 模块位置: `site_builder/mini_app/`

---

## 目录

1. [概述](#1-概述)
2. [BaseMiniAppGenerator 接口](#2-baseminiappgenerator-接口)
3. [模板目录结构规范](#3-模板目录结构规范)
4. [模板变量替换](#4-模板变量替换)
5. [现有平台生成器](#5-现有平台生成器)
6. [新增平台生成器](#6-新增平台生成器)

---

## 1. 概述

Mini-App 生成器模块负责将品牌配置、站点信息等系统数据渲染为各平台的小程序代码（源代码.zip）。

### 1.1 架构

```
MiniAppEngine (engine.py)
      │
      ├── DouyinGenerator  →  templates/douyin/  →  .zip (app.js + pages/)
      ├── WechatGenerator  →  templates/wechat/  →  .zip (app.js + pages/)
      ├── TelegramGenerator →  templates/telegram/ → .zip (index.html + js/)
      └── LineGenerator    →  templates/line/    →  .zip (index.html + js/)
      │
      └── MiniAppPackager (packager.py) → .zip
      └── MiniAppDeployer (deployer.py) → 部署到平台
```

### 1.2 工作流程

```
1. 用户通过 /admin/site-builder/mini-app/generate 触发
2. MiniAppEngine 读取 site_config + brand + options
3. 调用对应平台的 Generator.generate()
   ├── _copy_template()  — 复制模板目录到输出目录
   ├── 遍历模板文件      — _render_template() 替换 {{ variable }}
   └── _write_file()    — 写入渲染后的文件
4. MiniAppPackager.package() 打包为 .zip
5. 用户可下载或通过 MiniAppDeployer 部署
```

---

## 2. BaseMiniAppGenerator 接口

所有平台生成器继承自 `site_builder/mini_app/generators/base.py` 中的 `BaseMiniAppGenerator`。

### 2.1 抽象方法

```python
class BaseMiniAppGenerator(ABC):
    platform: str = ''          # 'douyin' | 'wechat' | 'telegram' | 'line'
    template_dir: str = ''      # 模板目录绝对路径
    output_base: str = 'dist'   # 输出基础目录

    @abstractmethod
    def generate(self, site_config: dict, brand: dict, options: dict) -> dict:
        """生成小程序文件。

        Args:
            site_config: 站点配置（token、模板等）
            brand: 品牌设置（site_name, primary_color, logo_url 等）
            options: 生成选项（include_chat, include_pages, base_url 等）

        Returns:
            {
                'output_dir': 'dist/douyin/',
                'files': ['app.js', 'pages/chat/chat.js', ...],
                'platform': 'douyin',
                'compatible_with': ['toutiao']  # 可选
            }
        """
```

### 2.2 工具方法

| 方法 | 签名 | 用途 |
|------|------|------|
| `_copy_template()` | `(output_dir: str)` | 复制模板目录到输出目录，先清空目标 |
| `_render_template()` | `(template_path: str, context: dict) -> str` | `{{ variable }}` 替换模板变量 |
| `_write_file()` | `(path: str, content: str)` | 写入文件，自动创建父目录 |
| `_get_brand_context()` | `(brand: dict) -> dict` | 提取品牌变量（`app_name`, `primary_color` 等） |
| `_get_api_context()` | `(options: dict) -> dict` | 提取 API 变量（`base_url`, `api_prefix` 等） |
| `_collect_files()` | `(output_dir: str) -> list` | 收集输出目录中所有文件的相对路径 |

### 2.3 模板变量替换

使用简单的 `{{ variable }}` 占位符替换（非 Jinja2），变量来自：

| 变量来源 | 方法 | 可用变量 |
|----------|------|----------|
| Brand | `_get_brand_context()` | `app_name`, `tagline`, `primary_color`, `secondary_color`, `logo_url`, `favicon_url`, `brand_story` |
| API | `_get_api_context()` | `base_url`, `api_prefix`, `platform` |
| 自定义 | generate() 中自行注入 | 各平台特有变量 |

---

## 3. 模板目录结构规范

### 3.1 通用规则

- 模板目录放在 `site_builder/mini_app/templates/<platform>/`
- 模板文件使用平台对应的扩展名
- 所有 `{{ variable }}` 占位符在渲染时被替换
- 产物目录（`workspace/`）由生成器管理，不提交到版本控制

### 3.2 原生小程序平台（抖音/微信）

```
templates/<platform>/
├── app.js                       # 小程序入口
├── app.{ttss,wxss}              # 全局样式
├── pages/
│   ├── home/                    # 首页
│   │   ├── home.js
│   │   ├── home.{ttml,wxml}
│   │   └── home.{ttss,wxss}
│   ├── chat/                    # AI 对话页
│   │   ├── chat.js
│   │   ├── chat.{ttml,wxml}
│   │   └── chat.{ttss,wxss}
│   └── profile/                 # 个人中心
│       ├── profile.js
│       ├── profile.{ttml,wxml}
│       └── profile.{ttss,wxss}
└── components/
    └── chat-widget/             # 聊天组件
        ├── chat-widget.js
        ├── chat-widget.{ttml,wxml}
        └── chat-widget.{ttss,wxss}
```

### 3.3 WebView 平台（Telegram/LINE）

```
templates/<platform>/
├── index.html                   # 主入口
├── chat.html                    # 聊天页面
├── css/
│   └── style.css                # 样式
└── js/
    └── app.js                   # 应用逻辑
```

---

## 4. 模板变量替换

### 4.1 可用变量

以下变量可在模板文件中使用 `{{ variable }}` 引用：

| 变量名 | 来源 | 示例值 |
|--------|------|--------|
| `app_name` | brand | `"VeroRun AI"` |
| `tagline` | brand | `"智能建站助手"` |
| `primary_color` | brand | `"#1890ff"` |
| `secondary_color` | brand | `"#52c41a"` |
| `logo_url` | brand | `"https://easykai.cn/static/logo.png"` |
| `favicon_url` | brand | `"https://easykai.cn/favicon.ico"` |
| `brand_story` | brand | `"..."` |
| `base_url` | options | `"https://easykai.cn"` |
| `api_prefix` | options | `"/api/v1/mini-program"` |
| `platform` | options | `"douyin"` |

### 4.2 示例（Telegram index.html）

```html
<!DOCTYPE html>
<html>
<head>
  <title>{{ app_name }}</title>
  <meta name="theme-color" content="{{ primary_color }}">
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
  <script src="js/app.js"></script>
</body>
</html>
```

---

## 5. 现有平台生成器

### 5.1 抖音（DouyinGenerator）

| 属性 | 值 |
|------|-----|
| `platform` | `'douyin'` |
| `template_dir` | `mini_app/templates/douyin/` |
| 兼容平台 | `['toutiao']` |

**实现要点**：
- 使用 `tt.*` API
- 入口 `app.js` 调用 `tt.login()` → 换取系统 JWT
- 页面使用 `.ttml` / `.ttss` 扩展名

### 5.2 微信（WechatGenerator）

| 属性 | 值 |
|------|-----|
| `platform` | `'wechat'` |
| `template_dir` | `mini_app/templates/wechat/` |
| 兼容平台 | `[]` |

**实现要点**：
- 使用 `wx.*` API
- 页面使用 `.wxml` / `.wxss` 扩展名
- SDK: `@verorun/sdk-wechat`

### 5.3 Telegram（TelegramGenerator）

| 属性 | 值 |
|------|-----|
| `platform` | `'telegram'` |
| `template_dir` | `mini_app/templates/telegram/` |
| 兼容平台 | `[]` |

**实现要点**：
- WebView 模式，全 HTML/JS
- 集成了 `Telegram.WebApp` SDK
- SDK: `@verorun/sdk-telegram`

### 5.4 LINE（LineGenerator）

| 属性 | 值 |
|------|-----|
| `platform` | `'line'` |
| `template_dir` | `mini_app/templates/line/` |
| 兼容平台 | `[]` |

**实现要点**：
- LIFF 模式，全 HTML/JS
- 集成了 LIFF v2 SDK
- SDK: `@verorun/sdk-line`

---

## 6. 新增平台生成器

### 步骤

1. **创建模板目录**

```
site_builder/mini_app/templates/<platform>/
├── ... 按 §3 规范放置模板文件
```

2. **创建生成器类**

```python
# site_builder/mini_app/generators/<platform>.py
from .base import BaseMiniAppGenerator

class MyPlatformGenerator(BaseMiniAppGenerator):
    platform = 'my_platform'
    template_dir = os.path.join(
        os.path.dirname(__file__), '..', 'templates', 'my_platform'
    )

    def generate(self, site_config, brand, options):
        output_dir = os.path.join(self.output_base, self.platform)
        self._copy_template(output_dir)

        context = {**self._get_brand_context(brand), **self._get_api_context(options)}
        # 自定义上下文
        context['custom_var'] = options.get('custom_var', '')

        for root, _, files in os.walk(output_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                rendered = self._render_template(fpath, context)
                self._write_file(fpath, rendered)

        return {
            'output_dir': output_dir,
            'files': self._collect_files(output_dir),
            'platform': self.platform,
        }
```

3. **注册到 MiniAppEngine**

```python
# site_builder/mini_app/__init__.py
from .generators.my_platform import MyPlatformGenerator

GENERATORS = {
    'douyin': DouyinGenerator,
    'wechat': WechatGenerator,
    'telegram': TelegramGenerator,
    'line': LineGenerator,
    'my_platform': MyPlatformGenerator,  # 新增
}
```

4. **更新平台列表 API**

```python
# site_builder/routes.py — list_platforms() 端点
# 返回中包含新平台的标识
```

5. **创建 SDK（可选）**

如需在生成的代码中使用统一 API，可参考 `sdks/` 下对应平台的 SDK。

---

> **文档维护**  
> 本文档基于 v2026.07 代码生成。新增平台生成器时请同步更新本文档 §5 和 §6。
