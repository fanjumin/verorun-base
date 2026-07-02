#!/bin/bash
# init_centos.sh — CentOS 容器初始化脚本
# 模板变量: {{ROOT_PASSWORD}} {{CONTAINER_NAME}} {{INSTANCE_ID}}

set -e

echo "=== 开始初始化 CentOS (Instance: {{INSTANCE_ID}}) ==="

# 设置 root 密码
echo "{{ROOT_PASSWORD}}" | passwd --stdin root

# 配置 SSH
sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart sshd

# 系统更新
yum update -y -q
yum install -y -q epel-release
yum install -y -q curl wget git vim htop net-tools nginx

# 安装 Python
yum install -y -q python3 python3-pip

# 安装 Node.js
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
yum install -y -q nodejs

# 配置 Nginx
systemctl enable nginx
systemctl start nginx

# 创建网站目录
mkdir -p /var/www/html

# 配置防火墙
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload || true

echo "=== 初始化完成 ==="
