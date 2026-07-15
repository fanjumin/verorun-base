/**
 * 阿里巴巴API管理控制台 - 前端交互
 * Admin dark theme version (no Bootstrap dependency)
 */
let currentPage = 'dashboard';
let currentProductPage = 1;
let currentLogPage = 1;
let currentAiItemId = null;

// ===== auth =====
const _pageToken = new URLSearchParams(location.search).get('token') || '';
axios.interceptors.request.use(function(config) {
    const csrfToken = getCookie('csrf_token');
    if (csrfToken) config.headers['X-CSRF-Token'] = csrfToken;
    if (_pageToken) config.headers['Authorization'] = 'Bearer ' + _pageToken;
    return config;
}, function(error) { return Promise.reject(error); });

function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
}

// ===== modal helpers =====
function showModal(id) {
    var el = document.getElementById(id);
    if (el) el.className = 'mo show';
}
function closeModal(id) {
    var el = document.getElementById(id);
    if (el) el.className = 'mo';
}

// ===== utils =====
function showLoading() {
    var el = document.getElementById('lo');
    if (el) el.className = 'lo show';
}
function hideLoading() {
    var el = document.getElementById('lo');
    if (el) el.className = 'lo';
}
function showMessage(elementId, message, type) {
    var el = document.getElementById(elementId);
    if (!el) return;
    var cls = type === 'error' ? 'msg err' : type === 'success' ? 'msg ok' : 'msg info';
    el.innerHTML = '<div class="'+cls+'">'+message+'</div>';
}
function formatPrice(p) {
    if (p===null||p===undefined) return '未定价';
    return '¥'+parseFloat(p).toFixed(2);
}
function formatDate(d) {
    if (!d) return '-';
    try { return new Date(d).toLocaleString(); } catch(e) { return d; }
}
function getStatusBadge(status) {
    var m = {
        'active': '<span class="stbd on">活跃</span>',
        'inactive': '<span class="stbd off">非活跃</span>',
        'draft': '<span class="bdg gy">草稿</span>',
        'published': '<span class="bdg g">已发布</span>',
        'unpublished': '<span class="bdg y">已下架</span>',
        'failed': '<span class="bdg r">失败</span>',
    };
    return m[status] || '<span class="bdg gy">'+status+'</span>';
}

// ===== navigation =====
document.addEventListener('DOMContentLoaded', function() {
    initNavigation();
    loadDashboard();

    document.getElementById('collect-single-btn')?.addEventListener('click', collectSingleProduct);
    document.getElementById('search-collect-btn')?.addEventListener('click', searchCollect);
    document.getElementById('ai-optimize-btn')?.addEventListener('click', async function() {
        var id = document.getElementById('ai-product-id')?.value?.trim();
        if (!id) { showMessage('ai-result', '请输入商品ID', 'error'); return; }
        var n = parseInt(id);
        if (isNaN(n)) { showMessage('ai-result', '请输入数字ID', 'error'); return; }
        await generateAiTitles(n);
    });
    document.getElementById('product-search')?.addEventListener('keypress', function(e) { if (e.key==='Enter') loadProducts(1); });
    document.getElementById('status-filter')?.addEventListener('change', function() { loadProducts(1); });
    document.getElementById('filter-logs-btn')?.addEventListener('click', function() { loadLogs(1); });
    document.getElementById('log-endpoint')?.addEventListener('keypress', function(e) { if (e.key==='Enter') loadLogs(1); });
    document.getElementById('refresh-cache-stats')?.addEventListener('click', loadCacheStats);
    document.getElementById('cache-type')?.addEventListener('change', function() {
        var c = document.getElementById('product-id-container');
        if (c) c.style.display = this.value === 'product' ? 'block' : 'none';
    });
    document.getElementById('clear-cache-btn')?.addEventListener('click', async function() {
        if (!confirm('确定清理缓存？')) return;
        var type = document.getElementById('cache-type')?.value || 'all';
        var productId = document.getElementById('cache-product-id')?.value?.trim() || '';
        var data = { type: type };
        if (type==='product' && productId) data.product_id = productId;
        try {
            showLoading();
            var res = await axios.post('/admin/ali-api/cache/clear', data);
            if (res.data.success) { showMessage('clear-result', res.data.message, 'success'); loadCacheStats(); if (document.getElementById('cache-product-id')) document.getElementById('cache-product-id').value=''; }
            else { showMessage('clear-result', '清理失败: '+res.data.error, 'error'); }
        } catch(e) { showMessage('clear-result', '清理失败', 'error'); }
        finally { hideLoading(); }
    });
    // upload zone
    var uz = document.getElementById('upload-zone');
    var ui = document.getElementById('image-upload-input');
    if (uz && ui) {
        uz.addEventListener('click', function() { ui.click(); });
        ui.addEventListener('change', function() { if (this.files&&this.files.length>0&&_galleryItemId) { uploadGalleryImages(_galleryItemId, this.files); this.value=''; } });
        uz.addEventListener('dragover', function(e) { e.preventDefault(); this.style.borderColor='var(--accent)'; this.style.background='rgba(0,245,255,0.05)'; });
        uz.addEventListener('dragleave', function(e) { e.preventDefault(); this.style.borderColor=''; this.style.background='var(--bg)'; });
        uz.addEventListener('drop', function(e) { e.preventDefault(); this.style.borderColor=''; this.style.background='var(--bg)'; if (e.dataTransfer.files&&e.dataTransfer.files.length>0&&_galleryItemId) uploadGalleryImages(_galleryItemId, e.dataTransfer.files); });
    }
});

