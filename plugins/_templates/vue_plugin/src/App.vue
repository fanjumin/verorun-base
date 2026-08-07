<!-- 可选 SFC 源码（§16 审核要求：提交打包产物必须附源码 + 可复现构建）
     构建命令（esbuild，项目已有该依赖）：
       npx esbuild src/App.vue --bundle --format=iife --outfile=static/js/app.js --loader:.vue=jsx
     构建后 app.js 会引用系统 UMD 全局 Vue，保持挂载点 #app 不变。 -->
<template>
  <div class="vd-card">
    <h2>{{ title }}</h2>
    <p>{{ desc }}</p>
    <p class="vd-muted">{{ tokenLabel }}: <b>{{ tokenStatus }}</b></p>
    <button @click="callApi">{{ callLabel }}</button>
    <p id="vd-result" class="vd-muted"></p>
  </div>
</template>

<script>
export default {
  name: 'VueDemoApp',
  data() {
    const T = window.__t || {};
    const TOKEN = window.__SSO_TOKEN || '';
    return {
      title: T['demo.title'] || 'Vue Plugin Demo',
      desc: T['demo.desc'] || 'This page is rendered by Vue 3 (local UMD, no CDN).',
      tokenLabel: T['demo.token'] || 'SSO token',
      callLabel: T['demo.call'] || 'Call API',
      tokenStatus: TOKEN ? 'ok' : 'missing'
    };
  },
  methods: {
    callApi() {
      const TOKEN = window.__SSO_TOKEN || '';
      fetch('/admin/vue-demo/api/hello', {
        headers: { Authorization: 'Bearer ' + TOKEN }
      })
        .then((r) => r.json())
        .then((d) => { document.getElementById('vd-result').textContent = JSON.stringify(d); })
        .catch((e) => console.error(e));
    }
  }
};
</script>
