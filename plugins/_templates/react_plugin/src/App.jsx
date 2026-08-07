// 可选 JSX 源码（§16 审核要求：提交打包产物必须附源码 + 可复现构建）
// 构建命令（esbuild，项目已有该依赖）：
//   npx esbuild src/App.jsx --bundle --format=iife --outfile=static/js/app.js
// 构建后 app.js 会引用系统 UMD 全局 React/ReactDOM，保持路径不变。
function DemoApp() {
  const T = window.__t || {};
  const TOKEN = window.__SSO_TOKEN || '';
  const [result, setResult] = React.useState('');

  return (
    <div className="rd-card">
      <h2>{T['demo.title'] || 'React Plugin Demo'}</h2>
      <p>{T['demo.desc'] || 'This page is rendered by React 18 (local UMD, no CDN).'}</p>
      <p className="rd-muted">{(T['demo.token'] || 'SSO token') + ': ' + (TOKEN ? 'ok' : 'missing')}</p>
      <button onClick={() => {
        fetch('/admin/react-demo/api/hello', {
          headers: { Authorization: 'Bearer ' + TOKEN }
        })
          .then((r) => r.json())
          .then((d) => setResult(JSON.stringify(d)))
          .catch((e) => console.error(e));
      }}>{T['demo.call'] || 'Call API'}</button>
      <p className="rd-muted">{result}</p>
    </div>
  );
}

const root = document.getElementById('app');
if (root) ReactDOM.createRoot(root).render(React.createElement(DemoApp, null));
