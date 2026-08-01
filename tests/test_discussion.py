#!/usr/bin/env python3
"""
Unit tests for Agent Discussion Mode (v2.0)

Tests cover:
  - JSON decision parsing (direct + LLM retry fallback)
  - Context compaction / summarization
  - Agent domain lookup
  - DAG workflow trigger
  - Agent availability check with degradation

Run: pytest tests/test_discussion.py -v
"""

import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# Ensure project root in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


class TestParseDecisionJson(unittest.TestCase):
    """Tests for _parse_decision_json() — direct parse + LLM retry."""

    def setUp(self):
        from agent_matrix.orchestrator import AgentOrchestrator
        self.orch = AgentOrchestrator(models_module=MagicMock())

    def test_direct_parse_valid_json_fenced(self):
        """Valid JSON inside ```json fence should parse directly."""
        text = '''Here is my decision:
```json
{"approved": true, "confidence": 0.9, "reason": "good", "steps": [{"type": "test", "params": {}}]}
```
Done.'''
        result = self.orch._parse_decision_json(text, {})
        self.assertIsNotNone(result)
        self.assertTrue(result['approved'])
        self.assertEqual(result['confidence'], 0.9)
        self.assertEqual(len(result['steps']), 1)

    def test_direct_parse_valid_json_no_fence(self):
        """Valid JSON without fence but with 'approved' key should parse."""
        text = 'The plan is: {"approved": false, "confidence": 0.2, "reason": "unsafe", "steps": []}'
        result = self.orch._parse_decision_json(text, {})
        self.assertIsNotNone(result)
        self.assertFalse(result['approved'])
        self.assertEqual(result['confidence'], 0.2)

    def test_direct_parse_invalid_json(self):
        """Invalid JSON should return None (no retry without agent_config)."""
        text = 'This is not JSON at all.'
        # With empty agent_config and no _run_discussion_agent mock, should return None
        result = self.orch._parse_decision_json(text, {}, max_retries=0)
        self.assertIsNone(result)

    def test_llm_retry_on_parse_failure(self):
        """When direct parse fails, LLM retry should attempt reformatting."""
        bad_text = 'not json'
        fixed_text = '{"approved": true, "confidence": 1.0, "reason": "fixed", "steps": []}'

        with patch.object(self.orch, '_run_discussion_agent', return_value=fixed_text):
            result = self.orch._parse_decision_json(bad_text, {'name': 'Test'}, max_retries=1)
            self.assertIsNotNone(result)
            self.assertTrue(result['approved'])

    def test_all_retries_exhausted(self):
        """When both direct parse and LLM retries fail, return None."""
        bad_text = 'garbage'

        with patch.object(self.orch, '_run_discussion_agent', return_value='still garbage'):
            result = self.orch._parse_decision_json(bad_text, {'name': 'Test'}, max_retries=2)
            self.assertIsNone(result)


class TestCompactContext(unittest.TestCase):
    """Tests for _compact_context() and _summarize_earlier()."""

    def setUp(self):
        from agent_matrix.orchestrator import AgentOrchestrator
        self.orch = AgentOrchestrator(models_module=MagicMock())
        self.orch.MAX_CONTEXT_CHARS = 100  # low threshold to trigger compaction

    def test_no_compaction_when_under_limit(self):
        """Context under the limit should be returned unchanged."""
        context = [
            {'agent': 'A', 'role': 'Planner', 'content': 'short'},
            {'agent': 'B', 'role': 'Reviewer', 'content': 'also short'},
        ]
        self.orch.MAX_CONTEXT_CHARS = 10000
        result = self.orch._compact_context(context)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['content'], 'short')

    def test_compaction_when_over_limit(self):
        """Context over the limit should be compacted to summary + latest."""
        context = [
            {'agent': 'A', 'role': 'Planner', 'content': 'x' * 60},
            {'agent': 'B', 'role': 'Reviewer', 'content': 'y' * 60},
            {'agent': 'C', 'role': 'Decider', 'content': 'latest message'},
        ]
        result = self.orch._compact_context(context)
        # Should be 2 entries: summary + latest
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['role'], 'Discussion Summary')
        self.assertEqual(result[1]['content'], 'latest message')

    def test_summarize_earlier_fallback(self):
        """When LLM summarization fails, should fall back to truncation."""
        messages = [
            {'agent': 'A', 'role': 'Planner', 'content': 'long ' * 20},
            {'agent': 'B', 'role': 'Reviewer', 'content': 'message ' * 20},
        ]
        # Mock UnifiedLLM to raise exception
        with patch('agent_matrix.engine.UnifiedLLM', side_effect=Exception('fail')):
            from agent_matrix.orchestrator import AgentOrchestrator
            orch = AgentOrchestrator(models_module=MagicMock())
            summary = orch._summarize_earlier(messages)
            self.assertIn('...', summary)
            self.assertIn('[Planner]', summary)


