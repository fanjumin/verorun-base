#!/usr/bin/env python3
"""
plugins/base.py — 插件基类
============================
所有插件必须继承 BasePlugin 并实现对应方法。

BasePlugin for the EasyKai Plugin System.
Every plugin must subclass BasePlugin and implement the required lifecycle methods.

Plugin lifecycle:
  install → enable → (运行) → disable → uninstall

i18n compliance: all user-facing strings use _() from i18n module.
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any, TYPE_CHECKING

# 添加项目根到路径，确保能导入 i18n
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from i18n import _

if TYPE_CHECKING:
    from plugins.registry import PluginRegistry


class PluginStatus:
    """插件状态常量"""
    UNINSTALLED = 'uninstalled'
    INSTALLED = 'installed'
    ENABLED = 'enabled'
    DISABLED = 'disabled'
    ERROR = 'error'


class BasePlugin(ABC):
    """
    插件基类 — 所有 EasyKai 插件必须继承此类。

    子类需要覆盖以下方法来实现功能：
    - register_routes(): 返回 Flask Blueprint 列表
    - register_jobs(): 返回 APScheduler job 配置字典列表
    - register_dag_nodes(): 返回 DAG 节点处理器字典
    - register_health_checks(): 返回健康检查项列表
    - get_event_handlers(): 返回事件处理器字典 {'event_name': handler}
    """

    # ── 元数据（子类必须设置） ──
    name: str = ''
    version: str = '0.1.0'
    description: str = ''
    author: str = ''
    depends_on: List[str] = []  # 依赖的其他插件 name 列表
    config_schema: Dict[str, Any] = {}  # 配置项定义（JSON Schema 风格）

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化插件实例。
        子类可以覆盖 __init__，但必须调用 super().__init__(config)。
        """
        self.config = config or {}
        self.status = PluginStatus.UNINSTALLED
        self._error_message: str = ''

    # ═══════════════════════════════════════════════════════════
    # 生命周期钩子（默认实现为空，子类按需覆盖）
    # ═══════════════════════════════════════════════════════════

    def on_install(self, registry: 'PluginRegistry') -> bool:
        """
        插件安装时调用。
        可用于：创建数据库表、初始化配置文件等。
        返回 True 表示安装成功，False 表示失败。
        """
        return True

    def on_uninstall(self, registry: 'PluginRegistry') -> bool:
        """
        插件卸载时调用。
        可用于：清理数据、删除配置等。
        返回 True 表示卸载成功。
        """
        return True

    def on_enable(self, registry: 'PluginRegistry') -> bool:
        """
        插件启用时调用。
        可用于：启动后台线程、注册信号等。
        返回 True 表示启用成功。
        """
        return True

    def on_disable(self, registry: 'PluginRegistry') -> bool:
        """
        插件禁用时调用。
        可用于：停止后台任务、释放资源等。
        返回 True 表示禁用成功。
        """
        return True

    # ═══════════════════════════════════════════════════════════
    # 路由注册（实现此方法以添加 Flask 路由）
    # ═══════════════════════════════════════════════════════════

    def register_routes(self) -> List[Any]:
        """
        返回此插件提供的 Flask Blueprint 列表。
        返回空列表表示不注册任何路由。
        示例:
            return [my_bp]
        """
        return []

    # ═══════════════════════════════════════════════════════════
    # 定时任务注册
    # ═══════════════════════════════════════════════════════════

    def register_jobs(self) -> List[Dict[str, Any]]:
        """
        返回此插件提供的 APScheduler job 配置列表。
        每条配置格式:
        {
            'job_id': 'unique_job_id',       # 必填
            'func': callable,                # 必填，任务函数
            'trigger': 'cron|interval|date',  # 必填
            'kwargs': {                       # trigger 参数
                'hour': 2,                   # cron
                'minute': 0,
                # 或 interval: {'seconds': 3600}
                # 或 date: {'run_date': datetime(...)}
            },
            'priority': 'normal',            # critical/high/normal/low
            'max_retries': 2,               # 失败重试次数
        }
        返回空列表表示不注册定时任务。
        """
        return []

    # ═══════════════════════════════════════════════════════════
    # DAG 工作流节点注册
    # ═══════════════════════════════════════════════════════════

    def register_dag_nodes(self) -> Dict[str, Any]:
        """
        返回此插件提供的 DAG 节点处理器。
        key 为节点类型名，value 为处理函数或类。
        示例:
            return {'my_node_type': my_handler_func}
        返回空字典表示不注册 DAG 节点。
        """
        return {}

    # ═══════════════════════════════════════════════════════════
    # 健康检查注册
    # ═══════════════════════════════════════════════════════════

    def register_health_checks(self) -> List[Dict[str, Any]]:
        """
        返回此插件提供的健康检查项列表。
        每条格式:
        {
            'check_id': 'unique_check_id',   # 必填
            'name': '检查项名称',              # 必填（使用中文源文本）
            'category': 'database|api|custom',# 必填
            'func': callable,                 # 必填，返回 {status: 'ok'|'warn'|'error', msg: str}
            'severity': 'warning|critical',   # 默认 'warning'
            'interval_seconds': 300,          # 检查间隔，默认 300
        }
        返回空列表表示不注册健康检查。
        """
        return []

    # ═══════════════════════════════════════════════════════════
    # 事件钩子注册
    # ═══════════════════════════════════════════════════════════

    def get_event_handlers(self) -> Dict[str, Any]:
        """
        返回此插件注册的事件处理器。
        key 为事件名（见 hooks.py 中的 EventName 常量），
        value 为处理函数。
        示例:
            return {
                EventName.ORDER_PAID: self.on_order_paid,
            }
        返回空字典表示不注册事件钩子。
        """
        return {}

    # ═══════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════

    def get_config_value(self, key: str, default=None):
        """获取插件配置值"""
        return self.config.get(key, default)

    def log(self, message: str, level: str = 'info'):
        """统一日志输出（后续可接入 logging 模块）"""
        prefix = f'[Plugin:{self.name}]'
        print(f'{prefix} [{level.upper()}] {message}')

    def validate_config(self) -> Optional[str]:
        """
        根据 config_schema 校验插件配置。
        返回 None 表示通过，返回字符串表示错误描述。
        子类可覆盖以实现自定义校验逻辑。
        """
        if not self.config_schema:
            return None

        for key, spec in self.config_schema.items():
            if spec.get('required', False) and key not in self.config:
                return _(f'缺少必填配置项: {key}')
            if key in self.config:
                expected_type = spec.get('type')
                if expected_type == 'int' and not isinstance(self.config[key], int):
                    return _(f'配置项 {key} 应为整数')
                if expected_type == 'bool' and not isinstance(self.config[key], bool):
                    return _(f'配置项 {key} 应为布尔值')
                if expected_type == 'str' and not isinstance(self.config[key], str):
                    return _(f'配置项 {key} 应为字符串')

        return None

    def __repr__(self) -> str:
        return f'<Plugin {self.name} v{self.version} [{self.status}]>'
