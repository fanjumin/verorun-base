# Vault (vault)

## 概述

Vault 是 VeroRun 的数据备份与恢复插件，提供全量/增量备份、AES-256-GCM 加密、定时备份调度、审计日志以及多目标存储等企业级数据保护能力。支持将备份文件上传至 SFTP 等远程存储目标，确保数据安全可靠。

版本：**2.0.0**

## 功能特性

- **全量备份**：一键创建数据库的完整备份快照
- **增量备份**：基于变更日志的增量备份，减少存储空间和传输时间
- **AES-256-GCM 加密**：备份文件使用 AES-256-GCM 算法加密，保障数据机密性
- **定时备份**：基于 cron 表达式的定时备份调度器，自动化备份任务
- **审计日志**：完整记录备份操作的审计日志，满足合规要求
- **多目标存储**：支持本地存储和 SFTP 远程存储，可扩展其他存储后端
- **一键恢复**：从备份快照中快速恢复数据库
- **备份通知**：备份完成/失败时发送通知
- **管理后台**：通过嵌入页面管理备份任务和查看历史记录

## 架构设计

### 数据库策略

插件使用 VeroRun 主库存储备份配置、任务记录和审计日志。

### 备份流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    scheduler.py / run_scheduler.py               │
│                      (定时备份调度器)                              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   backup_engine.py                               │
│                    (备份引擎编排)                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌────────────────┐ ┌──────────────────┐
│   dumper.py      │ │ compressor.py  │ │  encryptor.py    │
│   (数据库导出)    │ │  (压缩打包)     │ │  (AES-256-GCM)   │
└────────┬─────────┘ └───────┬────────┘ └────────┬─────────┘
         │                   │                    │
         └───────────────────┼────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     uploader.py                                  │
│                   (多目标存储上传)                                  │
│                  ┌──────────────┐                                │
│                  │  storage/    │                                │
│                  │  sftp.py     │                                │
│                  │  base.py     │                                │
│                  └──────────────┘                                │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     audit.py                                     │
│                    (审计日志记录)                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 恢复流程

```
┌─────────────────────────────────────────────────────────────────┐
│                   restore_engine.py                              │
│                    (恢复引擎编排)                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌────────────────┐ ┌──────────────────┐
│  encryptor.py    │ │ compressor.py  │ │   dumper.py      │
│  (解密)          │ │  (解压)        │ │  (数据库导入)     │
└──────────────────┘ └────────────────┘ └──────────────────┘
```

### 模块结构

| 模块 | 职责 |
|------|------|
| `backup_engine.py` | 备份流程编排引擎，协调各子模块执行备份 |
| `dumper.py` | 数据库导出模块，执行 pg_dump / SQLite dump |
| `compressor.py` | 压缩模块，将备份文件打包压缩 |
| `encryptor.py` | 加密模块，使用 AES-256-GCM 加密备份文件 |
| `uploader.py` | 上传模块，将备份文件上传至远程存储 |
| `restore_engine.py` | 恢复流程编排引擎，协调各子模块执行恢复 |
| `scheduler.py` | 定时任务调度模块 |
| `audit.py` | 审计日志记录模块 |
| `notifier.py` | 备份通知模块 |
| `storage/base.py` | 存储后端抽象基类 |
| `storage/sftp.py` | SFTP 远程存储实现 |

## 目录结构

```
vault/
├── __init__.py              # 插件入口，注册 Hook 与路由
├── routes.py                # 管理后台 API 路由
├── run_scheduler.py         # 调度器启动入口
├── plugin.json              # 插件元数据配置
├── services/
│   ├── __init__.py
│   ├── backup_engine.py     # 备份引擎（流程编排）
│   ├── dumper.py            # 数据库导出模块
│   ├── compressor.py        # 压缩模块
│   ├── encryptor.py         # AES-256-GCM 加密模块
│   ├── uploader.py          # 多目标存储上传模块
│   ├── restore_engine.py    # 恢复引擎（流程编排）
│   ├── scheduler.py         # 定时任务调度模块
│   ├── audit.py             # 审计日志模块
│   ├── notifier.py          # 备份通知模块
│   └── storage/
│       ├── base.py           # 存储后端抽象基类
│       └── sftp.py           # SFTP 远程存储实现
├── migrations/
│   └── 001_initial.sql      # 数据库初始化迁移脚本
├── i18n/
│   ├── en.yml               # 英文国际化
│   └── zh-CN.yml            # 中文国际化
├── static/
│   ├── vault.css            # 管理后台样式
│   └── vault.js             # 管理后台脚本
└── templates/
    └── vault.html           # 管理后台页面模板
```

## 安装与启用

### 安装

插件已包含在 VeroRun 的默认插件目录中，无需额外安装步骤。

### 依赖安装

插件依赖以下 Python 第三方库：

```bash
pip install croniter cryptography paramiko requests
```

