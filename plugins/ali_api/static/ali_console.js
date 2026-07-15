/**
 * 阿里巴巴API管理控制台 - 前端交互
 * 
 * 功能：
 * 1. 仪表板数据加载
 * 2. 商品列表/搜索
 * 3. 商品采集（单次/批量搜索）
 * 4. AI 多标题选项生成 + 选择
 * 5. 商品发布到本地商城
 * 6. API 日志查看
 * 7. 缓存管理
 * 8. 配置查看
 */

// ===== 全局状态 =====
let currentPage = 'dashboard';
let currentProductPage = 1;
let currentLogPage = 1;
let currentAiItemId = null; // 当前正在AI处理的商品ID

// ===== CSRF 防护 + JWT 鉴权 =====
// 从 iframe URL 读取 token（父页面通过 ?token= 传入），附加到所有请求
const _pageToken = new URLSearchParams(location.search).get('token') || '';
// 在所有 axios 请求中自动附加 CSRF Token + JWT
axios.interceptors.request.use(function(config) {
    const csrfToken = getCookie('csrf_token');
    if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken;
    }
    if (_pageToken) {
        config.headers['Authorization'] = 'Bearer ' + _pageToken;
    }
    return config;
}, function(error) {
    return Promise.reject(error);
});

function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
}

// ===== 工具函数 =====

function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = 'none';
}

function showMessage(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    if (!element) return;
    const alertClass = type === 'error' ? 'alert-danger' :
                       type === 'success' ? 'alert-success' : 'alert-info';
    element.innerHTML = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
}

function formatPrice(price) {
    if (price === null || price === undefined) return '未定价';
    return '¥' + parseFloat(price).toFixed(2);
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        return new Date(dateStr).toLocaleString();
    } catch {
        return dateStr;
    }
}

function getStatusBadge(status) {
    const map = {
        'active': '<span class="api-status status-active">活跃</span>',
        'inactive': '<span class="api-status status-inactive">非活跃</span>',
        'draft': '<span class="badge bg-secondary">草稿</span>',
        'published': '<span class="badge bg-success">已发布</span>',
        'unpublished': '<span class="badge bg-warning text-dark">已下架</span>',
        'failed': '<span class="badge bg-danger">失败</span>',
    };
    return map[status] || `<span class="badge bg-light text-dark">${status}</span>`;
}

// ===== 页面切换 =====
function initNavigation() {
    document.querySelectorAll('[data-page]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.getAttribute('data-page');
            switchPage(page);
        });
    });
}

