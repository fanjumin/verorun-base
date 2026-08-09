# VeroRun Code — 开发版部署指南

## 版本说明

| 仓库 | 类型 | 内容 | 用途 | 默认部署脚本 |
|------|------|------|------|--------------|
| `verorun-base` | 公开 | 系统基座，不含插件 | 专业版（对外分发）+ 本地/LAN 部署 | `install.sh`（HTTPS，无需 SSH Key）<br>`install-local.sh`（HTTPS，本地/LAN 无域名） |
| `verorun-code` | **私人** | 完整源码 + 全部插件 | 官方开发版 / 团队内网 | `install-dev.sh`（SSH，不含 plugins）<br>`install-code.sh`（SSH，含全部 plugins） |

本文档覆盖 **verorun-base（公开版）** 与 **verorun-code（开发版）** 两种部署方式。

---

## 前置条件

- Ubuntu 20.04+ / Debian 11+
- Python 3.8+
- 服务器 1.6GB+ 内存
- 一个 GitHub 账号（需要访问 `fanjumin/verorun-code` 私人仓库）

---

## 首次安装（公开版 verorun-base）

`deploy/install.sh` 现在**默认从公开仓库 HTTPS 克隆**，无需 SSH Key。

**方式一：HTTPS 克隆后本地运行（推荐）**
```bash
git clone https://github.com/fanjumin/verorun-base.git
cd verorun-base
sudo bash deploy/install.sh install your-domain.com
```

**方式二：一键安装**
> `install.sh` 支持 `curl | sudo bash` 管道一键部署：脚本从 stdin 执行时会自动从
> `verorun-base` 拉取 `deploy/lib/common.sh` 公共函数库，无需预装 git。
```bash
curl -sSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh | sudo bash
```

脚本会自动（**不生成 SSH Key**）：
- 通过 HTTPS 克隆 `verorun-base` 到 `/home/<user>/verorun`
- 安装依赖、配置 systemd、配置 Nginx
- 启动所有服务

### 配置域名

```bash
sudo bash deploy/install.sh configure-domain your-domain.com
```

---

## 开发版 verorun-code（SSH，可选）

需要部署私人仓库 `verorun-code`（含全部插件）时，使用以下脚本之一：

- **install-dev.sh**（开发者工作站，不含 plugins）：<br>`GIT_REPO=git@github.com:fanjumin/verorun-code.git`，sparse-checkout 排除 plugins/，克隆体积约减 50%
- **install-code.sh**（团队内网，含全部 plugins）：<br>`GIT_REPO=git@github.com:fanjumin/verorun-code.git`，sparse-checkout 包含所有目录

1. 将 `install-dev.sh` 上传到服务器：
   ```bash
   scp deploy/install-dev.sh user@your-server:~/
   ```
2. 首次运行，脚本自动在 `/root/.ssh/` 生成 ED25519 SSH 密钥对并打印公钥，然后退出：
   ```bash
   sudo bash install-dev.sh install
   ```
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
3. 添加 Deploy Key 到 GitHub：
   - 复制终端中打印的公钥内容（`ssh-ed25519 AAAAC3Nza...` 开头的那一行）
   - 打开 https://github.com/fanjumin/verorun-code/settings/keys/new
   - **Title**：填写服务器标识（如 `instance-20260731-045222`）
   - **Key**：粘贴公钥，点击 **Add key**
4. 重新运行安装，脚本会通过 SSH 克隆 `verorun-code` 到 `/home/<user>/verorun`：
   - 检测到 SSH key 已存在
   - 添加 `github.com` 到 `known_hosts`
   - 安装依赖、配置 systemd、配置 Nginx
   - 启动所有服务

---

## 日常更新

### 自动更新

```bash
sudo bash deploy/install.sh update
```

脚本会自动：
1. 确保 git 认证正常（`ensure_git_auth`；HTTPS 公开仓库自动跳过 SSH 设置）
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

## 已有服务器切换仓库来源（可选）

### 切换为 HTTPS（公开版 verorun-base）

`install.sh` 默认即 HTTPS，无需任何操作。若当前是 SSH 仓库需切回公开版：

```bash
cd ~/verorun && sudo git remote set-url origin https://github.com/fanjumin/verorun-base.git
sudo bash deploy/install.sh update
```

### 切换为 SSH（私有 verorun-code，开发者可选）

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
| `GIT_REPO` | `https://github.com/fanjumin/verorun-base.git`（install.sh / install-local.sh）<br>`git@github.com:fanjumin/verorun-code.git`（install-dev.sh / install-code.sh） | Git 仓库地址 |
| `GIT_BRANCH` | `master` | 分支 |
| `APP_USER` | `$SUDO_USER` | 应用运行用户 |
| `APP_HOME` | `/home/$APP_USER/verorun` | 应用目录 |
| `DOMAIN` | — | 部署域名 |
| `REGION` | `global` | `cn` 或 `global` |
| `GITHUB_TOKEN` | — | 发布插件时使用 |
| `VERORUN_STORE_CATALOG_URL` | GitHub Raw URL | 商店目录地址 |