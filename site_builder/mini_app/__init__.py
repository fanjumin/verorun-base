#!/usr/bin/env python3
"""site_builder/mini_app/ — Mini-Program Generation Module

Extends Site_builder to generate social media mini-programs for
Douyin, WeChat, Telegram, and LINE platforms.
"""

# Re-export key classes
from .engine import MiniAppEngine
from .packager import MiniAppPackager
from .deployer import MiniAppDeployer