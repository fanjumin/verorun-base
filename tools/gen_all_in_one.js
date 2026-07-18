/**
 * All-In-One v4 — react-dom UMD 已修复，直接内联
 */
const fs = require('fs');
const path = require('path');

const TOOLS = __dirname;
const ROOT = path.resolve(TOOLS, '..');
const OUT = path.resolve(TOOLS, 'test_all_in_one.html');

function read(name) {
  return fs.readFileSync(path.resolve(ROOT, 'node_modules', name), 'utf-8');
}
function stripBOM(s) { return s.charCodeAt(0) === 0xFEFF ? s.slice(1) : s; }

function forceBrowserUMD(s) {
  return s
    .replace(
      /typeof exports === ['"]object['"]\s*&&\s*typeof module !== ['"]undefined['"]/g,
      'false /*forced browser*/'
    )
    .replace(
      /typeof define === ['"]function['"]\s*&&\s*define\.amd/g,
      'false /*forced browser*/'
    );
}

console.log('Reading files...');

// React 生产 UMD
const reactSrc = forceBrowserUMD(stripBOM(read('react/umd/react.production.min.js')));

// ReactDOM 开发 UMD（已修复，完整下载）
const reactDomSrc = forceBrowserUMD(stripBOM(read('react-dom/umd/react-dom.development.js')));

// ReactFlow UMD
const rfSrc = forceBrowserUMD(read('react-flow-renderer/dist/umd/index.js'));

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>VeroRun — All-In-One v4</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: system-ui, sans-serif; background:#f8fafc; color:#1e293b; padding:20px; }
h1 { font-size:18px; margin-bottom:12px; }
#results { margin-bottom:12px; }
.result { padding:6px 12px; border-radius:6px; margin-bottom:4px; font-size:13px; }
.pass { background:#dcfce7; color:#166534; border:1px solid #bbf7d0; }
.fail { background:#fef2f2; color:#991b1b; border:1px solid #fecaca; }
.info { background:#eff6ff; color:#1e40af; border:1px solid #bfdbfe; }
#root { width:100%; height:500px; border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; margin-top:12px; }
</style>
</head>
<body>

<h1>🧪 All-In-One v4 (react-dom 已修复)</h1>
<div id="results"></div>
<div id="root"><p style="padding:20px;color:#94a3b8;">等待...</p></div>

<!-- Script 1: React UMD -->
<script>${reactSrc}</script>

<!-- Script 2: ReactDOM UMD（已修复完整文件） -->
<script>${reactDomSrc}</script>

<!-- Script 3: react-flow-renderer UMD -->
<script>${rfSrc}</script>

<link rel="stylesheet" href="local-libs/style.css"/>

<!-- Script 4: 验证 -->
<script>
(function() {
  var R = document.getElementById('results');
  function p(label, ok, detail) {
    var d = document.createElement('div');
    d.className = 'result ' + (ok ? 'pass' : 'fail');
    d.textContent = (ok ? '✅ ' : '❌ ') + label + (detail ? ' — ' + detail : '');
    R.appendChild(d);
  }
  function i(text) {
    var d = document.createElement('div');
    d.className = 'result info';
    d.textContent = 'ℹ️ ' + text;
    R.appendChild(d);
  }

  try {
    p('React', typeof React !== 'undefined', 'v' + (React.version || '?'));
    p('ReactDOM', typeof ReactDOM !== 'undefined', 'method count=' + (ReactDOM ? Object.keys(ReactDOM).length : 0));
    if (ReactDOM) p('ReactDOM.createRoot', typeof ReactDOM.createRoot === 'function', '');
    
    var lib = typeof ReactFlowRenderer !== 'undefined' ? ReactFlowRenderer 
           : typeof ReactFlow !== 'undefined' ? ReactFlow : null;
    p('ReactFlow', lib !== null, lib ? Object.keys(lib).length + ' exports' : '');
    if (!lib) {
      for (var k in window) { if (k.toLowerCase().indexOf('flow') >= 0) i('  ' + k + ' = ' + typeof window[k]); }
      return;
    }

    ['default','ReactFlow','ReactFlowProvider','Handle','Position',
     'useNodesState','useEdgesState','addEdge','MiniMap','Controls','Background'].forEach(function(k) {
      p('  lib.' + k, typeof lib[k] !== 'undefined', typeof lib[k]);
    });

    var RF = lib.default || lib.ReactFlow || lib;
    var Provider = lib.ReactFlowProvider;
    if (typeof RF !== 'function') { p('主组件', false, 'not function'); return; }

    function N(props) {
      return React.createElement('div', {style:{
        padding:'12px 16px', borderRadius:'8px', background:'#fff',
        border:'2px solid ' + (props.data.color||'#6366f1'), fontSize:'13px', minWidth:'140px',
        boxShadow:'0 1px 3px rgba(0,0,0,0.08)'
      }},
        React.createElement('div',{style:{fontWeight:600,marginBottom:'4px'}},
          (props.data.icon||'') + ' ' + (props.data.label||'')),
        React.createElement('div',{style:{fontSize:'11px',color:'#64748b'}}, props.data.description||''),
        React.createElement(lib.Handle,{type:'target',position:lib.Position.Left,style:{background:'#6366f1'}}),
        React.createElement(lib.Handle,{type:'source',position:lib.Position.Right,style:{background:'#6366f1'}})
      );
    }
    var ns = lib.useNodesState([
      {id:'n1',type:'custom',position:{x:50,y:180},data:{icon:'📡',label:'Data',color:'#2563eb'}},
      {id:'n2',type:'custom',position:{x:350,y:180},data:{icon:'🤖',label:'AI',color:'#7c3aed'}},
      {id:'n3',type:'custom',position:{x:650,y:180},data:{icon:'📤',label:'Publish',color:'#16a34a'}},
    ]);
    var es = lib.useEdgesState([
      {id:'e1-2',source:'n1',target:'n2',style:{stroke:'#94a3b8'}},
      {id:'e2-3',source:'n2',target:'n3',style:{stroke:'#94a3b8'}},
    ]);

    var root = document.getElementById('root');
    ReactDOM.createRoot(root).render(
      React.createElement(Provider, null,
        React.createElement('div',{style:{width:'100%',height:'500px'}},
          React.createElement(RF,{
            nodes:ns[0],edges:es[0],onNodesChange:ns[2],onEdgesChange:es[2],
            nodeTypes:{custom:N},fitView:true,attributionPosition:'bottom-left'
          },
            React.createElement(lib.Controls,null),
            React.createElement(lib.Background,{gap:20,size:1}),
            React.createElement(lib.MiniMap,{style:{width:120,height:80}})
          )
        )
      )
    );
    p('画布渲染', true, '3 节点 + 2 连线');
  } catch(e) {
    p('错误', false, e.message);
    console.error('FULL ERROR:', e);
    if (e.stack) i('  stack: ' + e.stack.substring(0,300));
  }
})();
</script>
</body>
</html>`;

fs.writeFileSync(OUT, html, 'utf-8');
const kb = (html.length / 1024).toFixed(1);
console.log(`✅ Generated: ${OUT} (${kb} KB)`);
