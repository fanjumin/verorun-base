# 🚀 社交媒体管理功能 - 快速启动指南

## 立即开始

### 1️⃣ 确认修改已应用

运行验证脚本：
```bash
cd /home/***REMOVED***/projects/easykai.cn
./verify_refactor.sh
```

预期输出：所有 5 个检查都显示 ✅ 通过

### 2️⃣ 重启后端服务

```bash
# 如果使用 Flask 内置服务器
python3 admin/app.py

# 或通过 systemd（如已配置）
sudo systemctl restart community  # 或你的服务名称
```

### 3️⃣ 访问管理后台

1. 打开浏览器：`http://localhost:5000/admin` (或你的域名)
2. 登录管理员账户
3. 导航到 **「系统与安全」→ 「系统设置」**
4. 查看新的标签页界面

### 4️⃣ 测试社媒管理

在 **系统设置** 页面：
1. 点击 **「社媒管理」** 标签页
2. 查看现有的社交媒体链接列表
3. 尝试：
   - 点击 **「+ 新增社交媒体」** 添加新链接
   - 编辑现有链接
   - 删除不需要的链接
   - 切换启用/禁用状态

### 5️⃣ 验证前端显示

打开以下页面，检查底部社交媒体链接是否正确显示：

1. **首页**: `http://localhost:5000/` 
   - 查找 `socFooter` 容器中的社媒链接

2. **门户页面**: `http://localhost:5000/portal_index.html`
   - 同样位置应该显示社媒链接

3. **CMS 页面**: `http://localhost:5000/platform/cms_page.html`
   - 底部应该有社媒链接

---

## 常用 API 端点

### 获取社交媒体链接（前端）
```bash
# 获取所有已启用的链接（无需认证）
curl http://localhost:5000/api/social-media

# 别名端点（向后兼容）
curl http://localhost:5000/api/social-links
```

### 管理社交媒体（后台）
```bash
# 获取所有链接（需要管理员令牌）
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5000/admin/social-media

# 创建新链接
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform_name": "微博",
    "icon_type": "fontawesome",
    "icon_value": "fab fa-weibo",
    "url": "https://weibo.com/...",
    "hover_text": "关注我们",
    "is_enabled": true
  }' \
  http://localhost:5000/admin/social-media

# 更新链接
curl -X PUT \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"platform_name": "新名称", ...}' \
  http://localhost:5000/admin/social-media/1

# 删除链接
curl -X DELETE \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5000/admin/social-media/1
```

---

## 图标类型使用指南

### Font Awesome 图标
```json
{
  "icon_type": "fontawesome",
  "icon_value": "fab fa-weixin"  // 使用 Font Awesome 类名
}
```

常见平台：
- 微信: `fab fa-weixin`
- 微博: `fab fa-weibo`
- GitHub: `fab fa-github`
- X (Twitter): `fab fa-x-twitter`
- Telegram: `fab fa-telegram`
- LinkedIn: `fab fa-linkedin`
- 抖音: `fab fa-tiktok`

### 图片 URL
```json
{
  "icon_type": "image_url",
  "icon_value": "https://example.com/icon.png"
}
```

### Lucide 图标
```json
{
  "icon_type": "lucide",
  "icon_value": "social-media-name"  // Lucide 图标名
}
```

---

## 数据库检查

查看已存储的社交媒体链接：

```bash
# 进入数据库
sqlite3 community/community.db

# 查询社交媒体表
SELECT * FROM social_media_links;

# 查询已启用的链接
SELECT platform_name, url, is_enabled FROM social_media_links WHERE is_enabled=1;

# 离开
.quit
```

---

## 故障排查

### 问题 1: 后台无法显示社媒管理标签页

**症状**: 系统设置页面没有出现社媒管理标签

