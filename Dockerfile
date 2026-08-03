# ============================================================
# 易站AI — 独立部署 Docker 镜像
# 单容器运行所有服务（platform/admin/auth-center/captcha）
# ============================================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx-light supervisor curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ── 运行时镜像 ──
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx-light supervisor curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从 builder 复制 Python 包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制项目代码（排除不需要的文件）
COPY . /app/
RUN rm -rf /app/__pycache__ /app/.* 2>/dev/null; \
    find /app -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; \
    find /app -name '*.pyc' -delete

# Nginx 配置
COPY deploy/nginx.conf /etc/nginx/sites-enabled/default

# Supervisor 配置
COPY deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 入口脚本
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 数据卷
VOLUME ["/app/data"]

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
