// ═══════════════════════════════════════════════════════════════════════════
// 自定义 Toast / Modal（替代原生 alert/confirm）
// ═══════════════════════════════════════════════════════════════════════════
function showToast(msg, type) {
  type = type || 'info';
  console.log('[Toast]', type, msg);
  // Unified: use the admin shell's system toast (bottom-center) when embedded
  try {
    if (window.top !== window && window.top.showToast) {
      window.top.showToast(msg, type === 'info' ? '' : type);
      return;
    }
  } catch(e) { console.log('[Toast] top window not accessible, using own body'); }
  // Standalone fallback (page opened directly): keep local implementation
  var colors = {
    error:   { bg: 'rgba(244,63,94,0.15)', border: 'rgba(244,63,94,0.4)', color: '#f43f5e' },
    success: { bg: 'rgba(0,255,159,0.12)', border: 'rgba(0,255,159,0.3)', color: '#00ff9f' },
    info:    { bg: 'rgba(0,245,255,0.1)', border: 'rgba(0,245,255,0.25)', color: '#00f5ff' }
  };
  var c = colors[type] || colors.info;
  var el = document.createElement('div');
  el.style.cssText =
    'position:fixed;top:20px;left:50%;z-index:99999;padding:12px 24px;border-radius:10px;' +
    'font-size:14px;max-width:480px;text-align:center;box-shadow:0 4px 30px rgba(0,0,0,0.5);' +
    'transform:translateX(-50%);transition:opacity 0.3s ease;opacity:0;' +
    'background:' + c.bg + ';border:1px solid ' + c.border + ';color:' + c.color + ';';
  el.textContent = msg;
  // Try parent window first (for iframe), fall back to own body
  var target = document.body;
  try {
    if (window.top !== window && window.top.document && window.top.document.body) {
      target = window.top.document.body;
    }
  } catch(e) { console.log('[Toast] top window not accessible, using own body'); }
  target.appendChild(el);
  requestAnimationFrame(function(){ el.style.opacity = '1'; });
  setTimeout(function(){
    el.style.opacity = '0';
    setTimeout(function(){ if (el.parentNode) el.parentNode.removeChild(el); }, 300);
  }, 3000);
}

