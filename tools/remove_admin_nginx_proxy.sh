#!/bin/bash
# ============================================================
# remove_admin_nginx_proxy.sh
# 移除 easykai.cn /admin/ → 8084 的 Nginx 代理配置
# 执行后管理后台仅能通过配置的域名（如 agent.easykai.cn）访问
# ============================================================
set -euo pipefail

NGINX_CONF="/etc/nginx/sites-enabled/easykai.conf"
BACKUP_DIR="/etc/nginx/backups"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 开始移除 easykai.cn /admin/ Nginx 代理配置${NC}"
echo ""

# 检查 root 权限
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}❌ 请使用 sudo 或 root 用户执行本脚本${NC}"
    echo "   sudo bash $0"
    exit 1
fi

# 检查配置文件是否存在
if [[ ! -f "$NGINX_CONF" ]]; then
    echo -e "${RED}❌ 未找到 Nginx 配置文件: $NGINX_CONF${NC}"
    echo "   请确认路径是否正确"
    exit 1
fi

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 生成备份文件名（含时间戳）
BACKUP_FILE="$BACKUP_DIR/easykai.conf.bak.$(date +%Y%m%d_%H%M%S)"
cp "$NGINX_CONF" "$BACKUP_FILE"
echo -e "${GREEN}✅ 备份已创建: $BACKUP_FILE${NC}"

# 统计要删除的行数
TARGET_LINES=$(grep -n "location /admin/" "$NGINX_CONF" | head -1 | cut -d: -f1)

if [[ -z "$TARGET_LINES" ]]; then
    echo -e "${YELLOW}⚠️  未在 $NGINX_CONF 中找到 'location /admin/' 配置，可能已被移除${NC}"
    echo -e "${YELLOW}⚠️  跳过修改，直接验证 Nginx 配置${NC}"
else
    echo -e "${YELLOW}📝 在文件第 $TARGET_LINES 行附近找到 location /admin/ block，正在注释...${NC}"

    # 安全做法：注释而非删除，便于回滚
    # 从 "location /admin/" 开始到下一个 "}" 结束（不嵌套的 location block）
    python3 -c "
import re

with open('$NGINX_CONF', 'r') as f:
    content = f.read()
    lines = content.split('\n')

# 找到第一个 location /admin/ 区块
new_lines = []
in_block = False
brace_depth = 0
block_start = -1
commented = 0

for i, line in enumerate(lines):
    stripped = line.strip()
    if not in_block and stripped.startswith('location /admin/'):
        in_block = True
        block_start = i
        new_lines.append('# ' + line.rstrip() + '  # [commented by remove_admin_nginx_proxy.sh]')
        commented += 1
        continue

    if in_block:
        brace_count = stripped.count('{') - stripped.count('}')
        brace_depth += brace_count
        new_lines.append('# ' + line.rstrip())
        commented += 1
        if brace_depth <= 0:
            # Block closed — stop commenting
            in_block = False
            brace_depth = 0
            continue

    if not in_block:
        new_lines.append(line)

output = '\n'.join(new_lines)
with open('$NGINX_CONF', 'w') as f:
    f.write(output)

print(f'已注释 {commented} 行 (location /admin/ block)')
" || {
    echo -e "${RED}❌ Python 脚本执行失败${NC}"
    echo -e "${YELLOW}⚠️  正在恢复备份...${NC}"
    cp "$BACKUP_FILE" "$NGINX_CONF"
    echo -e "${GREEN}✅ 已恢复备份${NC}"
    exit 1
}
fi

echo ""

# 验证 Nginx 配置语法
echo -e "${YELLOW}🔍 验证 Nginx 配置语法...${NC}"
if nginx -t 2>&1; then
    echo -e "${GREEN}✅ Nginx 配置语法正确${NC}"
else
    echo -e "${RED}❌ Nginx 配置语法错误，正在回滚...${NC}"
    cp "$BACKUP_FILE" "$NGINX_CONF"
    echo -e "${GREEN}✅ 已恢复备份至: $NGINX_CONF${NC}"
    exit 1
fi

echo ""

# 重载 Nginx
echo -e "${YELLOW}🔄 重载 Nginx...${NC}"
if systemctl reload nginx 2>/dev/null || nginx -s reload 2>/dev/null; then
    echo -e "${GREEN}✅ Nginx 已重载${NC}"
else
    echo -e "${RED}❌ Nginx 重载失败，请手动执行: systemctl reload nginx${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅  完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}📌 管理后台已禁止通过 easykai.cn/admin/ 访问${NC}"
echo -e "${YELLOW}📌 请通过 agent.easykai.cn 或在系统设置中配置的域名访问${NC}"
echo -e "${YELLOW}📌 如需回滚: cp $BACKUP_FILE $NGINX_CONF && systemctl reload nginx${NC}"
