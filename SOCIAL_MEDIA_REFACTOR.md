# 社交媒体管理功能 - 重构总结

## 修改概览

本次重构完成了以下改动：

### 1. 菜单结构调整
**文件**: `admin/templates/admin.html`
- ❌ 移除：从「系统与安全」顶级菜单中移除「社媒管理」选项
- 📌 改动位置：GROUPS 数组（第 182 行附近）

### 2. 系统设置页面重构
**文件**: `admin/templates/admin.html`（第 1030-1150 行附近）

#### 函数改动：
- `l_config()` 函数重新设计为标签页界面
  - 新增：标签导航栏（系统配置、社媒管理）
  - 改动：使用 `config-tab-content` 容器显示内容
  
- `switchConfigTab(tab)` - 新增函数
  - 切换标签页的主要逻辑
  - 参数：'system' 或 'social'
  
- `loadSystemConfig()` - 原 `loadConfigs()` 改名
  - 加载系统配置数据
  - 渲染到 `config-tab-content` 容器
  
- `loadSocialMediaConfig()` - 新增函数
  - 加载社交媒体列表
  - 提供添加、编辑、删除、启用/禁用功能

#### 保留的辅助函数（移到底部）：
```javascript
- smRenderIcon()      // 图标渲染
- smShowAddForm()     // 显示添加表单
- smEditForm()        // 显示编辑表单
- smSave()            // 保存社交媒体
- smDelete()          // 删除社交媒体
- smCloseForm()       // 关闭表单
- escAttr()           // HTML 属性转义
```

### 3. 后端 API 增强
**文件**: `auth-center/routes/social_media.py`

#### 新增端点：
```
GET /api/social-links (别名端点，向后兼容)
```
- 调用 `get_enabled_social_media()` 的包装
- 为旧前端页面提供向后兼容支持

#### 现有端点：
```
GET    /admin/social-media              # 获取所有记录（管理员）
POST   /admin/social-media              # 创建记录（管理员）
PUT    /admin/social-media/<id>         # 更新记录（管理员）
DELETE /admin/social-media/<id>         # 删除记录（管理员）
PUT    /admin/social-media/reorder      # 批量排序（管理员）
GET    /api/social-media                # 获取已启用记录（公开）
GET    /api/social-links                # 别名，同上（公开）
```

### 4. 前端页面现代化

#### 移除硬编码图标 (SOC_SVGS)
- 🗑️ 删除：11 个平台的 SVG 硬编码定义
- ✅ 改为：从后端 `/api/social-media` 动态获取

#### 更新的前端页面：

**1. `index.html` (第 521-570 行)**
```javascript
// 之前：硬编码 SOC_SVGS 对象 + 预设平台
// 现在：动态获取，支持三种图标类型：
//   - Font Awesome (fab fa-xxx)
//   - Lucide (SVG 图标库)
//   - Image URL (自定义图片)
```

**2. `portal_index.html` (同上)**
- 与 index.html 完全相同的改动

**3. `platform/templates/cms_page.html`**
- 与上述文件完全相同的改动
- 图标容器 ID: `socFooter`

#### 动态渲染逻辑：
```javascript
function getSocialIconHTML(item) {
  // item.icon_type: 'fontawesome' | 'lucide' | 'image_url'
  // item.icon_value: 对应的值（Font Awesome 类名、图片 URL 等）
}

// 获取已启用的社交媒体并渲染
fetch("/api/social-media").then(...).then(function(d){
  d.data.forEach(function(item) {
    var iconHtml = getSocialIconHTML(item);
    // 构建链接并插入到页面
  });
})
```

### 5. 数据字段对应关系

后端返回的字段：
```json
{
  "id": 1,
  "platform_name": "官方微信",        // 平台名称
  "icon_type": "fontawesome",         // 图标类型
  "icon_value": "fab fa-weixin",      // 图标值
  "url": "https://mp.weixin.qq.com",  // 链接 URL
  "hover_text": "扫码关注",            // 鼠标悬停文字
  "is_enabled": 1,                     // 是否启用
  "display_order": 1                   // 显示顺序
}
```

前端使用字段映射：
| 前端使用 | 后端字段 | 说明 |
|---------|--------|------|
| 图标 | icon_type + icon_value | 渲染图标 |
| 标题 | platform_name / hover_text | 鼠标悬停文本 |
| 链接 | url | 点击跳转 |
| 排序 | display_order | 页面显示顺序 |

## 测试清单

### 后端测试
- [ ] 启动 Flask 应用，验证蓝图注册
- [ ] 测试 `/admin/social-media` GET 端点（需要管理员令牌）
- [ ] 测试 `/api/social-media` 端点（无需认证）
- [ ] 测试 `/api/social-links` 别名端点
- [ ] 创建、编辑、删除社交媒体记录

### 前端测试
- [ ] 打开 admin 后台，导航到「系统设置」
- [ ] 验证标签页界面（系统配置 / 社媒管理 标签）
- [ ] 在社媒管理标签中：
  - [ ] 查看现有记录列表
  - [ ] 添加新的社交媒体链接
  - [ ] 编辑现有记录
  - [ ] 删除记录
  - [ ] 验证启用/禁用状态显示
- [ ] 打开首页 index.html，验证底部社交媒体链接正确显示
- [ ] 打开 portal_index.html，验证底部社交媒体链接正确显示
- [ ] 打开 CMS 页面 (platform/templates/cms_page.html)，验证底部社交媒体链接正确显示

### 兼容性测试
- [ ] 旧 API `/api/social-links` 仍可用（别名端点）
- [ ] 前端页面自动适应后端返回的动态数据
- [ ] 新添加的社交媒体立即显示在前端

## 已知事项

### 数据库
- 社交媒体数据存储在 `social_media_links` 表
- 表结构已在 `community/models.py` 中定义
- 包含 4 条初始测试数据

### 图标支持
- **Font Awesome**: 使用 `fab fa-xxx` 格式，需要 Font Awesome CDN
- **Lucide**: 可选的 SVG 图标库
- **Image URL**: 自定义图片，支持相对/绝对路径

### 性能考虑
- 前端缓存管理员令牌在 `T` 全局变量
- 社交媒体列表通过 `/api/social-media` 公开获取（无认证需要）
- 建议在生产环境中缓存响应

## 回滚计划

如需回滚到之前的版本：

1. 恢复菜单结构：将 social_media 项添加回 GROUPS 数组
2. 恢复 l_config：替换为原始的配置加载逻辑
3. 恢复 l_social_media：添加回原始的独立函数
4. 恢复前端页面：恢复 SOC_SVGS 硬编码和原始 fetch 逻辑
5. 移除别名端点 `/api/social-links`

## 文件修改摘要

| 文件 | 修改 | 行数 |
|-----|------|------|
| admin/templates/admin.html | 菜单调整、标签页重构、函数改名 | ~120 |
| auth-center/routes/social_media.py | 新增别名端点 | +5 |
| index.html | 移除 SOC_SVGS、更新动态渲染 | ~45 |
| portal_index.html | 同 index.html | ~45 |
| platform/templates/cms_page.html | 同 index.html | ~30 |

## 总行数变化
- **增加**：~5 行（别名端点）
- **删除**：~150 行（硬编码 SVG 定义）
- **修改**：~100 行（函数重构）
- **净变化**：-45 行（代码整体简化）
