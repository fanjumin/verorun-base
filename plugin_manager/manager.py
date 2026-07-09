#!/usr/bin/env python3
"""
Plugin Manager — 插件管理器核心类
====================================
管理插件生命周期（5 状态）、发现、依赖解析、持久化。

生命周期:
    UNKNOWN → INSTALLED → ENABLED → ACTIVE → DISABLED → UNINSTALLED
                           ↑                         │
                           └─── ENABLED ←────────────┘
"""

import os
import sys
import json
import importlib
import importlib.util
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from .models import (
    PluginInfo, PluginStatus,
    init_plugin_registry_table, get_registry_db,
)
from .discovery import PluginDiscovery, version_satisfies
from .exceptions import (
    PluginNotFoundError, PluginNotInstalledError,
    PluginNotEnabledError, PluginDependencyError,
    PluginCircularDependencyError, PluginStateError,
    PluginVersionError,
)
from .hooks import HookRegistry, get_hook_registry
from .event_bus import EventBus, get_event_bus, EventName
from . import deps as deps_module
from .config_validator import validate_config as _validate_config, coerce_config
from .logger import get_plugin_logger, init_plugin_logging
from .license import LicenseManager, get_license_manager
from .store import StoreAPIClient, get_store_client


class PluginManager:
    """插件管理器核心类"""

    def __init__(self, app=None, hook_registry: HookRegistry = None,
                 event_bus: EventBus = None):
        self.app = app
        self.plugins_dir = None
        self._discovery = PluginDiscovery()
        self._lock = threading.Lock()

        # 运行时缓存: {identifier: PluginInfo}
        self._cache: Dict[str, PluginInfo] = {}

        # 运行时实例: {identifier: instance}
        self._instances: Dict[str, Any] = {}

        # 钩子系统 & 事件总线
        self._hook_registry = hook_registry or get_hook_registry()
        self._event_bus = event_bus or get_event_bus()

        # License & 商店
        self._license_mgr: Optional[LicenseManager] = None
        self._store_client: Optional[StoreAPIClient] = None

        if app is not None:
            self.init_app(app)

    # ── 初始化 ──────────────────────────────────────────────────────────

    def init_app(self, app):
        """工厂模式初始化，绑定到 Flask 应用

        调用时机: app 创建后，第一个请求前调用一次。
        """
        self.app = app

        # 确定插件目录
        plugins_dir = getattr(app, 'plugins_dir', None) or \
            os.path.join(app.root_path, 'plugins')
        self.plugins_dir = os.path.abspath(plugins_dir)
        self._discovery.set_plugins_dir(self.plugins_dir)

        # 初始化数据库表
        init_plugin_registry_table()

        # 初始化日志系统
        init_plugin_logging()

        # 初始化 License & Store 表
        from .models_store import init_license_store_tables
        init_license_store_tables()

        # License & Store 客户端（延迟初始化）
        self._license_mgr = get_license_manager()
        self._store_client = get_store_client()

        # 从数据库加载已注册插件到缓存
        self._load_cache()

        # 自动安装新发现的插件
        try:
            discovered = self._discovery.discover()
            auto_installed = 0
            for info in discovered:
                if info.identifier not in self._cache:
                    self.install(info.identifier)
                    auto_installed += 1
            if auto_installed > 0:
                print(f'[PluginManager] ✅ 自动安装 {auto_installed} 个新插件')
                self._load_cache()  # 重新加载缓存
                # 自动启用新安装的插件
                auto_enabled = 0
                for info in discovered:
                    cached = self._cache.get(info.identifier)
                    if cached and cached.status == PluginStatus.INSTALLED:
                        try:
                            self.enable(info.identifier)
                            auto_enabled += 1
                        except Exception as e:
                            print(f'[PluginManager] ⚠️ auto-enable {info.identifier}: {e}')
                if auto_enabled > 0:
                    print(f'[PluginManager] ✅ 自动启用 {auto_enabled} 个新插件')
                    self._load_cache()

            # 用磁盘 plugin.json 刷新已缓存插件的静态元信息（menu/version 等）。
            # 仅更新内存缓存，不写 DB，避免污染运行时状态（status/config）；
            # 保证 plugin.json 始终是菜单等静态元信息的权威来源。
            for disk_info in discovered:
                cached = self._cache.get(disk_info.identifier)
                if cached:
                    cached.metadata = disk_info.metadata
                    cached.version = disk_info.version

            # ── 加载所有插件的 locale 翻译 ─────────────────────
            try:
                from i18n import seed_plugin_translations
                for disk_info in discovered:
                    locale_dir = os.path.join(disk_info.path, 'locale')
                    if os.path.isdir(locale_dir):
                        seed_plugin_translations(disk_info.identifier, locale_dir)
            except Exception as e:
                print(f'[PluginManager] ⚠️ 加载插件翻译失败: {e}')
        except Exception as e:
            print(f'[PluginManager] ⚠️ 自动安装失败: {e}')

        # 记录到 app 扩展
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['plugin_manager'] = self

        print(f'[PluginManager] ✅ 已初始化 (plugins: {self.plugins_dir}, '
              f'cached: {len(self._cache)})')

    # ── 发现 ────────────────────────────────────────────────────────────

    def discover(self) -> List[PluginInfo]:
        """扫描 plugins/ 目录，返回新发现的插件列表"""
        discovered = self._discovery.discover()
        # 过滤出尚未注册的
        new_plugins = [p for p in discovered if p.identifier not in self._cache]
        return new_plugins

    def discover_all(self) -> List[PluginInfo]:
        """扫描并返回所有插件（含已注册的）"""
        return self._discovery.discover()

    # ── 安装 ────────────────────────────────────────────────────────────

    def install(self, identifier: str) -> PluginInfo:
        """安装插件: 写入 registry 持久化, 状态 → INSTALLED"""
        with self._lock:
            if identifier in self._cache:
                info = self._cache[identifier]
                if info.status in (PluginStatus.INSTALLED, PluginStatus.ENABLED,
                                   PluginStatus.ACTIVE):
                    print(f'[PluginManager] {identifier} 已安装，跳过')
                    return info

            # 从磁盘扫描
            info = self._discovery.discover_one(identifier)
            if info is None:
                raise PluginNotFoundError(identifier)

            info.status = PluginStatus.INSTALLED
            info.installed_at = datetime.now().isoformat()
            info.updated_at = datetime.now().isoformat()

            # 持久化到数据库
            self._save_to_db(info)
            self._cache[identifier] = info

            # 触发事件
            self._emit('plugin.installed', plugin_id=identifier)

            print(f'[PluginManager] ✅ {identifier} v{info.version} installed')
            return info

    # ── 启用 ────────────────────────────────────────────────────────────

    def enable(self, identifier: str) -> PluginInfo:
        """启用插件: 检查依赖 + 执行 setup(), 状态 → ENABLED"""
        with self._lock:
            info = self._get_cached(identifier)

            # 验证状态转换
            if not info.status.can_transition_to(PluginStatus.ENABLED):
                raise PluginStateError(identifier, info.status.value, 'enabled')

            # 解析依赖
            deps = info.dependencies
            if deps:
                self._resolve_dependencies(identifier, deps)

            # 检查最低应用版本
            if info.min_app_version and hasattr(self.app, 'version'):
                if not version_satisfies(self.app.version, f'>={info.min_app_version}'):
                    raise PluginVersionError(
                        identifier, info.min_app_version,
                        getattr(self.app, 'version', '?')
                    )

            # ── License 检查 ───────────────────────────────────────
            # 付费插件必须有有效 License 才能启用
            if self._license_mgr and self._license_mgr.is_paid_plugin(identifier):
                lic_result = self._license_mgr.validate(identifier)
                if not lic_result.get('valid'):
                    info.last_error = f'License required: {lic_result.get("error", "unlicensed")}'
                    info.status = PluginStatus.ERROR
                    self._save_to_db(info)
                    raise PluginStateError(
                        identifier, 'unlicensed',
                        f'enable failed: {lic_result.get("error", "no license")}'
                    )
                print(f'[PluginManager] {identifier}: license valid ({lic_result.get("status")})')

            # 执行插件 setup()
            try:
                instance = self._load_instance(info)
                if hasattr(instance, 'setup') and callable(instance.setup):
                    setup_result = instance.setup()
                    if setup_result is False:
                        raise RuntimeError('setup() returned False')

                self._instances[identifier] = instance
            except Exception as e:
                info.last_error = f'setup error: {e}'
                info.status = PluginStatus.ERROR
                self._save_to_db(info)
                print(f'[PluginManager] ❌ {identifier} setup failed: {e}')
                raise

            info.status = PluginStatus.ENABLED
            info.updated_at = datetime.now().isoformat()
            self._save_to_db(info)

            self._emit('plugin.enabled', plugin_id=identifier)
            print(f'[PluginManager] ✅ {identifier} enabled')

            # ── 自动激活: enable 后立即注册路由/钩子 ────────────
            try:
                instance = self._instances.get(identifier)
                if instance:
                    if hasattr(instance, 'activate') and callable(instance.activate):
                        instance.activate()

                    # 注册路由
                    if self.app and hasattr(instance, 'register_routes'):
                        bps = instance.register_routes()
                        for bp in bps:
                            prefix = self._get_route_prefix(identifier, bp)
                            self.app.register_blueprint(bp, url_prefix=prefix)
                            print(f'[PluginManager] {identifier}: mounted {prefix}')

                    # 注册钩子
                    if self._hook_registry and hasattr(instance, 'get_event_handlers'):
                        handlers = instance.get_event_handlers()
                        for event, handler in handlers.items():
                            self._hook_registry.add_action(event, handler)

                    info.status = PluginStatus.ACTIVE
                    info.updated_at = datetime.now().isoformat()
                    self._save_to_db(info)
                    print(f'[PluginManager] ✅ {identifier} active (auto)')
            except Exception as e:
                print(f'[PluginManager] ⚠️ {identifier} auto-activate warning: {e}')

            return info

    # ── 激活 ────────────────────────────────────────────────────────────

    def activate(self, identifier: str) -> PluginInfo:
        """激活插件: 加载模块 + 注册路由/钩子, 状态 → ACTIVE"""
        with self._lock:
            info = self._get_cached(identifier)

            if not info.status.can_transition_to(PluginStatus.ACTIVE):
                raise PluginStateError(identifier, info.status.value, 'active')

            # 检查依赖是否都已激活
            if identifier in self._instances:
                self._check_deps_active(info)

            instance = self._instances.get(identifier)
            if instance is None:
                raise PluginNotEnabledError(identifier)

            # 执行 activate()
            try:
                if hasattr(instance, 'activate') and callable(instance.activate):
                    instance.activate()

                # 注册路由（如果插件提供了 Blueprint）
                if self.app and hasattr(instance, 'register_routes'):
                    bps = instance.register_routes()
                    for bp in bps:
                        prefix = self._get_route_prefix(identifier, bp)
                        self.app.register_blueprint(bp, url_prefix=prefix)
                        print(f'[PluginManager] {identifier}: mounted {prefix}')

                # 注册钩子（如果启用了钩子系统）
                if self._hook_registry and hasattr(instance, 'get_event_handlers'):
                    handlers = instance.get_event_handlers()
                    for event, handler in handlers.items():
                        self._hook_registry.add_action(event, handler)

            except Exception as e:
                info.last_error = f'activate error: {e}'
                info.status = PluginStatus.ERROR
                self._save_to_db(info)
                print(f'[PluginManager] ❌ {identifier} activate failed: {e}')
                raise

            info.status = PluginStatus.ACTIVE
            info.updated_at = datetime.now().isoformat()
            self._save_to_db(info)

            print(f'[PluginManager] ✅ {identifier} active')
            return info

    # ── 禁用 ────────────────────────────────────────────────────────────

    def disable(self, identifier: str) -> PluginInfo:
        """禁用插件: 反注册路由/钩子, 状态 → DISABLED"""
        with self._lock:
            info = self._get_cached(identifier)

            if not info.status.can_transition_to(PluginStatus.DISABLED):
                raise PluginStateError(identifier, info.status.value, 'disabled')

            # 通知依赖本插件的插件
            self._notify_dependents(identifier, 'disable')

            # 执行 deactivate()
            instance = self._instances.pop(identifier, None)
            if instance:
                try:
                    if hasattr(instance, 'deactivate') and callable(instance.deactivate):
                        instance.deactivate()

                    # 移除路由（Phase 2 完善）
                    if self.app and hasattr(instance, 'register_routes'):
                        bps = instance.register_routes()
                        for bp in bps:
                            self._unregister_blueprint(bp)
                except Exception as e:
                    print(f'[PluginManager] {identifier} deactivate warning: {e}')

            info.status = PluginStatus.DISABLED
            info.updated_at = datetime.now().isoformat()
            self._save_to_db(info)

            self._emit('plugin.disabled', plugin_id=identifier)
            print(f'[PluginManager] ✅ {identifier} disabled')
            return info

    # ── 卸载 ────────────────────────────────────────────────────────────

    def uninstall(self, identifier: str) -> None:
        """卸载插件: 禁用 + 清理 + 移除 registry 记录"""
        with self._lock:
            info = self._get_cached(identifier)

            # 如果处于 ACTIVE 或 ENABLED，先禁用
            if info.status in (PluginStatus.ACTIVE, PluginStatus.ENABLED):
                self.disable(identifier)

            # 执行 on_uninstall（如果插件有 cleanup）
            instance = self._instances.pop(identifier, None)
            if instance and hasattr(instance, 'on_uninstall'):
                try:
                    instance.on_uninstall()
                except Exception as e:
                    print(f'[PluginManager] {identifier} uninstall warning: {e}')

            # 从数据库中移除记录
            self._delete_from_db(identifier)

            # 从缓存中移除
            self._cache.pop(identifier, None)

            self._emit('plugin.uninstalled', plugin_id=identifier)
            print(f'[PluginManager] ✅ {identifier} uninstalled')

    # ── 批量操作 ────────────────────────────────────────────────────────

    def install_all(self) -> List[str]:
        """安装所有已发现但未注册的插件"""
        installed = []
        for plugin in self.discover():
            try:
                self.install(plugin.identifier)
                installed.append(plugin.identifier)
            except Exception as e:
                print(f'[PluginManager] ❌ install {plugin.identifier}: {e}')
        return installed

    def enable_all(self) -> List[str]:
        """启用所有已安装的插件"""
        enabled = []
        for identifier, info in self._cache.items():
            if info.status == PluginStatus.INSTALLED:
                try:
                    self.enable(identifier)
                    enabled.append(identifier)
                except Exception as e:
                    print(f'[PluginManager] ❌ enable {identifier}: {e}')
        return enabled

    def activate_all(self) -> List[str]:
        """激活所有已启用的插件"""
        activated = []
        for identifier, info in self._cache.items():
            if info.status == PluginStatus.ENABLED:
                try:
                    self.activate(identifier)
                    activated.append(identifier)
                except Exception as e:
                    print(f'[PluginManager] ❌ activate {identifier}: {e}')
        return activated

    def _activate_enabled(self):
        """启动时自动激活所有状态为 enabled 的插件"""
        for identifier, info in self._cache.items():
            if info.status == PluginStatus.ENABLED:
                try:
                    self.activate(identifier)
                except Exception as e:
                    print(f'[PluginManager] ❌ auto-activate {identifier}: {e}')

    def mount_active_routes(self):
        """启动期挂载所有 enabled/active 插件的路由（必须在首个请求前调用）。

        Flask 的 register_blueprint 只能在启动阶段调用，运行时 activate() 挂载的路由
        无法生效。因此在 app 初始化时统一挂载已启用插件的 Blueprint。
        幂等：已挂载的 Blueprint（同名）会跳过，可安全重复调用。
        """
        if not self.app:
            return
        mounted = []
        for identifier, info in self._cache.items():
            if info.status not in (PluginStatus.ENABLED, PluginStatus.ACTIVE):
                continue
            try:
                instance = self._instances.get(identifier)
                if instance is None:
                    instance = self._load_instance(info)
                    if hasattr(instance, 'setup') and callable(instance.setup):
                        instance.setup()
                    self._instances[identifier] = instance
                if hasattr(instance, 'register_routes'):
                    for bp in instance.register_routes():
                        if bp.name in self.app.blueprints:
                            continue  # 已挂载，跳过
                        prefix = self._get_route_prefix(identifier, bp)
                        self.app.register_blueprint(bp, url_prefix=prefix)
                        mounted.append(f'{identifier}:{prefix}')
            except Exception as e:
                print(f'[PluginManager] ⚠️ mount {identifier} failed: {e}')
        if mounted:
            print(f'[PluginManager] ✅ 启动挂载路由: {mounted}')

    # ── 查询方法 ────────────────────────────────────────────────────────

    def get_info(self, identifier: str) -> Optional[PluginInfo]:
        """获取插件信息（从缓存）"""
        return self._cache.get(identifier)

    def list_plugins(self, status: str = None) -> List[PluginInfo]:
        """列出插件，可按状态筛选"""
        if status:
            return [p for p in self._cache.values() if p.status.value == status]
        return list(self._cache.values())

    def is_enabled(self, identifier: str) -> bool:
        info = self._cache.get(identifier)
        return info is not None and info.status in (
            PluginStatus.ENABLED, PluginStatus.ACTIVE)

    def is_active(self, identifier: str) -> bool:
        info = self._cache.get(identifier)
        return info is not None and info.status == PluginStatus.ACTIVE

    def get_instance(self, identifier: str) -> Optional[Any]:
        """获取插件运行时实例"""
        return self._instances.get(identifier)

    def count(self) -> int:
        return len(self._cache)

    def count_by_status(self) -> Dict[str, int]:
        counts = {}
        for p in self._cache.values():
            s = p.status.value
            counts[s] = counts.get(s, 0) + 1
        return counts

    # ── 配置读写 ────────────────────────────────────────────────────────

    def get_config(self, identifier: str, key: str = None, default=None):
        """读取插件配置"""
        info = self._cache.get(identifier)
        if not info:
            return default
        if key:
            return info.config.get(key, default)
        return info.config

    def set_config(self, identifier: str, key: str, value,
                   validate: bool = True) -> bool:
        """写入单条插件配置并持久化

        Args:
            identifier: 插件标识
            key: 配置键
            value: 配置值
            validate: 是否校验

        校验失败会打印警告但仍会保存（防止前端设置损坏后无法恢复）。
        """
        with self._lock:
            info = self._cache.get(identifier)
            if not info:
                return False

            if validate and info.settings_schema:
                test_config = dict(info.config)
                test_config[key] = value
                errors = _validate_config(test_config, info.settings_schema)
                if errors:
                    print(f'[PluginManager] {identifier}: config validate warnings: {errors}')

            info.config[key] = value
            info.updated_at = datetime.now().isoformat()
            self._save_to_db(info)
            return True

    def set_config_batch(self, identifier: str, config: dict,
                         coerce: bool = True) -> dict:
        """批量保存插件配置（带 Schema 校验 + 类型转换）

        Args:
            identifier: 插件标识
            config: 完整配置 dict
            coerce: 是否自动类型转换

        Returns:
            {'success': bool, 'errors': [str], 'coerced': dict}
        """
        with self._lock:
            info = self._cache.get(identifier)
            if not info:
                return {'success': False, 'errors': ['Plugin not found'], 'coerced': {}}

            schema = info.settings_schema or {}
            target = config

            # 类型强制转换
            if coerce and schema:
                target = coerce_config(target, schema)

            # 校验
            errors = _validate_config(target, schema)

            if errors:
                # 仍保存（宽松模式），但返回错误列表
                print(f'[PluginManager] {identifier}: config warnings: {errors}')

            info.config = target
            info.updated_at = datetime.now().isoformat()
            self._save_to_db(info)

            return {
                'success': True,
                'errors': errors,
                'coerced': target,
            }

    # ── 配置校验 ──────────────────────────────────────────────────────

    def validate_config(self, identifier: str,
                        config: dict = None) -> dict:
        """校验插件配置

        Args:
            identifier: 插件标识
            config: 待校验的配置（None 表示当前已保存的配置）

        Returns:
            {'success': bool, 'errors': [str], 'schema': dict}
        """
        info = self._cache.get(identifier)
        if not info:
            return {'success': False, 'errors': ['Plugin not found'], 'schema': {}}

        schema = info.settings_schema or {}
        target = config if config is not None else info.config
        errors = _validate_config(target, schema)

        return {
            'success': len(errors) == 0,
            'errors': errors,
            'schema': schema,
        }

    # ── 依赖解析 ──────────────────────────────────────────────────────

    def resolve_install_order(self) -> List[str]:
        """拓扑排序，返回安装/激活顺序（依赖优先）"""
        plugin_graph = {}
        for pid, pinfo in self._cache.items():
            plugin_graph[pid] = list(pinfo.dependencies.keys())
        return deps_module.topological_sort(plugin_graph)

    def get_dependency_tree(self, identifier: str) -> dict:
        """获取插件依赖树"""
        plugin_graph = {}
        for pid, pinfo in self._cache.items():
            plugin_graph[pid] = list(pinfo.dependencies.keys())
        return deps_module.get_dependency_tree(identifier, plugin_graph)

    def get_dependents_tree(self, identifier: str) -> dict:
        """获取被哪些插件依赖"""
        plugin_graph = {}
        for pid, pinfo in self._cache.items():
            plugin_graph[pid] = list(pinfo.dependencies.keys())
        _, reverse = deps_module.build_dependency_graph(plugin_graph)
        reverse_plugins = {k: list(v) for k, v in reverse.items()}
        return deps_module.get_dependents_tree(identifier, reverse_plugins)

    def get_plugin_menus(self) -> list:
        """收集所有已安装+已启用插件的菜单项"""
        menus = []
        for pid, pinfo in self._cache.items():
            if pinfo.status not in (PluginStatus.ENABLED, PluginStatus.ACTIVE):
                continue
            # 从 plugin.json 读取 menu 配置
            menu_cfg = pinfo.metadata.get('menu') if pinfo.metadata else None
            if not menu_cfg:
                # 尝试从插件实例获取
                inst = getattr(pinfo, 'instance', None)
                if inst and hasattr(inst, 'get_menu'):
                    menu_cfg = inst.get_menu()
            if menu_cfg:
                menu_cfg['_plugin_id'] = pid
                menus.append(menu_cfg)
        return menus

    # ── 日志 ──────────────────────────────────────────────────────────

    def read_log(self, identifier: str, lines: int = 50) -> str:
        """读取插件日志最后 N 行"""
        from .logger import read_plugin_log
        return read_plugin_log(identifier, lines)

    def clear_log(self, identifier: str) -> bool:
        """清空插件日志"""
        from .logger import clear_plugin_log
        return clear_plugin_log(identifier)

    # ── License & Store 访问器 ───────────────────────────────────────

    @property
    def license_manager(self):
        return self._license_mgr

    @property
    def store_client(self):
        return self._store_client

    # ── 钩子/事件代理（Phase 3 完整实现） ──────────────────────────────

    def register_hook(self, identifier: str, hook_name: str, callback):
        if self._hook_registry:
            self._hook_registry.add_action(hook_name, callback)

    def trigger_action(self, hook_name: str, *args, **kwargs):
        if self._hook_registry:
            self._hook_registry.do_action(hook_name, *args, **kwargs)

    def apply_filter(self, hook_name: str, value, **kwargs):
        if self._hook_registry:
            return self._hook_registry.apply_filters(hook_name, value, **kwargs)
        return value

    # ── 内部方法 ────────────────────────────────────────────────────────

    def _get_cached(self, identifier: str) -> PluginInfo:
        """获取缓存中的插件信息，不存在则抛出异常"""
        info = self._cache.get(identifier)
        if info is None:
            # 尝试从数据库恢复
            info = self._load_from_db(identifier)
            if info:
                self._cache[identifier] = info
            else:
                raise PluginNotFoundError(identifier)
        return info

    def _load_instance(self, info: PluginInfo) -> Any:
        """动态加载插件模块，返回 BasePlugin 子类实例"""
        identifier = info.identifier
        plugin_dir = info.path

        if not os.path.isdir(plugin_dir):
            raise PluginNotFoundError(identifier)

        # 确保项目根在 sys.path（供插件导入根业务模块 analytics/health_check 等）
        project_root = os.path.dirname(os.path.dirname(plugin_dir))  # plugins/ 的父目录
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            # 用命名空间包导入（plugins.<identifier>），避免插件包名污染顶层命名空间，
            # 防止如 plugins/analytics 遮蔽项目根 analytics 业务模块。
            mod = importlib.import_module(f'plugins.{identifier}')

            from plugin_manager.base import BasePlugin

            instance = None
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (isinstance(attr, type) and
                        issubclass(attr, BasePlugin) and
                        attr is not BasePlugin):
                    instance = attr()
                    instance._config = info.config
                    # 注入引用
                    instance.plugin_info = info
                    instance.manager = self
                    # 注入独立日志器
                    instance._log = get_plugin_logger(identifier)
                    # 重新加载 i18n
                    if hasattr(instance, '_load_i18n'):
                        instance._load_i18n()
                    break

            if instance is None:
                # 新式插件: 尝试直接实例化 __plugin__.py 中的类
                plugin_mod_path = os.path.join(plugin_dir, '__plugin__.py')
                if os.path.isfile(plugin_mod_path):
                    spec = importlib.util.spec_from_file_location(
                        f'{identifier}.__plugin__', plugin_mod_path)
                    plugin_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(plugin_mod)
                    for attr_name in dir(plugin_mod):
                        attr = getattr(plugin_mod, attr_name)
                        if (isinstance(attr, type) and
                                issubclass(attr, BasePlugin) and
                                attr is not BasePlugin):
                            instance = attr()
                            instance.plugin_info = info
                            instance.manager = self
                            instance._log = get_plugin_logger(identifier)
                            break

            if instance is None:
                raise RuntimeError(f'No BasePlugin subclass found in {identifier}')

            return instance

        except ImportError as e:
            raise RuntimeError(f'ImportError loading {identifier}: {e}')

    def _resolve_dependencies(self, identifier: str, deps: Dict[str, str]):
        """解析并验证依赖: 检查依赖是否已启用 + 版本满足"""
        if not deps:
            return

        # 检测循环依赖（简单版：两跳内）
        dep_stack = list(deps.keys())
        for dep_id in dep_stack:
            dep_info = self._cache.get(dep_id)
            if dep_info and dep_info.dependencies:
                if identifier in dep_info.dependencies:
                    raise PluginCircularDependencyError([identifier, dep_id, identifier])

        # 检查每个依赖
        missing = []
        for dep_id, version_spec in deps.items():
            dep_info = self._cache.get(dep_id)
            if dep_info is None:
                missing.append(dep_id)
                continue

            if dep_info.status not in (PluginStatus.ENABLED, PluginStatus.ACTIVE):
                missing.append(f'{dep_id} (status: {dep_info.status.value})')
                continue

            if version_spec and not version_satisfies(dep_info.version, version_spec):
                raise PluginVersionError(dep_id, version_spec, dep_info.version)

        if missing:
            raise PluginDependencyError(identifier, missing)

    def _check_deps_active(self, info: PluginInfo):
        """检查依赖插件是否都已激活"""
        for dep_id in info.dependencies:
            dep_info = self._cache.get(dep_id)
            if dep_info and dep_info.status != PluginStatus.ACTIVE:
                # 自动尝试激活
                if dep_info.status == PluginStatus.ENABLED:
                    self.activate(dep_id)

    def _notify_dependents(self, identifier: str, action: str):
        """通知依赖此插件的其他插件"""
        for pid, pinfo in self._cache.items():
            if identifier in pinfo.dependencies:
                print(f'[PluginManager] {pid}: dependency {identifier} {action}')

    def _get_route_prefix(self, identifier: str, bp) -> str:
        """确定路由前缀"""
        # 如果 Blueprint 已自定义 url_prefix，则使用自定义的
        if bp.url_prefix:
            return bp.url_prefix
        return f'/plugin/{identifier}'

    def _unregister_blueprint(self, bp):
        """从 Flask app 移除 Blueprint（实验性）"""
        if not self.app:
            return
        # Flask 没有官方方法来反注册，这里只是从 app 的蓝图中移除引用
        name = bp.name
        if name in self.app.blueprints:
            del self.app.blueprints[name]

    def _emit(self, event_name: str, **data):
        """触发内部事件（由 EventBus + HookRegistry 消费）"""
        # 通过 EventBus 发布（异步，订阅者模式）
        if hasattr(self._event_bus, 'emit'):
            self._event_bus.emit(event_name, **data)

        # 通过 HookRegistry 执行 action
        if self._hook_registry:
            # 约定: event_name = "plugin.installed" → hook = "plugin/installed"
            hook_name = event_name.replace('.', '/')
            self._hook_registry.do_action(hook_name, **data)

    # ── 数据库操作 ──────────────────────────────────────────────────────

    def _load_cache(self):
        """从数据库加载所有已注册插件到缓存"""
        self._cache.clear()
        with get_registry_db() as conn:
            rows = conn.execute(
                'SELECT * FROM plugin_registry ORDER BY identifier'
            ).fetchall()
            for row in rows:
                info = self._row_to_info(dict(row))
                self._cache[info.identifier] = info

    def _load_from_db(self, identifier: str) -> Optional[PluginInfo]:
        """从数据库加载单个插件"""
        with get_registry_db() as conn:
            row = conn.execute(
                'SELECT * FROM plugin_registry WHERE identifier = ?',
                (identifier,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_info(dict(row))

    def _save_to_db(self, info: PluginInfo):
        """保存或更新插件记录到数据库"""
        with get_registry_db() as conn:
            conn.execute("""
                INSERT INTO plugin_registry (
                    identifier, name, version, author, description,
                    min_app_version, path, metadata, status, config,
                    dependencies, provides_hooks, listens_hooks,
                    permissions, settings_schema, installed_at,
                    updated_at, last_error
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(identifier) DO UPDATE SET
                    name=excluded.name,
                    version=excluded.version,
                    author=excluded.author,
                    description=excluded.description,
                    min_app_version=excluded.min_app_version,
                    path=excluded.path,
                    metadata=excluded.metadata,
                    status=excluded.status,
                    config=excluded.config,
                    dependencies=excluded.dependencies,
                    provides_hooks=excluded.provides_hooks,
                    listens_hooks=excluded.listens_hooks,
                    permissions=excluded.permissions,
                    settings_schema=excluded.settings_schema,
                    updated_at=excluded.updated_at,
                    last_error=excluded.last_error
            """, (
                info.identifier, info.name, info.version,
                info.author, info.description,
                info.min_app_version, info.path,
                json.dumps(info.metadata, ensure_ascii=False, default=str),
                info.status.value,
                json.dumps(info.config, ensure_ascii=False, default=str),
                json.dumps(info.dependencies, ensure_ascii=False),
                json.dumps(info.provides_hooks, ensure_ascii=False),
                json.dumps(info.listens_hooks, ensure_ascii=False),
                json.dumps(info.permissions, ensure_ascii=False),
                json.dumps(info.settings_schema, ensure_ascii=False, default=str),
                info.installed_at or datetime.now().isoformat(),
                info.updated_at or datetime.now().isoformat(),
                info.last_error,
            ))
            conn.commit()

    def _delete_from_db(self, identifier: str):
        """从数据库删除插件记录"""
        with get_registry_db() as conn:
            conn.execute(
                'DELETE FROM plugin_registry WHERE identifier = ?',
                (identifier,)
            )
            conn.commit()

    def _row_to_info(self, row: dict) -> PluginInfo:
        """数据库行 → PluginInfo"""
        return PluginInfo(
            identifier=row['identifier'],
            name=row['name'],
            version=row['version'],
            author=row.get('author', ''),
            description=row.get('description', ''),
            min_app_version=row.get('min_app_version', '1.0.0'),
            path=row.get('path', ''),
            metadata=json.loads(row.get('metadata', '{}')),
            status=PluginStatus(row['status']),
            config=json.loads(row.get('config', '{}')),
            dependencies=json.loads(row.get('dependencies', '{}')),
            provides_hooks=json.loads(row.get('provides_hooks', '[]')),
            listens_hooks=json.loads(row.get('listens_hooks', '[]')),
            permissions=json.loads(row.get('permissions', '[]')),
            settings_schema=json.loads(row.get('settings_schema', '{}')),
            installed_at=row.get('installed_at'),
            updated_at=row.get('updated_at'),
            last_error=row.get('last_error', ''),
        )
