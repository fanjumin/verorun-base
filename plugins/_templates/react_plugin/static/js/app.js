/* React Demo — 无构建入口（React UMD + React.createElement，纯静态文件）
 * 系统本地 React 库由 index.html 注入，此文件只依赖 window.__SSO_TOKEN / window.__t。
 * 如需 JSX：见 src/App.jsx + 构建命令（esbuild 产物输出到本文件位置）。
 */
(function () {
  var TOKEN = window.__SSO_TOKEN || '';
  var T = window.__t || {};

  function DemoApp() {
    return React.createElement(
      'div',
      { className: 'rd-card' },
      React.createElement('h2', null, T['demo.title'] || 'React Plugin Demo'),
      React.createElement('p', null, T['demo.desc'] || 'This page is rendered by React 18 (local UMD, no CDN).'),
      React.createElement('p', { className: 'rd-muted' },
        (T['demo.token'] || 'SSO token') + ': ' + (TOKEN ? 'ok' : 'missing')),
      React.createElement('button', { onClick: callApi }, T['demo.call'] || 'Call API'),
      React.createElement('p', { id: 'rd-result', className: 'rd-muted' })
    );
  }

  function callApi() {
    // 同域 API，携带 Bearer token（§15.4：禁止发往第三方域名）
    fetch('/admin/react-demo/api/hello', {
      headers: { Authorization: 'Bearer ' + TOKEN }
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        document.getElementById('rd-result').textContent = JSON.stringify(d);
      })
      .catch(function (e) { console.error(e); });
  }

  var root = document.getElementById('app');
  if (root) {
    ReactDOM.createRoot(root).render(React.createElement(DemoApp, null));
  }
})();
