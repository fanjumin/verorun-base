/* Vue Demo — 无构建入口（Vue 3 UMD 全局 createApp，纯静态文件）
 * 系统本地 Vue 库由 index.html 注入，此文件只依赖 window.__SSO_TOKEN / window.__t。
 * 如需 SFC（.vue）：见 src/App.vue + 构建命令（esbuild 产物输出到本文件位置）。
 */
(function () {
  var TOKEN = window.__SSO_TOKEN || '';
  var T = window.__t || {};

  var app = Vue.createApp({
    template:
      '<div class="vd-card">' +
        '<h2>{{ title }}</h2>' +
        '<p>{{ desc }}</p>' +
        '<p class="vd-muted">{{ tokenLabel }}: <b>{{ tokenStatus }}</b></p>' +
        '<button @click="callApi">{{ callLabel }}</button>' +
        '<p id="vd-result" class="vd-muted"></p>' +
      '</div>',
    data: function () {
      return {
        title: T['demo.title'] || 'Vue Plugin Demo',
        desc: T['demo.desc'] || 'This page is rendered by Vue 3 (local UMD, no CDN).',
        tokenLabel: T['demo.token'] || 'SSO token',
        callLabel: T['demo.call'] || 'Call API',
        tokenStatus: TOKEN ? 'ok' : 'missing'
      };
    },
    methods: {
      callApi: function () {
        // 同域 API，携带 Bearer token（§15.4：禁止发往第三方域名）
        var self = this;
        fetch('/admin/vue-demo/api/hello', {
          headers: { Authorization: 'Bearer ' + TOKEN }
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            document.getElementById('vd-result').textContent = JSON.stringify(d);
          })
          .catch(function (e) { console.error(e); });
      }
    }
  });

  app.mount('#app');
})();