| 依赖 | 用途 |
|------|------|
| `croniter` | 解析 cron 表达式，驱动定时备份调度 |
| `cryptography` | 提供 AES-256-GCM 加密/解密能力 |
| `paramiko` | SFTP 远程存储连接与文件传输 |
| `requests` | HTTP 通知发送 |

### 启用

1. 安装上述依赖
2. 运行数据库迁移脚本：

```bash
python -m plugins.vault.migrations.001_initial
```

3. 在 VeroRun 管理后台 "插件管理" 页面中启用 Vault 插件
4. 管理后台 "System" 菜单组将出现 Vault 备份管理入口

### 调度器启动

定时备份调度器需要单独启动：

```bash
python -m plugins.vault.run_scheduler
```

## 配置说明

在 `plugin.json` 中配置以下参数：

```json
{
  "name": "vault",
  "version": "2.0.0",
  "backup": {
    "retention_days": 30,
    "max_backups": 50,
    "temp_dir": "/tmp/verorun_backups"
  },
  "encryption": {
    "algorithm": "AES-256-GCM",
    "key_source": "app_secret_key"
  },
  "scheduler": {
    "enabled": true,
    "default_cron": "0 2 * * *"
  },
  "storage": {
    "default": "local",
    "targets": {
      "local": {
        "path": "data/backups/"
      },
      "sftp": {
        "host": "",
        "port": 22,
        "username": "",
        "key_path": "",
        "remote_path": "/backups/"
      }
    }
  },
  "notification": {
    "on_success": true,
    "on_failure": true,
    "channels": ["email", "site_message"]
  }
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `backup.retention_days` | 备份保留天数 | `30` |
| `backup.max_backups` | 最大保留备份数量 | `50` |
| `backup.temp_dir` | 临时文件目录 | `/tmp/verorun_backups` |
| `encryption.algorithm` | 加密算法 | `AES-256-GCM` |
| `encryption.key_source` | 加密密钥来源 | `app_secret_key` |
| `scheduler.enabled` | 是否启用定时备份 | `true` |
| `scheduler.default_cron` | 默认定时备份 cron 表达式 | `0 2 * * *`（每日凌晨2点） |
| `storage.default` | 默认存储目标 | `local` |
| `storage.targets.local.path` | 本地存储路径 | `data/backups/` |
| `storage.targets.sftp.host` | SFTP 主机地址 | 空 |
| `storage.targets.sftp.port` | SFTP 端口 | `22` |
| `notification.on_success` | 备份成功时通知 | `true` |
| `notification.on_failure` | 备份失败时通知 | `true` |
| `notification.channels` | 通知渠道 | `email, site_message` |

## API 端点

### Hook 提供

| Hook 标识符 | 类型 | 说明 |
|-------------|------|------|
| `vault/create_backup` | Hook | 手动触发一次备份任务 |
| `vault/list_backups` | Hook | 列出所有备份记录 |
| `vault/delete_backup` | Hook | 删除指定备份 |
| `vault/health_check` | Hook | 检查备份系统健康状态 |
| `vault/audit_log` | Hook | 查询备份审计日志 |

### 管理后台 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/admin/vault/` | 备份管理仪表盘（嵌入页面） |
| `POST` | `/api/vault/backup` | 手动触发备份 |
| `GET` | `/api/vault/backups` | 列出备份记录 |
| `GET` | `/api/vault/backups/<id>` | 查看备份详情 |
| `DELETE` | `/api/vault/backups/<id>` | 删除备份 |
| `POST` | `/api/vault/backups/<id>/restore` | 从备份恢复 |
| `GET` | `/api/vault/schedules` | 列出定时备份计划 |
| `POST` | `/api/vault/schedules` | 创建定时备份计划 |
| `PUT` | `/api/vault/schedules/<id>` | 更新定时备份计划 |
| `DELETE` | `/api/vault/schedules/<id>` | 删除定时备份计划 |
| `GET` | `/api/vault/audit` | 查询审计日志 |

### 管理后台

| 菜单项 | 分组 | 说明 |
|--------|------|------|
| `Vault` | `System` | 备份管理（嵌入 URL：`/admin/vault/`） |

## 依赖关系

### 内部依赖

- VeroRun 核心框架：Hook 系统、路由注册、调度器
- 管理后台（auth-center）：仪表盘嵌入与菜单渲染
- **email** 插件：邮件通知渠道

### 外部依赖

| 依赖 | 版本要求 | 用途 |
|------|----------|------|
| `croniter` | >= 1.0 | cron 表达式解析 |
| `cryptography` | >= 3.0 | AES-256-GCM 加密 |
| `paramiko` | >= 2.7 | SFTP 远程连接 |
| `requests` | >= 2.25 | HTTP 通知 |

### 被依赖

- 系统运维：数据备份与恢复操作
- 数据库管理：数据库级备份与恢复

## 许可证

本插件为 VeroRun 项目的一部分，遵循 VeroRun 项目的整体许可证协议。