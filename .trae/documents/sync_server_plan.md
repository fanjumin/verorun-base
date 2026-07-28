# 服务器同步方案

## 目标
将本地修改的文件同步到服务器 `/home/easykai/easykai-workspace/easykai.cn/`

## 差异分析
| 文件 | 服务器大小 | 本地大小 | 差异 |
|------|-----------|---------|------|
| platform/routes/shop_public.py | 36991 | 36994 | +3 字节（本地更新） |
| platform/templates/index.html | 117184 | 117184 | 一致 |

## 需要同步的文件
1. `platform/routes/shop_public.py` - 移除了 `/ucenter` 路由
2. `platform/templates/index.html` - 已一致，但建议重新上传确保完整

## 同步步骤
1. 使用 pscp 将 `platform/routes/shop_public.py` 上传到服务器
2. 使用 pscp 将 `platform/templates/index.html` 上传到服务器
3. 验证文件大小一致

## 潜在风险
- 无，只是文件替换，数据库不变

## 确认
请回复「方案通过」或「可以执行」后开始同步。