#!/usr/bin/env python3
"""
Workflow Templates — 预置内容工作流模板（只读蓝图）
====================================================
这些模板是_"Blueprint"，不写入数据库。前端通过 GET /admin/automation/workflow-templates
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

WORKFLOW_TEMPLATES = [
    {
        "key": "daily_content_collect",
        "name": _"Daily Content Collection and Processing",
        "description": "定时采集 RSS 源 → AI 加工 → 人工审核 → 通知管理员",
        "triggers": [{"type": "cron", "cron": "0 8 * * *"}],
        "max_concurrency": 1,
        "timeout_minutes": 60,
        "on_error": "pause",
        "definition": {
            "nodes": [
                {"id": "n1", "type": "data_collect", "name": _"Content Source",
                 "config": {"source_ids": [], "max_per_source": 10},
                 "position": {"x": 100, "y": 100}},
                {"id": "n2", "type": "ai_process", "name": _"AI Processing",
                 "config": {"instruction": _"Analyze the collected content and output a Chinese summary",
                            "fields": ["title", "summary", "body", "keywords"]},
                 "position": {"x": 320, "y": 100}},
                {"id": "n3", "type": "approval", "name": _"Manual review",
                 "config": {"approver_role": "admin"},
                 "position": {"x": 540, "y": 100}},
                {"id": "n4", "type": "notify", "name": _"Notify administrator",
                 "config": {"channels": ["notification"], "title": _"New content pending review"},
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
        "name": _"Scheduled Full-site Static Generation",
        "description": "定时检查新发布文章 → 增量生成静态页 → 通知完成",
        "triggers": [{"type": "cron", "cron": "0 3 * * *"}],
        "max_concurrency": 1,
        "timeout_minutes": 30,
        "on_error": "pause",
        "definition": {
            "nodes": [
                {"id": "n1", "type": "script", "name": _"Check New Article",
                 "config": {"script": "check_new_posts", "lang": "builtin"},
                 "position": {"x": 100, "y": 100}},
                {"id": "n2", "type": "script", "name": _"Incremental Static Page Generation"",
                 "config": {"script": "generate_static_incremental", "lang": "builtin"},
                 "position": {"x": 320, "y": 100}},
                {"id": "n3", "type": "notify", "name": _"Notification completed",
                 "config": {"channels": ["notification"], "title": _"Static site has been updated"},
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
        "name": _"Auto Social Posting",
        "description": "判断是否满足发布条件 → 推送到微信/微博/头条 → 通知结果",
        "triggers": [{"type": "event", "event": "cms.published"}],
        "max_concurrency": 2,
        "timeout_minutes": 20,
        "on_error": "continue",
        "definition": {
            "nodes": [
                {"id": "n1", "type": "condition", "name": _"Publish to Social Media?",
                 "config": {"expression": "true",
                            "branches": [{"value": True, "to": "n2"},
                                         {"value": False, "to": "n3"}]},
                 "position": {"x": 100, "y": 100}},
                {"id": "n2", "type": "publish", "name": _"Publish to social media",
                 "config": {"platforms": ["weixin", "weibo", "toutiao"]},
                 "position": {"x": 320, "y": 60}},
                {"id": "n3", "type": "notify", "name": _"Notification result",
                 "config": {"channels": ["notification"], "title": _"Social Post Completed"},
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
        "name": _"Knowledge Base Sync",
        "description": "采集新文章 → AI 清洗 → 推送到知识库 → 通知",
        "triggers": [{"type": "event", "event": "cms.published"}],
        "max_concurrency": 1,
        "timeout_minutes": 30,
        "on_error": "pause",
        "definition": {
            "nodes": [
                {"id": "n1", "type": "data_collect", "name": _"Get New Articles",
                 "config": {"source_ids": [], "max_per_source": 20},
                 "position": {"x": 100, "y": 100}},
                {"id": "n2", "type": "ai_process", "name": _"AI Cleaning",
                 "config": {"instruction": _"Clean and structure article content for knowledge base retrieval",
                            "fields": ["title", "summary", "body"]},
                 "position": {"x": 320, "y": 100}},
                {"id": "n3", "type": "notify", "name": _"Notification synchronization completed",
                 "config": {"channels": ["notification"], "title": _"New content has been synced with the knowledge base"},
                 "position": {"x": 540, "y": 100}},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"},
            ],
        },
    },
]
