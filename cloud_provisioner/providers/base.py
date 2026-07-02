#!/usr/bin/env python3
"""Provider 抽象基类 — 所有云厂商适配器继承此类"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """云服务提供商适配器抽象基类"""

    @abstractmethod
    def validate_config(self, config: dict) -> tuple:
        """验证配置是否合法，返回 (is_valid: bool, error_msg: str)"""
        return True, ''

    @abstractmethod
    def provision(self, instance_id: int, specs: dict, log_callback=None) -> dict:
        """
        创建云资源
        返回: {resource_id, connect_info: {ip, port, username, password, domain}, extra: {}}
        """
        pass

    @abstractmethod
    def get_status(self, resource_id: str) -> str:
        """查询资源状态: pending/running/stopped/terminated/failed"""
        pass

    @abstractmethod
    def terminate(self, resource_id: str) -> bool:
        """销毁资源"""
        pass

    def get_console_url(self, resource_id: str) -> str:
        """获取管理面板链接（可选）"""
        return ''

    def estimate_cost(self, specs: dict) -> dict:
        """预估费用（可选）"""
        return {'monthly': 0, 'setup': 0}
