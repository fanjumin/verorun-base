/* ══════════════════════════════════════════════════════════════
   workflow_editor.js — 编辑器工具函数
   非 React 逻辑：API 调用、节点默认值、配置面板、序列化等
   ══════════════════════════════════════════════════════════════ */

window.editor = (function() {
  'use strict';

  var T = window.__SSO_TOKEN || '';
  var API_BASE = '/admin/automation/workflows';
  var CURRENT_WORKFLOW_ID = null;  // 编辑模式时非 null
  var EDITOR_INSTANCE = null;      // 保存时获取画布状态

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

  // ── 配置字段定义 ──
  var CONFIG_FIELDS = {
    ai_agent: [
      { key: 'agent_type', type: 'select', label: 'Agent Type', options: ['system','user'], default: 'system' },
      { key: 'agent_id', type: 'number', label: 'Agent ID', default: 0 },
      { key: 'prompt', type: 'textarea', label: 'Prompt Template', default: '', placeholder: 'Enter prompt template...' },
      { key: 'model', type: 'text', label: 'Model', default: '', placeholder: 'e.g. qwen-turbo' }
    ],
    data_collect: [
      { key: 'source_ids', type: 'tags', label: 'Data Sources', default: [], placeholder: 'Enter source IDs, comma-separated' },
      { key: 'max_per_source', type: 'number', label: 'Max Per Source', default: 10 },
      { key: 'keywords', type: 'text', label: 'Keywords', default: '', placeholder: 'comma-separated' }
    ],
    ai_process: [
      { key: 'instruction', type: 'textarea', label: 'Processing Instruction', default: '', placeholder: 'Describe what to do...' },
      { key: 'fields', type: 'tags', label: 'Output Fields', default: [], placeholder: 'Field names, comma-separated' },
      { key: 'model', type: 'text', label: 'Model', default: '', placeholder: 'e.g. qwen-turbo' }
    ],
    condition: [
      { key: 'expression', type: 'textarea', label: 'Condition Expression', default: '', placeholder: 'e.g. context.source_count > 5' }
    ],
    wait: [
      { key: 'seconds', type: 'number', label: 'Wait Time (seconds)', default: 60 }
    ],
    publish: [
      { key: 'platforms', type: 'tags', label: 'Publish Platforms', default: [], placeholder: 'Platform names, comma-separated' },
      { key: 'title', type: 'text', label: 'Title Template', default: '', placeholder: 'e.g. Daily Report - ${date}' },
      { key: 'category', type: 'text', label: 'Category', default: '', placeholder: 'e.g. tech' }
    ],
    notify: [
      { key: 'channels', type: 'tags', label: 'Notification Channels', default: [], placeholder: 'webhook, email, sms...' },
      { key: 'title', type: 'text', label: 'Notification Title', default: '' },
      { key: 'message', type: 'textarea', label: 'Message Template', default: '', placeholder: 'Message content...' },
      { key: 'webhook_url', type: 'text', label: 'Webhook URL', default: '', placeholder: 'https://...' },
      { key: 'email_to', type: 'text', label: 'Email To', default: '', placeholder: 'user@example.com' }
    ],
    approval: [
      { key: 'approver_role', type: 'select', label: 'Approver Role', options: ['admin','manager','editor'], default: 'admin' },
      { key: 'require_approval_on_error', type: 'checkbox', label: 'Require Approval on Error', default: false }
    ],
    script: [
      { key: 'script', type: 'text', label: 'Script Name', default: '', placeholder: 'script_name' },
      { key: 'lang', type: 'select', label: 'Language', options: ['python','shell','builtin'], default: 'python' }
    ],
    http_request: [
      { key: 'url', type: 'text', label: 'URL', default: '', placeholder: 'https://api.example.com/endpoint' },
      { key: 'method', type: 'select', label: 'Method', options: ['GET','POST','PUT','DELETE'], default: 'GET' },
      { key: 'headers', type: 'textarea', label: 'Headers (JSON)', default: '{}', placeholder: '{"Authorization": "Bearer ..."}' },
      { key: 'body', type: 'textarea', label: 'Request Body', default: '', placeholder: 'JSON body template...' }
    ],
    market_check: [
      { key: 'symbol', type: 'text', label: 'Stock Symbol', default: '', placeholder: 'e.g. sh000001, AAPL' },
      { key: 'metric', type: 'select', label: 'Metric', options: ['price','change_pct','volume'], default: 'price' },
      { key: 'operator', type: 'select', label: 'Operator', options: ['>','<','>=','<=','=='], default: '>' },
      { key: 'threshold', type: 'number', label: 'Threshold', default: 0 }
    ],
    sub_workflow: [
      { key: 'workflow_id', type: 'number', label: 'Target Workflow ID', default: 0, placeholder: 'Enter workflow ID' }
    ]
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
    var fields = CONFIG_FIELDS[type] || [];
    var defaultConfig = {};
    fields.forEach(function(f) { defaultConfig[f.key] = f.default; });
    return {
      type: type,
      label: (window.__t && window.__t._(cfg.label)) || cfg.label,
      description: cfg.description,
      color: cfg.color,
      icon: cfg.icon,
      showInput: cfg.showInput !== false,
      showOutput: cfg.showOutput !== false,
      incomplete: true,
      config: defaultConfig
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

  // ═══════════════════════════════════════════════════════════
  //  配置面板渲染
  // ═══════════════════════════════════════════════════════════

  // 渲染配置表单
  function renderConfigPanel(node) {
    var panel = document.getElementById('node-config-panel');
    if (!panel) return;
    if (!node) {
      panel.innerHTML = '<div class="panel-empty">{{ _("Select a node to configure") }}</div>';
      return;
    }
    var data = node.data;
    var fields = CONFIG_FIELDS[data.type];
    if (!fields) {
      panel.innerHTML = '<div class="panel-title" style="margin-bottom:8px">' + (data.label || '') + '</div>';
      panel.innerHTML += '<div style="font-size:11px;color:var(--text-dim)">No configurable fields for this node type.</div>';
      return;
    }

    var config = data.config || {};
    var html = '';
    html += '<div class="cp-header">' + (data.icon || '') + ' ' + (data.label || '') + '</div>';
    html += '<div class="cp-type">' + (data.type || '') + '</div>';
    html += '<div class="cp-fields">';

    fields.forEach(function(f) {
      var val = (config[f.key] !== undefined && config[f.key] !== null) ? config[f.key] : f.default;
      html += '<div class="cp-field">';
      html += '<label class="cp-label">' + f.label + '</label>';

      if (f.type === 'select') {
        html += '<select class="cp-input cp-select" data-key="' + f.key + '" data-type="' + f.type + '">';
        (f.options || []).forEach(function(o) {
          html += '<option value="' + escAttr(o) + '"' + (val === o ? ' selected' : '') + '>' + o + '</option>';
        });
        html += '</select>';
      } else if (f.type === 'checkbox') {
        html += '<input type="checkbox" class="cp-checkbox" data-key="' + f.key + '" data-type="checkbox"' + (val ? ' checked' : '') + '>';
      } else if (f.type === 'number') {
        html += '<input type="number" class="cp-input" data-key="' + f.key + '" data-type="number" value="' + val + '"' + (f.placeholder ? ' placeholder="' + escAttr(f.placeholder) + '"' : '') + '>';
      } else if (f.type === 'textarea') {
        html += '<textarea class="cp-input cp-textarea" data-key="' + f.key + '" data-type="textarea" rows="3"' + (f.placeholder ? ' placeholder="' + escAttr(f.placeholder) + '"' : '') + '>' + esc(String(val)) + '</textarea>';
      } else if (f.type === 'tags') {
        var tagStr = Array.isArray(val) ? val.join(', ') : String(val);
        html += '<input class="cp-input" data-key="' + f.key + '" data-type="tags" value="' + escAttr(tagStr) + '"' + (f.placeholder ? ' placeholder="' + escAttr(f.placeholder) + '"' : '') + '>';
      } else {
        html += '<input class="cp-input" data-key="' + f.key + '" data-type="text" value="' + escAttr(String(val)) + '"' + (f.placeholder ? ' placeholder="' + escAttr(f.placeholder) + '"' : '') + '>';
      }

      html += '</div>';
    });

    html += '</div>';

    // 保存/取消按钮
    html += '<div class="cp-actions">';
    html += '<button class="btn bp bs" data-action="save-config">{{ _("Save") }}</button>';
    html += '<button class="btn bo bs" data-action="cancel-config" style="margin-left:6px">{{ _("Cancel") }}</button>';
    html += '</div>';

    panel.innerHTML = html;

    // 绑定事件
    panel.querySelector('[data-action="save-config"]').onclick = function() {
      saveNodeConfig(node.id, data.type);
    };
    panel.querySelector('[data-action="cancel-config"]').onclick = function() {
      renderConfigPanel(null);
    };
  }

  // 读取表单数据
  function readFormData(nodeType) {
    var fields = CONFIG_FIELDS[nodeType];
    if (!fields) return {};
    var data = {};
    fields.forEach(function(f) {
      var el = document.querySelector('[data-key="' + f.key + '"]');
      if (!el) { data[f.key] = f.default; return; }
      var tag = el.tagName.toLowerCase();
      if (f.type === 'checkbox') {
        data[f.key] = el.checked;
      } else if (f.type === 'number') {
        data[f.key] = parseFloat(el.value) || 0;
      } else if (f.type === 'tags') {
        data[f.key] = el.value.split(',').map(function(s) { return s.trim(); }).filter(function(s) { return s.length > 0; });
      } else {
        data[f.key] = el.value;
      }
    });
    return data;
  }

  // 保存节点配置
  function saveNodeConfig(nodeId, nodeType) {
    var config = readFormData(nodeType);
    // 检查必填项
    var fields = CONFIG_FIELDS[nodeType] || [];
    var incomplete = false;
    fields.forEach(function(f) {
      var val = config[f.key];
      if (f.type === 'text' || f.type === 'textarea') {
        if (f.key === 'prompt' || f.key === 'instruction' || f.key === 'expression' || f.key === 'url') {
          if (!val || val.trim() === '') incomplete = true;
        }
      }
    });

    var flowState = window.editor.__flowState;
    if (flowState) {
      flowState.updateNodeConfig(nodeId, config, incomplete);
    }
    renderConfigPanel(null);
  }

  // ═══════════════════════════════════════════════════════════
  //  序列化 / 反序列化
  // ═══════════════════════════════════════════════════════════

  // 将 React Flow 状态 → 后端 definition JSON
  function serializeToDefinition(nodes, edges) {
    var defNodes = (nodes || []).map(function(n) {
      return {
        id: n.id,
        type: n.data.type || 'unknown',
        name: n.data.label || '',
        config: n.data.config || {},
        position: { x: n.position.x, y: n.position.y }
      };
    });
    var defEdges = (edges || []).map(function(e) {
      return {
        from: e.source,
        to: e.target,
        sourceHandle: e.sourceHandle || undefined,
        condition: e.sourceHandle || 'success'
      };
    });
    return { nodes: defNodes, edges: defEdges };
  }

  // 将后端 definition JSON → React Flow state
  function deserializeFromDefinition(definition) {
    if (!definition) return { nodes: [], edges: [] };
    var defNodes = definition.nodes || [];
    var defEdges = definition.edges || [];

    var nodes = defNodes.map(function(n) {
      var cfg = NODE_CONFIGS[n.type];
      var defaults = getNodeDefaults(n.type);
      var config = n.config || {};
      var incomplete = false;
      // 检查配置是否完整
      var fields = CONFIG_FIELDS[n.type] || [];
      fields.forEach(function(f) {
        var val = config[f.key];
        if ((f.type === 'text' || f.type === 'textarea') && f.placeholder) {
          if (!val || val.toString().trim() === '') incomplete = true;
        }
      });

      return {
        id: n.id,
        type: (n.type === 'condition' || n.type === 'market_check') ? n.type : 'default',
        position: n.position || { x: 100, y: 100 },
        data: {
          type: n.type,
          label: n.name || defaults.label,
          description: cfg ? cfg.description : '',
          color: cfg ? cfg.color : '#6366f1',
          icon: cfg ? cfg.icon : '',
          showInput: cfg ? cfg.showInput !== false : true,
          showOutput: cfg ? cfg.showOutput !== false : true,
          config: config,
          incomplete: incomplete
        }
      };
    });

    var edges = defEdges.map(function(e) {
      return {
        id: 'edge_' + e.from + '_' + e.to,
        source: e.from,
        target: e.to,
        sourceHandle: e.sourceHandle || null,
        animated: true,
        style: { stroke: '#6366f1', strokeWidth: 2 }
      };
    });

    // 修复被截断的边 label
    return { nodes: nodes, edges: edges };
  }

  // ═══════════════════════════════════════════════════════════
  //  DAG 循环检测（DFS）
  // ═══════════════════════════════════════════════════════════

  function wouldCreateCycle(edges, source, target) {
    var adj = {};
    edges.forEach(function(e) {
      if (!adj[e.source]) adj[e.source] = [];
      adj[e.source].push(e.target);
    });
    var visited = {};
    var stack = [target];
    while (stack.length > 0) {
      var node = stack.pop();
      if (node === source) return true;
      if (visited[node]) continue;
      visited[node] = true;
      (adj[node] || []).forEach(function(next) { stack.push(next); });
    }
    return false;
  }

  function validateConnection(nodes, edges, source, target, sourceHandle) {
    if (source === target) {
      return { ok: false, reason: window.__t && window.__t._('toast.self_connect') || 'Cannot connect a node to itself' };
    }
    var dup = edges.some(function(e) {
      return e.source === source && e.target === target && e.sourceHandle === sourceHandle;
    });
    if (dup) {
      return { ok: false, reason: window.__t && window.__t._('toast.duplicate_edge') || 'Duplicate connection exists' };
    }
    if (wouldCreateCycle(edges, source, target)) {
      return { ok: false, reason: window.__t && window.__t._('toast.cycle_detected') || 'Cycle detected' };
    }
    return { ok: true };
  }

  var _getEdges = function() { return []; };
  var _getNodes = function() { return []; };
  function setEdgeAccessor(getNodes, getEdges) {
    _getNodes = getNodes;
    _getEdges = getEdges;
  }

  // ═══════════════════════════════════════════════════════════
  //  API 操作
  // ═══════════════════════════════════════════════════════════

  // 保存工作流
  function save() {
    var flowState = window.editor.__flowState;
    if (!flowState) { alert('Editor not ready'); return; }
    var nodes = flowState.getNodes();
    var edges = flowState.getEdges();
    if (!nodes || nodes.length === 0) {
      alert(window.__t && window.__t._('toast.empty_workflow') || 'Cannot save an empty workflow');
      return;
    }

    var definition = serializeToDefinition(nodes, edges);
    var nameInput = document.getElementById('workflow-name');
    var name = nameInput ? nameInput.value.trim() : '';
    if (!name) name = 'Untitled Workflow';

    var payload = {
      name: name,
      definition: definition
    };

    var url = API_BASE;
    var method = 'POST';
    if (CURRENT_WORKFLOW_ID) {
      url += '/' + CURRENT_WORKFLOW_ID;
      method = 'PUT';
    }

    document.getElementById('btn-save').disabled = true;
    document.getElementById('btn-save').textContent = 'Saving...';

    fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + T },
      body: JSON.stringify(payload)
    }).then(function(r) { return r.json(); }).then(function(d) {
      document.getElementById('btn-save').disabled = false;
      document.getElementById('btn-save').textContent = window.__t && window.__t._('editor.save') || 'Save';
      if (d.success) {
        if (d.data && d.data.id && !CURRENT_WORKFLOW_ID) {
          CURRENT_WORKFLOW_ID = d.data.id;
          // 更新 URL
          if (history.pushState) {
            var url = new URL(window.location);
            url.searchParams.set('id', d.data.id);
            history.pushState({}, '', url);
          }
        }
        var fs = document.getElementById('footer-status');
        if (fs) { fs.textContent = window.__t && window.__t._('statusbar.saved') || 'Saved'; fs.style.color = 'var(--green)'; }
        toast(window.__t && window.__t._('toast.save.success') || 'Saved');
      } else {
        toast(window.__t && window.__t._('toast.save.failed') || 'Save failed: ' + (d.error || ''));
      }
    }).catch(function(err) {
      document.getElementById('btn-save').disabled = false;
      document.getElementById('btn-save').textContent = window.__t && window.__t._('editor.save') || 'Save';
      toast(window.__t && window.__t._('toast.save.failed') || 'Network error');
    });
  }

  // 加载工作流
  function load(id) {
    fetch(API_BASE + '/' + id, { headers: { 'Authorization': 'Bearer ' + T } })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) {
        toast(window.__t && window.__t._('toast.load.failed') || 'Load failed');
        return;
      }
      var wf = d.data;
      CURRENT_WORKFLOW_ID = wf.id;
      var nameInput = document.getElementById('workflow-name');
      if (nameInput) nameInput.value = wf.name || '';

      var definition = wf.definition;
      if (typeof definition === 'string') {
        try { definition = JSON.parse(definition); } catch(e) { definition = null; }
      }
      var state = definition ? deserializeFromDefinition(definition) : { nodes: [], edges: [] };
      var flowState = window.editor.__flowState;
      if (flowState) {
        flowState.setNodes(state.nodes);
        flowState.setEdges(state.edges);
      }
      if (state.nodes.length > 0) {
        var fs = document.getElementById('footer-status');
        if (fs) { fs.textContent = window.__t && window.__t._('statusbar.saved') || 'Loaded'; fs.style.color = 'var(--green)'; }
      }
      toast('Workflow loaded: ' + (wf.name || '#') + wf.id);
    })
    .catch(function() {
      toast(window.__t && window.__t._('toast.load.failed') || 'Load failed');
    });
  }

  function run() {
    if (!CURRENT_WORKFLOW_ID) { save(); return; }
    fetch(API_BASE + '/' + CURRENT_WORKFLOW_ID + '/run', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + T }
    }).then(function(r) { return r.json(); }).then(function(d) {
      if (d.success) {
        toast(window.__t && window.__t._('toast.run.success') || 'Workflow started');
      } else {
        toast(window.__t && window.__t._('toast.run.failed') || 'Run failed: ' + (d.error || ''));
      }
    }).catch(function() {
      toast(window.__t && window.__t._('toast.run.failed') || 'Network error');
    });
  }

  // ── Toast ──
  function toast(message, type) {
    type = type || 'info';
    console.log('[' + type + '] ' + message);
  }

  // ── 初始化 ──
  function init() {
    renderNodePanel();

    // 解析 URL ?id 参数
    var params = new URLSearchParams(window.location.search);
    var loadId = params.get('id');
    if (loadId) {
      CURRENT_WORKFLOW_ID = parseInt(loadId);
      load(CURRENT_WORKFLOW_ID);
    }
  }

  return {
    NODE_CONFIGS: NODE_CONFIGS,
    CONFIG_FIELDS: CONFIG_FIELDS,
    NODE_CATEGORIES: NODE_CATEGORIES,
    getNodeDefaults: getNodeDefaults,
    renderNodePanel: renderNodePanel,
    onNodeDragStart: onNodeDragStart,
    renderConfigPanel: renderConfigPanel,
    saveNodeConfig: saveNodeConfig,
    serializeToDefinition: serializeToDefinition,
    deserializeFromDefinition: deserializeFromDefinition,
    save: save,
    run: run,
    load: load,
    toast: toast,
    validateConnection: validateConnection,
    wouldCreateCycle: wouldCreateCycle,
    setEdgeAccessor: setEdgeAccessor,
    init: init
  };
})();

// ── 页面加载后初始化 ──
document.addEventListener('DOMContentLoaded', function() {
  window.editor.init();
});
