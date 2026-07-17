/* ══════════════════════════════════════════════════════════════
   workflow_editor.js — 编辑器工具函数
   非 React 逻辑：API 调用、节点默认值、序列化等
   ══════════════════════════════════════════════════════════════ */

window.editor = (function() {
  'use strict';

  var T = window.__SSO_TOKEN || '';
  var API_BASE = '/admin/automation/workflows';

  // ── 节点类型配置 ──
  var NODE_CONFIGS = {
    data_collect: { icon: '📡', color: '#2563eb', label: 'node.data_collect', description: 'Get source data', showInput: false },
    ai_agent:     { icon: '🤖', color: '#7c3aed', label: 'node.ai_agent', description: 'AI agent call' },
    ai_process:   { icon: '🧠', color: '#7c3aed', label: 'node.ai_process', description: 'Data processing' },
    condition:    { icon: '🔀', color: '#eab308', label: 'node.condition', description: 'Branch logic' },
    wait:         { icon: '⏱️', color: '#64748b', label: 'node.wait', description: 'Time delay' },
    publish:      { icon: '📤', color: '#16a34a', label: 'node.publish', description: 'Auto publish' },
    notify:       { icon: '🔔', color: '#ec4899', label: 'node.notify', description: 'Send notification', showOutput: false },
    approval:     { icon: '✅', color: '#ef4444', label: 'node.approval', description: 'Human approval' },
    script:       { icon: '📜', color: '#a16207', label: 'node.script', description: 'Custom script' },
    http_request: { icon: '🌐', color: '#0891b2', label: 'node.http_request', description: 'HTTP call' },
    market_check: { icon: '📊', color: '#ea580c', label: 'node.market_check', description: 'Market data check' },
    sub_workflow: { icon: '🔗', color: '#15803d', label: 'node.sub_workflow', description: 'Nested workflow' }
  };

  // 按分类组织
  var NODE_CATEGORIES = [
    { name: 'AI Processing',    key: 'panel.category.ai',      nodes: ['ai_agent','data_collect','ai_process'] },
    { name: 'Flow Control',     key: 'panel.category.flow',    nodes: ['condition','wait'] },
    { name: 'Output Actions',   key: 'panel.category.output',  nodes: ['publish','notify'] },
    { name: 'Human Interaction',key: 'panel.category.human',   nodes: ['approval'] },
    { name: 'Advanced',         key: 'panel.category.advanced', nodes: ['script','http_request','market_check','sub_workflow'] }
  ];

  // ── 获取节点默认 data ──
  function getNodeDefaults(type) {
    var cfg = NODE_CONFIGS[type];
    if (!cfg) return { label: type, color: '#6366f1', description: '' };
    return {
      type: type,
      label: (window.__t && window.__t._(cfg.label)) || cfg.label,
      description: cfg.description,
      color: cfg.color,
      icon: cfg.icon,
      showInput: cfg.showInput !== false,
      showOutput: cfg.showOutput !== false,
      incomplete: true,
      config: {}
    };
  }

  // ── 渲染节点面板 ──
  function renderNodePanel(container) {
    if (!container) container = document.getElementById('node-panel-list');
    if (!container) return;
    var html = '';
    NODE_CATEGORIES.forEach(function(cat) {
      var catLabel = (window.__t && window.__t._(cat.key)) || cat.name;
      html += '<div class="panel-title" style="margin-top:12px">' + catLabel + '</div>';
      cat.nodes.forEach(function(type) {
        var cfg = NODE_CONFIGS[type];
        html += '<div class="node-panel-item" draggable="true" data-node-type="' + type + '"';
        html += ' ondragstart="editor.onNodeDragStart(event)">';
        html += '<span class="node-icon" style="background:' + (cfg.color + '22') + ';color:' + cfg.color + '">' + cfg.icon + '</span>';
        html += (window.__t && window.__t._(cfg.label)) || cfg.label;
        html += '</div>';
      });
    });
    container.innerHTML = html;
  }

  // ── 拖拽开始 ──
  function onNodeDragStart(event) {
    var type = event.target.closest('[data-node-type]').getAttribute('data-node-type');
    event.dataTransfer.setData('application/reactflow', type);
    event.dataTransfer.effectAllowed = 'move';
  }

  // ── 保存工作流 ──
  function save() {
    // Will be implemented in Phase 4
    console.log('Save workflow...');
  }

  // ── 运行工作流 ──
  function run() {
    // Will be implemented in Phase 4
    console.log('Run workflow...');
  }

  // ── Toast 消息 ──
  function toast(message, type) {
    type = type || 'info';
    console.log('[' + type + '] ' + message);
  }

  // ── 初始化 ──
  function init() {
    renderNodePanel();
    // 节点面板拖拽事件由 onNodeDragStart 处理
    // ReactFlow 的 onDragOver/onDrop 由 React 组件管理
  }

  return {
    NODE_CONFIGS: NODE_CONFIGS,
    NODE_CATEGORIES: NODE_CATEGORIES,
    getNodeDefaults: getNodeDefaults,
    renderNodePanel: renderNodePanel,
    onNodeDragStart: onNodeDragStart,
    save: save,
    run: run,
    toast: toast,
    init: init
  };
})();

// ── 页面加载后初始化 ──
document.addEventListener('DOMContentLoaded', function() {
  window.editor.init();
});
