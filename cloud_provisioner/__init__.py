#!/usr/bin/env python3
"""
Cloud Provisioner — 云服务自动开通引擎

功能：
1. 云服务商品化（ECS/OSS/CDN/数据库等）
2. 下单后自动开通（Docker容器/云API）
3. 初始化脚本执行（建站环境部署）
4. 状态追踪与通知
5. AI 赋能：通过 Shop Agent/口令控制台下达指令

架构：
   订单支付 → Provisioner Engine → Provider Adapter → 创建资源 → 初始化 → 通知客户
                        │
                    ┌───┴───┐
                Template    Cloud API
                (Docker)    (Aliyun/TC/BD)

Phase 1: Docker/LXC 模板化（零资质要求）
Phase 2: 阿里云/腾讯云 API 直连（需合作伙伴资质）
"""

__version__ = "1.0.0"

from .engine import ProvisionerEngine
from .routes import provisioner_bp


def init_provisioner(app):
    """初始化开通引擎模块"""
    from .models import init_tables
    init_tables()

    app.register_blueprint(provisioner_bp)

    print(f'[CloudProvisioner] ✅ 云服务开通引擎已初始化')
    print(f'[CloudProvisioner] 📋 API: /cloud/* /admin/cloud/*')

    # 注册到启动后的自动恢复
    @app.after_request
    def _noop(r):
        return r

    return app
