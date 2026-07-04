#!/usr/bin/env python3
"""
Health Check — AI Fixer
========================
LLM-powered analysis engine for health check results.

Flow:
  1. Collect check results (errors, warnings, fix suggestions)
  2. Build a system prompt with analysis context
  3. Call LLM via AIEngine -> return structured repair plan
  4. Execute fixes (with admin confirmation)

Uses the project's AIEngine (agent_matrix/engine.py) which supports
providers available in China: DashScope, DeepSeek, SiliconFlow, etc.
Defaults to the 'cleaner_ai' config from system_config.
"""

import json
import logging
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Ensure project path is accessible
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))
sys.path.insert(0, os.path.join(BASE_DIR, '..'))

from .checkers import (
    FixSuggestion,
    FIX_ACTION_NOTIFY_ADMIN,
    ALL_FIX_ACTIONS,
)


# ─── LLM Configuration via AIEngine ───────────────────────────────────

def _build_aiengine_config() -> dict:
    """
    Build an AIEngine-compatible config dict from system_config.

    Reads cleaner_ai_* keys, falls back to:
      - provider-specific api_key (e.g. deepseek_api_key)
      - environment variable (e.g. DEEPSEEK_API_KEY)
    """
    config = {
        'provider': 'deepseek',
        'model_name': 'deepseek-chat',
        'base_url': '',
        'system_prompt': '',
    }

    try:
        from models import get_db
        with get_db() as conn:
            rows = conn.execute(
                "SELECT key, value FROM system_config WHERE key IN "
                "('cleaner_ai_provider', 'cleaner_ai_model', "
                "'cleaner_ai_base_url', 'cleaner_ai_api_key')"
            ).fetchall()
            for r in rows:
                key = r['key']
                val = r['value']
                if key == 'cleaner_ai_provider' and val:
                    config['provider'] = val
                elif key == 'cleaner_ai_model' and val:
                    config['model_name'] = val
                elif key == 'cleaner_ai_base_url' and val:
                    config['base_url'] = val

        conn.close()
    except Exception as e:
        logger.warning("Failed to read AIEngine config from DB: %s", e)

    return config