function showConfirm(title, message, onConfirm) {
  var overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML =
    '<div class="modal-dialog">' +
    '<div class="modal-title">' + title + '</div>' +
    '<div class="modal-body">' + message + '</div>' +
    '<div class="modal-actions">' +
    '<button class="modal-btn" id="modalCancel">{{ _('Cancel') }}</button>' +
    '<button class="modal-btn danger" id="modalOk">{{ _('Delete') }}</button>' +
    '</div></div>';
  document.body.appendChild(overlay);
  document.getElementById('modalCancel').addEventListener('click', function(){
    document.body.removeChild(overlay);
  });
  document.getElementById('modalOk').addEventListener('click', function(){
    document.body.removeChild(overlay);
    if (onConfirm) onConfirm();
  });
  overlay.addEventListener('click', function(e){
    if (e.target === overlay) document.body.removeChild(overlay);
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// 粒子系统
// ═══════════════════════════════════════════════════════════════════════════
tsParticles.load('particles-js', {
  background: { color: '#050508' },
  fpsLimit: 30,
  particles: {
    number: { value: 48, density: { enable: true, area: 800 } },
    color: { value: ['#00f5ff','#a020f0','#6366f1','#22d3ee','#00ff9f'] },
    shape: { type: 'circle' },
    opacity: { value: { min: 0.1, max: 0.4 } },
    size: { value: { min: 1, max: 3 } },
    links: {
      enable: true,
      distance: 150,
      color: '#00f5ff',
      opacity: 0.08,
      width: 1,
      triangles: { enable: true, opacity: 0.03 }
    },
    move: {
      enable: true,
      speed: 0.8,
      direction: 'none',
      random: true,
      outModes: { default: 'bounce' }
    }
  },
  interactivity: {
    events: {
      onHover: { enable: true, mode: 'grab' },
      onClick: { enable: true, mode: 'push' }
    },
    modes: {
      grab: { distance: 140, links: { opacity: 0.15 } },
      push: { quantity: 2 }
    }
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// 时钟
// ═══════════════════════════════════════════════════════════════════════════
function updateClock() {
  var now = new Date();
  document.getElementById('liveTime').textContent =
    now.getFullYear() + '-' +
    String(now.getMonth()+1).padStart(2,'0') + '-' +
    String(now.getDate()).padStart(2,'0') + ' ' +
    String(now.getHours()).padStart(2,'0') + ':' +
    String(now.getMinutes()).padStart(2,'0') + ':' +
    String(now.getSeconds()).padStart(2,'0');
}
setInterval(updateClock, 1000);
updateClock();

// ═══════════════════════════════════════════════════════════════════════════
// 标签页切换
// ═══════════════════════════════════════════════════════════════════════════
document.querySelectorAll('.tab-btn').forEach(function(btn){
  btn.addEventListener('click', function(){
    document.querySelectorAll('.tab-btn').forEach(function(b){ b.classList.remove('active'); });
    document.querySelectorAll('.tab-content').forEach(function(t){ t.classList.remove('active'); });
    this.classList.add('active');
    var tab = this.getAttribute('data-tab');
    document.getElementById('tab-' + tab).classList.add('active');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// Chart.js 全局配置（暗色调）
// ═══════════════════════════════════════════════════════════════════════════
Chart.defaults.color = '#6b7280';
Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
Chart.defaults.font.family = "'Inter','Noto Sans SC',sans-serif";

// 渐变填充辅助
function createGradient(ctx, chartArea, color1, color2) {
  var gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
  gradient.addColorStop(0, color1);
  gradient.addColorStop(1, color2);
  return gradient;
}

// 图表实例缓存
var charts = {};

// ═══════════════════════════════════════════════════════════════════════════
// API 调用
// ═══════════════════════════════════════════════════════════════════════════
var API_BASE = '/admin/analytics/api/v1';
// GeoIP 设置 API 不在 /api/v1/ 下
var SETTINGS_BASE = '/admin/analytics';
var REFRESH_INTERVAL = 30000; // 30s
var REFRESH_TIMER = null;

// 从 URL 提取 token（iframe 传参用）
var _TOKEN = '';
(function(){
  var m = location.search.match(/[?&]token=([^&]+)/);
  if (m) _TOKEN = decodeURIComponent(m[1]);
})();

function api(path) {
  var headers = {};
  // srcdoc iframe: URL token 或 cookie（与父页面共享）
  var tk = _TOKEN;
  if (!tk) {
    var c = document.cookie.match(/(?:^|;\s*)sso_token=([^;]+)/);
    if (c) tk = c[1];
  }
  if (tk) headers['Authorization'] = 'Bearer ' + tk;
  return fetch(API_BASE + path, {headers: headers}).then(function(r){ return r.json(); });
}

// ═══════════════════════════════════════════════════════════════════════════
// Chart.js 就绪检查（CDN 异步加载时使用）
// ═══════════════════════════════════════════════════════════════════════════
var CHART_READY = false;
var CHART_QUEUE = [];
function checkChart(callback) {
  if (typeof Chart !== 'undefined') {
    if (!CHART_READY) { CHART_READY = true; }
    callback();
  } else {
    if (CHART_QUEUE.indexOf(callback) === -1) CHART_QUEUE.push(callback);
    if (CHART_QUEUE.length === 1) {
      var timer = setInterval(function(){
        if (typeof Chart !== 'undefined') {
          CHART_READY = true;
          var q = CHART_QUEUE.slice();
          CHART_QUEUE = [];
          q.forEach(function(fn){ try{fn()}catch(e){console.error('Chart deferred error:',e)} });
          clearInterval(timer);
        }
      }, 200);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// 实时概览
// ═══════════════════════════════════════════════════════════════════════════
function loadRealtime() {
  api('/realtime').then(function(res){
    if (!res.success) return;
    var d = res.data;
    document.getElementById('onlineCount').textContent = d.online.count;
    document.getElementById('todayPV').textContent = (d.today.pv || 0).toLocaleString();
    document.getElementById('todayUV').textContent = (d.today.uv || 0).toLocaleString();
    document.getElementById('todaySessions').textContent = (d.today.sessions || 0).toLocaleString();
    document.getElementById('todayAvgResp').innerHTML =
      (d.current_hour.avg_response_time || 0) + ' <span style="font-size:14px">ms</span>';
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// 趋势图
// ═══════════════════════════════════════════════════════════════════════════
function loadTrend() {
  api('/trend?days=30').then(function(res){
    if (!res.success || !res.data.length) {
      document.getElementById('trendTable').innerHTML =
        '<div class="empty-state"><div class="icon">📊</div><div class="text">{{ _('No trend data yet, will auto-generate after publishing') }}</div></div>';
      return;
    }
    renderTrendChart(res.data);
    renderTrendTable(res.data);
  });
}

function renderTrendChart(data) {
  var ctx = document.getElementById('trendChart').getContext('2d');
  if (charts.trend) charts.trend.destroy();

  var labels = data.map(function(d){ return d.date.slice(5); });
  checkChart(function(){ charts.trend = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'PV',
        data: data.map(function(d){ return d.pv; }),
        borderColor: '#00f5ff',
        backgroundColor: function(context) {
          var c = context.chart;
          if (!c.chartArea) return 'rgba(0,245,255,0.1)';
          return createGradient(c.ctx, c.chartArea, 'rgba(0,245,255,0.25)', 'rgba(0,245,255,0)');
        },
        fill: true,
        tension: 0.4,
        pointRadius: 2,
        pointHoverRadius: 5,
        borderWidth: 2,
      }, {
        label: 'UV',
        data: data.map(function(d){ return d.uv; }),
        borderColor: '#a020f0',
        backgroundColor: function(context) {
          var c = context.chart;
          if (!c.chartArea) return 'rgba(160,32,240,0.1)';
          return createGradient(c.ctx, c.chartArea, 'rgba(160,32,240,0.2)', 'rgba(160,32,240,0)');
        },
        fill: true,
        tension: 0.4,
        pointRadius: 2,
        pointHoverRadius: 5,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          labels: { color: '#6b7280', font: { size: 11 }, usePointStyle: true, padding: 16 }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
          ticks: { color: '#6b7280', font: { size: 10 }, maxTicksLimit: 10 }
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
          ticks: { color: '#6b7280', font: { size: 10 }, callback: function(v){ return v >= 1000 ? (v/1000).toFixed(1)+'k' : v; } }
        }
      }
    }
  }); });
}

function renderTrendTable(data) {
  var html = '<table class="data-table"><thead><tr><th>{{ _('Date') }}</th><th>PV</th><th>UV</th><th>{{ _('Session') }}</th><th>{{ _('Bounce Rate') }}</th><th>{{ _('Avg Duration') }}</th></tr></thead><tbody>';
  data.forEach(function(d, i){
    html += '<tr>' +
      '<td>' + d.date + '</td>' +
      '<td style="color:var(--blue);font-weight:600">' + (d.pv||0).toLocaleString() + '</td>' +
      '<td style="color:var(--violet);font-weight:600">' + (d.uv||0).toLocaleString() + '</td>' +
      '<td>' + (d.sessions||0).toLocaleString() + '</td>' +
      '<td>' + (d.bounce_rate||0).toFixed(1) + '%</td>' +
      '<td>' + (d.avg_duration||0).toFixed(0) + 's</td>' +
      '</tr>';
  });
  html += '</tbody></table>';
  document.getElementById('trendTable').innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════════════
// 小时分布
// ═══════════════════════════════════════════════════════════════════════════
function loadHourly() {
  api('/hourly').then(function(res){
    if (!res.success) return;
    renderHourlyChart(res.data);
  });
}

function renderHourlyChart(data) {
  var ctx = document.getElementById('hourlyChart').getContext('2d');
  if (charts.hourly) charts.hourly.destroy();

  // 构建 0-23 的完整数组
  var map = {};
  data.forEach(function(d){ map[d.hour] = d; });
  var labels = [];
  var pvData = [];
  var uvData = [];
  for (var h = 0; h < 24; h++) {
    labels.push(h + ':00');
    var entry = map[h] || {pv:0, uv:0, session_count:0};
    pvData.push(entry.pv);
    uvData.push(entry.uv);
  }

  checkChart(function(){ charts.hourly = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'PV',
        data: pvData,
        backgroundColor: 'rgba(0,245,255,0.4)',
        borderColor: '#00f5ff',
        borderWidth: 1,
        borderRadius: 2,
      }, {
        label: 'UV',
        data: uvData,
        backgroundColor: 'rgba(160,32,240,0.4)',
        borderColor: '#a020f0',
        borderWidth: 1,
        borderRadius: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#6b7280', font: { size: 11 }, usePointStyle: true, padding: 16 } }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#6b7280', font: { size: 9 }, maxTicksLimit: 12 }
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
          ticks: { color: '#6b7280', font: { size: 10 } }
        }
      }
    }
  }); });
}

// ═══════════════════════════════════════════════════════════════════════════
// 页面排行
// ═══════════════════════════════════════════════════════════════════════════
function loadPages() {
  api('/pages?days=30&limit=20').then(function(res){
    if (!res.success || !res.data.length) {
      document.getElementById('pagesContent').innerHTML =
        '<div class="empty-state"><div class="icon">📄</div><div class="text">{{ _('No page data') }}</div></div>';
      return;
    }
    var html = '<table class="data-table"><thead><tr><th>#</th><th>{{ _('Path') }}</th><th>PV</th><th>UV</th><th>{{ _('Avg Response') }}</th></tr></thead><tbody>';
    res.data.forEach(function(d, i){
      html += '<tr>' +
        '<td class="rank-num">#' + (i+1) + '</td>' +
        '<td style="font-family:var(--font-en);font-size:12px;color:var(--cyan)">' + d.path + '</td>' +
        '<td style="color:var(--blue);font-weight:600">' + (d.pv||0).toLocaleString() + '</td>' +
        '<td>' + (d.uv||0).toLocaleString() + '</td>' +
        '<td>' + (d.avg_time||0) + ' ms</td>' +
        '</tr>';
    });
    html += '</tbody></table>';
    document.getElementById('pagesContent').innerHTML = html;
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// 来源分析
// ═══════════════════════════════════════════════════════════════════════════
function loadSources() {
  api('/sources?days=30').then(function(res){
    if (!res.success) return;
    renderSourcesChart(res.data);
    renderSourcesTable(res.data);
  });
}

function renderSourcesChart(data) {
  var ctx = document.getElementById('sourcesChart').getContext('2d');
  if (charts.sources) charts.sources.destroy();

  var top5 = data.slice(0, 5);
  var labels = top5.map(function(d){ return d.source_name; });
  var values = top5.map(function(d){ return d.pv; });
  var colors = ['#00f5ff','#a020f0','#6366f1','#22d3ee','#00ff9f'];

  checkChart(function(){ charts.sources = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: 'rgba(5,5,8,0.5)',
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#6b7280', font: { size: 11 }, padding: 12 }
        }
      }
    }
  }); });
}

function renderSourcesTable(data) {
  var html = '<table class="data-table"><thead><tr><th>{{ _('Type') }}</th><th>{{ _('Source') }}</th><th>PV</th><th>UV</th><th>{{ _('Percentage') }}</th></tr></thead><tbody>';
  data.forEach(function(d){
    var pct = parseFloat(d.pct) || 0;
    html += '<tr>' +
      '<td><span style="font-size:11px;padding:2px 6px;border-radius:4px;background:rgba(99,102,241,0.1);color:var(--indigo)">' + d.source_type + '</span></td>' +
      '<td>' + d.source_name + '</td>' +
      '<td style="color:var(--blue);font-weight:600">' + (d.pv||0).toLocaleString() + '</td>' +
      '<td>' + (d.uv||0).toLocaleString() + '</td>' +
      '<td><span class="pct-bar" style="width:' + pct + 'px;max-width:100px"></span>' + pct.toFixed(1) + '%</td>' +
      '</tr>';
  });
  html += '</tbody></table>';
  document.getElementById('sourcesContent').innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════════════
// 访问分布图（主视图）— ECharts 中国地图热力图 + 省份/城市双排名
// ═══════════════════════════════════════════════════════════════════════════

// 城市 → 省份映射（键 = 拼音 + 中文双覆盖，值 = 中文省份名，匹配 china.json GeoJSON）
// 注意：键值均不调用 _() —— 键被翻译后与 API 返回的城市名不匹配；值被翻译后无法匹配中文 GeoJSON
var _CITY_PROVINCE = {
  // 直辖市
  'Beijing': '北京市', '北京': '北京市',
  'Shanghai': '上海市', '上海': '上海市',
  'Tianjin': '天津市', '天津': '天津市',
  'Chongqing': '重庆市', '重庆': '重庆市',
  // 广东省
  'Guangzhou': '广东省', '广州': '广东省', 'Guangzhou City': '广东省',
  'Shenzhen': '广东省', '深圳': '广东省', 'Shenzhen City': '广东省',
  'Dongguan': '广东省', '东莞': '广东省', 'Dongguan City': '广东省',
  'Foshan': '广东省', '佛山': '广东省', 'Foshan City': '广东省',
  'Zhuhai': '广东省', '珠海': '广东省', 'Zhuhai City': '广东省',
  'Huizhou': '广东省', '惠州': '广东省', 'Huizhou City': '广东省',
  'Zhongshan': '广东省', '中山': '广东省', 'Zhongshan City': '广东省',
  'Shantou': '广东省', '汕头': '广东省',
  'Jiangmen': '广东省', '江门': '广东省',
  'Zhanjiang': '广东省', '湛江': '广东省',
  // 江苏省
  'Nanjing': '江苏省', '南京': '江苏省', 'Nanjing City': '江苏省',
  'Suzhou': '江苏省', '苏州': '江苏省', 'Suzhou City': '江苏省',
  'Wuxi': '江苏省', '无锡': '江苏省', 'Wuxi City': '江苏省',
  'Changzhou': '江苏省', '常州': '江苏省', 'Changzhou City': '江苏省',
  'Nantong': '江苏省', '南通': '江苏省', 'Nantong City': '江苏省',
  'Xuzhou': '江苏省', '徐州': '江苏省',
  'Yangzhou': '江苏省', '扬州': '江苏省', 'Yangzhou City': '江苏省',
  'Zhenjiang': '江苏省', '镇江': '江苏省',
  'Yancheng': '江苏省', '盐城': '江苏省',
  'Taizhou': '江苏省', '泰州': '江苏省',
  // 浙江省
  'Hangzhou': '浙江省', '杭州': '浙江省', 'Hangzhou City': '浙江省',
  'Ningbo': '浙江省', '宁波': '浙江省', 'Ningbo City': '浙江省',
  'Wenzhou': '浙江省', '温州': '浙江省', 'Wenzhou City': '浙江省',
  'Jiaxing': '浙江省', '嘉兴': '浙江省', 'Jiaxing City': '浙江省',
  'Shaoxing': '浙江省', '绍兴': '浙江省', 'Shaoxing City': '浙江省',
  'Jinhua': '浙江省', '金华': '浙江省', 'Jinhua City': '浙江省',
  'Huzhou': '浙江省', '湖州': '浙江省',
  // 四川省
  'Chengdu': '四川省', '成都': '四川省', 'Chengdu City': '四川省',
  'Mianyang': '四川省', '绵阳': '四川省', 'Mianyang City': '四川省',
  'Yibin': '四川省', '宜宾': '四川省', 'Yibin City': '四川省',
  'Deyang': '四川省', '德阳': '四川省',
  'Luzhou': '四川省', '泸州': '四川省',
  // 湖北省
  'Wuhan': '湖北省', '武汉': '湖北省', 'Wuhan City': '湖北省',
  'Yichang': '湖北省', '宜昌': '湖北省', 'Yichang City': '湖北省',
  'Xiangyang': '湖北省', '襄阳': '湖北省', 'Xiangyang City': '湖北省',
  'Jingzhou': '湖北省', '荆州': '湖北省',
  'Huangshi': '湖北省', '黄石': '湖北省',
  // 湖南省
  'Changsha': '湖南省', '长沙': '湖南省', 'Changsha City': '湖南省',
  'Zhuzhou': '湖南省', '株洲': '湖南省', 'Zhuzhou City': '湖南省',
  'Yueyang': '湖南省', '岳阳': '湖南省', 'Yueyang City': '湖南省',
  'Hengyang': '湖南省', '衡阳': '湖南省',
  'Changde': '湖南省', '常德': '湖南省',
  // 陕西省
  "Xi'an": '陕西省', "Xi'an City": '陕西省', 'Xian': '陕西省', '西安': '陕西省',
  'Xianyang': '陕西省', '咸阳': '陕西省', 'Xianyang City': '陕西省',
  'Baoji': '陕西省', '宝鸡': '陕西省',
  // 河南省
  'Zhengzhou': '河南省', '郑州': '河南省', 'Zhengzhou City': '河南省',
  'Luoyang': '河南省', '洛阳': '河南省', 'Luoyang City': '河南省',
  'Kaifeng': '河南省', '开封': '河南省', 'Kaifeng City': '河南省',
  'Xinxiang': '河南省', '新乡': '河南省',
  'Nanyang': '河南省', '南阳': '河南省',
  // 山东省
  'Jinan': '山东省', '济南': '山东省', 'Jinan City': '山东省',
  'Qingdao': '山东省', '青岛': '山东省', 'Qingdao City': '山东省',
  'Yantai': '山东省', '烟台': '山东省', 'Yantai City': '山东省',
  'Weifang': '山东省', '潍坊': '山东省', 'Weifang City': '山东省',
  'Weihai': '山东省', '威海': '山东省', 'Weihai City': '山东省',
  'Linyi': '山东省', '临沂': '山东省', 'Linyi City': '山东省',
  'Zibo': '山东省', '淄博': '山东省',
  'Jining': '山东省', '济宁': '山东省',
  'Rizhao': '山东省', '日照': '山东省',
  // 福建省
  'Fuzhou': '福建省', '福州': '福建省', 'Fuzhou City': '福建省',
  'Xiamen': '福建省', '厦门': '福建省', 'Xiamen City': '福建省',
  'Quanzhou': '福建省', '泉州': '福建省', 'Quanzhou City': '福建省',
  'Zhangzhou': '福建省', '漳州': '福建省',
  'Putian': '福建省', '莆田': '福建省',
  // 安徽省
  'Hefei': '安徽省', '合肥': '安徽省', 'Hefei City': '安徽省',
  'Wuhu': '安徽省', '芜湖': '安徽省', 'Wuhu City': '安徽省',
  'Bengbu': '安徽省', '蚌埠': '安徽省', 'Bengbu City': '安徽省',
  'Maanshan': '安徽省', '马鞍山': '安徽省',
  'Anqing': '安徽省', '安庆': '安徽省',
  // 辽宁省
  'Shenyang': '辽宁省', '沈阳': '辽宁省', 'Shenyang City': '辽宁省',
  'Dalian': '辽宁省', '大连': '辽宁省', 'Dalian City': '辽宁省',
  'Anshan': '辽宁省', '鞍山': '辽宁省',
  'Fushun': '辽宁省', '抚顺': '辽宁省',
  // 黑龙江省
  'Harbin': '黑龙江省', '哈尔滨': '黑龙江省', 'Harbin City': '黑龙江省',
  'Daqing': '黑龙江省', '大庆': '黑龙江省',
  'Qiqihar': '黑龙江省', '齐齐哈尔': '黑龙江省',
  // 吉林省
  'Changchun': '吉林省', '长春': '吉林省', 'Changchun City': '吉林省',
  'Jilin': '吉林省', '吉林': '吉林省',
  // 河北省
  'Shijiazhuang': '河北省', '石家庄': '河北省', 'Shijiazhuang City': '河北省',
  'Tangshan': '河北省', '唐山': '河北省', 'Tangshan City': '河北省',
  'Baoding': '河北省', '保定': '河北省', 'Baoding City': '河北省',
  'Langfang': '河北省', '廊坊': '河北省', 'Langfang City': '河北省',
  'Handan': '河北省', '邯郸': '河北省',
  'Qinhuangdao': '河北省', '秦皇岛': '河北省',
  // 山西省
  'Taiyuan': '山西省', '太原': '山西省', 'Taiyuan City': '山西省',
  'Datong': '山西省', '大同': '山西省',
  'Linfen': '山西省', '临汾': '山西省',
  // 云南省
  'Kunming': '云南省', '昆明': '云南省', 'Kunming City': '云南省',
  'Dali': '云南省', '大理': '云南省',
  'Lijiang': '云南省', '丽江': '云南省',
  // 贵州省
  'Guiyang': '贵州省', '贵阳': '贵州省', 'Guiyang City': '贵州省',
  'Zunyi': '贵州省', '遵义': '贵州省', 'Zunyi City': '贵州省',
  // 广西
  'Nanning': '广西壮族自治区', '南宁': '广西壮族自治区', 'Nanning City': '广西壮族自治区',
  'Guilin': '广西壮族自治区', '桂林': '广西壮族自治区', 'Guilin City': '广西壮族自治区',
  'Liuzhou': '广西壮族自治区', '柳州': '广西壮族自治区',
  // 江西省
  'Nanchang': '江西省', '南昌': '江西省', 'Nanchang City': '江西省',
  'Jiujiang': '江西省', '九江': '江西省',
  'Ganzhou': '江西省', '赣州': '江西省',
  // 海南省
  'Haikou': '海南省', '海口': '海南省', 'Haikou City': '海南省',
  'Sanya': '海南省', '三亚': '海南省', 'Sanya City': '海南省',
  // 甘肃省
  'Lanzhou': '甘肃省', '兰州': '甘肃省', 'Lanzhou City': '甘肃省',
  'Tianshui': '甘肃省', '天水': '甘肃省',
  // 内蒙古
  'Hohhot': '内蒙古自治区', '呼和浩特': '内蒙古自治区', 'Hohhot City': '内蒙古自治区',
  'Baotou': '内蒙古自治区', '包头': '内蒙古自治区',
  // 新疆
  'Urumqi': '新疆维吾尔自治区', '乌鲁木齐': '新疆维吾尔自治区', 'Urumqi City': '新疆维吾尔自治区',
  // 西藏
  'Lhasa': '西藏自治区', '拉萨': '西藏自治区', 'Lhasa City': '西藏自治区',
  // 青海
  'Xining': '青海省', '西宁': '青海省', 'Xining City': '青海省',
  // 宁夏
  'Yinchuan': '宁夏回族自治区', '银川': '宁夏回族自治区', 'Yinchuan City': '宁夏回族自治区',
  // 港澳台
  'Hong Kong': '香港特别行政区', '香港': '香港特别行政区',
  'Macau': '澳门特别行政区', '澳门': '澳门特别行政区',
  'Taiwan': '台湾省', '台湾': '台湾省',
  'Taipei': '台湾省', '台北': '台湾省', 'Taipei City': '台湾省',
  'New Taipei': '台湾省', '新北': '台湾省',
  'Kaohsiung': '台湾省', '高雄': '台湾省',
};

function loadChinaCities(skipMap) {
  api('/geo/china-cities?days=30').then(function(res){
    if (!res.success || !res.data.length) {
      var titleEl = document.getElementById('mapTitle');
      if (titleEl) titleEl.textContent = _MARKET === 'cn' ? '{{ _('🇨🇳 China') }}' : '{{ _('🌍 World') }}';
      document.getElementById('chinaMapChart').innerHTML =
        '<div class="empty-state" style="padding:40px 20px"><div class="icon">&#x1F1E8;&#x1F1F3;</div>' +
        '<div class="text">{{ _('No geographic data yet') }}</div>' +
        '<div class="text" style="font-size:12px;color:var(--text-dim);margin-top:8px;max-width:400px;margin-left:auto;margin-right:auto">{{ _('Go to the Settings tab to set up GeoIP databases — ip2region (free, no registration) for Chinese IPs or MaxMind GeoLite2 for international coverage.') }}</div></div>';
      document.getElementById('chinaCityContent').innerHTML = '';
      document.getElementById('chinaProvinceContent').innerHTML = '';
      toggleCountrySection(true);
      return;
    }
    // 聚合省份数据（未匹配的归入「其他地区」，避免地级市混入省列表）
    var provMap = {};
    var chinaData = [];
    res.data.forEach(function(d){
      var prov = _CITY_PROVINCE[d.city];
      if (!prov) {
        // 不含中文 → 境外数据跳过
        if (!/[\u4e00-\u9fff]/.test(d.city||'')) return;
        prov = "{{ _('Other Regions') }}";  // 未识别的中文城市统一归类
      }
      if (!provMap[prov]) provMap[prov] = {pv:0, uv:0};
      provMap[prov].pv += (d.pv||0);
      provMap[prov].uv += (d.uv||0);
      chinaData.push(d);
    });
    var provinces = Object.keys(provMap).map(function(k){ return {name:k, pv:provMap[k].pv, uv:provMap[k].uv}; });
    provinces.sort(function(a,b){ return b.pv - a.pv; });

    if (!skipMap) renderChinaMap(provinces);
    renderChinaProvinceTable(provinces);
    renderChinaCityTable(chinaData.slice(0, 15));
  });
}

// ECharts 中国地图（省份热力图）
function renderChinaMap(provinces) {
  var titleEl = document.getElementById('mapTitle');
  if (titleEl) titleEl.textContent = '{{ _('🇨🇳 China') }}';
  var dom = document.getElementById('chinaMapChart');
  if (charts.chinaMap) charts.chinaMap.dispose();

  // 构建 name→value 映射
  var pvMax = 0;
  var mapData = [];
  provinces.forEach(function(p){
    mapData.push({name: p.name, value: p.pv});
    if (p.pv > pvMax) pvMax = p.pv;
  });
  if (pvMax === 0) pvMax = 1;

  // 加载中国地图 GeoJSON
  fetch('/admin/analytics/static/china.json')
    .then(function(r){ return r.json(); })
    .then(function(geoJson){
      echarts.registerMap('china', geoJson);
      charts.chinaMap = echarts.init(dom);

      var option = {
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(10,10,18,0.92)',
          borderColor: 'rgba(0,245,255,0.2)',
          textStyle: { color: '#e2e4e9', fontSize: 12 },
          formatter: function(p){
            if (!p.value) return '<b>' + p.name + '</b><br/>{{ _('No data') }}';
            return '<b>' + p.name + '</b><br/>PV: ' + p.value.toLocaleString();
          }
        },
        visualMap: {
          min: 0,
          max: pvMax,
          left: 'left',
          bottom: 10,
          text: ['{{ _('High') }}', '{{ _('Low') }}'],
          textStyle: { color: '#6b7280' },
          inRange: {
            color: ['#0f1a2e', '#1a3860', '#2568a0', '#3d98d0', '#00f5ff']
          },
          calculable: true
        },
        series: [{
          type: 'map',
          map: 'china',
          roam: false,
          zoom: 1.15,
          center: [104.5, 36],
          label: {
            show: true,
            color: '#6b7280',
            fontSize: 9,
            formatter: function(p){ return mapData.some(function(d){return d.name===p.name}) ? p.name : ''; }
          },
          emphasis: {
            label: { show: true, color: '#00f5ff', fontSize: 12 },
            itemStyle: { areaColor: 'rgba(0,245,255,0.25)' }
          },
          itemStyle: {
            borderColor: 'rgba(255,255,255,0.08)',
            borderWidth: 0.5,
            areaColor: '#0a1628'
          },
          data: mapData
        }]
      };
      charts.chinaMap.setOption(option);
    })
    .catch(function(){
      dom.innerHTML = '<div class="empty-state" style="padding:60px 0"><div class="text" style="color:var(--rose)">{{ _('Map loading failed (network issue). See table below for data.') }}</div></div>';
    });
}

// ── ISO 国家码 → ECharts 国家名映射（世界地图用） ──
var _COUNTRY_NAMES = {
  'CN':'China','US':'United States','JP':'Japan','KR':'South Korea','GB':'United Kingdom',
  'DE':'Germany','FR':'France','RU':'Russia','IN':'India','BR':'Brazil','CA':'Canada',
  'AU':'Australia','SG':'Singapore','MY':'Malaysia','TH':'Thailand','VN':'Vietnam',
  'ID':'Indonesia','PH':'Philippines','NL':'Netherlands','IT':'Italy','ES':'Spain',
  'SE':'Sweden','CH':'Switzerland','HK':'Hong Kong','TW':'Taiwan','MO':'Macau',
  'AE':'United Arab Emirates','SA':'Saudi Arabia','NO':'Norway','FI':'Finland',
  'DK':'Denmark','BE':'Belgium','AT':'Austria','IE':'Ireland','NZ':'New Zealand',
  'PL':'Poland','CZ':'Czech Republic','PT':'Portugal','GR':'Greece','HU':'Hungary',
  'IL':'Israel','TR':'Turkey','ZA':'South Africa','MX':'Mexico','AR':'Argentina',
  'CO':'Colombia','CL':'Chile','PE':'Peru','EG':'Egypt','NG':'Nigeria','KE':'Kenya',
  'PK':'Pakistan','BD':'Bangladesh','LK':'Sri Lanka','MM':'Myanmar','KH':'Cambodia',
  'LA':'Laos','MN':'Mongolia','KZ':'Kazakhstan','UZ':'Uzbekistan','RO':'Romania',
  'UA':'Ukraine','SK':'Slovakia','SI':'Slovenia','HR':'Croatia','BG':'Bulgaria',
  'RS':'Serbia','LT':'Lithuania','LV':'Latvia','EE':'Estonia','IS':'Iceland',
  'LU':'Luxembourg','MT':'Malta','CY':'Cyprus','CR':'Costa Rica','PA':'Panama',
  'GT':'Guatemala','DO':'Dominican Republic','PR':'Puerto Rico','EC':'Ecuador',
  'VE':'Venezuela','PY':'Paraguay','UY':'Uruguay','BO':'Bolivia','TT':'Trinidad and Tobago'
};

// ISO 国家码 → 国旗 emoji
function _flagEmoji(cc) {
  if (!cc || cc.length !== 2) return '';
  return String.fromCodePoint(0x1F1E6 + cc.charCodeAt(0) - 65) + String.fromCodePoint(0x1F1E6 + cc.charCodeAt(1) - 65);
}

// 世界地图（国家热力图）— 国际模式替代中国地图
function loadWorldMap() {
  api('/geo?days=30').then(function(res){
    if (!res.success || !res.data.length) {
      var titleEl = document.getElementById('mapTitle');
      if (titleEl) titleEl.textContent = '{{ _('🌍 World') }}';
      document.getElementById('chinaMapChart').innerHTML =
        '<div class="empty-state" style="padding:40px 20px"><div class="icon">🌍</div>' +
        '<div class="text">{{ _('No geographic data yet') }}</div>' +
        '<div class="text" style="font-size:12px;color:var(--text-dim);margin-top:8px;max-width:400px;margin-left:auto;margin-right:auto">{{ _('Go to the Settings tab to set up GeoIP databases — MaxMind GeoLite2 (free registration) for international coverage or ip2region for Chinese IPs.') }}</div></div>';
      return;
    }
    renderWorldMap(res.data);
  });
}
// 世界城市/国家排名（国际模式替代中国省份/城市表）
function loadWorldCities() {
  api('/geo/cities?days=30').then(function(res){
    if (!res.success || !res.data.length) {
      document.getElementById('chinaProvinceContent').innerHTML =
        '<div class="empty-state"><div class="icon">🌍</div><div class="text">{{ _('No city data') }}</div></div>';
      document.getElementById('chinaCityContent').innerHTML =
        '<div class="empty-state"><div class="icon">🌍</div><div class="text">{{ _('No city data') }}</div></div>';
      return;
    }
    // 按国家聚合
    var countryMap = {};
    res.data.forEach(function(d){
      var cc = d.country || 'XX';
      if (!countryMap[cc]) countryMap[cc] = {name: _COUNTRY_NAMES[cc] || cc, country: cc, pv:0, uv:0};
      countryMap[cc].pv += (d.pv||0);
      countryMap[cc].uv += (d.uv||0);
    });
    var countries = Object.keys(countryMap).map(function(k){ return countryMap[k]; });
    countries.sort(function(a,b){ return b.pv - a.pv; });

    renderWorldProvinceTable(countries);
    renderWorldCityTable(res.data.slice(0, 15));
  });
}

// 世界国家排名表
function renderWorldProvinceTable(countries) {
  var top10 = countries.slice(0, 10);
  var totalPv = countries.reduce(function(s,d){ return s + d.pv; }, 0) || 1;
  var html = '<table class="data-table"><thead><tr><th>#</th><th>{{ _('Country') }}</th><th>PV</th><th>{{ _('Percentage') }}</th></tr></thead><tbody>';
  top10.forEach(function(d, i){
    var pct = (d.pv / totalPv * 100).toFixed(1);
    var flag = _flagEmoji(d.country);
    html += '<tr>' +
      '<td style="color:var(--text-dim);font-size:11px">' + (i+1) + '</td>' +
      '<td style="font-weight:600">' + flag + ' ' + d.name + '</td>' +
      '<td style="color:var(--blue);font-weight:600">' + d.pv.toLocaleString() + '</td>' +
      '<td><span class="pct-bar" style="width:' + Math.min(pct*3,100) + 'px;max-width:100px"></span>' + pct + '%</td>' +
      '</tr>';
  });
  html += '</tbody></table>';
  document.getElementById('chinaProvinceContent').innerHTML = html;
}

// 世界城市明细表
function renderWorldCityTable(cities) {
  var totalPv = cities.reduce(function(s,d){ return s + (d.pv||0); }, 0) || 1;
  var html = '<table class="data-table"><thead><tr><th>#</th><th>{{ _('Country') }}</th><th>{{ _('City') }}</th><th>PV</th><th>UV</th></tr></thead><tbody>';
  cities.forEach(function(d, i){
    var pct = ((d.pv||0) / totalPv * 100).toFixed(1);
    var flag = _flagEmoji(d.country);
    html += '<tr>' +
      '<td style="color:var(--text-dim);font-size:11px">' + (i+1) + '</td>' +
      '<td>' + flag + '</td>' +
      '<td style="font-weight:600">' + (d.city || '{{ _('Unknown') }}') + '</td>' +
      '<td style="color:var(--red);font-weight:600">' + (d.pv||0).toLocaleString() + '</td>' +
      '<td>' + (d.uv||0).toLocaleString() + '</td>' +
      '</tr>';
  });
  html += '</tbody></table>';
  document.getElementById('chinaCityContent').innerHTML = html;
}

function renderWorldMap(data) {
  var dom = document.getElementById('chinaMapChart');
  if (charts.chinaMap) charts.chinaMap.dispose();
  var pvMax = 0, mapData = [];
  data.forEach(function(d){
    var name = _COUNTRY_NAMES[d.country] || d.country;
    mapData.push({name: name, value: d.pv || 0});
    if (d.pv > pvMax) pvMax = d.pv;
  });
  if (pvMax === 0) pvMax = 1;
  fetch('/admin/analytics/static/world.json')
    .then(function(r){ return r.json(); })
    .then(function(geoJson){
      _worldGeoJson = geoJson;
      echarts.registerMap('world', geoJson);
      charts.chinaMap = echarts.init(dom);
      var option = {
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(10,10,18,0.92)',
          borderColor: 'rgba(0,245,255,0.2)',
          textStyle: { color: '#e2e4e9', fontSize: 12 },
          formatter: function(p){
            return p.value ? '<b>' + p.name + '</b><br/>PV: ' + p.value.toLocaleString()
              : '<b>' + p.name + '</b><br/>{{ _('No data') }}';
          }
        },
        visualMap: {
          min: 0, max: pvMax, left: 'left', bottom: 10,
          text: ['{{ _('High') }}', '{{ _('Low') }}'],
          textStyle: { color: '#6b7280' },
          inRange: { color: ['#0f1a2e', '#1a3860', '#2568a0', '#3d98d0', '#00f5ff'] },
          calculable: true
        },
        series: [{
          type: 'map', map: 'world', roam: true, scaleLimit: {min:1, max:20},
          label: {
            show: true, color: '#6b7280', fontSize: 8,
            formatter: function(p){ return mapData.some(function(d){return d.name===p.name}) ? p.name : ''; }
          },
          emphasis: {
            label: { show: true, color: '#00f5ff', fontSize: 12 },
            itemStyle: { areaColor: 'rgba(0,245,255,0.25)' }
          },
          itemStyle: {
            borderColor: 'rgba(255,255,255,0.08)', borderWidth: 0.5, areaColor: '#0a1628'
          },
          data: mapData
        }]
      };
      charts.chinaMap.setOption(option);
      // Click country → zoom in
      charts.chinaMap.off('click');
      charts.chinaMap.on('click', function(params){
        if (!params.name || !_worldGeoJson) return;
        var f = _worldGeoJson.features.find(function(x){ return x.properties.name === params.name; });
        if (!f) return;
        // Compute centroid from all coordinates
        var lons=[], lats=[];
        function walk(coords){
          if (typeof coords[0]==='number') { lons.push(coords[0]); lats.push(coords[1]); return; }
          coords.forEach(function(c){ walk(c); });
        }
        walk(f.geometry.coordinates);
        if (!lons.length) return;
        var cx = lons.reduce(function(a,b){return a+b;},0)/lons.length;
        var cy = lats.reduce(function(a,b){return a+b;},0)/lats.length;
        charts.chinaMap.setOption({series:[{center:[cx,cy], zoom:6}]});
        var backBtn = document.getElementById('mapBackBtn');
        if (backBtn) backBtn.style.display = '';
      });
    })
    .catch(function(){
      dom.innerHTML = '<div class="empty-state" style="padding:60px 0"><div class="text" style="color:var(--rose)">{{ _('World map loading failed (network issue). See table below for data.') }}</div></div>';
    });
}

// 省份排名表
function renderChinaProvinceTable(provinces) {
  var top10 = provinces.slice(0, 10);
  var totalPv = provinces.reduce(function(s,p){ return s + p.pv; }, 0) || 1;
  var html = '<table class="data-table"><thead><tr><th>#</th><th>{{ _('Province') }}</th><th>PV</th><th>{{ _('Percentage') }}</th></tr></thead><tbody>';
  top10.forEach(function(d, i){
    var pct = (d.pv / totalPv * 100).toFixed(1);
    html += '<tr>' +
      '<td style="color:var(--text-dim);font-size:11px">' + (i+1) + '</td>' +
      '<td style="font-weight:600">' + d.name + '</td>' +
      '<td style="color:var(--blue);font-weight:600">' + d.pv.toLocaleString() + '</td>' +
      '<td><span class="pct-bar" style="width:' + Math.min(pct*3,100) + 'px;max-width:100px"></span>' + pct + '%</td>' +
      '</tr>';
  });
  html += '</tbody></table>';
  document.getElementById('chinaProvinceContent').innerHTML = html;
}

// 城市明细表
function renderChinaCityTable(data) {
  var totalPv = data.reduce(function(s,d){ return s + (d.pv||0); }, 0) || 1;
  var html = '<table class=\"data-table\"><thead><tr><th>#</th><th>{{ _('City') }}</th><th>PV</th><th>UV</th><th>{{ _('Percentage') }}</th></tr></thead><tbody>';
  data.forEach(function(d, i){
    var pct = ((d.pv||0) / totalPv * 100).toFixed(1);
    html += '<tr>' +
      '<td style=\"color:var(--text-dim);font-size:11px\">' + (i+1) + '</td>' +
      '<td style=\"font-weight:600\">' + (d.city || '{{ _('Unknown') }}') + '</td>' +
      '<td style=\"color:var(--red);font-weight:600\">' + (d.pv||0).toLocaleString() + '</td>' +
      '<td>' + (d.uv||0).toLocaleString() + '</td>' +
      '<td>' + pct + '%</td>' +
      '</tr>';
  });
  html += '</tbody></table>';
  document.getElementById('chinaCityContent').innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════════════
// 国家/地区分布（次要，可折叠）
// ═══════════════════════════════════════════════════════════════════════════
var countryDataLoaded = false;
function loadGeo() {
  api('/geo?days=30').then(function(res){
    if (!res.success || !res.data.length) {
      document.getElementById('geoContent').innerHTML =
        '<div class="empty-state"><div class="icon">🌍</div><div class="text">{{ _('No geolocation data (GeoIP required)') }}</div></div>';
      return;
    }
    countryDataLoaded = true;
    renderGeoChart(res.data);
    renderGeoTable(res.data);
  });
}

function toggleCountrySection(forceShow) {
  var sec = document.getElementById('countrySection');
  var icon = document.getElementById('countryToggleIcon');
  if (forceShow || sec.style.display === 'none') {
    sec.style.display = '';
    if (icon) icon.textContent = '▼';
    if (!countryDataLoaded) loadGeo();
  } else {
    sec.style.display = 'none';
    if (icon) icon.textContent = '▶';
  }
}

function renderGeoChart(data) {
  var ctx = document.getElementById('geoChart').getContext('2d');
  if (charts.geo) charts.geo.destroy();

  var top10 = data.slice(0, 10);
  var labels = top10.map(function(d){ return d.country || '{{ _('Unknown') }}'; });
  var values = top10.map(function(d){ return d.pv; });

  checkChart(function(){ charts.geo = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'PV',
        data: values,
        backgroundColor: 'rgba(0,245,255,0.4)',
        borderColor: '#00f5ff',
        borderWidth: 1,
        borderRadius: 2,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
          ticks: { color: '#6b7280', font: { size: 10 } }
        },
        y: {
          grid: { display: false },
          ticks: { color: '#6b7280', font: { size: 11 } }
        }
      }
    }
  }); });
}