function initNavigation() {
    document.querySelectorAll('.tb-i').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var page = this.getAttribute('data-page');
            document.querySelectorAll('.tb-i').forEach(function(b) { b.classList.remove('act'); });
            this.classList.add('act');
            document.querySelectorAll('.page').forEach(function(el) { el.style.display='none'; });
            var p = document.getElementById(page+'-page');
            if (p) p.style.display='block';
            currentPage = page;
            loadPageData(page);
        });
    });
}
function loadPageData(page) {
    switch(page) {
        case 'dashboard': loadDashboard(); break;
        case 'products': loadProducts(); break;
        case 'logs': loadLogs(); break;
        case 'cache': loadCacheStats(); break;
        case 'settings': loadSettings(); break;
        case 'config': loadConfig(); break;
    }
}

// ===== dashboard =====
async function loadDashboard() {
    try {
        showLoading();
        var res = await axios.get('/admin/ali-api/dashboard');
        if (!res.data.success) return;
        var d = res.data.data;
        document.getElementById('total-items').textContent = d.items.total;
        document.getElementById('active-items').textContent = d.items.active;
        document.getElementById('total-calls').textContent = d.api_calls.total;
        document.getElementById('today-calls').textContent = d.api_calls.today;
        document.getElementById('total-users').textContent = d.users.total;
        var aiS = document.getElementById('ai-status');
        var aiP = document.getElementById('ai-provider');
        if (d.ai.available) { aiS.textContent='可用'; aiS.className='v s4'; aiP.textContent=d.ai.provider; }
        else { aiS.textContent='不可用'; aiS.className='v'; aiS.style.color='#f85149'; aiP.textContent='未配置'; }
        updateRateLimitStats(d.rate_limit);
        updateCacheStats(d.cache);
    } catch(e) { console.error('dashboard load failed', e); }
    finally { hideLoading(); }
}
function updateRateLimitStats(s) {
    var el = document.getElementById('rate-limit-stats');
    if (!el || !s) return;
    el.innerHTML = '<div><div style="font-size:11px;color:var(--dim)">用户限流</div><div style="font-size:12px;color:var(--muted);margin-top:4px">每日剩余: '+(s.user_limits?.daily_remaining??'-')+'/'+(s.user_limits?.daily_limit??'-')+'<br>每小时剩余: '+(s.user_limits?.hourly_remaining??'-')+'/'+(s.user_limits?.hourly_limit??'-')+'</div></div><div><div style="font-size:11px;color:var(--dim)">并发控制</div><div style="font-size:12px;color:var(--muted);margin-top:4px">活跃请求: '+(s.concurrent?.active_requests??0)+'/'+(s.concurrent?.max_concurrent??'-')+'<br>当前QPS: '+(s.concurrent?.current_qps??0)+'/'+(s.concurrent?.qps_limit??'-')+'</div></div>';
}
function updateCacheStats(s) {
    var el = document.getElementById('cache-stats');
    if (!el || !s) return;
    var rc = s.redis?.connected;
    el.innerHTML = '<div><div style="font-size:11px;color:var(--dim)">Redis</div><div style="font-size:12px;color:var(--muted);margin-top:4px">状态: '+(rc?'<span class="stbd on">已连接</span>':'<span class="stbd off">未连接</span>')+(rc?'<br>内存: '+(s.redis.used_memory||'N/A'):'<br>使用内存缓存')+'</div></div><div><div style="font-size:11px;color:var(--dim)">内存缓存</div><div style="font-size:12px;color:var(--muted);margin-top:4px">条目: '+(s.memory?.size??0)+'/'+(s.memory?.maxsize??'-')+'<br>TTL: '+(s.memory?.ttl??'-')+'秒</div></div>';
}