function switchPage(page) {
    // 更新导航状态
    document.querySelectorAll('.nav-link').forEach(nav => nav.classList.remove('active'));
    const navLink = document.querySelector(`[data-page="${page}"]`);
    if (navLink) navLink.classList.add('active');

    // 切换页面
    document.querySelectorAll('.page').forEach(el => el.style.display = 'none');
    const pageEl = document.getElementById(`${page}-page`);
    if (pageEl) pageEl.style.display = 'block';

    currentPage = page;
    loadPageData(page);
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

// ===== 仪表板 =====
async function loadDashboard() {
    try {
        showLoading();
        const res = await axios.get('/admin/ali-api/dashboard');
        if (!res.data.success) return;

        const d = res.data.data;
        document.getElementById('total-items').textContent = d.items.total;
        document.getElementById('active-items').textContent = d.items.active;
        document.getElementById('total-calls').textContent = d.api_calls.total;
        document.getElementById('today-calls').textContent = d.api_calls.today;
        document.getElementById('total-users').textContent = d.users.total;

        // AI状态
        const aiStatus = document.getElementById('ai-status');
        const aiProvider = document.getElementById('ai-provider');
        if (d.ai.available) {
            aiStatus.textContent = '可用';
            aiStatus.className = 'api-status status-active';
            aiProvider.textContent = d.ai.provider;
        } else {
            aiStatus.textContent = '不可用';
            aiStatus.className = 'api-status status-inactive';
            aiProvider.textContent = '未配置';
        }

        updateRateLimitStats(d.rate_limit);
        updateCacheStats(d.cache);
    } catch (e) {
        console.error('仪表板加载失败', e);
    } finally {
        hideLoading();
    }
}

function updateRateLimitStats(stats) {
    const el = document.getElementById('rate-limit-stats');
    if (!el || !stats) return;
    el.innerHTML = `
        <div class="col-md-6">
            <h6><i class="bi bi-person"></i> 用户限流</h6>
            <p>每日剩余: ${stats.user_limits?.daily_remaining ?? '-'}/${stats.user_limits?.daily_limit ?? '-'}</p>
            <p>每小时剩余: ${stats.user_limits?.hourly_remaining ?? '-'}/${stats.user_limits?.hourly_limit ?? '-'}</p>
        </div>
        <div class="col-md-6">
            <h6><i class="bi bi-globe"></i> 并发控制</h6>
            <p>活跃请求: ${stats.concurrent?.active_requests ?? 0}/${stats.concurrent?.max_concurrent ?? '-'}</p>
            <p>当前QPS: ${stats.concurrent?.current_qps ?? 0}/${stats.concurrent?.qps_limit ?? '-'}</p>
        </div>
    `;
}

function updateCacheStats(stats) {
    const el = document.getElementById('cache-stats');
    if (!el || !stats) return;
    const redisConnected = stats.redis?.connected;
    el.innerHTML = `
        <div class="col-md-6">
            <h6><i class="bi bi-database"></i> Redis</h6>
            <p>状态: ${redisConnected ? '<span class="api-status status-active">已连接</span>' : '<span class="api-status status-inactive">未连接</span>'}</p>
            ${redisConnected ? `<p>内存: ${stats.redis.used_memory || 'N/A'}</p>` : '<p>使用内存缓存</p>'}
        </div>
        <div class="col-md-6">
            <h6><i class="bi bi-memory"></i> 内存缓存</h6>
            <p>条目: ${stats.memory?.size ?? 0}/${stats.memory?.maxsize ?? '-'}</p>
            <p>TTL: ${stats.memory?.ttl ?? '-'}秒</p>
        </div>
    `;
}

// ===== 商品管理 =====
async function loadProducts(page) {
    if (page === undefined) page = currentProductPage;
    try {
        showLoading();
        const status = document.getElementById('status-filter')?.value || 'active';
        const keyword = document.getElementById('product-search')?.value || '';
        let url = `/admin/ali-api/items?page=${page}&per_page=20&status=${status}`;
        if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;

        const res = await axios.get(url);
        if (res.data.success) {
            updateProductsTable(res.data.data.items);
            updateProductsPagination(res.data.data.pagination);
            currentProductPage = page;
        }
    } catch (e) {
        console.error('加载商品失败:', e);
        showMessage('products-table', '加载商品失败', 'error');
    } finally {
        hideLoading();
    }
}

function updateProductsTable(items) {
    const tbody = document.getElementById('products-table');
    if (!tbody) return;

    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center">暂无商品数据</td></tr>';
        return;
    }

    tbody.innerHTML = items.map(item => {
        const images = parseJsonField(item.images, []);
        const imgHtml = images.length > 0
            ? `<img src="${escHtml(images[0])}" class="product-image" alt="图片" onerror="safeImgOnError.call(this)">`
            : '<div class="product-image bg-light d-flex align-items-center justify-content-center text-muted" style="font-size:12px">无图</div>';

        return `<tr>
            <td>${item.id}</td>
            <td>${imgHtml}</td>
            <td>
                <strong>${escHtml(item.title || item.original_title || '无标题')}</strong><br>
                <small class="text-muted">ID: ${escHtml(item.product_id)}</small>
            </td>
            <td>${formatPrice(item.price)}</td>
            <td>${escHtml(item.category || '未分类')}</td>
            <td>${getStatusBadge(item.status)}<br>${getStatusBadge(item.publish_status)}</td>
            <td>${formatDate(item.updated_at)}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" title="查看" onclick="viewProduct(${item.id})"><i class="bi bi-eye"></i></button>
                    <button class="btn btn-outline-secondary" title="图片" onclick="openImageGallery(${item.id})"><i class="bi bi-images"></i></button>
                    <button class="btn btn-outline-info" title="AI标题" onclick="generateAiTitles(${item.id})"><i class="bi bi-magic"></i></button>
                    <button class="btn btn-outline-success" title="发布" onclick="publishProduct(${item.id})" ${item.publish_status === 'published' ? 'disabled' : ''}><i class="bi bi-upload"></i></button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

function updateProductsPagination(pagination) {
    const el = document.getElementById('products-pagination');
    if (!el) return;
    const { page, total_pages } = pagination;
    let html = '';

    // prev
    html += page > 1
        ? `<li class="page-item"><a class="page-link" href="#" onclick="loadProducts(${page-1});return false;">上一页</a></li>`
        : `<li class="page-item disabled"><a class="page-link">上一页</a></li>`;

    // pages
    const start = Math.max(1, page - 2);
    const end = Math.min(total_pages, page + 2);
    for (let i = start; i <= end; i++) {
        html += i === page
            ? `<li class="page-item active"><a class="page-link">${i}</a></li>`
            : `<li class="page-item"><a class="page-link" href="#" onclick="loadProducts(${i});return false;">${i}</a></li>`;
    }

    // next
    html += page < total_pages
        ? `<li class="page-item"><a class="page-link" href="#" onclick="loadProducts(${page+1});return false;">下一页</a></li>`
        : `<li class="page-item disabled"><a class="page-link">下一页</a></li>`;

    el.innerHTML = html;
}

async function viewProduct(itemId) {
    try {
        const res = await axios.get(`/admin/ali-api/items/${itemId}`);
        if (!res.data.success) { alert('获取失败: ' + res.data.error); return; }
        const p = res.data.data;
        
        // 解析字段显示
        const specs = parseJsonField(p.specs, {});
        const sku = parseJsonField(p.product_sku, []);
        const images = parseJsonField(p.images, []);
        const titleOptions = parseJsonField(p.ai_title_options, []);

        let detail = `📝 商品详情
━━━━━━━━━━━━━━━
ID: ${p.id}
商品ID: ${p.product_id}
标题: ${p.title || p.original_title || '-'}
`;
        if (p.ai_title) detail += `AI标题: ${p.ai_title}\n`;
        if (p.selected_title) detail += `已选标题: ${p.selected_title}\n`;
        detail += `价格: ${formatPrice(p.price)}
原价: ${formatPrice(p.original_price)}
类目: ${p.category || '-'}
状态: ${p.status} | 发布: ${p.publish_status}
图片: ${images.length} 张`;
        if (p.target_product_id) detail += `本地商品ID: ${p.target_product_id}\n`;
        if (Object.keys(specs).length > 0) detail += `规格: ${JSON.stringify(specs, null, 2)}\n`;
        if (sku.length > 0) detail += `SKU: ${sku.length} 个\n`;
        if (images.length > 0) {
            detail += `\n图片列表:\n`;
            images.forEach((img, i) => {
                const url = typeof img === 'string' ? img : (img.url || '');
                detail += `  ${i+1}. ${url.substring(0, 60)}${url.length > 60 ? '...' : ''}\n`;
            });
        }
        if (titleOptions.length > 0) {
            detail += `\nAI标题选项:\n`;
            titleOptions.forEach((opt, i) => {
                detail += `  ${i+1}. [${opt.style}] ${opt.title}\n`;
            });
        }

        alert(detail);
    } catch (e) {
        console.error(e);
        alert('查看失败');
    }
}

// ===== 图片画廊 =====
let _galleryItemId = null;

async function openImageGallery(itemId) {
    _galleryItemId = itemId;
    const modal = document.getElementById('image-gallery-modal');
    if (!modal) return;
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    await loadGalleryImages(itemId);
}

async function loadGalleryImages(itemId) {
    const container = document.getElementById('image-gallery-container');
    const countEl = document.getElementById('image-count');
    if (!container) return;

    try {
        const res = await axios.get(`/admin/ali-api/items/${itemId}/images`);
        if (!res.data.success) {
            container.innerHTML = `<div class="text-center text-danger py-5">加载失败: ${res.data.error}</div>`;
            return;
        }

        const images = res.data.data.images || [];
        if (countEl) countEl.textContent = `共${images.length}张图片`;

        if (images.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-inbox" style="font-size:3rem;"></i>
                    <p class="mt-2">暂无图片，请点击上方区域上传</p>
                </div>`;
            return;
        }

        container.innerHTML = `<div class="row g-3" id="image-grid">${
            images.map((img, idx) => `
                <div class="col-md-4 col-lg-3" data-index="${idx}">
                    <div class="card position-relative">
                        <img src="${escHtml(img.url)}" class="card-img-top" style="height:180px;object-fit:cover;" alt="商品图片"
                             onerror="safeImgOnError.call(this, 'large')">
                        <div class="card-body py-2 px-2">
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">${idx + 1}</small>
                                <div>
                                    <button class="btn btn-sm btn-outline-danger" title="删除" onclick="deleteGalleryImage(${itemId}, ${idx})">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('')
        }</div>`;
    } catch (e) {
        container.innerHTML = `<div class="text-center text-danger py-5">加载失败: ${e.message}</div>`;
    }
}

async function deleteGalleryImage(itemId, index) {
    if (!confirm(`确定要删除第 ${index + 1} 张图片吗？`)) return;
    try {
        showLoading();
        const res = await axios.delete(`/admin/ali-api/items/${itemId}/images/${index}`);
        if (res.data.success) {
            await loadGalleryImages(itemId);
            if (currentPage === 'products') loadProducts(currentProductPage);
        } else {
            alert('删除失败: ' + res.data.error);
        }
    } catch (e) {
        alert('删除失败: ' + (e.response?.data?.error || e.message));
    } finally {
        hideLoading();
    }
}

async function uploadGalleryImages(itemId, files) {
    if (!files || files.length === 0) return;
    
    for (const file of files) {
        if (file.size > 5 * 1024 * 1024) {
            alert(`文件 ${file.name} 超过 5MB 限制`);
            continue;
        }
        
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) {
            alert(`文件 ${file.name} 格式不支持`);
            continue;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            showLoading();
            const res = await axios.post(`/admin/ali-api/items/${itemId}/images/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            if (!res.data.success) {
                alert(`上传 ${file.name} 失败: ${res.data.error}`);
            }
        } catch (e) {
            alert(`上传 ${file.name} 失败: ${e.response?.data?.error || e.message}`);
        } finally {
            hideLoading();
        }
    }
    
    await loadGalleryImages(itemId);
    if (currentPage === 'products') loadProducts(currentProductPage);
}