function renderGeoTable(data) {
  var html = '<table class="data-table"><thead><tr><th>{{ _('Country') }}</th><th>PV</th><th>UV</th></tr></thead><tbody>';
  data.forEach(function(d){
    var cc = d.country || '{{ _('Unknown') }}';
    html += '<tr>' +
      '<td>' + cc + '</td>' +
      '<td style="color:var(--blue)">' + (d.pv||0).toLocaleString() + '</td>' +
      '<td>' + (d.uv||0).toLocaleString() + '</td>' +
      '</tr>';
  });
  html += '</tbody></table>';
  document.getElementById('geoContent').innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════════════
// 设备分布
// ═══════════════════════════════════════════════════════════════════════════
function loadDevices() {
  api('/devices?days=30').then(function(res){
    if (!res.success) return;
    renderDeviceChart(res.data.by_device);
    renderDeviceDetail(res.data.by_browser, res.data.by_os);
  });
}

function renderDeviceChart(data) {
  var ctx = document.getElementById('deviceChart').getContext('2d');
  if (charts.device) charts.device.destroy();

  if (!data.length) {
    document.getElementById('deviceContent').innerHTML =
      '<div class="empty-state"><div class="icon">📱</div><div class="text">{{ _('No device data') }}</div></div>';
    return;
  }

  var labels = data.map(function(d){ return d.device_type; });
  var values = data.map(function(d){ return d.pv; });
  var colors = {'desktop':'#00f5ff','mobile':'#a020f0','tablet':'#6366f1','bot':'#f43f5e','unknown':'#6b7280'};
  var bgColors = labels.map(function(l){ return colors[l] || '#6b7280'; });

  checkChart(function(){ charts.device = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: bgColors,
        borderColor: 'rgba(5,5,8,0.5)',
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#6b7280', font: { size: 11 }, padding: 12 }
        }
      }
    }
  }); });
}

