# React Plugin Template（官方模板）

基于 **插件标准 v1.5 §15 前端框架插件指南** 的最小可运行 React 插件。

## 使用步骤

1. 复制本目录到 `plugins/<your_id>/`
2. 修改以下占位：
   - `plugin.json`：`identifier` / `name` / `menu.key` / `menu.label` / `menu.embed_url`
   - `routes.py`：Blueprint 名称、`url_prefix`
   - `__init__.py`：类名、`name`
3. 在 Admin 插件管理中启用

## 技术要点

- **iframe 路径**：`menu.embed_url` 指向 `/admin/react-demo/`，不参与内联 `l_<key>()`
- **React 18 UMD**：系统本地静态库（`/static/lib/workflow/react*.js`），**禁外网 CDN**
- **SSO**：`goPlugin()` 以 `?token=` 注入，页面经 `before_request` 校验管理员 JWT；前端以 `Authorization: Bearer` 调同域 API
- **i18n**：服务端渲染时注入 `window.__t` 字典，组件用 `window.__t['key']` 读取
- **样式**：引用 `design-system.css` 变量（`--bg-card` / `--text` / `--border` 等）

## 构建（可选，JSX）

```bash
npx esbuild src/App.jsx --bundle --format=iife --outfile=static/js/app.js
```

提交打包产物时须附 `src/` 源码 + 本构建命令（§16 审核要求）。
