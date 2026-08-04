#!/usr/bin/env python3
"""
Workflow Templates — 预置内容工作流模板（只读蓝图）
====================================================
这些模板是"蓝图"，不写入数据库。前端通过 GET /admin/automation/workflow-templates
读取后，用户选择某个模板即可将其 definition POST 到 /admin/automation/workflows
来实例化为可编辑的工作流。

节点结构约定（与 WorkflowEngine 一致）：
  node  = {"id", "type", "name", "config": {...}, "position": {x, y}}
  edge  = {"from", "to", "condition"?}
可用节点类型：ai_agent, data_collect, ai_process, condition, publish,
             notify, market_check, wait, approval, sub_workflow,
             http_request, script

@package orchestrator
"""

from i18n import _

WORKFLOW_TEMPLATES = [
    {
        "key": "daily_content_collect",
        "name": _("每日内容采集处理"),
        "description": _("定时采集 RSS 源 → AI 加工 → 人工审核 → 通知管理员"),
        "triggers": [{"type": "cron", "cron": "0 8 * * *"}],
        "max_concurrency": 1,
        "timeout_minutes": 60,
        "on_error": "pause",
        "definition": {
            "nodes": [
                {"id": "n1", "type": "data_collect", "name": _("采集内容源"),
                 "config": {"source_ids": [], "max_per_source": 10},
                 "position": {"x": 100, "y": 100}},
                {"id": "n2", "type": "ai_process", "name": _("AI 加工"),
                 "config": {"instruction": _("对采集内容进行解读分析，输出中文摘要"),
                            "fields": ["title", "summary", "body", "keywords"]},
                 "position": {"x": 320, "y": 100}},
                {"id": "n3", "type": "approval", "name": _("人工审核"),
                 "config": {"approver_role": "admin"},
                 "position": {"x": 540, "y": 100}},
                {"id": "n4", "type": "notify", "name": _("通知管理员"),
                 "config": {"channels": ["notification"], "title": _("有新内容待审核")},
                 "position": {"x": 760, "y": 100}},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"},
                {"from": "n3", "to": "n4", "condition": "success"},
            ],
        },
    },
    {
        "key": "scheduled_static_gen",
        "name": _("定时全站静态生成"),
        "description": _("定时检查新发布文章 → 增量生成静态页 → 通知完成"),
        "triggers": [{"type": "cron", "cron": "0 3 * * *"}],
        "max_concurrency": 1,
        "timeout_minutes": 30,
        "on_error": "pause",
        "definition": {
            "nodes": [
                {"id": "n1", "type": "script", "name": _("检查新文章"),
                 "config": {"script": "check_new_posts", "lang": "builtin"},
                 "position": {"x": 100, "y": 100}},
                {"id": "n2", "type": "script", "name": _("增量生成静态页"),
                 "config": {"script": "generate_static_incremental", "lang": "builtin"},
                 "position": {"x": 320, "y": 100}},
                {"id": "n3", "type": "notify", "name": _("通知完成"),
                 "config": {"channels": ["notification"], "title": _("静态站点已更新")},
                 "position": {"x": 540, "y": 100}},
            ],
            "edges": [
                {"from": "n1", "to": "n2", "condition": "success"},
                {"from": "n2", "to": "n3"},
            ],
        },
    },
    {
        "key": "social_auto_publish",
        "name": _("社交自动发布"),
        "description": _("判断是否满足发布条件 → 推送到微信/微博/头条 → 通知结果"),
        "triggers": [{"type": "event", "event": "cms.published"}],
        "max_concurrency": 2,
        "timeout_minutes": 20,
        "on_error": "skip",
        "definition": {
            "nodes": [
                {"id": "n1", "type": "condition", "name": _("是否发布社媒"),
                 "config": {"expression": "true",
                            "branches": [{"value": True, "to": "n2"},
                                         {"value": False, "to": "n3"}]},
                 "position": {"x": 100, "y": 100}},
                {"id": "n2", "type": "publish", "name": _("发布到社媒"),
                 "config": {"platforms": ["weixin", "weibo", "toutiao"]},
                 "position": {"x": 320, "y": 60}},
                {"id": "n3", "type": "notify", "name": _("通知结果"),
                 "config": {"channels": ["notification"], "title": _("社交发布完成")},
                 "position": {"x": 540, "y": 100}},
            ],
            "edges": [
                {"from": "n1", "to": "n2", "condition": "success"},
                {"from": "n2", "to": "n3"},
            ],
        },
    },
    {
        "key": "knowledge_base_sync",
        "name": _("知识库同步"),
        "description": _("采集新文章 → AI 清洗 → 推送到知识库 → 通知"),
        "triggers": [{"type": "event", "event": "cms.published"}],
        "max_concurrency": 1,
        "timeout_minutes": 30,
        "on_error": "pause",
        "definition": {
            "nodes": [
                {"id": "n1", "type": "data_collect", "name": _("获取新文章"),
                 "config": {"source_ids": [], "max_per_source": 20},
                 "position": {"x": 100, "y": 100}},
                {"id": "n2", "type": "ai_process", "name": _("AI 清洗"),
                 "config": {"instruction": _("清洗并结构化文章内容，供知识库检索"),
                            "fields": ["title", "summary", "body"]},
                 "position": {"x": 320, "y": 100}},
                {"id": "n3", "type": "notify", "name": _("通知同步完成"),
                 "config": {"channels": ["notification"], "title": _("知识库已同步新内容")},
                 "position": {"x": 540, "y": 100}},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"},
            ],
        },
    },
]
