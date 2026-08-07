#!/usr/bin/env python3
"""
React Plugin Template — 官方 React 插件模板（插件标准 v1.5 §15 前端框架插件指南）
============================================================

用法：把本目录复制到 plugins/<your_id>/，并同步修改：
  - plugin.json 的 identifier / name / menu.key / menu.embed_url
  - routes.py 的 Blueprint 名称与 url_prefix
  - __init__.py 的类名与 name

约束（§15）：
  - 必须走 iframe（menu.embed_url），禁止内联 l_<key>() 路径
  - React UMD 用系统本地静态库，禁止外网 CDN
  - 提交打包产物须附 src/ 源码 + 构建命令（§16 审核要求）
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from plugin_manager.base import BasePlugin


class ReactPlugin(BasePlugin):
    name = 'react_plugin'
    version = '0.1.0'
    description = 'Official React plugin template (iframe, local UMD, no CDN)'
    author = 'VeroRun'

    def on_enable(self, registry):
        return True

    def register_routes(self):
        from .routes import react_demo_bp
        return [react_demo_bp]
