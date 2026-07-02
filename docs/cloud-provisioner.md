# Cloud Provisioner — 云服务自动开通引擎

## 概述 (Overview)

**Cloud Provisioner** 是易站智能建站系统 (easykai.cn) 的核心引擎之一，负责实现 **订单支付 → 自动开通云资源** 的全自动化流程。

当用户在商城购买云服务器 (Cloud VPS)、对象存储 (OSS)、CDN 等云服务类商品并完成支付后，Provisioner 会自动创建对应的底层资源（Docker 容器 / 云 API 实例），执行初始化脚本部署建站环境，并将连接信息（IP、端口、密码等）返回给用户。

```
用户下单 → 支付成功 → Provisioner Engine → Provider Adapter → 创建资源 → 初始化 → 通知用户
```

---

## 目录结构 (File Tree)

```
cloud_provisioner/
├── __init__.py          # 模块入口，暴露 ProvisionerEngine 和 provisioner_bp
├── engine.py            # 开通编排核心 (ProvisionerEngine)
├── models.py            # 数据库模型 (cloud_instances, provision_logs)
├── routes.py            # API 路由 (/cloud/*, /admin/cloud/*)
├── providers/
│   ├── __init__.py      # Provider 工厂函数 get_provider()
│   ├── base.py          # 抽象基类 BaseProvider
│   └── template.py      # 模板化开通适配器 TemplateProvider (Docker)
└── scripts/
    ├── init_ubuntu.sh   # Ubuntu 容器初始化脚本
    └── init_centos.sh   # CentOS 容器初始化脚本
```

---

## 架构 (Architecture)

三层解耦设计：**ProvisionerEngine → Provider Adapter → Cloud Resource**

```
┌─────────────────────────────────────────────────────────┐
│                    ProvisionerEngine                     │
│                    (engine.py)                           │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐ │
│  │validate  │ │provision │ │poll    │ │update &      │ │
│  │config    │→│resource  │→│status  │→│notify user   │ │
│  └─────────┘ └──────────┘ └────────┘ └──────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ calls
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 Provider Adapter Layer                   │
│                    (providers/)                          │
│                                                         │
│   BaseProvider (抽象基类, base.py)                       │
│       ▲                    ▲                             │
│       │                    │                             │
│  TemplateProvider     AliyunProvider                     │
│  (template.py)        (预留, 未实现)                     │
│  Docker 容器开通       云 API 直连                       │
└────────────────────────┬────────────────────────────────┘
                         │ creates
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Cloud Resource                         │
│                                                         │
│   Docker 容器 / 云厂商 ECS 实例                          │
│   + 连接信息 (IP, 端口, 密码)                            │
│   + 初始化脚本 (建站环境)                                │
└─────────────────────────────────────────────────────────┘
```

### ProvisionerEngine (`cloud_provisioner/engine.py`)

编排核心，定义了完整的开通流程：

| 步骤 | 方法 | 说明 |
|------|------|------|
| 0 | `create_instance()` | 在数据库创建 `cloud_instances` 记录，状态为 `pending` |
| 1 | `provider.validate_config()` | 验证规格参数（CPU/内存/磁盘）是否合法 |
| 2 | `provider.provision()` | 调用适配器创建实际资源 |
| 3 | 轮询 `provider.get_status()` | 等待资源进入 `running` 状态 |
| 4 | `update_instance()` | 更新连接信息、资源 ID、状态 |
| 5 | `add_log()` | 记录完整开通日志 |

核心方法：

- `provision(order_data)` — 执行自动开通全流程
- `get_status(instance_id)` — 查询实例状态（优先查 Provider 实时状态）
- `terminate(instance_id)` — 销毁实例及其底层资源

支持通过 `shop_admin.py` 中的订单支付回调自动触发，也支持管理员手动重试和销毁。

### Provider 适配器层 (`providers/`)

#### BaseProvider (`cloud_provisioner/providers/base.py`)

抽象基类，所有云厂商适配器必须实现的方法：

| 方法 | 签名 | 说明 |
|------|------|------|
| `validate_config()` | `(config) → (bool, str)` | 验证配置合法性 |
| `provision()` | `(instance_id, specs, log_callback) → dict` | 创建云资源，返回 `{resource_id, connect_info, extra}` |
| `get_status()` | `(resource_id) → str` | 查询资源实时状态 |
| `terminate()` | `(resource_id) → bool` | 销毁资源 |
| `get_console_url()` | `(resource_id) → str` | （可选）管理面板链接 |
| `estimate_cost()` | `(specs) → dict` | （可选）预估费用 |

