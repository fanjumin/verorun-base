#!/usr/bin/env python3
"""Provider 适配器包"""
from .base import BaseProvider
from .template import TemplateProvider


def get_provider(provider_type: str = 'template', config: dict = None):
    """获取 Provider 实例"""
    if provider_type == 'template':
        return TemplateProvider(config or {})
    # Future: aliyun, tencent, baidu
    raise ValueError(f'不支持的云厂商: {provider_type}')
