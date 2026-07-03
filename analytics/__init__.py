"""
Analytics — Server-side, Cookieless 网站统计分析系统

设计原则:
  - Server-side 优先: 所有数据在服务器端采集和处理
  - Cookieless: 不使用持久 Cookie，不依赖客户端标识
  - Visitor Hashing: IP + UA + 日期 → 每日临时访客哈希
  - IP 匿名化: 第一时间脱敏
  - 符合 GDPR/CCPA

架构:
  analytics/                   # 分析服务
    middleware.py              # Flask 请求拦截中间件（采集 + 匿名化 + hashing）
    models.py                 # SQLite 11表 + 完整 CRUD
    processor.py              # 异步批处理聚合
    tracker.py                # 自定义事件追踪 + 告警引擎
    geoip.py                  # MaxMind GeoIP2 地理解析
    ua_parser.py             # User-Agent 解析
    dashboard.py              # Flask Blueprint（API + 管理后台）
    templates/analytics.html  # 完整仪表盘 UI（深色科幻风格）
    static/analytics.js       # 前端 JS（图表 + 实时更新 + 交互）
    cli.py                    # CLI 维护工具

集成方式:
  1. 在所有 Flask 服务中注册 middleware
  2. 作为独立服务启动 analytics 仪表盘
  3. 通过 orchestrator 工作流生成报告

数据流向:
  Request → middleware (capture + anonymize + hash) → analytics_logs
    → processor.py (batch every 60s) → daily_stats / hourly_stats / page_stats / ...
    → 长期存储聚合数据，原始日志 7-30 天自动清理

依赖:
  pip install geoip2 ua-parser user-agents
"""
