#!/bin/bash
set -e
cd /home/easykai/easykai-workspace/easykai.cn/admin
export JWT_SECRET=30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d
TK=$(python3 -c '
import sys,os
os.environ["JWT_SECRET"]="30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d"
sys.path=["/home/easykai/easykai-workspace/easykai.cn/admin","/home/easykai/easykai-workspace/easykai.cn/auth-center","/home/easykai/easykai-workspace/easykai.cn"]+sys.path
os.chdir("/home/easykai/easykai-workspace/easykai.cn/admin")
from services.jwt_service import create_token
print(create_token(1,phone="13910604299",is_admin=True))
')
echo "TOKEN: ${TK:0:40}..."

echo ""
echo "=== /admin/dashboard ==="
curl -s -m 10 -H "Authorization: Bearer $TK" http://127.0.0.1:8084/admin/dashboard | head -c 400

echo ""
echo "=== /admin/users ==="
curl -s -m 10 -H "Authorization: Bearer $TK" http://127.0.0.1:8084/admin/users | head -c 400

echo ""
echo "=== /admin/agents ==="
curl -s -m 10 -H "Authorization: Bearer $TK" http://127.0.0.1:8084/admin/agents | head -c 400