class TestFindAgentByDomain(unittest.TestCase):
    """Tests for _find_agent_by_domain()."""

    def test_find_existing_agent(self):
        """Should return the first matching active agent."""
        mock_models = MagicMock()
        mock_models.list_agents.return_value = [
            {'id': 1, 'name': 'Builder', 'domain': 'site_builder', 'is_active': 1}
        ]
        from agent_matrix.orchestrator import AgentOrchestrator
        orch = AgentOrchestrator(models_module=mock_models)
        agent = orch._find_agent_by_domain('site_builder')
        self.assertIsNotNone(agent)
        self.assertEqual(agent['name'], 'Builder')

    def test_find_nonexistent_agent(self):
        """Should return None when no agent matches the domain."""
        mock_models = MagicMock()
        mock_models.list_agents.return_value = []
        from agent_matrix.orchestrator import AgentOrchestrator
        orch = AgentOrchestrator(models_module=mock_models)
        agent = orch._find_agent_by_domain('nonexistent')
        self.assertIsNone(agent)


class TestTriggerDagFromPlan(unittest.TestCase):
    """Tests for _trigger_dag_from_plan()."""

    def test_triggers_with_explicit_workflow_id(self):
        """Should use the workflow_id from the plan if specified."""
        exec_plan = {
            'approved': True,
            'workflow_id': 42,
            'confidence': 0.9,
            'reason': 'test',
            'steps': [{'type': 'http_request', 'params': {'url': '/api/test'}}]
        }

        mock_engine = MagicMock()
        mock_engine.run_workflow.return_value = 'WF-123'

        with patch('orchestrator.workflow_engine.WorkflowEngine', return_value=mock_engine):
            from agent_matrix.orchestrator import AgentOrchestrator
            orch = AgentOrchestrator(models_module=MagicMock())
            result = orch._trigger_dag_from_plan(exec_plan, user_id=1)
            mock_engine.run_workflow.assert_called_once()
            call_kwargs = mock_engine.run_workflow.call_args[1]
            self.assertEqual(call_kwargs['workflow_id'], 42)
            self.assertEqual(call_kwargs['trigger_type'], 'agent_discussion')
            self.assertIn('WF-123', result)

    def test_falls_back_to_env_var(self):
        """Should fall back to DISCUSS_DEFAULT_WORKFLOW_ID env var."""
        exec_plan = {
            'approved': True,
            'confidence': 0.9,
            'reason': 'test',
            'steps': [{'type': 'test', 'params': {}}]
        }

        mock_engine = MagicMock()
        mock_engine.run_workflow.return_value = 'WF-456'

        with patch('orchestrator.workflow_engine.WorkflowEngine', return_value=mock_engine):
            with patch.dict('os.environ', {'DISCUSS_DEFAULT_WORKFLOW_ID': '99'}):
                from agent_matrix.orchestrator import AgentOrchestrator
                orch = AgentOrchestrator(models_module=MagicMock())
                result = orch._trigger_dag_from_plan(exec_plan, user_id=1)
                call_kwargs = mock_engine.run_workflow.call_args[1]
                self.assertEqual(call_kwargs['workflow_id'], 99)

    def test_falls_back_to_default_1(self):
        """Should fall back to workflow_id=1 when nothing is specified."""
        exec_plan = {
            'approved': True,
            'confidence': 0.9,
            'reason': 'test',
            'steps': [{'type': 'test', 'params': {}}]
        }

        mock_engine = MagicMock()
        mock_engine.run_workflow.return_value = 'WF-1'

        with patch('orchestrator.workflow_engine.WorkflowEngine', return_value=mock_engine):
            with patch.dict('os.environ', {}, clear=True):
                from agent_matrix.orchestrator import AgentOrchestrator
                orch = AgentOrchestrator(models_module=MagicMock())
                result = orch._trigger_dag_from_plan(exec_plan, user_id=1)
                call_kwargs = mock_engine.run_workflow.call_args[1]
                self.assertEqual(call_kwargs['workflow_id'], 1)

    def test_workflow_engine_error(self):
        """Should raise RuntimeError when workflow engine fails."""
        exec_plan = {
            'approved': True,
            'confidence': 0.9,
            'reason': 'test',
            'steps': []
        }

        mock_engine = MagicMock()
        mock_engine.run_workflow.side_effect = Exception('Engine crashed')

        with patch('orchestrator.workflow_engine.WorkflowEngine', return_value=mock_engine):
            from agent_matrix.orchestrator import AgentOrchestrator
            orch = AgentOrchestrator(models_module=MagicMock())
            with self.assertRaises(RuntimeError) as ctx:
                orch._trigger_dag_from_plan(exec_plan, user_id=1)
            self.assertIn('DAG workflow failed to start', str(ctx.exception))


