/**
 * 在 Node.js VM 中验证 react-dom UMD 是否能正确初始化
 */
const vm = require('vm');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

// 1. 加载 React UMD
const reactUMD = fs.readFileSync(path.join(ROOT, 'node_modules/react/umd/react.production.min.js'), 'utf-8');

// 2. 加载 react-dom UMD (development)
const reactDomUMD = fs.readFileSync(path.join(ROOT, 'node_modules/react-dom/umd/react-dom.development.js'), 'utf-8');

// 创建沙箱
const sandbox = {
  window: {},
  console: console,
  setTimeout: setTimeout,
  clearTimeout: clearTimeout,
  requestAnimationFrame: (fn) => setTimeout(fn, 16),
  cancelAnimationFrame: (id) => clearTimeout(id),
};
sandbox.self = sandbox.window;
sandbox.globalThis = sandbox.window;
sandbox.global = sandbox.window;

const context = vm.createContext(sandbox);

// 3. 先执行 React UMD
const reactScript = new vm.Script(reactUMD);
reactScript.runInContext(context);
console.log('React loaded:', typeof context.window.React, 'v' + context.window.React.version);
console.log('window keys with React:', Object.keys(context.window).filter(k => k.toLowerCase().includes('react')));

// 4. 再执行 react-dom UMD
try {
  const rdScript = new vm.Script(reactDomUMD);
  rdScript.runInContext(context);
  console.log('\nReactDOM loaded:', typeof context.window.ReactDOM);
  if (context.window.ReactDOM) {
    console.log('ReactDOM keys:', Object.keys(context.window.ReactDOM).length);
    console.log('has createRoot:', typeof context.window.ReactDOM.createRoot);
    console.log('has render:', typeof context.window.ReactDOM.render);
    console.log('sample keys:', Object.keys(context.window.ReactDOM).slice(0, 10));
  }
} catch(e) {
  console.log('\nReactDOM ERROR:', e.message);
}
