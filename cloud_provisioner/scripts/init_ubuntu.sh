#!/bin/bash
# init_ubuntu.sh — Ubuntu 容器初始化脚本
# 模板变量: {{ROOT_PASSWORD}} {{CONTAINER_NAME}} {{INSTANCE_ID}}

set -e

echo "=== 开始初始化 (Instance: {{INSTANCE_ID}}, Container: {{CONTAINER_NAME}}) ==="

# 设置 root 密码
echo "root:{{ROOT_PASSWORD}}" | chpasswd

# 配置 SSH
sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
service ssh restart

# 系统更新
apt update -qq && apt upgrade -y -qq
apt install -y -qq curl wget git vim htop net-tools ufw

# 安装 Nginx
apt install -y -qq nginx
systemctl enable nginx
systemctl start nginx

# 安装 Certbot (SSL)
apt install -y -qq certbot python3-certbot-nginx

# 安装 Python
apt install -y -qq python3 python3-pip python3-venv

# 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y -qq nodejs

# 安装 Docker (容器内可选)
# curl -fsSL https://get.docker.com | bash || true

# 安装 Docker Compose
# curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
# chmod +x /usr/local/bin/docker-compose

# 配置 UFW 防火墙
ufw --force disable  # Docker 环境下跳过防火墙

# 创建部署用户
useradd -m -s /bin/bash deploy || true
echo "deploy:{{ROOT_PASSWORD}}" | chpasswd
usermod -aG sudo deploy || true

# 创建网站目录
mkdir -p /var/www/html
chown -R www-data:www-data /var/www

# 配置 Nginx 默认站点
cat > /etc/nginx/sites-available/default << 'NGINX_EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.html index.htm index.php;

    server_name _;

    location / {
        try_files $uri $uri/ =404;
    }

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
}
NGINX_EOF

# 创建默认页面
cat > /var/www/html/index.html << 'HTML_EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>开通成功！</title>
    <style>
        body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#0a0a0a;color:#e0e0e0}
        .card{text-align:center;padding:60px 40px;max-width:500px}
        .check{font-size:64px;color:#22c55e;margin-bottom:20px}
        h1{font-size:28px;margin-bottom:12px}
        p{color:#888;line-height:1.6;margin-bottom:8px}
        .info{background:rgba(255,255,255,0.04);border-radius:8px;padding:16px;margin-top:24px;font-size:13px;text-align:left}
        .info code{color:#00f5ff}
    </style>
</head>
<body>
    <div class="card">
        <div class="check">✅</div>
        <h1>云服务器开通成功！</h1>
        <p>您的云服务器已准备就绪，可以使用 SSH 连接管理。</p>
        <div class="info">
            <p>📌 <strong>连接信息</strong></p>
            <p>SSH: <code>ssh root@<服务器IP> -p <SSH端口></code></p>
            <p>Web: <code>http://<服务器IP>:<HTTP端口></code></p>
            <p>请立即修改默认密码以保障安全。</p>
        </div>
        <p style="font-size:11px;color:#555;margin-top:32px">由 易站AI 云服务平台自动开通</p>
    </div>
</body>
</html>
HTML_EOF

systemctl reload nginx || true

echo "=== 初始化完成 ==="
echo "SSH: root@<host>"
echo "Password: {{ROOT_PASSWORD}}"