// ===== 商品采集 =====
async function collectSingleProduct() {
    const productId = document.getElementById('product-id')?.value?.trim();
    if (!productId) { showMessage('collect-result', '请输入商品ID', 'error'); return; }

    try {
        showLoading();
        const res = await axios.post('/admin/ali-api/items/collect', { product_id: productId });
        if (res.data.success) {
            const tag = res.data.data.from_cache ? '（来自缓存）' : '';
            showMessage('collect-result', `✅ 采集成功${tag}！商品ID: ${res.data.data.item_id}`, 'success');
            document.getElementById('product-id').value = '';
            if (currentPage === 'dashboard') loadDashboard();
        } else {
            showMessage('collect-result', `❌ 采集失败: ${res.data.error}`, 'error');
        }
    } catch (e) {
        showMessage('collect-result', '❌ 采集失败: ' + (e.response?.data?.error || e.message), 'error');
    } finally {
        hideLoading();
    }
}

async function searchCollect() {
    const keywords = document.getElementById('search-keywords')?.value?.trim();
    if (!keywords) { showMessage('search-result', '请输入搜索关键词', 'error'); return; }

    const page = document.getElementById('search-page')?.value || 1;
    const size = document.getElementById('search-size')?.value || 20;

    try {
        showLoading();
        const res = await axios.post('/admin/ali-api/items/search', {
            keywords, page_no: parseInt(page), page_size: parseInt(size)
        });
        if (res.data.success) {
            const data = res.data.data;
            let msg = `✅ 搜索成功！找到${data.total} 个商品<br>`;
            if (data.products?.length > 0) {
                msg += '<hr><strong>结果预览:</strong><br>';
                data.products.slice(0, 5).forEach((p, i) => {
                    msg += `${i+1}. ${escHtml(p.title)} - ${formatPrice(p.price)}<br>`;
                });
                if (data.products.length > 5) msg += `...还有 ${data.products.length - 5} 个`;
            }
            showMessage('search-result', msg, 'success');
        } else {
            showMessage('search-result', '❌ 搜索失败: ' + res.data.error, 'error');
        }
    } catch (e) {
        const errMsg = e.response?.data?.error || e.message || '未知错误';
        showMessage('search-result', '❌ 搜索失败: ' + errMsg, 'error');
    } finally {
        hideLoading();
    }
}