def _call_llm(system_prompt: str, user_prompt: str,
              temperature: float = 0.3) -> Optional[str]:
    """
    Call LLM via AIEngine (agent_matrix/engine.py).

    AIEngine handles API key resolution across all supported providers,
    including DashScope, DeepSeek, SiliconFlow (all accessible in China).
    """
    engine_config = _build_aiengine_config()

    try:
        from agent_matrix.engine import AIEngine
        engine = AIEngine(engine_config)
    except ImportError:
        logger.error("agent_matrix.engine.AIEngine not available")
        return None
    except Exception as e:
        logger.error("Failed to initialize AIEngine: %s", e)
        return None

    if not engine.client:
        logger.error("AIEngine has no client (missing API key)")
        return None

    try:
        resp = engine.client.chat.completions.create(
            model=engine.model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            temperature=temperature,
            max_tokens=4096,
            response_format={'type': 'json_object'},
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error("LLM call via AIEngine failed: %s", e)
        return None


# ─── Prompt Templates ────────────────────────────────────────────────────

FIXER_SYSTEM_PROMPT = """You are a senior site reliability engineer for the VeroRun system.

Your job is to analyze health check results and produce a structured repair plan.
You will receive JSON containing health check results with various issues.

Analyze each issue and return a JSON object with the following structure:

{
  "summary": "Brief summary of all issues found",
  "items": [
    {
      "check_key": "The check item key (e.g. internal_links, media_integrity)",
      "issue": "Description of the specific problem",
      "root_cause": "Analysis of what caused this issue",
      "action": "One of: update_url / mark_disabled / run_sql / notify_admin",
      "params": {
        // Action-specific parameters (see below)
      },
      "priority": "high/medium/low",
      "reason": "Why this fix is recommended"
    }
  ]
}

Action parameter formats:
- update_url:  {"table": "table_name", "record_id": 123, "field": "url_column", "new_value": "https://new-url.com"}
- mark_disabled: {"table": "table_name", "record_id": 123}
- run_sql: {"sql": "UPDATE table SET field='value' WHERE id=?", "params": [123]}
- notify_admin: {"message": "Alert message", "level": "warning/critical"}

Rules:
1. Only suggest fixes for clearly identified problems
2. For broken links (404/410), suggest mark_disabled or update_url if you know the correct URL
3. For redirect chains, suggest update_url to the final destination
4. For server resources (disk/memory), suggest run_sql to clean old logs/cache, or notify_admin
5. For database issues, suggest run_sql with appropriate repair queries
6. If unsure, mark as notify_admin
7. BE CONSERVATIVE — do not suggest destructive actions without strong evidence
"""


# ─── AIFixer Class ───────────────────────────────────────────────────────

class AIFixer:
    """
    LLM-powered fix analysis engine.

    Uses AIEngine from Agent Matrix to support all providers
    (DashScope, DeepSeek, SiliconFlow, OpenAI, etc.).

    Usage:
        fixer = AIFixer()
        plan = fixer.analyze(check_results)
        # Review plan, then:
        results = fixer.execute_fix(plan, conn)
    """

    def analyze(self, check_results: dict) -> dict:
        """
        Analyze health check results and return a repair plan.

        check_results should be a dict with at minimum:
            {'check_key': str, 'status': str, 'message': str, 'detail': dict}
        """
        user_prompt = json.dumps(check_results, ensure_ascii=False, indent=2)

        response_text = _call_llm(FIXER_SYSTEM_PROMPT, user_prompt)
        if not response_text:
            return {'summary': 'LLM analysis failed', 'items': []}

        try:
            plan = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                try:
                    plan = json.loads(match.group())
                except json.JSONDecodeError:
                    plan = {'summary': 'Failed to parse LLM response', 'items': []}
            else:
                plan = {'summary': 'Failed to parse LLM response', 'items': []}

        return plan

    def suggestions_from_plan(self, plan: dict) -> list:
        """Convert a LLM repair plan into FixSuggestion objects."""
        suggestions = []
        for item in plan.get('items', []):
            action = item.get('action', '')
            if action not in ALL_FIX_ACTIONS:
                continue
            suggestions.append(FixSuggestion(
                action=action,
                reason=item.get('reason', ''),
                params=item.get('params', {}),
                record_type=item.get('check_key', ''),
            ))
        return suggestions

    def execute_fix(self, conn, suggestions: list) -> dict:
        """
        Execute a list of FixSuggestion objects.
        Returns stats dict: {applied: int, errors: list}
        """
        applied = 0
        errors = []

        for sug in suggestions:
            try:
                if sug.action == FIX_ACTION_NOTIFY_ADMIN:
                    if conn:
                        msg = sug.params.get('message', sug.reason)
                        level = sug.params.get('level', 'warning')
                        conn.execute(
                            "INSERT INTO alerts (type, message, severity, created_at) "
                            "VALUES ('auto_remediation', ?, ?, datetime('now'))",
                            (msg, level)
                        )
                    applied += 1
                else:
                    ok = FixSuggestion.apply_fix(conn, sug)
                    if ok:
                        applied += 1
                    else:
                        errors.append(f"{sug.action}: could not be applied")
            except Exception as e:
                errors.append(f"{sug.action}: {e}")

        return {
            'applied': applied,
            'total': len(suggestions),
            'errors': errors,
        }


# ─── Convenience function ────────────────────────────────────────────────

def analyze_and_fix(check_results: dict, conn) -> dict:
    """
    One-shot: analyze check results with LLM via AIEngine, then execute fixes.
    Returns full result dict.
    """
    fixer = AIFixer()
    plan = fixer.analyze(check_results)
    suggestions = fixer.suggestions_from_plan(plan)
    result = fixer.execute_fix(conn, suggestions)
    return {
        'plan': plan,
        'execution': result,
    }