// ===== products =====
async function loadProducts(page) {
    if (page===undefined) page=currentProductPage;
    try {
        showLoading();
        var status = document.getElementById('status-filter')?.value||'active';
        var kw = document.getElementById('product-search')?.value||'';
        var url = '/admin/ali-api/items?page='+page+'&per_page=20&status='+status;
        if (kw) url+='&keyword='+encodeURIComponent(kw);
        var res = await axios.get(url);
        if (res.data.success) { updateProductsTable(res.data.data.items); updateProductsPagination(res.data.data.pagination); currentProductPage=page; }
    } catch(e) { console.error('load products failed', e); showMessage('products-table', '加载商品失败', 'error'); }
    finally { hideLoading(); }
}
function updateProductsTable(items) {
    var tbody = document.getElementById('products-table');
    if (!tbody) return;
    if (!items||items.length===0) { tbody.innerHTML='<tr><td colspan="8" class="tc dim" style="padding:20px">暂无商品数据</td></tr>'; return; }
    tbody.innerHTML = items.map(function(item) {
        var imgs = parseJsonField(item.images, []);
        var imgH = imgs.length>0 ? '<img src="'+escHtml(imgs[0])+'" class="pr-img" alt="图片" onerror="safeImgOnError.call(this)">' : '<div class="pr-img no">无图</div>';
        return '<tr><td>'+item.id+'</td><td>'+imgH+'</td><td><strong>'+escHtml(item.title||item.original_title||'无标题')+'</strong><br><span class="dim" style="font-size:10px">ID: '+escHtml(item.product_id)+'</span></td><td>'+formatPrice(item.price)+'</td><td>'+escHtml(item.category||'未分类')+'</td><td>'+getStatusBadge(item.status)+'<br>'+getStatusBadge(item.publish_status)+'</td><td>'+formatDate(item.updated_at)+'</td><td><div style="display:flex;gap:3px">'+
            '<button class="btn bs" title="查看" onclick="viewProduct('+item.id+')">&#x1F441;</button>'+
            '<button class="btn bs" title="图片" onclick="openImageGallery('+item.id+')">&#x1F5BC;</button>'+
            '<button class="btn bs" title="AI标题" onclick="generateAiTitles('+item.id+')">&#x2728;</button>'+
            '<button class="btn bs" title="发布" onclick="publishProduct('+item.id+')"'+(item.publish_status==='published'?' disabled':'')+'>&#x2B06;</button>'+
            '</div></td></tr>';
    }).join('');
}
function updateProductsPagination(p) {
    var el = document.getElementById('products-pagination');
    if (!el) return;
    var page=p.page, total=p.total_pages;
    var h='';
    h+=page>1?'<a onclick="loadProducts('+(page-1)+');return false;">上一页</a>':'<a class="dis">上一页</a>';
    var start=Math.max(1,page-2), end=Math.min(total,page+2);
    for(var i=start;i<=end;i++) h+=i===page?'<a class="act">'+i+'</a>':'<a onclick="loadProducts('+i+');return false;">'+i+'</a>';
    h+=page<total?'<a onclick="loadProducts('+(page+1)+');return false;">下一页</a>':'<a class="dis">下一页</a>';
    el.innerHTML=h;
}
async function viewProduct(itemId) {
    try {
        var res = await axios.get('/admin/ali-api/items/'+itemId);
        if (!res.data.success) { alert('获取失败: '+res.data.error); return; }
        var p = res.data.data;
        var specs = parseJsonField(p.specs, {});
        var sku = parseJsonField(p.product_sku, []);
        var images = parseJsonField(p.images, []);
        var titleOpts = parseJsonField(p.ai_title_options, []);
        var detail = 'ID: '+p.id+'\n商品ID: '+p.product_id+'\n标题: '+(p.title||p.original_title||'-')+'\n';
        if (p.ai_title) detail+='AI标题: '+p.ai_title+'\n';
        if (p.selected_title) detail+='已选标题: '+p.selected_title+'\n';
        detail+='价格: '+formatPrice(p.price)+'\n原价: '+formatPrice(p.original_price)+'\n类目: '+(p.category||'-')+'\n状态: '+p.status+' | 发布: '+p.publish_status+'\n图片: '+images.length+' 张';
        if (p.target_product_id) detail+='\n本地商品ID: '+p.target_product_id;
        if (Object.keys(specs).length>0) detail+='\n规格: '+JSON.stringify(specs,null,2);
        if (sku.length>0) detail+='\nSKU: '+sku.length+' 个';
        if (images.length>0) { detail+='\n\n图片列表:'; images.forEach(function(img,i){ var u=typeof img==='string'?img:(img.url||''); detail+='\n  '+(i+1)+'. '+u.substring(0,60)+(u.length>60?'...':''); }); }
        if (titleOpts.length>0) { detail+='\n\nAI标题选项:'; titleOpts.forEach(function(opt,i){ detail+='\n  '+(i+1)+'. ['+opt.style+'] '+opt.title; }); }
        alert(detail);
    } catch(e) { console.error(e); alert('查看失败'); }
}

