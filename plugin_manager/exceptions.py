#!/usr/bin/env python3
"""
Plugin Manager — 自定义异常
=============================
"""


class PluginError(Exception):
    """插件系统基础异常"""
    pass


class PluginNotFoundError(PluginError):
    """插件未找到"""
    def __init__(self, identifier: str):
        super().__init__(f'插件 "{identifier}" 未找到')
        self.identifier = identifier


class PluginNotInstalledError(PluginError):
    """插件未安装"""
    def __init__(self, identifier: str):
        super().__init__(f'插件 "{identifier}" 未安装')
        self.identifier = identifier


class PluginNotEnabledError(PluginError):
    """插件未启用"""
    def __init__(self, identifier: str):
        super().__init__(f'插件 "{identifier}" 未启用')
        self.identifier = identifier


class PluginDependencyError(PluginError):
    """插件依赖错误"""
    def __init__(self, identifier: str, missing_deps: list):
        super().__init__(f'插件 "{identifier}" 依赖缺失: {", ".join(missing_deps)}')
        self.identifier = identifier
        self.missing_deps = missing_deps


class PluginCircularDependencyError(PluginError):
    """循环依赖错误"""
    def __init__(self, cycle: list):
        super().__init__(f'检测到循环依赖: {" → ".join(cycle)}')
        self.cycle = cycle


class PluginStateError(PluginError):
    """状态转换非法"""
    def __init__(self, identifier: str, current: str, target: str):
        super().__init__(f'插件 "{identifier}" 状态 {current} 不能转换到 {target}')
        self.identifier = identifier
        self.current = current
        self.target = target


class PluginVersionError(PluginError):
    """版本不兼容"""
    def __init__(self, identifier: str, required: str, installed: str):
        super().__init__(f'插件 "{identifier}" 需要版本 {required}，当前 {installed}')
        self.identifier = identifier
        self.required = required
        self.installed = installed
