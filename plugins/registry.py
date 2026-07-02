#!/usr/bin/env python3
"""
plugins/registry.py — 插件注册表
==================================
统一管理所有插件的发现、加载、生命周期。

Plugin Registry — scans, loads, and manages plugin lifecycle.
Handles discovery, dependency resolution, loading, enabling and disabling.

i18n compliance: all user-facing strings use _() from i18n module.
"""

import os
import sys
import json
import importlib
import traceback
from typing import Optional, Dict, List, Any, Type

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from i18n import _
from plugins.base import BasePlugin, PluginStatus
from plugins.hooks import get_event_bus, register_plugin_hooks, EventName


class PluginError(Exception):
    """插件相关错误"""
    pass


class PluginNotFoundError(PluginError):
    """插件未找到"""
    pass


class PluginDependencyError(PluginError):
    """插件依赖未满足"""
    pass


class PluginRegistry:
    """
    插件注册表 — 管理所有插件的中央注册中心。

    用法:
        registry = PluginRegistry(plugins_dir='/path/to/plugins')
        registry.discover()              # 扫描插件目录
        registry.load_all()              # 加载所有插件
        registry.enable('my_plugin')     # 启用指定插件
        registry.mount_all(app)          # 将所有已启用插件的 Blueprint 挂载到 Flask app
    """

    def __init__(self, plugins_dir: Optional[str] = None, flask_app=None):
        self.plugins_dir = plugins_dir or os.path.join(
            _BASE_DIR, 'plugins'
        )
        self.flask_app = flask_app
        self._plugins: Dict[str, BasePlugin] = {}      # name → 实例
        self._metadata: Dict[str, dict] = {}            # name → plugin.json 元数据
        self._disabled_on_start: set = set()            # 启动时未启用的插件

    # ═══════════════════════════════════════════════════════════
    # 插件发现
    # ═══════════════════════════════════════════════════════════

    def discover(self) -> List[str]:
        """
        扫描 plugins_dir 下的所有子目录，找到包含 plugin.json 的插件。
        返回发现的插件 name 列表。
        不包含 __pycache__ 及以下划线开头的目录。
        """
        if not os.path.isdir(self.plugins_dir):
            return []

        discovered = []
        for item in os.listdir(self.plugins_dir):
            item_path = os.path.join(self.plugins_dir, item)
            if not os.path.isdir(item_path):
                continue
            if item.startswith('_') or item.startswith('.'):
                continue
            if item == '__pycache__':
                continue

            # 查找 plugin.json 或 Python 包
            meta_path = os.path.join(item_path, 'plugin.json')
            init_path = os.path.join(item_path, '__init__.py')

            if os.path.isfile(meta_path) and os.path.isfile(init_path):
                discovered.append(item)

        return discovered

    def _read_metadata(self, plugin_name: str) -> dict:
        """读取插件目录下的 plugin.json 元数据"""
        meta_path = os.path.join(self.plugins_dir, plugin_name, 'plugin.json')
        if not os.path.isfile(meta_path):
            raise PluginNotFoundError(
                _('Plugin {name} missing plugin.json').format(name=plugin_name)
            )
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            # 确保 name 字段存在
            if 'name' not in meta:
                meta['name'] = plugin_name
            return meta
        except json.JSONDecodeError as e:
            raise PluginError(
                _('插件 {name} 的 plugin.json 格式无效: {err}').format(
                    name=plugin_name, err=str(e))
            )

    # ═══════════════════════════════════════════════════════════
    # 插件加载
    # ═══════════════════════════════════════════════════════════

    def load(self, plugin_name: str) -> BasePlugin:
        """
        加载并实例化一个插件（不执行生命周期钩子）。
        返回插件实例。

        Raises:
            PluginNotFoundError: 插件目录不存在
            PluginError: 加载失败
        """
        if plugin_name in self._plugins:
            return self._plugins[plugin_name]

        # 1. 验证插件目录
        plugin_path = os.path.join(self.plugins_dir, plugin_name)
        if not os.path.isdir(plugin_path):
            raise PluginNotFoundError(
                _('插件目录不存在: {path}').format(path=plugin_path)
            )

        # 2. 读取元数据
        meta = self._read_metadata(plugin_name)
        self._metadata[plugin_name] = meta

        # 3. 动态导入插件模块
        module_path = f'plugins.{plugin_name}'
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise PluginError(
                _('插件 {name} 导入失败: {err}').format(
                    name=plugin_name, err=str(e))
            )

        # 4. 查找继承 BasePlugin 的类
        plugin_cls = self._find_plugin_class(module, plugin_name)
        if not plugin_cls:
            raise PluginError(
                _('Plugin {name} has no class inheriting BasePlugin').format(name=plugin_name)
            )

        # 5. 实例化
        config = meta.get('config', {})
        try:
            instance = plugin_cls(config=config)
        except Exception as e:
            raise PluginError(
                _('插件 {name} 实例化失败: {err}').format(
                    name=plugin_name, err=str(e))
            )

        # 6. 校验
        if not instance.name:
            instance.name = plugin_name

        errors = self._validate_plugin(instance)
        if errors:
            raise PluginError(
                _('插件 {name} 校验失败: {errs}').format(
                    name=plugin_name, errs='; '.join(errors))
            )

        self._plugins[plugin_name] = instance
        instance.status = PluginStatus.INSTALLED
        instance.on_install(self)

        # 发射事件
        get_event_bus().emit(EventName.PLUGIN_INSTALLED,
                             plugin_name=plugin_name, version=instance.version)

        instance.log(_('Plugin loaded successfully'), 'info')
        return instance

    def _find_plugin_class(self, module, plugin_name: str) -> Optional[Type[BasePlugin]]:
        """
        在模块中查找第一个继承 BasePlugin 的类。
        跳过 BasePlugin 本身。
        """
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not isinstance(attr, type):
                continue
            if not issubclass(attr, BasePlugin):
                continue
            if attr is BasePlugin:
                continue
            return attr
        return None

    def _validate_plugin(self, instance: BasePlugin) -> List[str]:
        """校验插件实例，返回错误列表"""
        errors = []

        if not instance.name:
            errors.append(_('Plugin name is empty'))
        if not instance.description:
            errors.append(_('Plugin description is empty'))
        if not instance.author:
            errors.append(_('Plugin author is empty'))

        # 配置校验
        config_err = instance.validate_config()
        if config_err:
            errors.append(config_err)

        return errors

    def load_all(self) -> Dict[str, BasePlugin]:
        """
        发现并加载所有插件。
        返回 {plugin_name: instance} 字典。
        """
        discovered = self.discover()
        loaded = {}

        for plugin_name in discovered:
            try:
                instance = self.load(plugin_name)
                loaded[plugin_name] = instance
            except PluginError as e:
                print(f'[PluginRegistry] {_("Plugin load failed")}: {plugin_name} — {e}')
                self._disabled_on_start.add(plugin_name)
            except Exception as e:
                print(f'[PluginRegistry] {_("Plugin load error")}: {plugin_name} — {e}')
                traceback.print_exc()
                self._disabled_on_start.add(plugin_name)

        # 自动启用已加载的插件（如果 plugin.json 中 enabled=true 或未设置）
        for name, instance in loaded.items():
            meta = self._metadata.get(name, {})
            if meta.get('enabled', True):
                self.enable(name)

        return loaded

    # ═══════════════════════════════════════════════════════════
    # 启用/禁用
    # ═══════════════════════════════════════════════════════════

    def enable(self, plugin_name: str) -> bool:
        """
        启用指定插件。
        自动检查依赖并递归启用。
        """
        instance = self._plugins.get(plugin_name)
        if not instance:
            self.load(plugin_name)
            instance = self._plugins.get(plugin_name)
            if not instance:
                return False

        if instance.status == PluginStatus.ENABLED:
            return True

        # 检查并启用依赖
        deps = instance.depends_on
        for dep_name in deps:
            if dep_name not in self._plugins:
                try:
                    self.load(dep_name)
                except PluginError:
                    instance.log(
                        _('Dependency plugin {dep} load failed, cannot enable').format(dep=dep_name),
                        'error'
                    )
                    return False
            dep_instance = self._plugins[dep_name]
            if dep_instance.status != PluginStatus.ENABLED:
                if not self.enable(dep_name):
                    instance.log(
                        _('Dependency plugin {dep} enable failed').format(dep=dep_name),
                        'error'
                    )
                    return False

        # 执行启用钩子
        try:
            if not instance.on_enable(self):
                instance.status = PluginStatus.ERROR
                instance._error_message = _('on_enable returned False')
                return False
        except Exception as e:
            instance.status = PluginStatus.ERROR
            instance._error_message = str(e)
            instance.log(_('启用插件异常: {err}').format(err=str(e)), 'error')
            return False

        # 注册事件钩子
        hooks = instance.get_event_handlers()
        if hooks:
            register_plugin_hooks(hooks)

        instance.status = PluginStatus.ENABLED
        get_event_bus().emit(EventName.PLUGIN_ENABLED, plugin_name=plugin_name)
        instance.log(_('Plugin enabled'), 'info')
        return True

    def disable(self, plugin_name: str) -> bool:
        """禁用指定插件"""
        instance = self._plugins.get(plugin_name)
        if not instance:
            return False

        if instance.status == PluginStatus.DISABLED:
            return True

        try:
            if not instance.on_disable(self):
                return False
        except Exception as e:
            instance.log(_('禁用插件异常: {err}').format(err=str(e)), 'error')

        instance.status = PluginStatus.DISABLED
        get_event_bus().emit(EventName.PLUGIN_DISABLED, plugin_name=plugin_name)
        instance.log(_('Plugin disabled'), 'info')
        return True

    # ═══════════════════════════════════════════════════════════
    # 挂载到 Flask App
    # ═══════════════════════════════════════════════════════════

    def mount_all(self, app) -> List[str]:
        """
        将所有已启用插件的 Blueprint 挂载到 Flask app。
        返回成功挂载的插件名称列表。
        """
        mounted = []
        self.flask_app = app

        for name, instance in self._plugins.items():
            if instance.status != PluginStatus.ENABLED:
                continue

            try:
                blueprints = instance.register_routes()
                for bp in blueprints:
                    # 自动添加 url_prefix: /plugin/{plugin_name}
                    if not bp.url_prefix:
                        bp.url_prefix = f'/plugin/{name}'
                    app.register_blueprint(bp)
                mounted.append(name)
            except Exception as e:
                instance.log(
                    _('挂载路由失败: {err}').format(err=str(e)), 'error'
                )

        return mounted

    def mount_health_checks(self, health_module) -> List[str]:
        """
        将所有已启用插件的健康检查注册到 easykai_health 模块。
        返回成功注册的插件名称列表。
        """
        registered = []

        for name, instance in self._plugins.items():
            if instance.status != PluginStatus.ENABLED:
                continue

            try:
                checks = instance.register_health_checks()
                if not checks:
                    continue
                for check in checks:
                    health_module.register_check(
                        check_id=check['check_id'],
                        name=check['name'],
                        category=check.get('category', 'custom'),
                        func=check['func'],
                        severity=check.get('severity', 'warning'),
                        interval_seconds=check.get('interval_seconds', 300),
                    )
                registered.append(name)
            except Exception as e:
                instance.log(
                    _('注册健康检查失败: {err}').format(err=str(e)), 'error'
                )

        return registered

    # ═══════════════════════════════════════════════════════════
    # 查询接口
    # ═══════════════════════════════════════════════════════════

    def get(self, plugin_name: str) -> Optional[BasePlugin]:
        """获取插件实例"""
        return self._plugins.get(plugin_name)

    def list_all(self) -> List[dict]:
        """列出所有已发现插件的基本信息"""
        result = []
        for name, meta in self._metadata.items():
            instance = self._plugins.get(name)
            result.append({
                'name': name,
                'version': meta.get('version', 'unknown'),
                'description': meta.get('description', ''),
                'author': meta.get('author', ''),
                'status': instance.status if instance else 'not_loaded',
                'depends_on': meta.get('depends_on', []) if not instance
                              else list(instance.depends_on),
            })
        return result

    def get_status(self, plugin_name: str) -> str:
        """获取插件状态"""
        instance = self._plugins.get(plugin_name)
        return instance.status if instance else 'not_loaded'

    def is_enabled(self, plugin_name: str) -> bool:
        """检查插件是否已启用"""
        instance = self._plugins.get(plugin_name)
        return instance is not None and instance.status == PluginStatus.ENABLED

    def count(self) -> int:
        """返回已加载的插件数量"""
        return len(self._plugins)

    def count_enabled(self) -> int:
        """返回已启用的插件数量"""
        return sum(
            1 for i in self._plugins.values()
            if i.status == PluginStatus.ENABLED
        )

    # ═══════════════════════════════════════════════════════════
    # 注册 Scheduler Jobs
    # ═══════════════════════════════════════════════════════════

    def register_all_jobs(self, scheduler) -> List[str]:
        """
        将所有已启用插件的定时任务注册到 APScheduler。
        返回成功注册的插件名称列表。
        """
        registered = []

        for name, instance in self._plugins.items():
            if instance.status != PluginStatus.ENABLED:
                continue

            try:
                jobs = instance.register_jobs()
                for job in jobs:
                    job_id = job['job_id']
                    func = job['func']
                    trigger = job['trigger']
                    kwargs = job.get('kwargs', {})

                    if trigger == 'cron':
                        from apscheduler.triggers.cron import CronTrigger
                        t = CronTrigger(**kwargs)
                    elif trigger == 'interval':
                        from apscheduler.triggers.interval import IntervalTrigger
                        t = IntervalTrigger(**kwargs)
                    elif trigger == 'date':
                        from apscheduler.triggers.date import DateTrigger
                        t = DateTrigger(**kwargs)
                    else:
                        instance.log(
                            _('不支持的 trigger 类型: {t}').format(t=trigger), 'error'
                        )
                        continue

                    scheduler.add_job(
                        func=func,
                        trigger=t,
                        id=job_id,
                        replace_existing=True,
                    )
                registered.append(name)
            except Exception as e:
                instance.log(
                    _('注册定时任务失败: {err}').format(err=str(e)), 'error'
                )

        return registered

    # ═══════════════════════════════════════════════════════════
    # 注册 DAG 节点
    # ═══════════════════════════════════════════════════════════

    def register_all_dag_nodes(self, engine) -> List[str]:
        """
        将所有已启用插件的 DAG 节点注册到 WorkflowEngine。
        返回成功注册的插件名称列表。
        """
        registered = []

        for name, instance in self._plugins.items():
            if instance.status != PluginStatus.ENABLED:
                continue

            try:
                dag_nodes = instance.register_dag_nodes()
                for node_type, handler in dag_nodes.items():
                    engine.NODE_HANDLERS[node_type] = handler
                registered.append(name)
            except Exception as e:
                instance.log(
                    _('注册 DAG 节点失败: {err}').format(err=str(e)), 'error'
                )

        return registered