// ===== image gallery =====
var _galleryItemId = null;
async function openImageGallery(itemId) {
    _galleryItemId = itemId;
    showModal('image-gallery-modal');
    await loadGalleryImages(itemId);
}
async function loadGalleryImages(itemId) {
    var container = document.getElementById('image-gallery-container');
    var countEl = document.getElementById('image-count');
    if (!container) return;
    try {
        var res = await axios.get('/admin/ali-api/items/'+itemId+'/images');
        if (!res.data.success) { container.innerHTML='<div class="ac dg" style="padding:20px">加载失败: '+res.data.error+'</div>'; return; }
        var images = res.data.data.images||[];
        if (countEl) countEl.textContent='共'+images.length+'张图片';
        if (images.length===0) { container.innerHTML='<div class="ac dim" style="padding:20px;font-size:13px"><div style="font-size:28px;opacity:.4">&#x1F4E5;</div><p style="margin-top:8px">暂无图片，请点击上方区域上传</p></div>'; return; }
        container.innerHTML = '<div class="igg">'+images.map(function(img,idx){
            return '<div class="ig-item"><img src="'+escHtml(img.url)+'" class="ig-img" alt="图片" onerror="safeImgOnError.call(this,\'large\')"><div class="ig-ft"><span class="dim">'+(idx+1)+'</span><button class="btn bs" onclick="deleteGalleryImage('+itemId+','+idx+')" title="删除" style="color:#f85149">&times;</button></div></div>';
        }).join('')+'</div>';
    } catch(e) { container.innerHTML='<div class="ac dg" style="padding:20px">加载失败: '+e.message+'</div>'; }
}
async function deleteGalleryImage(itemId, index) {
    if (!confirm('确定要删除第 '+(index+1)+' 张图片吗？')) return;
    try { showLoading(); var res=await axios.delete('/admin/ali-api/items/'+itemId+'/images/'+index); if (res.data.success){ await loadGalleryImages(itemId); if (currentPage==='products') loadProducts(currentProductPage); } else alert('删除失败: '+res.data.error); } catch(e){ alert('删除失败: '+(e.response?.data?.error||e.message)); } finally { hideLoading(); }
}
async function uploadGalleryImages(itemId, files) {
    if (!files||files.length===0) return;
    for (var i=0;i<files.length;i++) {
        var f=files[i];
        if (f.size>5*1024*1024) { alert('文件 '+f.name+' 超过 5MB 限制'); continue; }
        var ext=f.name.split('.').pop().toLowerCase();
        if (!['png','jpg','jpeg','gif','webp'].includes(ext)) { alert('文件 '+f.name+' 格式不支持'); continue; }
        var fd=new FormData(); fd.append('file',f);
        try { showLoading(); var r=await axios.post('/admin/ali-api/items/'+itemId+'/images/upload',fd,{headers:{'Content-Type':'multipart/form-data'}}); if(!r.data.success) alert('上传 '+f.name+' 失败: '+r.data.error); } catch(e){ alert('上传 '+f.name+' 失败: '+(e.response?.data?.error||e.message)); } finally { hideLoading(); }
    }
    await loadGalleryImages(itemId);
    if (currentPage==='products') loadProducts(currentProductPage);
}