**解决**:
1. 刷新页面 (Ctrl+F5)
2. 检查浏览器控制台是否有 JavaScript 错误
3. 确认 `/admin/social-media` 端点可用：
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/admin/social-media
   ```

### 问题 2: 前端页面底部没有显示社交媒体链接

**症状**: 首页、门户、CMS 页面底部没有社媒链接

**解决**:
1. 打开浏览器控制台 (F12)
2. 检查 Network 标签，查看 `/api/social-media` 请求：
   - 应该返回 HTTP 200
   - Response 应该包含 social_media_links 数据
3. 检查是否有任何已启用 (`is_enabled=1`) 的链接：
   ```bash
   curl http://localhost:5000/api/social-media | grep -o '"is_enabled":[01]'
   ```

### 问题 3: 图标无法显示

**症状**: 社交媒体链接显示但图标为空

**解决**:
1. 检查 `icon_type` 是否正确:
   - Font Awesome: 需要确保页面已加载 Font Awesome CDN
   - Image URL: 检查图片链接是否有效
2. 查看浏览器控制台错误日志
3. 验证图标值是否正确：
   ```bash
   curl http://localhost:5000/api/social-media | \
     grep -o '"icon_type":"[^"]*"' | sort | uniq
   ```

### 问题 4: 添加/编辑社媒链接提交失败

**症状**: 点击保存后没有反应或显示错误

**解决**:
1. 检查表单字段是否填完整（必填项：平台名、图标值、URL）
2. 检查浏览器控制台 Network 标签：
   - POST/PUT 请求是否返回 200
   - 响应是否包含错误信息
3. 确认 JWT 令牌有效
4. 查看服务器日志：
   ```bash
   tail -f /var/log/app/community.log
   ```

---

## 更新现有链接示例

### 添加新社交媒体平台

在后台「社媒管理」标签页中：

1. **平台名称**: 抖音
2. **图标类型**: Font Awesome
3. **图标值**: `fab fa-tiktok`
4. **链接 URL**: `https://www.douyin.com/user/YOUR_ID`
5. **Hover 提示文字**: 关注我们的抖音号
6. **启用**: 勾选

然后点击 **保存** — 前端首页立即更新！

### 禁用某个社交媒体

1. 找到要禁用的链接行
2. 点击 **编辑**
3. 取消勾选 **启用** 复选框
4. 点击 **保存**

链接从前端消失（但数据库中仍保留）

---

## 性能优化建议

### 生产环境配置

1. **启用缓存**（可选）:
   ```python
   # 在 auth-center/routes/social_media.py 中
   from flask import make_response
   
   response = make_response(...)
   response.cache_control.max_age = 3600  # 1 小时缓存
   return response
   ```

2. **CDN 部署**:
   - 将图片 URL 指向 CDN 地址
   - 减少主服务器负担

3. **数据库索引** (如链接数量很多):
   ```sql
   CREATE INDEX idx_social_media_enabled 
   ON social_media_links(is_enabled, display_order);
   ```

---

## 备份与恢复

### 备份社交媒体配置

```bash
# 导出为 JSON
sqlite3 community/community.db \
  "SELECT * FROM social_media_links" -json > backup_socials.json

# 导出为 CSV
sqlite3 community/community.db \
  ".mode csv" \
  ".output backup_socials.csv" \
  "SELECT * FROM social_media_links"
```

### 恢复

```bash
# 从 JSON 恢复（需要脚本处理）
# 或直接在数据库中执行 INSERT 语句
```

---

## 后续任务清单

- [ ] 配置生产环境的缓存策略
- [ ] 为新的社交媒体平台添加图标
- [ ] 定期审查社交媒体链接的有效性
- [ ] 监控社媒链接的点击率（可选）
- [ ] 考虑集成社交媒体分析

---

## 获取帮助

如需技术支持或有疑问，请参考：

1. **技术文档**:
   - [SOCIAL_MEDIA_REFACTOR.md](SOCIAL_MEDIA_REFACTOR.md) - 详细重构说明
   - [REFACTOR_COMPLETION_REPORT.md](REFACTOR_COMPLETION_REPORT.md) - 完成报告

2. **代码位置**:
   - 后端: `auth-center/routes/social_media.py`
   - 前端: `admin/templates/admin.html`
   - 页面: `index.html`, `portal_index.html`, `platform/templates/cms_page.html`

3. **API 测试工具**:
   - Postman 集合已生成
   - cURL 命令示例见上文

---

**祝您使用愉快！** 🎉

