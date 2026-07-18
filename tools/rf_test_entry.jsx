/**
 * Phase 0 — esbuild 本地打包验证
 * 用 esbuild 将 React + ReactFlow 打包为单文件
 */

import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import ReactFlow, {
  ReactFlowProvider,
  Controls,
  Background,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  addEdge,
} from 'react-flow-renderer';
import 'react-flow-renderer/dist/style.css';

// ------ 自定义节点 ------
function CustomNode({ data }) {
  return React.createElement('div', {
    style: {
      padding: '12px 16px', borderRadius: '8px',
      background: '#fff', border: '2px solid ' + (data.color || '#6366f1'),
      fontSize: '13px', minWidth: '140px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)'
    }
  },
    React.createElement('div', { style: { fontWeight: 600, marginBottom: '4px' } }, data.icon + ' ' + data.label),
    React.createElement('div', { style: { fontSize: '11px', color: '#64748b' } }, data.description || ''),
    React.createElement(Handle, { type: 'target', position: Position.Left, style: { background: '#6366f1' } }),
    React.createElement(Handle, { type: 'source', position: Position.Right, style: { background: '#6366f1' } })
  );
}

const nodeTypes = { custom: CustomNode };

// ------ 主画布组件 ------
function TestFlow() {
  const initialNodes = [
    { id: 'n1', type: 'custom', position: { x: 50, y: 180 }, data: { icon: '📡', label: 'Data Collect', description: 'Get source data', color: '#2563eb' } },
    { id: 'n2', type: 'custom', position: { x: 350, y: 180 }, data: { icon: '🤖', label: 'AI Process', description: 'Intelligent analysis', color: '#7c3aed' } },
    { id: 'n3', type: 'custom', position: { x: 650, y: 180 }, data: { icon: '📤', label: 'Publish', description: 'Auto publish', color: '#16a34a' } },
  ];
  const initialEdges = [
    { id: 'e1-2', source: 'n1', target: 'n2', label: 'success', style: { stroke: '#94a3b8' } },
    { id: 'e2-3', source: 'n2', target: 'n3', label: 'success', style: { stroke: '#94a3b8' } },
  ];

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  return React.createElement(ReactFlowProvider, null,
    React.createElement('div', { style: { width: '100%', height: '500px' } },
      React.createElement(ReactFlow, {
        nodes, edges,
        onNodesChange,
        onEdgesChange,
        nodeTypes,
        fitView: true,
        attributionPosition: 'bottom-left'
      },
        React.createElement(Controls, null),
        React.createElement(Background, { gap: 20, size: 1 }),
        React.createElement(MiniMap, { style: { width: 120, height: 80 } })
      )
    )
  );
}

// ------ 挂载 ------
var root = document.getElementById('root');
if (root) {
  createRoot(root).render(React.createElement(TestFlow, null));
}