// ===== collect =====
async function collectSingleProduct() {
    var pid = document.getElementById('product-id')?.value?.trim();
    if (!pid) { showMessage('collect-result', '请输入商品ID', 'error'); return; }
    try {
        showLoading();
        var res = await axios.post('/admin/ali-api/items/collect', {product_id:pid});
        if (res.data.success) { var tag=res.data.data.from_cache?'（来自缓存）':''; showMessage('collect-result','采集成功'+tag+'！商品ID: '+res.data.data.item_id,'success'); document.getElementById('product-id').value=''; if (currentPage==='dashboard') loadDashboard(); }
        else showMessage('collect-result','采集失败: '+res.data.error,'error');
    } catch(e) { showMessage('collect-result','采集失败: '+(e.response?.data?.error||e.message),'error'); }
    finally { hideLoading(); }
}
async function searchCollect() {
    var kw = document.getElementById('search-keywords')?.value?.trim();
    if (!kw) { showMessage('search-result', '请输入搜索关键词', 'error'); return; }
    var page = document.getElementById('search-page')?.value||1;
    var size = document.getElementById('search-size')?.value||20;
    try {
        showLoading();
        var res = await axios.post('/admin/ali-api/items/search', {keywords:kw,page_no:parseInt(page),page_size:parseInt(size)});
        if (res.data.success) {
            var d=res.data.data;
            var msg='搜索成功！共找到 '+d.total+' 个商品';
            if (d.products?.length>0) { msg+='<br><br><b>结果预览:</b><br>'; d.products.slice(0,5).forEach(function(p,i){ msg+=(i+1)+'. '+escHtml(p.title)+' - '+formatPrice(p.price)+'<br>'; }); if (d.products.length>5) msg+='...还有 '+(d.products.length-5)+' 个'; }
            showMessage('search-result',msg,'success');
        } else showMessage('search-result','搜索失败: '+res.data.error,'error');
    } catch(e) { showMessage('search-result','搜索失败: '+(e.response?.data?.error||e.message),'error'); }
    finally { hideLoading(); }
}

