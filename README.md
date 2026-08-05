# VeroRun Base

VeroRun 系统底座 —— 一个最小化、可安装的系统基础框架。

内置必要的核心模块，其余所有功能按需从插件商店安装。只装你需要的，不装你不想要的。

## 内置模块

| 模块 | 说明 |
|------|------|
| 邮箱验证 | 用户注册、密码重置 |
| 验证码 | 防机器人安全保护 |
| OAuth 登录 | 社交账号登录（Google / Facebook / 微信 / Telegram 等） |
| 备份恢复 | 数据自动备份与恢复 |
| 版权保护 | VeroGuard 运行时保护（编译为二进制，不可修改） |
| 插件管理器 | 内置插件生命周期管理 + 商店 |

## 商店可选模块

VeroRun Base 不包含以下模块，但你可以从内置商店免费或付费获取：

- 支付（支付宝 / 微信 / Stripe / PayPal）
- 短信验证
- 订阅管理
- 健康监控（CPU / 内存 / 磁盘 / API 告警 + AI 修复）
- AI 聊天机器人
- 内容工厂
- 数据分析
- 广告系统
- 评论系统
- 优惠券引擎
- 即时通讯网关
- 物流对接
- 供应链对接（1688）
- 社交推送

## 安装

**一键安装（Ubuntu 22.04/24.04）：**

```bash
curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh | sudo bash -s -- install your-domain.com
```

或通过 git clone：

```bash
git clone https://github.com/fanjumin/verorun-base.git
cd verorun-base
sudo bash deploy/install.sh install your-domain.com
```

中国区部署加 `--region=cn`。详见 [deploy/README.md](deploy/README.md)。

安装脚本会自动：安装 PostgreSQL 与依赖、创建 `verorun` 系统用户、生成 `.env`（自动密钥）、创建 5 个 systemd 服务（main / auth / admin / health / guardian）、配置 Nginx。

## 许可证

本项目使用 [VeroRun Base EULA v1.0](LICENSE)。

- 你可以查看和修改可见源码，用于自己的业务
- 编译的二进制组件（VeroGuard 等）**不可逆向、不可反编译**
- 生产商用部署需要商业授权
- 不得转售或重新分发

商业授权请联系：https://verorun.com

## 版本

当前版本：**v0.49.0**。

verorun-base 由 [verorun-code](https://github.com/fanjumin/verorun-code)（私有仓库）在每次发布版本 tag 时通过 CI 自动同步生成，内置插件从插件商店安装。