#### TemplateProvider (`cloud_provisioner/providers/template.py`)

当前生产环境使用的适配器，基于 Docker 容器实现"模板化开通"：

1. **拉取镜像** — `docker pull ubuntu:22.04`（支持自定义镜像）
2. **分配端口** — 在宿主机上查找空闲端口，映射到容器的 22/80/443 等端口
3. **创建容器** — `docker run` 设置 CPU、内存限制，配置端口映射
4. **执行初始化脚本** — 将 `init_ubuntu.sh` / `init_centos.sh` 注入容器执行，设置 root 密码、SSH 配置、安装建站环境
5. **返回连接信息** — 包含容器 IP、映射端口、用户名/密码

配置项（通过 `system_config` 管理）：

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `cloud.template.host` | `127.0.0.1` | 宿主机 IP |
| `cloud.template.ssh_user` | `root` | SSH 用户 |
| `cloud.template.ssh_key` | — | SSH 私钥路径 |
| `cloud.template.docker_cmd` | `/usr/bin/docker` | Docker 命令路径 |

当前支持的规格约束：CPU 1‑32 核、内存 0.5‑64 GB、磁盘 5‑500 GB。

#### AliyunProvider / TencentProvider (预留)

在 `providers/__init__.py` 的 `get_provider()` 工厂函数中预留了 `aliyun`、`tencent`、`baidu` 类型，未来通过云厂商 API 直连实现 ECS 实例创建（需合作伙伴资质）。

---

## 数据库 (Database)

两张表均在 `cloud_provisioner/models.py` 的 `init_tables()` 中幂等创建。

### cloud_instances

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 实例 ID |
| `order_id` | TEXT | 关联订单号 |
| `user_id` | INTEGER | 所属用户 |
| `product_id` | INTEGER | 关联商品 ID |
| `product_title` | TEXT | 商品名称 |
| `provider` | TEXT | 适配器类型: `template` / `aliyun` / `tencent` / `baidu` |
| `service_type` | TEXT | 服务类型: `vps` / `oss` / `cdn` / `rds` / `domain` / `ssl` |
| `region` | TEXT | 区域 (默认 `auto`) |
| `specs` | TEXT(JSON) | 规格配置: `{"cpu":1,"memory_gb":2,"disk_gb":20}` |
| `resource_id` | TEXT | 云厂商资源 ID 或 Docker 容器名 |
| `connect_info` | TEXT(JSON) | 连接信息: `{"ip":"","ports":{},"username":"","password":""}` |
| `status` | TEXT | 状态: `pending` / `provisioning` / `running` / `stopped` / `terminated` / `failed` |
| `provision_log` | TEXT | 开通日志摘要 |
| `expire_at` | TEXT | 到期时间 |
| `auto_renew` | INTEGER | 自动续费标志 |
| `metadata` | TEXT(JSON) | 扩展元数据 |
| `created_at` | TEXT | 创建时间 |
| `updated_at` | TEXT | 更新时间 |

索引：`user_id`、`order_id`、`status`。

### provision_logs

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 日志 ID |
| `instance_id` | INTEGER | 关联实例 |
| `step` | TEXT | 步骤: `validate` / `create_resource` / `wait_ready` / `run_script` / `notify` |
| `status` | TEXT | 步骤状态: `running` / `success` / `failed` |
| `message` | TEXT | 步骤消息 |
| `duration_ms` | INTEGER | 耗时(毫秒) |
| `raw_output` | TEXT | 原始输出 |
| `created_at` | TEXT | 记录时间 |

---

## API 路由 (API Routes)

所有路由注册在 `provisioner_bp` (Blueprint, url_prefix=`/cloud`)，通过 `cloud_provisioner/__init__.py` 的 `init_provisioner(app)` 注册到 Flask 应用。

### 用户端 API

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/cloud/products` | 无需 | 列出所有云服务类型商品 (`product_type='cloud_service'`) |
| GET | `/cloud/instances` | JWT | 当前用户的云资源列表 |
| GET | `/cloud/instances/<id>` | JWT | 实例详情（含开通日志） |
| GET | `/cloud/instances/<id>/status` | JWT | 查询实例实时状态 |

### 管理端 API

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/cloud/instances/provision` | Admin | 手动触发/重试开通 |
| POST | `/cloud/instances/<id>/terminate` | Admin | 销毁实例 |
| GET | `/cloud/admin/instances` | Admin | 查看所有实例（支持 `?status=` 筛选，关联用户信息） |
| POST | `/cloud/admin/products` | Admin | 创建云服务商品 |