// ===== AI titles =====
async function generateAiTitles(itemId) {
    if (!confirm('确定要使用AI生成多版本标题选项吗？')) return;
    try {
        showLoading();
        var res = await axios.post('/admin/ali-api/items/'+itemId+'/ai-titles');
        if (res.data.success) { showTitleSelectionModal(itemId, res.data.data.ai_title_options); }
        else alert('AI生成标题失败: '+res.data.error);
    } catch(e) { alert('AI生成标题失败: '+(e.response?.data?.error||e.message)); }
    finally { hideLoading(); }
}
function showTitleSelectionModal(itemId, options) {
    currentAiItemId=itemId;
    var list=document.getElementById('ai-title-options');
    if (!list) return;
    if (!options||options.length===0) { list.innerHTML='<div class="dim" style="font-size:12px">AI未生成有效的标题选项</div>'; }
    else {
        list.innerHTML = options.map(function(opt,idx){
            return '<div class="to" onclick="selectAiTitle(this,'+opt.id+')" data-title="'+escHtml(opt.title)+'"><div class="to-badges"><span class="bdg gy">选项'+(idx+1)+'</span><span class="bdg b">'+styleLabel(opt.style)+'</span>'+(idx===0?'<span class="bdg y">推荐</span>':'')+'</div><div style="font-size:13px;margin-bottom:2px;font-weight:600">'+escHtml(opt.title)+'</div><div class="dim" style="font-size:11px">'+escHtml(opt.reason||'')+'</div></div>';
        }).join('');
    }
    document.getElementById('confirm-title-btn').onclick = async function() {
        var sel=document.querySelector('.to.sel');
        if (!sel) { alert('请选择一个标题'); return; }
        await confirmSelectedTitle(itemId, sel.getAttribute('data-title'));
    };
    showModal('ai-title-modal');
}
function styleLabel(s) {
    var m={'professional':'专业型','attractive':'吸引力型','concise':'简洁型','normal':'通用'};
    return m[s]||s;
}
function selectAiTitle(el) {
    document.querySelectorAll('.to').forEach(function(e){ e.classList.remove('sel'); });
    el.classList.add('sel');
}
async function confirmSelectedTitle(itemId, title) {
    try {
        showLoading();
        var res = await axios.post('/admin/ali-api/items/'+itemId+'/select-title', {title:title});
        if (res.data.success) { alert('标题已选择成功！'); closeModal('ai-title-modal'); loadProducts(currentProductPage); }
        else alert('选择失败: '+res.data.error);
    } catch(e) { alert('选择失败: '+(e.response?.data?.error||e.message)); }
    finally { hideLoading(); }
}

// ===== publish =====
async function publishProduct(itemId) {
    var stock=prompt('请输入库存数量（默认999）','999'); if (stock===null) return;
    var n=parseInt(stock)||999;
    if (!confirm('确定要将商品发布到本地商城吗？库存: '+n)) return;
    try {
        showLoading();
        var res=await axios.post('/admin/ali-api/items/'+itemId+'/publish',{stock:n});
        if (res.data.success) { alert('发布成功！本地商品ID: '+res.data.data.target_product_id+'\n标题: '+res.data.data.title+'\n价格: '+formatPrice(res.data.data.price)); loadProducts(currentProductPage); }
        else alert('发布失败: '+res.data.error);
    } catch(e) { alert('发布失败: '+(e.response?.data?.error||e.message)); }
    finally { hideLoading(); }
}

// ===== logs =====
async function loadLogs(page) {
    if (page===undefined) page=currentLogPage;
    try {
        showLoading();
        var ep=document.getElementById('log-endpoint')?.value||'';
        var sc=document.getElementById('log-success')?.value||'';
        var url='/admin/ali-api/logs?page='+page+'&per_page=20';
        if (ep) url+='&endpoint='+encodeURIComponent(ep);
        if (sc) url+='&success='+sc;
        var res=await axios.get(url);
        if (res.data.success) { updateLogsTable(res.data.data.logs); updateLogsPagination(res.data.data.pagination); currentLogPage=page; }
    } catch(e) { console.error('load logs failed',e); }
    finally { hideLoading(); }
}
function updateLogsTable(logs) {
    var tbody=document.getElementById('logs-table'); if (!tbody) return;
    if (!logs||logs.length===0) { tbody.innerHTML='<tr><td colspan="8" class="tc dim" style="padding:20px">暂无日志</td></tr>'; return; }
    tbody.innerHTML=logs.map(function(log){
        return '<tr><td>'+log.id+'</td><td>'+(log.user_id||'系统')+'</td><td><code style="color:var(--accent);font-size:11px">'+escHtml(log.endpoint)+'</code></td><td><span class="dim" style="font-size:10px">'+escHtml(JSON.stringify(parseJsonField(log.params,{})).substring(0,40))+'</span></td><td>'+(log.response_code||'-')+'</td><td>'+(log.response_time||'-')+'</td><td>'+(log.success?'<span class="stbd on">成功</span>':'<span class="stbd off">失败</span>')+'</td><td>'+formatDate(log.created_at)+'</td></tr>';
    }).join('');
}
function updateLogsPagination(p) {
    var el=document.getElementById('logs-pagination'); if (!el) return;
    var page=p.page,total=p.total_pages;
    var h='';
    h+=page>1?'<a onclick="loadLogs('+(page-1)+');return false;">上一页</a>':'<a class="dis">上一页</a>';
    var start=Math.max(1,page-2),end=Math.min(total,page+2);
    for(var i=start;i<=end;i++) h+=i===page?'<a class="act">'+i+'</a>':'<a onclick="loadLogs('+i+');return false;">'+i+'</a>';
    h+=page<total?'<a onclick="loadLogs('+(page+1)+');return false;">下一页</a>':'<a class="dis">下一页</a>';
    el.innerHTML=h;
}