class TestDiscussAndExecuteDegradation(unittest.TestCase):
    """Tests for discuss_and_execute() degradation paths."""

    def test_all_agents_unavailable(self):
        """When no agents available, should yield a single error event."""
        mock_models = MagicMock()

        def list_agents_side_effect(**kwargs):
            return []

        mock_models.list_agents.side_effect = list_agents_side_effect

        from agent_matrix.orchestrator import AgentOrchestrator
        orch = AgentOrchestrator(models_module=mock_models)

        events = list(orch.discuss_and_execute('test task', user_id=1))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['type'], 'error')
        self.assertIn('Cannot start discussion', events[0]['content'])

    def test_single_agent_available_degradation(self):
        """When only one agent available, should degrade to fast mode."""
        mock_models = MagicMock()
        builder_agent = {'id': 1, 'name': 'Builder', 'domain': 'site_builder'}

        def list_agents_side_effect(role_type=None, domain=None, active_only=False):
            if domain == 'site_builder':
                return [builder_agent]
            return []

        mock_models.list_agents.side_effect = list_agents_side_effect

        from agent_matrix.orchestrator import AgentOrchestrator
        orch = AgentOrchestrator(models_module=mock_models)

        # Mock the _run_discussion_agent to return valid plan JSON
        plan_json = json.dumps({
            'approved': True,
            'confidence': 0.8,
            'reason': 'fast mode plan',
            'steps': [{'type': 'test', 'params': {}}]
        })

        mock_engine = MagicMock()
        mock_engine.run_workflow.return_value = 'WF-FAST'

        with patch.object(orch, '_run_discussion_agent', return_value=plan_json):
            with patch('orchestrator.workflow_engine.WorkflowEngine', return_value=mock_engine):
                events = list(orch.discuss_and_execute('test task', user_id=1))

        # Should have at least a warning + message
        event_types = [e['type'] for e in events]
        self.assertIn('warning', event_types)
        self.assertIn('message', event_types)


if __name__ == '__main__':
    unittest.main()
