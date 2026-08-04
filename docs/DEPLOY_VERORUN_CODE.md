# VeroRun Code — 开发版部署指南

## 版本说明

| 仓库 | 类型 | 内容 | 用途 |
|------|------|------|------|
| `verorun-code` | **私人** | 完整源码 + 全部插件 | 官方开发版 |
| `verorun-base` | 公开 | 系统基座 + 编译二进制，不含插件 | 专业版（对外分发） |

本文档仅适用于 **verorun-code（开发版）**。

---

## 前置条件

- Ubuntu 20.04+ / Debian 11+
- Python 3.8+
- 服务器 1.6GB+ 内存
- 一个 GitHub 账号（需要访问 `fanjumin/verorun-code` 私人仓库）

---

## 首次安装

### 1. 获取 install.sh

由于 `verorun-code` 是私人仓库，无法直接 `curl | bash`。需要先将 `install.sh` 上传到服务器：

**方式一：scp（本地已有克隆）**
```bash
scp deploy/install.sh user@your-server:~/install.sh
```

**方式二：手动复制内容**
在服务器上创建 `install.sh`，粘贴 `deploy/install.sh` 的完整内容。

### 2. 运行安装脚本（首次生成 SSH Deploy Key）

```bash
sudo bash install.sh
```

脚本会自动：
- 在 `/root/.ssh/` 生成 ED25519 SSH 密钥对
- 打印公钥内容
- 提示你将其添加到 GitHub，然后退出

预期输出类似：
```
[i] Generating SSH deploy key for git operations...
╔══════════════════════════════════════════════════════════════╗
║  ADD THIS DEPLOY KEY TO GITHUB (one-time setup):           ║
╠══════════════════════════════════════════════════════════════╣
║  URL: https://github.com/fanjumin/verorun-code/settings/keys/new
╠══════════════════════════════════════════════════════════════╣
║  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... verorun-deploy-xxx
╚══════════════════════════════════════════════════════════════╝
[WARN] After adding the key, re-run this script to continue.
```

### 3. 添加 Deploy Key 到 GitHub

1. 复制终端中打印的公钥内容（`ssh-ed25519 AAAAC3Nza...` 开头的那一行）
2. 打开 https://github.com/fanjumin/verorun-code/settings/keys/new
3. **Title**：填写服务器标识（如 `instance-20260731-045222`）
4. **Key**：粘贴公钥
5. 点击 **Add key**

### 4. 重新运行安装

```bash
sudo bash install.sh
```

这次脚本会：
- 检测到 SSH key 已存在
- 添加 `github.com` 到 `known_hosts`
- 通过 SSH 克隆 `verorun-code` 到 `/home/<user>/verorun`
- 安装依赖、配置 systemd、配置 Nginx
- 启动所有服务

### 5. 配置域名

```bash
sudo bash deploy/install.sh configure-domain your-domain.com
```

---

## 日常更新

### 自动更新

```bash
sudo bash deploy/install.sh update
```

脚本会自动：
1. 确保 SSH 认证正常（`ensure_git_auth`）
2. 备份当前版本
3. 恢复本地修改的文件
4. `git fetch` + `git merge` 拉取最新代码
5. 更新 Python 依赖
6. 同步 `.env` 配置
7. 重启所有服务

### 重启服务

```bash
sudo bash deploy/install.sh restart
```

### 健康检查

```bash
sudo bash deploy/install.sh health
```

---

## 已有服务器手动配置 SSH（首次）

如果服务器已经安装过 verorun-code，但 git remote 是 HTTPS，需要手动切换：

```bash
# 1. 生成 SSH key
sudo ssh-keygen -t ed25519 -N "" -f /root/.ssh/id_ed25519 -C "verorun-deploy-$(hostname)"

# 2. 打印公钥，复制到 GitHub
sudo cat /root/.ssh/id_ed25519.pub
# → 添加到 https://github.com/fanjumin/verorun-code/settings/keys/new

# 3. 修复 known_hosts 权限
sudo touch /root/.ssh/known_hosts
sudo chmod 644 /root/.ssh/known_hosts

# 4. 添加 github.com 到 known_hosts
sudo ssh-keyscan github.com >> /root/.ssh/known_hosts

# 5. 切换 git remote 为 SSH
cd ~/verorun && sudo git remote set-url origin git@github.com:fanjumin/verorun-code.git

# 6. 测试连接
sudo git fetch origin master
```

之后 `sudo bash deploy/install.sh update` 即可正常使用。

---

## 发布插件到 verorun-store

```bash
# 设置 GitHub Token（需要 repo 权限）
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# 发布插件
python tools/publish_plugin.py <plugin_identifier>

# 指定版本
python tools/publish_plugin.py analytics --version 2.1.0
```

插件发布后，verorun-base 用户在插件商店中即可看到并安装。

---

## 服务拓扑

| 服务 | 端口 | 说明 |
|------|------|------|
| verorun-main | 8081 | 主站后端 |
| verorun-auth | 8083 | 认证/订阅 |
| verorun-admin | 8084 | 管理后台 |

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GIT_REPO` | `git@github.com:fanjumin/verorun-code.git` | Git 仓库地址 |
| `GIT_BRANCH` | `master` | 分支 |
| `APP_USER` | `$SUDO_USER` | 应用运行用户 |
| `APP_HOME` | `/home/$APP_USER/verorun` | 应用目录 |
| `DOMAIN` | — | 部署域名 |
| `REGION` | `global` | `cn` 或 `global` |
| `GITHUB_TOKEN` | — | 发布插件时使用 |
| `VERORUN_STORE_CATALOG_URL` | GitHub Raw URL | 商店目录地址 |