// ===== cache =====
async function loadCacheStats() {
    try { var res=await axios.get('/admin/ali-api/cache/stats'); if(res.data.success) updateCacheDetails(res.data.data); } catch(e){ console.error(e); }
}
function updateCacheDetails(s) {
    var el=document.getElementById('cache-details'); if(!el) return;
    var rc=s.redis?.connected;
    el.innerHTML='<div style="font-size:12px;margin-bottom:6px"><b>Redis</b><br>状态: '+(rc?'<span class="stbd on">已连接</span>':'<span class="stbd off">未连接</span>')+(rc?'<br>内存: '+(s.redis.used_memory||'N/A')+'<br>连接数: '+(s.redis.connected_clients||0):'<br><span class="dim">使用内存缓存</span>')+'</div><div style="font-size:12px"><b>内存缓存</b><br>条目: '+(s.memory?.size??0)+'/'+(s.memory?.maxsize??'-')+'<br>过期: '+(s.memory?.expired_entries??0)+'<br>TTL: '+(s.memory?.ttl??'-')+'秒</div><div style="font-size:12px;margin-top:6px"><b>使用Redis:</b> '+(s.use_redis?'是':'否')+'</div>';
}

// ===== config =====
async function loadConfig() {
    try {
        var res=await axios.get('/admin/ali-api/config');
        if (!res.data.success) return;
        var c=res.data.data;
        var gw=document.getElementById('cfg-api-gateway'); if(gw) gw.value=c.alibaba.api_gateway||'';
        var ver=document.getElementById('cfg-api-version'); if(ver) ver.value=c.alibaba.api_version||'';
        var sig=document.getElementById('cfg-sign-method'); if(sig) sig.value=c.alibaba.sign_method||'';
        var key=document.getElementById('cfg-app-key'); if(key) key.value=c.alibaba.app_key_masked||'';
        var sec=document.getElementById('cfg-app-secret'); if(sec) sec.placeholder=c.alibaba.app_key_configured?'已配置，输入新值以覆盖':'输入 1688 AppSecret';
        var ai=document.getElementById('ai-config');
        if (ai) ai.innerHTML='<dt>供应商</dt><dd>'+escHtml(c.ai.provider)+'</dd><dt>模型</dt><dd>'+escHtml(c.ai.model)+'</dd><dt>状态</dt><dd><span class="stbd '+(c.ai.available?'on':'off')+'">'+(c.ai.available?'可用':'不可用')+'</span></dd>';
        var rl=document.getElementById('rate-limit-config');
        if (rl&&c.rate_limit) rl.innerHTML='<dt>用户日限</dt><dd>'+c.rate_limit.user_daily_limit+'</dd><dt>用户时限</dt><dd>'+c.rate_limit.user_hourly_limit+'</dd><dt>全局并发</dt><dd>'+c.rate_limit.global_concurrent_limit+'</dd><dt>全局QPS</dt><dd>'+c.rate_limit.global_qps_limit+'</dd><dt>熔断阈值</dt><dd>'+c.rate_limit.circuit_breaker_threshold+'</dd>';
        var ca=document.getElementById('cache-config');
        if (ca&&c.cache) ca.innerHTML='<dt>Redis</dt><dd><span class="stbd '+(c.cache.redis_configured?'on':'off')+'">'+(c.cache.redis_configured?'已配置':'未配置')+'</span></dd><dt>内存缓存</dt><dd>'+c.cache.memory_cache_maxsize+'</dd><dt>商品缓存TTL</dt><dd>'+c.cache.product_cache_ttl+'秒</dd>';
    } catch(e) { console.error('load config failed',e); }
}