// ===== AI 多标题选项生成 =====
async function generateAiTitles(itemId) {
    if (!confirm('确定要使用AI生成多版本标题选项吗？')) return;

    try {
        showLoading();
        const res = await axios.post(`/admin/ali-api/items/${itemId}/ai-titles`);
        if (res.data.success) {
            const options = res.data.data.ai_title_options;
            showTitleSelectionModal(itemId, options);
        } else {
            alert('AI生成标题失败: ' + res.data.error);
        }
    } catch (e) {
        alert('AI生成标题失败: ' + (e.response?.data?.error || e.message));
    } finally {
        hideLoading();
    }
}

function showTitleSelectionModal(itemId, options) {
    currentAiItemId = itemId;
    const modal = document.getElementById('ai-title-modal');
    if (!modal) return;

    const list = document.getElementById('ai-title-options');
    if (!list) return;

    if (!options || options.length === 0) {
        list.innerHTML = '<div class="text-muted">AI未生成有效的标题选项</div>';
    } else {
        list.innerHTML = options.map((opt, idx) => `
            <div class="card mb-2 title-option" onclick="selectAiTitle(this, ${opt.id})" data-title="${escHtml(opt.title)}" style="cursor:pointer">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center gap-2 mb-1">
                                <span class="badge bg-primary">选项${idx+1}</span>
                                <span class="badge bg-info">${styleLabel(opt.style)}</span>
                                ${idx === 0 ? '<span class="badge bg-warning text-dark">⭐ 推荐</span>' : ''}
                            </div>
                            <p class="mb-1 fw-bold">${escHtml(opt.title)}</p>
                            <small class="text-muted">${escHtml(opt.reason || '')}</small>
                        </div>
                        <div class="form-check ms-3 mt-2">
                            <input class="form-check-input" type="radio" name="title-radio" value="${idx}" ${idx === 0 ? 'checked' : ''}>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // 设置确认按钮
    document.getElementById('confirm-title-btn').onclick = async () => {
        const selected = document.querySelector('.title-option.selected');
        if (!selected) {
            alert('请选择一个标题');
            return;
        }
        const title = selected.getAttribute('data-title');
        await confirmSelectedTitle(itemId, title);
    };

    // 显示模态框
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

function styleLabel(style) {
    const map = { 'professional': '专业型', 'attractive': '吸引力型', 'concise': '简洁型', 'normal': '通用' };
    return map[style] || style;
}

function selectAiTitle(el, optId) {
    document.querySelectorAll('.title-option').forEach(e => {
        e.classList.remove('selected', 'border-primary');
    });
    el.classList.add('selected', 'border-primary');
    el.style.border = '2px solid #0d6efd';
    // 选中radio
    const radio = el.querySelector('input[type="radio"]');
    if (radio) radio.checked = true;
}

async function confirmSelectedTitle(itemId, title) {
    try {
        showLoading();
        const res = await axios.post(`/admin/ali-api/items/${itemId}/select-title`, { title });
        if (res.data.success) {
            alert('✅ 标题已选择成功！');
            // 关闭模态框
            const modal = document.getElementById('ai-title-modal');
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) bsModal.hide();
            // 刷新列表
            loadProducts(currentProductPage);
        } else {
            alert('选择失败: ' + res.data.error);
        }
    } catch (e) {
        alert('选择失败: ' + (e.response?.data?.error || e.message));
    } finally {
        hideLoading();
    }
}

// ===== 发布 =====
async function publishProduct(itemId) {
    const stock = prompt('请输入库存数量（默认999）', '999');
    if (stock === null) return;
    const stockNum = parseInt(stock) || 999;

    if (!confirm(`确定要将商品发布到本地商城吗？\n库存: ${stockNum}`)) return;

    try {
        showLoading();
        const res = await axios.post(`/admin/ali-api/items/${itemId}/publish`, { stock: stockNum });
        if (res.data.success) {
            alert(`✅ 发布成功！本地商品ID: ${res.data.data.target_product_id}\n标题: ${res.data.data.title}\n价格: ${formatPrice(res.data.data.price)}`);
            loadProducts(currentProductPage);
        } else {
            alert('❌ 发布失败: ' + res.data.error);
        }
    } catch (e) {
        alert('❌ 发布失败: ' + (e.response?.data?.error || e.message));
    } finally {
        hideLoading();
    }
}

// ===== API日志 =====
async function loadLogs(page) {
    if (page === undefined) page = currentLogPage;
    try {
        showLoading();
        const endpoint = document.getElementById('log-endpoint')?.value || '';
        const success = document.getElementById('log-success')?.value || '';
        let url = `/admin/ali-api/logs?page=${page}&per_page=20`;
        if (endpoint) url += `&endpoint=${encodeURIComponent(endpoint)}`;
        if (success) url += `&success=${success}`;

        const res = await axios.get(url);
        if (res.data.success) {
            updateLogsTable(res.data.data.logs);
            updateLogsPagination(res.data.data.pagination);
            currentLogPage = page;
        }
    } catch (e) {
        console.error('加载日志失败:', e);
    } finally {
        hideLoading();
    }
}

function updateLogsTable(logs) {
    const tbody = document.getElementById('logs-table');
    if (!tbody) return;
    if (!logs || logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">暂无日志</td></tr>';
        return;
    }
    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>${log.id}</td>
            <td>${log.user_id || '系统'}</td>
            <td><code>${escHtml(log.endpoint)}</code></td>
            <td><small class="text-muted">${escHtml(JSON.stringify(parseJsonField(log.params, {})).substring(0, 40))}</small></td>
            <td>${log.response_code || '-'}</td>
            <td>${log.response_time || '-'}</td>
            <td>${log.success ? '<span class="api-status status-active">成功</span>' : '<span class="api-status status-inactive">失败</span>'}</td>
            <td>${formatDate(log.created_at)}</td>
        </tr>
    `).join('');
}

function updateLogsPagination(pagination) {
    const el = document.getElementById('logs-pagination');
    if (!el) return;
    const { page, total_pages } = pagination;
    let html = '';
    html += page > 1
        ? `<li class="page-item"><a class="page-link" href="#" onclick="loadLogs(${page-1});return false;">上一页</a></li>`
        : `<li class="page-item disabled"><a class="page-link">上一页</a></li>`;
    const start = Math.max(1, page - 2);
    const end = Math.min(total_pages, page + 2);
    for (let i = start; i <= end; i++) {
        html += i === page
            ? `<li class="page-item active"><a class="page-link">${i}</a></li>`
            : `<li class="page-item"><a class="page-link" href="#" onclick="loadLogs(${i});return false;">${i}</a></li>`;
    }
    html += page < total_pages
        ? `<li class="page-item"><a class="page-link" href="#" onclick="loadLogs(${page+1});return false;">下一页</a></li>`
        : `<li class="page-item disabled"><a class="page-link">下一页</a></li>`;
    el.innerHTML = html;
}

// ===== 缓存管理 =====
async function loadCacheStats() {
    try {
        const res = await axios.get('/admin/ali-api/cache/stats');
        if (res.data.success) updateCacheDetails(res.data.data);
    } catch (e) {
        console.error(e);
    }
}

function updateCacheDetails(stats) {
    const el = document.getElementById('cache-details');
    if (!el) return;
    const redisConnected = stats.redis?.connected;
    el.innerHTML = `
        <h6><i class="bi bi-database"></i> Redis</h6>
        <p>状态: ${redisConnected ? '<span class="api-status status-active">已连接</span>' : '<span class="api-status status-inactive">未连接</span>'}</p>
        ${redisConnected ? `<p>内存: ${stats.redis.used_memory || 'N/A'}<br>连接数: ${stats.redis.connected_clients || 0}</p>` : '<p class="text-muted">使用内存缓存</p>'}
        <hr>
        <h6><i class="bi bi-memory"></i> 内存缓存</h6>
        <p>条目: ${stats.memory?.size ?? 0}/${stats.memory?.maxsize ?? '-'}<br>过期: ${stats.memory?.expired_entries ?? 0}<br>TTL: ${stats.memory?.ttl ?? '-'}秒</p>
        <hr>
        <p><strong>使用Redis:</strong> ${stats.use_redis ? '是' : '否'}</p>
    `;
}

// ===== 配置信息 =====
async function loadConfig() {
    try {
        const res = await axios.get('/admin/ali-api/config');
        if (!res.data.success) return;
        const c = res.data.data;

        // 阿里巴巴配置（填充输入框）
        const gwEl = document.getElementById('cfg-api-gateway');
        if (gwEl) gwEl.value = c.alibaba.api_gateway || '';
        const verEl = document.getElementById('cfg-api-version');
        if (verEl) verEl.value = c.alibaba.api_version || '';
        const sigEl = document.getElementById('cfg-sign-method');
        if (sigEl) sigEl.value = c.alibaba.sign_method || '';
        const keyEl = document.getElementById('cfg-app-key');
        if (keyEl) keyEl.value = c.alibaba.app_key_masked || '';
        // 如已配置则在 secret 输入框给予提示
        const secEl = document.getElementById('cfg-app-secret');
        if (secEl) secEl.placeholder = c.alibaba.app_key_configured ? '已配置，输入新值以覆盖' : '输入 1688 AppSecret';

        // AI配置
        const aiEl = document.getElementById('ai-config');
        if (aiEl) {
            aiEl.innerHTML = `
                <dt class="col-sm-5">供应商</dt><dd class="col-sm-7">${escHtml(c.ai.provider)}</dd>
                <dt class="col-sm-5">模型</dt><dd class="col-sm-7">${escHtml(c.ai.model)}</dd>
                <dt class="col-sm-5">状态</dt><dd class="col-sm-7"><span class="api-status ${c.ai.available ? 'status-active' : 'status-inactive'}">${c.ai.available ? '可用' : '不可用'}</span></dd>
            `;
        }

        // 风控配置
        const rlEl = document.getElementById('rate-limit-config');
        if (rlEl && c.rate_limit) {
            rlEl.innerHTML = `
                <dt class="col-sm-7">用户日限</dt><dd class="col-sm-5">${c.rate_limit.user_daily_limit}</dd>
                <dt class="col-sm-7">用户时限</dt><dd class="col-sm-5">${c.rate_limit.user_hourly_limit}</dd>
                <dt class="col-sm-7">全局并发</dt><dd class="col-sm-5">${c.rate_limit.global_concurrent_limit}</dd>
                <dt class="col-sm-7">全局QPS</dt><dd class="col-sm-5">${c.rate_limit.global_qps_limit}</dd>
                <dt class="col-sm-7">熔断阈值</dt><dd class="col-sm-5">${c.rate_limit.circuit_breaker_threshold}</dd>
            `;
        }

        // 缓存配置
        const cacheEl = document.getElementById('cache-config');
        if (cacheEl && c.cache) {
            cacheEl.innerHTML = `
                <dt class="col-sm-7">Redis</dt><dd class="col-sm-5"><span class="api-status ${c.cache.redis_configured ? 'status-active' : 'status-inactive'}">${c.cache.redis_configured ? '已配置' : '未配置'}</span></dd>
                <dt class="col-sm-7">内存缓存</dt><dd class="col-sm-5">${c.cache.memory_cache_maxsize}</dd>
                <dt class="col-sm-7">商品缓存TTL</dt><dd class="col-sm-5">${c.cache.product_cache_ttl}秒</dd>
            `;
        }
    } catch (e) {
        console.error('加载配置失败:', e);
    }
}

// ===== Settings（PluginManager 标准化配置）=====
async function loadSettings() {
    const el = document.getElementById('settings-content');
    if (!el) return;
    try {
        const res = await axios.get('/admin/ali-api/settings');
        if (!res.data.success) {
            el.innerHTML = '<div class="text-danger">加载失败: ' + escHtml(res.data.error) + '</div>';
            return;
        }
        const cfg = res.data.data.config || {};
        let h = '<div class="mb-3">';
        h += '<label class="form-label">API 网关地址</label>';
        h += '<input type="text" class="form-control" id="s-api-gateway" value="' + escHtml(cfg.api_gateway || '') + '" placeholder="https://gw.open.1688.com/openapi">';
        h += '<div class="form-text">1688 Open API 网关地址</div>';
        h += '</div>';
        h += '<button class="btn btn-primary" onclick="saveSettings()"><i class="bi bi-check-lg"></i> 保存配置</button>';
        h += ' <span id="settings-status" class="small text-muted"></span>';
        el.innerHTML = h;
    } catch (e) {
        el.innerHTML = '<div class="text-danger">加载失败: ' + escHtml(e.message) + '</div>';
    }
}

async function saveSettings() {
    const el = document.getElementById('settings-content');
    const btn = el ? el.querySelector('button') : null;
    const status = document.getElementById('settings-status');
    if (status) status.textContent = '保存中...';
    if (btn) btn.disabled = true;
    try {
        const data = {
            api_gateway: document.getElementById('s-api-gateway')?.value?.trim() || '',
        };
        const res = await axios.post('/admin/ali-api/settings', data);
        if (res.data.success) {
            if (status) { status.textContent = '✅ 已保存'; status.className = 'small text-success'; }
            setTimeout(() => { if (status) status.textContent = ''; }, 3000);
        } else {
            if (status) { status.textContent = '❌ ' + (res.data.error || '保存失败'); status.className = 'small text-danger'; }
        }
    } catch (e) {
        if (status) { status.textContent = '❌ ' + (e.response?.data?.error || e.message); status.className = 'small text-danger'; }
    } finally {
        if (btn) btn.disabled = false;
    }
}

// ===== 辅助函数 =====
function escHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function safeImgOnError(size) {
    const svg = size === 'large' 
        ? '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180"><rect fill="#f0f0f0" width="180" height="180"/><text x="55" y="95" font-size="14" fill="#999">加载失败</text></svg>'
        : '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><rect fill="#f0f0f0" width="80" height="80"/><text x="25" y="45" font-size="12" fill="#999">无图</text></svg>';
    this.src = 'data:image/svg+xml,' + encodeURIComponent(svg);
}

function parseJsonField(val, defaultVal) {
    if (val === null || val === undefined) return defaultVal;
    if (typeof val === 'string') {
        try { return JSON.parse(val); } catch { return defaultVal; }
    }
    return val;
}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', function() {
    initNavigation();
    loadDashboard();

    // 采集按钮
    const collectBtn = document.getElementById('collect-single-btn');
    if (collectBtn) collectBtn.addEventListener('click', collectSingleProduct);

    const searchBtn = document.getElementById('search-collect-btn');
    if (searchBtn) searchBtn.addEventListener('click', searchCollect);

    // AI优化按钮（采集页面的简化版）
    const aiOptBtn = document.getElementById('ai-optimize-btn');
    if (aiOptBtn) {
        aiOptBtn.addEventListener('click', async function() {
            const id = document.getElementById('ai-product-id')?.value?.trim();
            if (!id) { showMessage('ai-result', '请输入商品ID', 'error'); return; }
            const itemId = parseInt(id);
            if (isNaN(itemId)) { showMessage('ai-result', '请输入数字ID', 'error'); return; }
            await generateAiTitles(itemId);
        });
    }

    // 搜索回车
    const searchInput = document.getElementById('product-search');
    if (searchInput) searchInput.addEventListener('keypress', e => { if (e.key === 'Enter') loadProducts(1); });

    // 状态筛选
    const statusFilter = document.getElementById('status-filter');
    if (statusFilter) statusFilter.addEventListener('change', () => loadProducts(1));

    // 日志筛选
    const filterBtn = document.getElementById('filter-logs-btn');
    if (filterBtn) filterBtn.addEventListener('click', () => loadLogs(1));

    // 日志输入回车
    const logEndpoint = document.getElementById('log-endpoint');
    if (logEndpoint) logEndpoint.addEventListener('keypress', e => { if (e.key === 'Enter') loadLogs(1); });

    // 缓存管理
    const refreshBtn = document.getElementById('refresh-cache-stats');
    if (refreshBtn) refreshBtn.addEventListener('click', loadCacheStats);

    const cacheType = document.getElementById('cache-type');
    if (cacheType) {
        cacheType.addEventListener('change', function() {
            const container = document.getElementById('product-id-container');
            if (container) container.style.display = this.value === 'product' ? 'block' : 'none';
        });
    }

    const clearBtn = document.getElementById('clear-cache-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', async function() {
            if (!confirm('确定清理缓存？')) return;
            const type = document.getElementById('cache-type')?.value || 'all';
            const productId = document.getElementById('cache-product-id')?.value?.trim() || '';
            const data = { type };
            if (type === 'product' && productId) data.product_id = productId;

            try {
                showLoading();
                const res = await axios.post('/admin/ali-api/cache/clear', data);
                if (res.data.success) {
                    showMessage('clear-result', res.data.message, 'success');
                    loadCacheStats();
                    if (document.getElementById('cache-product-id')) document.getElementById('cache-product-id').value = '';
                } else {
                    showMessage('clear-result', '清理失败: ' + res.data.error, 'error');
                }
            } catch (e) {
                showMessage('clear-result', '清理失败', 'error');
            } finally {
                hideLoading();
            }
        });
    }

    // 图片上传区域
    const uploadZone = document.getElementById('upload-zone');
    const uploadInput = document.getElementById('image-upload-input');
    if (uploadZone && uploadInput) {
        uploadZone.addEventListener('click', () => uploadInput.click());
        
        uploadInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0 && _galleryItemId) {
                uploadGalleryImages(_galleryItemId, this.files);
                this.value = '';
            }
        });
        
        // 拖拽上传
        uploadZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.style.borderColor = '#0d6efd';
            this.style.background = '#e7f1ff';
        });
        uploadZone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.style.borderColor = '';
            this.style.background = '#f8f9fa';
        });
        uploadZone.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.borderColor = '';
            this.style.background = '#f8f9fa';
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0 && _galleryItemId) {
                uploadGalleryImages(_galleryItemId, e.dataTransfer.files);
            }
        });
    }
});

// ===== 配置保存 =====
async function saveConfig() {
    const appKey = document.getElementById('cfg-app-key')?.value?.trim();
    const appSecret = document.getElementById('cfg-app-secret')?.value?.trim();
    if (!appKey && !appSecret) {
        showMessage('config-save-result', '请至少填写 AppKey 或 AppSecret', 'error');
        return;
    }
    if (appKey && appKey.endsWith('...')) {
        showMessage('config-save-result', 'AppKey 显示为脱敏值，如需修改请完整输入新的 AppKey', 'error');
        return;
    }

    const btn = document.getElementById('save-config-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 保存中...'; }

    try {
        const res = await axios.post('/admin/ali-api/config', { app_key: appKey, app_secret: appSecret });
        if (res.data.success) {
            showMessage('config-save-result', '✅ ' + res.data.message, 'success');
            // 刷新配置展示
            loadConfig();
        } else {
            showMessage('config-save-result', '❌ ' + (res.data.error || '保存失败'), 'error');
        }
    } catch (e) {
        showMessage('config-save-result', '❌ 保存失败: ' + (e.response?.data?.error || e.message), 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-check-lg"></i> 保存配置'; }
    }
}