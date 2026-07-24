# Dashboard 全图形化实现方案

## 一、总体原则

- **只改 1 个文件**：`admin/templates/partials/dashboard.html`
- **不动后端**：不改 `admin.py`，不新增 API 字段
- **只使用现有数据**：当前 `/admin/dashboard` API 已返回的全部字段
- **全 ECharts 图形化**：所有核心指标用图表展示
- **数据为 0 时显示 "No Data"**

## 二、布局结构（共 5 行）

```
┌──────────────────────────────────────────────────────┐
│ Row 1:  用户环形图  │  收入仪表盘  │  订阅环形图       │  3列
├──────────────────────────────────────────────────────┤
│ Row 2:  API + Agent 组合图  │  Token 消耗排行图     │  2列
├──────────────────────────────────────────────────────┤
│ Row 3:  服务状态指示灯      │  今日流量概览          │  2列
├──────────────────────────────────────────────────────┤
│ Row 4:  待处理事项堆叠图    │  热门页面排行图        │  2列
├──────────────────────────────────────────────────────┤
│ Row 5:  最近注册用户表      │  最近订单表            │  2列
└──────────────────────────────────────────────────────┘
```

## 三、每个图表的详细规格

### Row 1 — 3 列核心指标

**图表 1：用户环形图（ECharts pie）**
- 类型：环形饼图（donut），中心显示总数
- 数据：`active_users`（活跃）、`total_users - active_users`（非活跃）、`today_new_users`（今日新增）
- 标题："Users"
- 中心文字：`total_users` + "Total"
- 尺寸：`height:240px`

**图表 2：收入仪表盘（ECharts gauge）**
- 类型：仪表盘
- 数据：`monthly_revenue`（当前值 ¥1,416）
- 最大值上限：`¥30,000`（固定目标值）
- 指针指向当前值，扇形区域从绿→黄→红渐变
- 标题："Monthly Revenue"
- 尺寸：`height:240px`

**图表 3：订阅环形图（ECharts pie）**
- 类型：环形饼图
- 数据：`active_subscriptions`（已付款）、`total_orders - active_subscriptions`（未付款）
- 标题："Subscriptions"
- 中心文字：`active_subscriptions` + "Active"
- 尺寸：`height:240px`

### Row 2 — 2 列使用量

**图表 4：API + Agent 组合条形图（ECharts bar）**
- 类型：分组柱状图
- 数据：
  - API Calls：`today_calls`（今日）、`total_calls`（总计/30 缩放）
  - Agents：`active_agents`（活跃）、`total_agents`（总数）
- X 轴：['API Calls', 'Agents']
- 图例：['Today/Active', 'Total']
- 标题："Usage Overview"
- 尺寸：`height:240px`

**图表 5：Token 消耗排行（ECharts horizontal bar）**
- 类型：横向条形图
- 数据：`top_token_agents`（最多 5 条，agent_name → total）
- 标题："Top Token Spend"
- 如果 `top_token_agents` 为空，显示 "No Data"
- 尺寸：`height:240px`

### Row 3 — 2 列状态

**图表 6：服务状态指示灯（HTML + CSS，非 ECharts）**
- 类型：纯 CSS 网格布局
- 数据：`services`（name + alive 布尔）
- 显示：每个服务一个圆点 + 名称，绿色=alive，红色=dead
- 不需要 ECharts，用纯 HTML 渲染

**图表 7：今日流量（ECharts pie 或 HTML）**
- 方案 C：纯数字 HTML 卡片（最稳定）
- 数据：`today_pv`、`today_uv`、`online_now`

### Row 4 — 2 列内容

**图表 8：待处理事项堆叠条形图（ECharts bar）**
- 类型：水平堆叠条形图
- 数据：`pending_posts`、`pending_reviews`、`pending_contacts`、`today_failed_tasks`
- 标题："Pending Items"

**图表 9：热门页面排行（ECharts horizontal bar）**
- 类型：横向条形图
- 数据：`top_pages`（path → pv）
- 标题："Popular Pages"

### Row 5 — 2 列表格

**表格 1：最近注册用户**（纯 HTML table）
- 列：ID / Nickname / Phone / Time
- 数据：`recent_users`

**表格 2：最近订单**（纯 HTML table）
- 列：ID / Plan / Amount / Status（paid → 绿色标签）
- 数据：`recent_orders`

## 四、CSS 依赖

- 使用现有 class：`.cd`（卡片容器）、`.g2`（2列网格）、`.g3`（3列网格）
- ECharts 容器统一：`style="width:100%;height:240px"`
- 如不存在 `.g3` 样式，需在 `dashboard.html` 内联添加：

```css
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px}
```

## 五、涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `admin/templates/partials/dashboard.html` | **重写** | 全部替换为图形化布局 |
| `auth-center/routes/admin.py` | **不变** | 删除之前加的 `trend_30d` / `revenue_trend_30d` 代码 |
| `admin/templates/partials/head.html` | **不变** | ECharts 已加载 |

## 六、验证方式

1. 登录 `agent.easykai.cn/admin` 查看 Dashboard
2. 检查所有 9 个图表是否正确渲染
3. 检查服务状态指示灯颜色是否正确
4. 检查表格数据是否正常显示
5. 如果某些数据为 0，应显示 "No Data" 而非空容器