// ===== settings =====
async function loadSettings() {
    var el=document.getElementById('settings-content'); if(!el) return;
    try {
        var res=await axios.get('/admin/ali-api/settings');
        if (!res.data.success) { el.innerHTML='<div style="color:#f85149;font-size:12px">加载失败: '+escHtml(res.data.error)+'</div>'; return; }
        var cfg=res.data.data.config||{};
        el.innerHTML='<div style="margin-bottom:10px"><label for="s-api-gateway">API 网关地址</label><input class="in" id="s-api-gateway" value="'+escHtml(cfg.api_gateway||'')+'" placeholder="https://gw.open.1688.com/openapi"><div class="fh">1688 Open API 网关地址</div></div><button class="btn bp" onclick="saveSettings()">保存配置</button><span id="settings-status" class="mu" style="font-size:11px;margin-left:8px"></span>';
    } catch(e) { el.innerHTML='<div style="color:#f85149;font-size:12px">加载失败: '+escHtml(e.message)+'</div>'; }
}
async function saveSettings() {
    var el=document.getElementById('settings-content');
    var btn=el?el.querySelector('button'):null;
    var st=document.getElementById('settings-status');
    if (st) st.textContent='保存中...';
    if (btn) btn.disabled=true;
    try {
        var data={api_gateway:(document.getElementById('s-api-gateway')?.value?.trim()||'')};
        var res=await axios.post('/admin/ali-api/settings',data);
        if (res.data.success) { if(st){st.textContent='已保存';st.style.color='var(--accent)';} setTimeout(function(){if(st)st.textContent='';},3000); }
        else { if(st){st.textContent='保存失败: '+(res.data.error||'');st.style.color='#f85149';} }
    } catch(e) { if(st){st.textContent='保存失败: '+(e.response?.data?.error||e.message);st.style.color='#f85149';} }
    finally { if(btn) btn.disabled=false; }
}

// ===== save config =====
async function saveConfig() {
    var ak=document.getElementById('cfg-app-key')?.value?.trim();
    var as=document.getElementById('cfg-app-secret')?.value?.trim();
    if (!ak&&!as) { showMessage('config-save-result','请至少填写 AppKey 或 AppSecret','error'); return; }
    if (ak&&ak.endsWith('...')) { showMessage('config-save-result','AppKey 显示为脱敏值，如需修改请完整输入新的 AppKey','error'); return; }
    var btn=document.getElementById('save-config-btn');
    if (btn) { btn.disabled=true; btn.innerHTML='保存中...'; }
    try {
        var res=await axios.post('/admin/ali-api/config',{app_key:ak,app_secret:as});
        if (res.data.success) { showMessage('config-save-result',res.data.message,'success'); loadConfig(); }
        else showMessage('config-save-result','保存失败: '+(res.data.error||''),'error');
    } catch(e) { showMessage('config-save-result','保存失败: '+(e.response?.data?.error||e.message),'error'); }
    finally { if(btn){btn.disabled=false;btn.innerHTML='保存配置';} }
}

// ===== helpers =====
function escHtml(s) { if (!s) return ''; var d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
function safeImgOnError(size) {
    var svg=size==='large'?'<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180"><rect fill="#111" width="180" height="180"/><text x="55" y="95" font-size="14" fill="#555">加载失败</text></svg>':'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><rect fill="#111" width="80" height="80"/><text x="25" y="45" font-size="12" fill="#555">无图</text></svg>';
    this.src='data:image/svg+xml,'+encodeURIComponent(svg);
}
function parseJsonField(v,d) {
    if (v===null||v===undefined) return d;
    if (typeof v==='string') { try { return JSON.parse(v); } catch(e) { return d; } }
    return v;
}