认证方式：`Authorization: Bearer <JWT>`。

---

## 开通流程 (Provision Flow)

一次完整的自动开通包含以下步骤：

```
 订单支付成功 (shop_admin.py)
         │
         ▼
  ┌────────────────┐
  │ 1. 验证配置     │  provider.validate_config(specs)
  │    (validate)   │  CPU/内存/磁盘范围检查
  └───────┬────────┘
          │ valid
          ▼
  ┌────────────────┐
  │ 2. 创建实例记录 │  INSERT INTO cloud_instances (status='pending')
  │    (create)     │
  └───────┬────────┘
          │
          ▼
  ┌────────────────┐
  │ 3. 选择 Provider│  get_provider('template', config)
  │    (select)     │  根据 product_config 确定适配器类型
  └───────┬────────┘
          │
          ▼
  ┌────────────────┐
  │ 4. 执行开通     │  provider.provision(instance_id, specs)
  │    (provision)  │
  │    ├─ docker pull 镜像        │
  │    ├─ 分配空闲端口              │
  │    ├─ docker run 创建容器       │
  │    ├─ 注入并执行 init 脚本      │
  │    └─ 返回 connect_info        │
  └───────┬────────┘
          │ success
          ▼
  ┌────────────────┐
  │ 5. 轮询状态     │  provider.get_status(resource_id)
  │    (poll)       │  确认资源已 running
  └───────┬────────┘
          │
          ▼
  ┌────────────────┐
  │ 6. 更新 DB     │  UPDATE cloud_instances
  │    (update)    │  status='running', connect_info=..., resource_id=...
  └───────┬────────┘
          │
          ▼
  ┌────────────────┐
  │ 7. 通知完成     │  日志记录完成，API 返回连接信息
  │    (notify)    │  用户可在实例列表查看 IP/端口/密码
  └────────────────┘
```

---

## 集成点 (Integration)

### 商城订单支付回调

在 `auth-center/routes/shop_admin.py`（约第 1370‑1401 行）中，当订单支付确认成功且商品类型为 `cloud_service` 时，自动触发异步开通：

```python
from cloud_provisioner.engine import ProvisionerEngine

engine = ProvisionerEngine()
order_data = {
    'order_id': row['order_id'],
    'user_id': row['user_id'],
    'product_id': row['product_id'],
    'product_config': product_config,
    'service_type': product_config.get('service_type', 'vps'),
    'provider': 'template',
    # ...
}

# 异步开通，不阻塞订单确认响应
threading.Thread(target=_provision_async, daemon=True).start()
```

开通结果通过日志打印，无阻塞同步等待。

### 模块初始化

在 `cloud_provisioner/__init__.py` 的 `init_provisioner(app)` 中：

- 调用 `init_tables()` 幂等创建数据库表
- 注册 `/cloud/*` 和 `/admin/cloud/*` 路由到 Flask 应用
- 返回 `ProvisionerEngine` 和 `provisioner_bp` 供外部使用

---

## 部署脚本 (Deployment Scripts)

| 文件 | 目标系统 | 功能 |
|------|----------|------|
| `cloud_provisioner/scripts/init_ubuntu.sh` | Ubuntu (Debian 系) | 设置 root 密码、配置 SSH 允许密码登录、apt 更新、安装 curl/wget/git/vim/htop/net-tools/ufw 等基础工具 |
| `cloud_provisioner/scripts/init_centos.sh` | CentOS (RHEL 系) | 同上，但使用 yum 包管理器，安装 nginx/python3/nodejs 等建站组件 |

脚本通过 Docker `docker cp` 注入容器后由 `bash /tmp/setup.sh` 执行。支持模板变量替换：`{{ROOT_PASSWORD}}`、`{{CONTAINER_NAME}}`、`{{INSTANCE_ID}}`。

---

## 当前状态与路线图 (Status & Roadmap)

| 阶段 | 状态 | 说明 |
|------|------|------|
| **Phase 1** — 模板化开通 | ✅ 已完成 | Docker 容器模板化开通，零云厂商资质要求，适合初期运营 |
| **Phase 2** — 云 API 直连 | 📋 已规划 | 对接阿里云 / 腾讯云 / 百度云 API，实现真实的 ECS、OSS、CDN 资源创建 |
| **Phase 3** — AI 赋能 | 🔮 规划中 | 通过 Shop Agent / 口令控制台自然语言指令开通资源 |

当前所有云服务商品均由 `TemplateProvider` 基于 Docker 处理，适用于中小规模建站场景。
