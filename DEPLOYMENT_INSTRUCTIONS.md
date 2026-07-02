部署说明
========

已创建的文件：
- platform/routes/api_v1.py（新的API端点）
- platform/app.py（已更新以注册API蓝图）

部署到服务器的步骤：

1. 确保SSH访问：
   ssh easykai@100.124.0.103

2. 上传文件：
   scp platform/routes/api_v1.py easykai@100.124.0.103:/home/easykai/easykai-workspace/easykai.cn/platform/routes/
   scp platform/app.py easykai@100.124.0.103:/home/easykai/easykai-workspace/easykai.cn/platform/

3. 重启平台服务：
   ssh easykai@100.124.0.103 "
     fuser -k 8083/tcp 2>/dev/null; sleep 1;
     cd /home/easykai/easykai-workspace/easykai.cn/platform;
     tmux new-session -d -s platform-8083 'python3 -B app.py 8083';
   "

4. 验证部署：
   curl -s http://127.0.0.1:8083/api/v1/chat/status

替代方案：使用现有的上传脚本作为模板
您可以修改 scripts/upload_app_debug.py 来上传我们的文件并重启平台服务而不是admin服务。

代码已经提交到远程仓库（分支：merge/prod-and-github），因此
服务器管理员也可以拉取这些更改并手动部署。