function renderDeviceDetail(browsers, osList) {
  var html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">';
  html += {{ _('<div><div class="label" style="margin-bottom:8px">Top 5 Browsers</div>') | tojson }};
  html += '<table class="data-table"><thead><tr><th>{{ _('Browser') }}</th><th>PV</th></tr></thead><tbody>';
  browsers.slice(0, 5).forEach(function(d){
    html += '<tr><td>' + d.browser + '</td><td style="color:var(--blue)">' + (d.pv||0).toLocaleString() + '</td></tr>';
  });
  html += '</tbody></table></div>';

  html += {{ _('<div><div class="label" style="margin-bottom:8px">Top 5 Operating Systems</div>') | tojson }};
  html += '<table class="data-table"><thead><tr><th>OS</th><th>PV</th></tr></thead><tbody>';
  osList.slice(0, 5).forEach(function(d){
    html += '<tr><td>' + d.os_name + '</td><td style="color:var(--blue)">' + (d.pv||0).toLocaleString() + '</td></tr>';
  });
  html += '</tbody></table></div></div>';
  document.getElementById('deviceContent').innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════════════
// 事件统计
// ═══════════════════════════════════════════════════════════════════════════
function loadEvents() {
  api('/events?days=30').then(function(res){
    if (!res.success || !res.data.length) {
      document.getElementById('eventsContent').innerHTML =
        '<div class="empty-state"><div class="icon">🔔</div><div class="text">{{ _('No custom events. Automatically logged when users launch agents, view stocks, create workflows etc.') }}</div></div>';
      return;
    }
    var html = '<table class="data-table"><thead><tr><th>{{ _('Event') }}</th><th>{{ _('Categories') }}</th><th>{{ _('Count') }}</th><th>{{ _('Total') }}</th></tr></thead><tbody>';
    res.data.forEach(function(d){
      html += '<tr>' +
        '<td style="font-weight:600">' + d.event_name + '</td>' +
        '<td><span style="font-size:11px;padding:2px 6px;border-radius:4px;background:rgba(99,102,241,0.1);color:var(--indigo)">' + d.event_category + '</span></td>' +
        '<td style="color:var(--blue);font-weight:600">' + (d.count||0).toLocaleString() + '</td>' +
        '<td>' + (d.total_value||0).toLocaleString() + '</td>' +
        '</tr>';
    });
    html += '</tbody></table>';
    document.getElementById('eventsContent').innerHTML = html;
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// 告警管理
// ═══════════════════════════════════════════════════════════════════════════
function loadAlerts() {
  api('/alerts').then(function(res){
    if (!res.success) return;
    renderAlerts(res.data);
  });
}

function renderAlerts(alerts) {
  if (!alerts.length) {
    document.getElementById('alertsList').innerHTML =
      '<div class="empty-state"><div class="icon">🚨</div><div class="text">{{ _('No alert rules. System auto-notifies when metrics exceed thresholds after adding alerts.') }}</div></div>';
    return;
  }
  var html = '<table class="data-table"><thead><tr><th>{{ _('Name') }}</th><th>{{ _('Metric') }}</th><th>{{ _('Condition') }}</th><th>{{ _('Window') }}</th><th>{{ _('Status') }}</th><th>{{ _('Last Triggered') }}</th><th>{{ _('Actions') }}</th></tr></thead><tbody>';
  alerts.forEach(function(d){
    var opMap = {'gt':'>','lt':'<','gte':'≥','lte':'≤','eq':'='};
    var enabled = d.enabled == 1;
    html += '<tr>' +
      '<td>' + d.name + '</td>' +
      '<td>' + d.metric + '</td>' +
      '<td>' + (opMap[d.operator] || d.operator) + ' ' + d.threshold + '</td>' +
      '<td>' + d.time_window + '</td>' +
      '<td>' + (enabled ? '<span style="color:var(--green)">{{ _('● Enabled') }}</span>' : '<span style="color:var(--text-dim)">{{ _('○ Disabled') }}</span>') + '</td>' +
      '<td style="font-size:11px;color:var(--text-dim)">' + (d.last_triggered ? new Date(d.last_triggered*1000).toLocaleString() : '-') + '</td>' +
      '<td><button onclick="deleteAlert(' + d.id + ')" style="background:rgba(244,63,94,0.1);border:1px solid rgba(244,63,94,0.3);color:var(--rose);border-radius:4px;padding:2px 8px;font-size:11px;cursor:pointer">{{ _('Delete') }}</button></td>' +
      '</tr>';
  });
  html += '</tbody></table>';
  document.getElementById('alertsList').innerHTML = html;
}

function deleteAlert(id) {
  showConfirm('{{ _('Delete Alert Rule') }}', '{{ _('Delete this alert rule?') }}', function(){
    fetch(API_BASE + '/alerts/' + id, { method: 'DELETE' }).then(function(r){
      return r.json();
    }).then(function(res){
      if (res.success) loadAlerts();
    });
  });
}

// 告警表单
document.getElementById('alertForm').addEventListener('submit', function(e){
  e.preventDefault();
  var fd = new FormData(this);
  var data = {};
  fd.forEach(function(v, k){ data[k] = v; });
  fetch(API_BASE + '/alerts', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data),
  }).then(function(r){ return r.json(); }).then(function(res){
    if (res.success) {
      loadAlerts();
      e.target.reset();
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// GeoIP 设置
// ═══════════════════════════════════════════════════════════════════════════
function loadGeoipStatus() {
  fetch(SETTINGS_BASE + '/settings/geoip/status', {headers: _authHeaders()}).then(function(r){return r.json();}).then(function(res){
    if (!res.success) return;
    var d = res.data;

    // ip2region
    var ip2 = d.ip2region;
    var ip2El = document.getElementById('ip2regionStatus');
    if (ip2.installed) {
      ip2El.innerHTML = '<span style="color:var(--green);font-weight:600">&#x2705; {{ _('Installed') }}</span>' +
        ' <span style="color:var(--text-dim);font-size:11px">' + ip2.size_mb + ' MB &middot; ' + ip2.mtime + '</span>';
      document.getElementById('ip2regionBtn').textContent = '{{ _('Update ip2region') }}';
    } else {
      ip2El.innerHTML = '<span style="color:var(--rose);font-weight:600">&#x26A0; {{ _('Not installed') }}</span>' +
        ' <span style="color:var(--text-dim);font-size:11px">— {{ _('Click the button below to download from GitHub') }}</span>';
    }

    // MaxMind
    var mm = d.geolite2;
    var mmEl = document.getElementById('geolite2Status');
    if (mm.installed) {
      mmEl.innerHTML = '<span style="color:var(--green);font-weight:600">&#x2705; {{ _('Installed') }}</span>' +
        ' <span style="color:var(--text-dim);font-size:11px">' + mm.size_mb + ' MB &middot; ' + mm.mtime + '</span>';
      document.getElementById('geoipDownloadBtn').textContent = '{{ _('Update GeoLite2') }}';
    } else {
      mmEl.innerHTML = '<span style="color:var(--rose);font-weight:600">&#x26A0; {{ _('Not installed') }}</span>';
    }

    // 预填已保存的凭证
    if (d.maxmind_account_id !== undefined) {
      var aEl = document.querySelector('#geoipForm [name="account_id"]');
      if (aEl) aEl.value = d.maxmind_account_id || '';
    }
    if (d.maxmind_license_key !== undefined) {
      var kEl = document.querySelector('#geoipForm [name="license_key"]');
      if (kEl) kEl.value = d.maxmind_license_key || '';
    }
  });
}

function downloadIp2region() {
  var btn = document.getElementById('ip2regionBtn');
  btn.textContent = '{{ _('Downloading...') }}';
  btn.disabled = true;
  var statusEl = document.getElementById('ip2regionDownloadStatus');
  if (statusEl) statusEl.innerHTML = '';
  showProgress('ip2regionBtn');
  var xhr = new XMLHttpRequest();
  xhr.open('POST', SETTINGS_BASE + '/settings/geoip/download-ip2region');
  var hdrs = _authHeaders();
  for (var k in hdrs) xhr.setRequestHeader(k, hdrs[k]);
  xhr.onload = function() {
    console.log('[GeoIP Download] status=' + xhr.status + ' body=' + xhr.responseText.substring(0,200));
    btn.disabled = false;
    hideProgress('ip2regionBtn');
    try {
      var res = JSON.parse(xhr.responseText);
      if (res.success) {
        btn.textContent = '{{ _('Update ip2region') }}';
        if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">&#x2705; {{ _('Downloaded') }} ' + (res.size_mb||'?') + ' MB</span>';
        loadGeoipStatus();
      } else {
        btn.textContent = '{{ _('Download ip2region Database') }}';
        if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">&#x26A0; ' + (res.error || 'Unknown error') + '</span>';
        showToast(res.error || 'Unknown error', 'error');
      }
    } catch(e) {
      btn.textContent = '{{ _('Download ip2region Database') }}';
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">Parse error: ' + e.message + '</span>';
    }
  };
  xhr.onerror = function() {
    btn.disabled = false;
    hideProgress('ip2regionBtn');
    btn.textContent = '{{ _('Download ip2region Database') }}';
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">Network error</span>';
  };
  xhr.send();
}

function _authHeaders() {
  var h = {};
  var tk = _TOKEN;
  if (!tk) {
    var c = document.cookie.match(/(?:^|;\s*)sso_token=([^;]+)/);
    if (c) tk = c[1];
  }
  if (tk) h['Authorization'] = 'Bearer ' + tk;
  return h;
}

// ── Save MaxMind credentials ──
document.getElementById('geoipSaveBtn').addEventListener('click', function(){
  var accountIdEl = document.querySelector('#geoipForm [name="account_id"]');
  var keyEl = document.querySelector('#geoipForm [name="license_key"]');
  var accountId = accountIdEl ? accountIdEl.value.trim() : '';
  var key = keyEl ? keyEl.value.trim() : '';
  var btn = document.getElementById('geoipSaveBtn');
  btn.textContent = '{{ _('Saving...') }}';
  btn.disabled = true;
  var hdrs = _authHeaders();
  hdrs['Content-Type'] = 'application/json';
  fetch(SETTINGS_BASE + '/settings', {
    method: 'POST',
    headers: hdrs,
    body: JSON.stringify({maxmind_account_id: accountId, maxmind_license_key: key}),
  }).then(function(r){ return r.json(); }).then(function(res){
    btn.textContent = '{{ _('Save') }}';
    btn.disabled = false;
    if (res.success) {
      showToast('{{ _('Credentials saved') }}', 'success');
    } else {
      showToast('Error: ' + (res.error || res.warning || 'Unknown error'), 'error');
    }
  }).catch(function(err){
    btn.textContent = '{{ _('Save') }}';
    btn.disabled = false;
    showToast('Network error: ' + err.message, 'error');
  });
});

// ── Download GeoLite2 database ──
document.getElementById('geoipDownloadBtn').addEventListener('click', function(){
  var accountIdEl = document.querySelector('#geoipForm [name="account_id"]');
  var keyEl = document.querySelector('#geoipForm [name="license_key"]');
  var editionEl = document.querySelector('#geoipForm [name="edition"]');
  var accountId = accountIdEl ? accountIdEl.value.trim() : '';
  var key = keyEl ? keyEl.value.trim() : '';
  var edition = editionEl ? editionEl.value.trim() : 'GeoLite2-City';
  if (!key) {
    showToast('{{ _('License Key is required to download') }}', 'error');
    return;
  }
  var btn = document.getElementById('geoipDownloadBtn');
  btn.textContent = '{{ _('Downloading...') }}';
  btn.disabled = true;
  var statusEl = document.getElementById('geoipDownloadStatus');
  if (statusEl) statusEl.innerHTML = '';
  showProgress('geoipDownloadBtn');
  var xhr = new XMLHttpRequest();
  xhr.open('POST', SETTINGS_BASE + '/settings/geoip/download');
  var hdrs_dl = _authHeaders();
  hdrs_dl['Content-Type'] = 'application/json';
  for (var k in hdrs_dl) xhr.setRequestHeader(k, hdrs_dl[k]);
  xhr.onload = function() {
    console.log('[GeoLite2 Download] status=' + xhr.status + ' body=' + xhr.responseText.substring(0,200));
    btn.disabled = false;
    hideProgress('geoipDownloadBtn');
    try {
      var res = JSON.parse(xhr.responseText);
      if (res.success) {
        btn.textContent = '{{ _('Update Database') }}';
        if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">&#x2705; {{ _('Downloaded') }} ' + (res.size_mb||'?') + ' MB</span>';
        loadGeoipStatus();
      } else {
        btn.textContent = '{{ _('Download Database') }}';
        if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">&#x26A0; ' + (res.error || 'Unknown error') + '</span>';
        showToast(res.error || 'Unknown error', 'error');
      }
    } catch(e) {
      btn.textContent = '{{ _('Download Database') }}';
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">Parse error: ' + e.message + '</span>';
    }
  };
  xhr.onerror = function() {
    btn.disabled = false;
    hideProgress('geoipDownloadBtn');
    btn.textContent = '{{ _('Download Database') }}';
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">Network error</span>';
  };
  xhr.send(JSON.stringify({account_id: accountId, license_key: key, edition: edition}));
});

// ── Upload .mmdb file ──
document.getElementById('geoipUploadBtn').addEventListener('click', function(){
  document.getElementById('geoipFileInput').click();
});
document.getElementById('geoipFileInput').addEventListener('change', function(){
  var file = this.files[0];
  if (!file) return;
  if (!file.name.endsWith('.mmdb')) {
    showToast('{{ _('Only .mmdb files allowed') }}', 'error');
    return;
  }
  var btn = document.getElementById('geoipUploadBtn');
  btn.textContent = '{{ _('Uploading...') }}';
  btn.disabled = true;
  var statusEl = document.getElementById('geoipDownloadStatus');
  if (statusEl) statusEl.innerHTML = '';
  showProgress('geoipUploadBtn');

  var formData = new FormData();
  formData.append('file', file);

  var xhr = new XMLHttpRequest();
  xhr.open('POST', SETTINGS_BASE + '/settings/geoip/upload');
  var hdrs_ul = _authHeaders();
  for (var k in hdrs_ul) xhr.setRequestHeader(k, hdrs_ul[k]);
  xhr.onload = function() {
    btn.disabled = false;
    hideProgress('geoipUploadBtn');
    btn.textContent = '{{ _('Upload .mmdb') }}';
    try {
      var res = JSON.parse(xhr.responseText);
      if (res.success) {
        if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">&#x2705; {{ _('Uploaded') }} ' + (res.size_mb||'?') + ' MB</span>';
        loadGeoipStatus();
      } else {
        if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">&#x26A0; ' + (res.error || 'Unknown error') + '</span>';
        showToast(res.error || 'Unknown error', 'error');
      }
    } catch(e) {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">Parse error: ' + e.message + '</span>';
    }
  };
  xhr.onerror = function() {
    btn.disabled = false;
    hideProgress('geoipUploadBtn');
    btn.textContent = '{{ _('Upload .mmdb') }}';
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">Network error</span>';
  };
  xhr.send(formData);
});

// ── Download from CDN (free, no MaxMind account needed) ──
document.getElementById('geoipCdnBtn').addEventListener('click', function(){
  var btn = this;
  btn.textContent = '{{ _('Downloading...') }}';
  btn.disabled = true;
  var statusEl = document.getElementById('geoipDownloadStatus');
  if (statusEl) statusEl.innerHTML = '';
  showProgress('geoipCdnBtn');

  var xhr = new XMLHttpRequest();
  xhr.open('POST', SETTINGS_BASE + '/settings/geoip/download-cdn');
  var hdrs_cdn = _authHeaders();
  for (var k in hdrs_cdn) xhr.setRequestHeader(k, hdrs_cdn[k]);
  xhr.onload = function() {
    btn.disabled = false;
    hideProgress('geoipCdnBtn');
    btn.textContent = '{{ _('CDN Download') }}';
    try {
      var res = JSON.parse(xhr.responseText);
      if (res.success) {
        if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">&#x2705; {{ _('Downloaded') }} ' + (res.size_mb||'?') + ' MB (CDN)</span>';
        loadGeoipStatus();
      } else {
        if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">&#x26A0; ' + (res.error || 'Unknown error') + '</span>';
        showToast(res.error || 'Unknown error', 'error');
      }
    } catch(e) {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">Parse error: ' + e.message + '</span>';
    }
  };
  xhr.onerror = function() {
    btn.disabled = false;
    hideProgress('geoipCdnBtn');
    btn.textContent = '{{ _('CDN Download') }}';
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--rose)">Network error</span>';
  };
  xhr.send();
});

// 切换到 Settings tab 时加载 GeoIP 状态和设置
document.querySelectorAll('.tab-btn').forEach(function(btn){
  btn.addEventListener('click', function(){
    if (this.getAttribute('data-tab') === 'settings') {
      loadGeoipStatus();
      loadPluginSettings();
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 动态市场检测（根据客户端 IP 判断 cn / intl）
// ═══════════════════════════════════════════════════════════════════════════
var _MARKET = {{ geo_market | tojson }};  // 服务端渲染初始值（避免 'cn' 闪烁），客户端仍异步刷新
var _worldGeoJson = null;  // 世界地图 GeoJSON 缓存

function showProgress(containerId) {
  var el = document.getElementById(containerId);
  if (!el) return;
  var wrap = document.createElement('div');
  wrap.className = 'progress-bar-wrap';
  wrap.id = containerId + '-progress';
  wrap.innerHTML = '<div class="progress-bar-inner"></div>';
  // If inside a form, insert after the form (not inside flex layout)
  var form = el.closest('form');
  var anchor = form || el;
  anchor.parentNode.insertBefore(wrap, anchor.nextSibling);
}

function hideProgress(containerId) {
  var el = document.getElementById(containerId + '-progress');
  if (el) el.parentNode.removeChild(el);
}

function resetWorldZoom() {
  if (charts.chinaMap) {
    charts.chinaMap.setOption({series:[{center:null, zoom:1}]});
    var backBtn = document.getElementById('mapBackBtn');
    if (backBtn) backBtn.style.display = 'none';
  }
}

function detectMarket() {
  return fetch(SETTINGS_BASE + '/api/v1/geo/market', {headers: _authHeaders()})
    .then(function(r){ return r.json(); })
    .then(function(res){
      if (res.success && res.data) {
        _MARKET = res.data.market;
      }
    })
    .catch(function(){ /* keep default */ });
}

// ═══════════════════════════════════════════════════════════════════════════
// 通用插件设置保存
// ═══════════════════════════════════════════════════════════════════════════
function loadPluginSettings() {
  fetch(SETTINGS_BASE + '/settings', {headers: _authHeaders()})
    .then(function(r){ return r.json(); })
    .then(function(res){
      if (res.success && res.data) {
        var d = res.data;
        document.getElementById('cfgSampleRate').value = d.sample_rate || 1.0;
        document.getElementById('cfgGeoipEnabled').value = d.geoip_enabled ? 'true' : 'false';
        document.getElementById('cfgServiceName').value = d.service_name || 'admin';
      }
    });
}

document.getElementById('pluginSettingsForm').addEventListener('submit', function(e){
  e.preventDefault();
  var btn = document.getElementById('settingsSaveBtn');
  btn.textContent = '{{ _('Saving...') }}';
  btn.disabled = true;
  var data = {
    sample_rate: parseFloat(document.getElementById('cfgSampleRate').value) || 1.0,
    geoip_enabled: document.getElementById('cfgGeoipEnabled').value === 'true',
    service_name: document.getElementById('cfgServiceName').value.trim() || 'admin'
  };
  var hdrs3 = _authHeaders();
  hdrs3['Content-Type'] = 'application/json';
  fetch(SETTINGS_BASE + '/settings', {
    method: 'POST',
    headers: hdrs3,
    body: JSON.stringify(data),
  }).then(function(r){ return r.json(); }).then(function(res){
    btn.textContent = '{{ _('Save Settings') }}';
    btn.disabled = false;
    if (res.success) {
      showToast('{{ _('Settings saved successfully') }}', 'success');
    } else {
      showToast('Error: ' + (res.error || res.warning || 'Unknown error'), 'error');
    }
  }).catch(function(err){
    btn.textContent = '{{ _('Save Settings') }}';
    btn.disabled = false;
    showToast('Network error: ' + err.message, 'error');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 刷新全部
// ═══════════════════════════════════════════════════════════════════════════
function refreshAll() {
  // Batch 1: critical data (realtime + trend)
  loadRealtime();
  loadTrend();
  // Batch 2: secondary data (staggered to avoid browser connection limits)
  setTimeout(function(){ loadHourly(); loadPages(); }, 150);
  setTimeout(function(){ loadSources(); loadGeo(); }, 300);
  // Batch 3: map data (heavy)
  setTimeout(function(){
    loadWorldCities();
    loadWorldMap();
    toggleCountrySection(true);
  }, 450);
  // Batch 4: devices, events, alerts
  setTimeout(function(){ loadDevices(); loadEvents(); loadAlerts(); }, 600);
}

// ═══════════════════════════════════════════════════════════════════════════
// 自动刷新
// ═══════════════════════════════════════════════════════════════════════════
function startAutoRefresh() {
  if (REFRESH_TIMER) clearInterval(REFRESH_TIMER);
  REFRESH_TIMER = setInterval(refreshAll, REFRESH_INTERVAL);
}

// ═══════════════════════════════════════════════════════════════════════════
// 初始化
// ═══════════════════════════════════════════════════════════════════════════
// 先检测市场，完成后再加载数据和启动自动刷新（避免竞态条件）
detectMarket().then(function() {
  refreshAll();
  startAutoRefresh();
});
