#!/bin/bash
curl -s 'http://localhost:8084/admin?token=test' -o /tmp/admin_render.html
python3 /home/easykai/easykai-workspace/easykai.cn/check_js.py
