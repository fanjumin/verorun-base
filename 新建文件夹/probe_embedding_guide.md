# VeroRun 探针嵌入方案 — 完整实现指南

---

## 设计原则

探针不是独立模块，而是嵌入在系统核心代码中的"埋点纤维"。用户下载的代码包里没有 `telemetry/` 文件夹——探针逻辑散落在 `auth-center`、`agent_matrix`、`plugin_manager`、`site_builder` 的初始化代码中，删不掉，除非改源码。

```
你的服务器 (VeroRun Cloud)
┌─────────────────────────────────────────────────────┐
│  admin/app.py                                       │
│  ├── 探针接收 API（5 个路由，写死在 app 里）          │
│  ├── 监控仪表盘（/admin 菜单新增 "探针监控"）        │
│  └── 数据库表（随主库一起初始化）                    │
└──────────────┬──────────────────────────────────────┘
               │ HTTPS
               │ 所有用户实例定时上报
┌──────────────▼──────────────────────────────────────┐
│  用户下载的代码（开源部分）                           │
│                                                      │
│  auth-center/services/license_service.py             │
│  └── refresh() 方法中嵌入心跳上报                     │
│                                                      │
│  agent_matrix/engine.py                              │
│  └── run_agent() 执行前后嵌入埋点                     │
│                                                      │
│  plugin_manager/manager.py                           │
│  └── init_app() 完成后上报插件加载状态                │
│                                                      │
│  site_builder/engine.py                              │
│  └── build_site() 完成后上报建站事件                  │
└──────────────────────────────────────────────────────┘
```

---

## 一、服务端：数据库表

**位置：** 在 `auth-center/models/database.py` 的 `init_db()` 函数末尾追加建表 SQL。

用户实例的 SQLite 数据库不需要这些表——这些表只存在于你的 VeroRun Cloud 的 PostgreSQL 中。

### 建表 SQL（追加到 init_db 或单独执行）

```sql
-- 启动探针：每次用户实例启动记录一条（每日去重）
CREATE TABLE IF NOT EXISTS probe_startup (
    id              SERIAL PRIMARY KEY,
    device_id       VARCHAR(64) NOT NULL,
    license_key     VARCHAR(128),
    app_version     VARCHAR(32) NOT NULL,
    os_platform     VARCHAR(32),
    os_release      VARCHAR(64),
    client_ip       VARCHAR(45),
    extra_meta      JSONB DEFAULT '{}',
    received_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(device_id, DATE(received_at))
);

-- 心跳记录：高频写入，建议 30 天后归档
CREATE TABLE IF NOT EXISTS probe_heartbeat (
    id              SERIAL PRIMARY KEY,
    device_id       VARCHAR(64) NOT NULL,
    license_key     VARCHAR(128),
    status          VARCHAR(16) DEFAULT 'active',
    uptime_seconds  INTEGER DEFAULT 0,
    memory_mb       INTEGER DEFAULT 0,
    plugins_loaded  INTEGER DEFAULT 0,
    client_ip       VARCHAR(45),
    received_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 功能使用事件
CREATE TABLE IF NOT EXISTS probe_event (
    id              SERIAL PRIMARY KEY,
    device_id       VARCHAR(64) NOT NULL,
    license_key     VARCHAR(128),
    event_name      VARCHAR(64) NOT NULL,
    event_action    VARCHAR(32) NOT NULL,
    duration_ms     INTEGER,
    extra_data      JSONB DEFAULT '{}',
    received_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 错误报告
CREATE TABLE IF NOT EXISTS probe_error (
    id              SERIAL PRIMARY KEY,
    device_id       VARCHAR(64) NOT NULL,
    license_key     VARCHAR(128),
    error_type      VARCHAR(64) NOT NULL,
    error_message   TEXT,
    stack_trace     TEXT,
    severity        VARCHAR(16) DEFAULT 'warning',
    component       VARCHAR(64),
    received_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- License 验证记录
CREATE TABLE IF NOT EXISTS probe_license (
    id              SERIAL PRIMARY KEY,
    device_id       VARCHAR(64) NOT NULL,
    license_key     VARCHAR(128) NOT NULL,
    action          VARCHAR(16) NOT NULL,
    result          VARCHAR(16) NOT NULL,
    message         VARCHAR(255),
    client_ip       VARCHAR(45),
    received_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 设备汇聚表：去重后的设备信息
CREATE TABLE IF NOT EXISTS probe_devices (
    device_id       VARCHAR(64) PRIMARY KEY,
    license_key     VARCHAR(128),
    app_version     VARCHAR(32),
    os_platform     VARCHAR(32),
    os_release      VARCHAR(64),
    first_seen      TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen       TIMESTAMP NOT NULL DEFAULT NOW(),
    total_pings     INTEGER DEFAULT 0,
    total_errors    INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    is_banned       BOOLEAN DEFAULT FALSE,
    ban_reason      VARCHAR(255)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_hb_device  ON probe_heartbeat(device_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_hb_ts      ON probe_heartbeat(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_event_name ON probe_event(event_name, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_type ON probe_error(error_type, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_license_ts ON probe_license(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_dev_active ON probe_devices(last_seen DESC) WHERE is_active = TRUE;
```

---

## 二、服务端：探针接收 API

**位置：** 直接写在 `admin/app.py` 中，不创建独立 blueprint。

在 `admin/app.py` 的 `app = Flask(__name__)` 之后、蓝图注册之前，追加以下代码。

### 2.1 辅助函数

```python
# ── 探针接收辅助函数 ──────────────────────────────────────────────────
import json
import time
import hashlib
import hmac
import base64
from datetime import datetime

_PROBE_SECRET = os.environ.get('VERORUN_PROBE_SECRET', 'vr-probe-default-2026')
_PROBE_KEY_VERSION = 'v1'


def _probe_verify_signature(payload: dict, signature_b64: str, timestamp: int) -> bool:
    """验证探针数据的 HMAC-SHA256 签名 + 时间戳防重放"""
    now = int(time.time())
    if abs(now - timestamp) > 300:  # 5 分钟窗口
        return False
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    message = f'{timestamp}.{raw}'
    expected = hmac.new(
        _PROBE_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    expected_b64 = base64.b64encode(expected).decode('ascii')
    return hmac.compare_digest(expected_b64, signature_b64)


def _probe_decode_request(data: dict) -> dict or None:
    """解密 + 验签探针请求体"""
    encrypted = data.get('encrypted', '')
    signature = data.get('signature', '')
    timestamp = data.get('timestamp', 0)

    if not encrypted or not signature:
        return None

    # 解密（简单 XOR + 盐值，生产环境建议升级为 AES-256-GCM）
    try:
        packaged = base64.b64decode(encrypted)
        salt = packaged[4:20]
        ciphertext = packaged[20:]
        secret = _PROBE_SECRET
        key = hashlib.pbkdf2_hmac('sha256', secret.encode('utf-8'), salt, 100000, dklen=32)
        plaintext = bytes(ciphertext[i] ^ key[i % len(key)] for i in range(len(ciphertext)))
        payload = json.loads(plaintext.decode('utf-8'))
    except Exception:
        return None

    if not _probe_verify_signature(payload, signature, timestamp):
        return None

    return payload


def _probe_query_license(license_key: str) -> dict:
    """查询主库中的 License 信息"""
    if not license_key:
        return {'valid': False, 'status': 'no_key', 'days_remaining': 0, 'message': '未提供 License Key'}

    try:
        from models import get_db
        with get_db() as conn:
            row = conn.execute("""
                SELECT s.status, s.current_period_end, s.license_key, u.nickname
                FROM subscriptions s
                JOIN users u ON u.id = s.user_id
                WHERE s.license_key = %s
            """, (license_key,)).fetchone()

            if not row:
                return {'valid': False, 'status': 'invalid', 'days_remaining': 0, 'message': 'License 不存在'}

            row = dict(row)
            expires = row.get('current_period_end')
            now = datetime.now()

            if expires and isinstance(expires, str):
                expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))

            days = (expires - now).days if expires else 0
            return {
                'valid': days >= 0 and row.get('status') == 'active',
                'status': row.get('status', 'unknown'),
                'days_remaining': max(0, days),
                'expires_at': expires.isoformat() if expires else '',
                'user_name': row.get('nickname', ''),
            }
    except Exception as e:
        return {'valid': False, 'status': 'error', 'days_remaining': 0, 'message': str(e)}


def _probe_db_write(conn, table: str, **kwargs):
    """通用探针写入"""
    try:
        columns = ', '.join(kwargs.keys())
        placeholders = ', '.join(['%s'] * len(kwargs))
        conn.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            list(kwargs.values())
        )
    except Exception:
        pass  # 探针写入失败不抛异常
```

### 2.2 探针路由（追加到 admin/app.py）

```python
# ── 探针接收 API ──────────────────────────────────────────────────────

@app.route('/api/probe/startup', methods=['POST'])
def probe_startup():
    """
    接收启动探针 — 用户实例启动时自动调用
    请求体: { encrypted, signature, timestamp }
    解密后: { device_id, license_key, app_version, os_platform, os_release, started_at }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': '空请求'}), 400

    payload = _probe_decode_request(data)
    if not payload:
        return jsonify({'status': 'error', 'message': '验签失败'}), 403

    try:
        from models import get_db
        with get_db() as conn:
            _probe_db_write(conn, 'probe_startup',
                device_id=payload.get('device_id', ''),
                license_key=payload.get('license_key', ''),
                app_version=payload.get('app_version', ''),
                os_platform=payload.get('os_platform', ''),
                os_release=payload.get('os_release', ''),
                client_ip=request.remote_addr,
                extra_meta=json.dumps({}),
            )
            conn.commit()
    except:
        pass

    return jsonify({'status': 'ok', 'timestamp': int(time.time())})


@app.route('/api/probe/heartbeat', methods=['POST'])
def probe_heartbeat():
    """
    接收心跳 — 定时上报（5 分钟间隔）
    解密后: { device_id, license_key, status, uptime_seconds, memory_mb, plugins_loaded }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': '空请求'}), 400

    payload = _probe_decode_request(data)
    if not payload:
        return jsonify({'status': 'error', 'message': '验签失败'}), 403

    device_id = payload.get('device_id', '')
    license_key = payload.get('license_key', '')

    try:
        from models import get_db
        with get_db() as conn:
            _probe_db_write(conn, 'probe_heartbeat',
                device_id=device_id,
                license_key=license_key,
                status=payload.get('status', 'active'),
                uptime_seconds=payload.get('uptime_seconds', 0),
                memory_mb=payload.get('memory_mb', 0),
                plugins_loaded=payload.get('plugins_loaded', 0),
                client_ip=request.remote_addr,
            )
            # 更新设备汇聚表
            conn.execute("""
                INSERT INTO probe_devices (device_id, license_key, last_seen, total_pings, is_active)
                VALUES (%s, %s, NOW(), 1, TRUE)
                ON CONFLICT (device_id) DO UPDATE SET
                    last_seen = NOW(),
                    total_pings = probe_devices.total_pings + 1,
                    is_active = TRUE
            """, (device_id, license_key or ''))
            conn.commit()
    except:
        pass

    return jsonify({'status': 'ok', 'timestamp': int(time.time())})


@app.route('/api/probe/event', methods=['POST'])
def probe_event():
    """
    接收功能使用事件
    解密后: { device_id, license_key, event_name, event_action, duration_ms }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': '空请求'}), 400

    payload = _probe_decode_request(data)
    if not payload:
        return jsonify({'status': 'error', 'message': '验签失败'}), 403

    try:
        from models import get_db
        with get_db() as conn:
            _probe_db_write(conn, 'probe_event',
                device_id=payload.get('device_id', ''),
                license_key=payload.get('license_key', ''),
                event_name=payload.get('event_name', 'unknown'),
                event_action=payload.get('event_action', 'triggered'),
                duration_ms=payload.get('duration_ms'),
            )
            conn.commit()
    except:
        pass

    return jsonify({'status': 'ok'})


@app.route('/api/probe/error', methods=['POST'])
def probe_error():
    """
    接收错误报告
    解密后: { device_id, license_key, error_type, error_message, stack_trace, severity, component }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': '空请求'}), 400

    payload = _probe_decode_request(data)
    if not payload:
        return jsonify({'status': 'error', 'message': '验签失败'}), 403

    try:
        from models import get_db
        with get_db() as conn:
            _probe_db_write(conn, 'probe_error',
                device_id=payload.get('device_id', ''),
                license_key=payload.get('license_key', ''),
                error_type=payload.get('error_type', 'unknown'),
                error_message=payload.get('error_message', ''),
                stack_trace=payload.get('stack_trace'),
                severity=payload.get('severity', 'warning'),
                component=payload.get('component', ''),
            )
            conn.execute(
                "UPDATE probe_devices SET total_errors = total_errors + 1, last_seen = NOW() WHERE device_id = %s",
                (payload.get('device_id', ''),)
            )
            conn.commit()
    except:
        pass

    return jsonify({'status': 'ok'})


@app.route('/api/probe/license/check', methods=['POST'])
def probe_license_check():
    """
    License 验证 — 用户实例启动和定时检查时调用
    解密后: { device_id, license_key }
    返回: { status: 'ok', data: { valid, status, days_remaining, expires_at } }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': '空请求'}), 400

    payload = _probe_decode_request(data)
    if not payload:
        return jsonify({'status': 'error', 'message': '验签失败'}), 403

    license_key = payload.get('license_key', '')
    device_id = payload.get('device_id', '')
    result = _probe_query_license(license_key)

    try:
        from models import get_db
        with get_db() as conn:
            _probe_db_write(conn, 'probe_license',
                device_id=device_id,
                license_key=license_key,
                action='check',
                result='valid' if result['valid'] else 'invalid',
                message=result.get('message', ''),
                client_ip=request.remote_addr,
            )
            conn.commit()
    except:
        pass

    return jsonify({'status': 'ok', 'data': result, 'timestamp': int(time.time())})
```

---

## 三、服务端：监控仪表盘

**位置：** 在 `admin/templates/partials/` 下新建 `probe_monitor.html`，并在 `admin/templates/admin.html` 的侧边栏菜单中添加入口。

### 3.1 菜单入口（admin.html 侧边栏）

在 `admin.html` 的侧边栏 `<ul class="nav-sidebar">` 中追加：

```html
<li class="nav-item">
    <a href="#" class="nav-link" data-page="probe_monitor">
        <i class="nav-icon fas fa-satellite-dish"></i>
        <p>探针监控</p>
    </a>
</li>
```

### 3.2 监控仪表盘页面（probe_monitor.html）

```html
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <h4 class="mb-3">探针监控 — 设备运行状态</h4>
        </div>
    </div>

    <!-- 顶部统计卡片 -->
    <div class="row" id="probe-stats-cards">
        <div class="col-lg-3 col-6">
            <div class="small-box bg-info">
                <div class="inner">
                    <h3 id="stat-active-1h">--</h3>
                    <p>活跃设备 (1小时)</p>
                </div>
                <div class="icon"><i class="fas fa-broadcast-tower"></i></div>
            </div>
        </div>
        <div class="col-lg-3 col-6">
            <div class="small-box bg-success">
                <div class="inner">
                    <h3 id="stat-active-24h">--</h3>
                    <p>活跃设备 (24小时)</p>
                </div>
                <div class="icon"><i class="fas fa-check-circle"></i></div>
            </div>
        </div>
        <div class="col-lg-3 col-6">
            <div class="small-box bg-warning">
                <div class="inner">
                    <h3 id="stat-errors-today">--</h3>
                    <p>今日错误</p>
                </div>
                <div class="icon"><i class="fas fa-exclamation-triangle"></i></div>
            </div>
        </div>
        <div class="col-lg-3 col-6">
            <div class="small-box bg-danger">
                <div class="inner">
                    <h3 id="stat-expired">--</h3>
                    <p>过期 License</p>
                </div>
                <div class="icon"><i class="fas fa-clock"></i></div>
            </div>
        </div>
    </div>

    <!-- 设备列表 -->
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title">设备列表</h5>
                    <div class="card-tools">
                        <button class="btn btn-sm btn-outline-secondary" onclick="refreshProbeData()">
                            <i class="fas fa-sync-alt"></i> 刷新
                        </button>
                    </div>
                </div>
                <div class="card-body table-responsive p-0">
                    <table class="table table-hover text-nowrap">
                        <thead>
                            <tr>
                                <th>设备 ID</th>
                                <th>License</th>
                                <th>版本</th>
                                <th>系统</th>
                                <th>最后活跃</th>
                                <th>状态</th>
                            </tr>
                        </thead>
                        <tbody id="probe-devices-table">
                            <tr><td colspan="6" class="text-center">加载中...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="col-md-4">
            <!-- 功能使用排行 -->
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title">功能使用排行 (7天)</h5>
                </div>
                <div class="card-body p-0">
                    <ul class="list-group list-group-flush" id="probe-feature-ranking">
                        <li class="list-group-item text-center text-muted">加载中...</li>
                    </ul>
                </div>
            </div>

            <!-- 今日错误 -->
            <div class="card mt-3">
                <div class="card-header">
                    <h5 class="card-title">今日错误</h5>
                </div>
                <div class="card-body p-0">
                    <ul class="list-group list-group-flush" id="probe-error-list">
                        <li class="list-group-item text-center text-muted">加载中...</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function refreshProbeData() {
    fetch('/api/probe/admin/stats')
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'ok') return;

            // 统计卡片
            document.getElementById('stat-active-1h').textContent = data.data.active_devices_1h;
            document.getElementById('stat-active-24h').textContent = data.data.active_devices_24h;
            document.getElementById('stat-errors-today').textContent = data.data.errors_today;
            document.getElementById('stat-expired').textContent = data.data.expired_licenses || 0;

            // 设备列表
            const tbody = document.getElementById('probe-devices-table');
            tbody.innerHTML = '';
            if (data.data.devices && data.data.devices.length > 0) {
                data.data.devices.forEach(d => {
                    const statusBadge = d.is_active
                        ? '<span class="badge badge-success">在线</span>'
                        : '<span class="badge badge-secondary">离线</span>';
                    const bannedBadge = d.is_banned
                        ? '<span class="badge badge-danger ml-1">封禁</span>'
                        : '';
                    tbody.innerHTML += `
                        <tr>
                            <td><code>${(d.device_id || '').substring(0, 12)}...</code></td>
                            <td><small>${(d.license_key || '').substring(0, 12)}...</small></td>
                            <td>${d.app_version || '-'}</td>
                            <td>${d.os_platform || '-'} ${d.os_release || ''}</td>
                            <td><small>${d.last_seen || '-'}</small></td>
                            <td>${statusBadge}${bannedBadge}</td>
                        </tr>`;
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暂无设备</td></tr>';
            }

            // 功能排行
            const ranking = document.getElementById('probe-feature-ranking');
            ranking.innerHTML = '';
            if (data.data.feature_ranking && data.data.feature_ranking.length > 0) {
                data.data.feature_ranking.forEach((f, i) => {
                    ranking.innerHTML += `
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <span><span class="badge badge-primary mr-2">${i + 1}</span>${f.event_name}</span>
                            <span class="badge badge-info">${f.count} 次</span>
                        </li>`;
                });
            } else {
                ranking.innerHTML = '<li class="list-group-item text-center text-muted">暂无数据</li>';
            }

            // 错误列表
            const errorList = document.getElementById('probe-error-list');
            errorList.innerHTML = '';
            if (data.data.error_breakdown && data.data.error_breakdown.length > 0) {
                data.data.error_breakdown.forEach(e => {
                    const sevBadge = e.severity === 'error' || e.severity === 'critical'
                        ? 'badge-danger' : 'badge-warning';
                    errorList.innerHTML += `
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <span>${e.error_type} <span class="badge ${sevBadge}">${e.severity}</span></span>
                            <span class="badge badge-secondary">${e.count} 次</span>
                        </li>`;
                });
            } else {
                errorList.innerHTML = '<li class="list-group-item text-center text-muted">暂无错误</li>';
            }
        });
}

// 页面加载时自动刷新
refreshProbeData();
// 每 30 秒自动刷新
setInterval(refreshProbeData, 30000);
</script>
```

### 3.3 监控数据 API（追加到 admin/app.py）

```python
@app.route('/api/probe/admin/stats', methods=['GET'])
def probe_admin_stats():
    """
    探针数据概览 API — 监控仪表盘用
    返回: { status: 'ok', data: { active_devices_1h, active_devices_24h, ... } }
    """
    try:
        from models import get_db
        with get_db() as conn:
            # 活跃设备数
            active_1h = conn.execute(
                "SELECT COUNT(DISTINCT device_id) FROM probe_heartbeat WHERE received_at >= NOW() - INTERVAL '1 hour'"
            ).fetchone()
            active_24h = conn.execute(
                "SELECT COUNT(DISTINCT device_id) FROM probe_heartbeat WHERE received_at >= NOW() - INTERVAL '24 hours'"
            ).fetchone()

            # 今日错误
            errors_today = conn.execute(
                "SELECT COUNT(*) FROM probe_error WHERE received_at >= CURRENT_DATE"
            ).fetchone()

            # 过期 License
            expired = conn.execute(
                "SELECT COUNT(DISTINCT license_key) FROM probe_license WHERE result = 'invalid' AND received_at >= CURRENT_DATE"
            ).fetchone()

            # 设备列表
            devices = conn.execute("""
                SELECT device_id, license_key, app_version, os_platform, os_release,
                       last_seen, is_active, is_banned, total_pings, total_errors
                FROM probe_devices
                ORDER BY last_seen DESC
                LIMIT 50
            """).fetchall()

            # 功能排行
            features = conn.execute("""
                SELECT event_name, COUNT(*) as count, AVG(duration_ms)::INTEGER as avg_ms
                FROM probe_event
                WHERE received_at >= NOW() - INTERVAL '7 days'
                GROUP BY event_name
                ORDER BY count DESC
                LIMIT 10
            """).fetchall()

            # 错误分布
            errors = conn.execute("""
                SELECT error_type, severity, COUNT(*) as count
                FROM probe_error
                WHERE received_at >= CURRENT_DATE
                GROUP BY error_type, severity
                ORDER BY count DESC
                LIMIT 10
            """).fetchall()

        return jsonify({
            'status': 'ok',
            'timestamp': int(time.time()),
            'data': {
                'active_devices_1h': active_1h[0] if active_1h else 0,
                'active_devices_24h': active_24h[0] if active_24h else 0,
                'errors_today': errors_today[0] if errors_today else 0,
                'expired_licenses': expired[0] if expired else 0,
                'devices': [dict(d) for d in devices],
                'feature_ranking': [dict(f) for f in features],
                'error_breakdown': [dict(e) for e in errors],
                'server_time': datetime.now().isoformat(),
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
```

---

## 四、客户端：嵌入到用户下载的代码中

以下代码嵌入到用户下载的 VeroRun 源码中，不是独立模块。

### 4.1 核心探针函数（嵌入到 auth-center/services/license_service.py）

在 `license_service.py` 的 `LicenseService` 类中，修改 `refresh()` 方法，嵌入心跳上报逻辑。

**修改前的方法签名不变，在方法内部追加：**

```python
# ── 追加到 license_service.py 的 LicenseService 类中 ────────────────

def _build_probe_payload(self, action: str, extra: dict = None) -> dict:
    """
    构建探针请求体（加密 + 签名）。
    注意：此函数嵌入在 license_service.py 中，不是独立模块。
    """
    import hashlib, hmac, base64, os, time, json, platform

    _PROBE_SECRET = os.environ.get('VERORUN_PROBE_SECRET', 'vr-probe-default-2026')
    _PROBE_URL = os.environ.get('VERORUN_PROBE_URL', 'https://api.verorun.com')

    # 设备指纹
    hostname = platform.node()
    mac = str(getattr(__import__('uuid'), 'getnode')())
    device_id = hashlib.sha256(f'{hostname}|{mac}'.encode()).hexdigest()[:32]

    payload = {
        'device_id': device_id,
        'license_key': self._get_config('deployment_code', ''),
        'app_version': self._get_app_version(),
        'os_platform': platform.system(),
        'os_release': platform.release(),
        'action': action,
        'timestamp': int(time.time()),
    }
    if extra:
        payload.update(extra)

    # 加密
    secret = _PROBE_SECRET
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', secret.encode('utf-8'), salt, 100000, dklen=32)
    plaintext = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')
    ciphertext = bytes(plaintext[i] ^ key[i % len(key)] for i in range(len(plaintext)))
    version_flag = b'v1\x00\x00'
    packaged = version_flag + salt + ciphertext
    encrypted = base64.b64encode(packaged).decode('ascii')

    # 签名
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    message = f'{payload["timestamp"]}.{raw}'
    signature = hmac.new(
        secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256
    ).digest()
    signature_b64 = base64.b64encode(signature).decode('ascii')

    return {
        'url': _PROBE_URL,
        'payload': payload,
        'body': {
            'encrypted': encrypted,
            'signature': signature_b64,
            'timestamp': payload['timestamp'],
        }
    }


def _send_probe(self, action: str, extra: dict = None) -> bool:
    """
    发送探针到 VeroRun Cloud。
    失败不抛异常，不阻塞主流程。
    """
    try:
        probe = self._build_probe_payload(action, extra)
        import urllib.request
        body = json.dumps(probe['body']).encode('utf-8')
        req = urllib.request.Request(
            f'{probe["url"]}/api/probe/{action}',
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except:
        return False  # 探针失败不影响系统运行


def _get_app_version(self) -> str:
    """获取当前版本号"""
    try:
        from version import get_version
        return get_version()
    except:
        return '0.0.0'
```

### 4.2 修改 refresh() 方法（追加探针上报）

在 `license_service.py` 的 `refresh()` 方法**末尾**（`return self.get_status()` 之前），追加：

```python
    # ── 探针：刷新 License 时同时上报心跳 ──
    # 注意：这里不阻塞 refresh() 的正常返回
    try:
        import threading
        t = threading.Thread(target=self._send_probe, args=('heartbeat',), daemon=True)
        t.start()
    except:
        pass
```

### 4.3 嵌入到 agent_matrix/engine.py（Agent 执行埋点）

在 `engine.py` 的 `AIEngine` 类中找到 `run_agent` 或类似方法，在方法体前后插入：

```python
# ── 追加到 engine.py 的 AIEngine 类中 ──

def _track_agent_event(self, event_name: str, action: str, duration_ms: int = None):
    """
    Agent 执行事件埋点。
    注意：直接嵌入在 engine.py 中，不依赖外部模块。
    """
    try:
        import threading
        args = (event_name, action, duration_ms)
        t = threading.Thread(target=self._do_track, args=args, daemon=True)
        t.start()
    except:
        pass


def _do_track(self, event_name: str, action: str, duration_ms: int = None):
    """异步发送埋点（复用 license_service 的探针通道）"""
    try:
        from services.license_service import LicenseService
        svc = LicenseService()
        extra = {
            'event_name': event_name,
            'event_action': action,
        }
        if duration_ms is not None:
            extra['duration_ms'] = duration_ms
        svc._send_probe('event', extra)
    except:
        pass
```

在 `run_agent` 或 Agent 执行的方法中：

```python
def run_agent(self, instruction, session_id=None, ...):
    # ── 探针：记录开始 ──
    start_time = time.time()
    self._track_agent_event('agent_execution', 'started')

    try:
        # ... 原有 Agent 执行逻辑 ...
        result = self._execute_agent(instruction, session_id)

        # ── 探针：记录成功 ──
        duration = int((time.time() - start_time) * 1000)
        self._track_agent_event('agent_execution', 'completed', duration)
        return result

    except Exception as e:
        # ── 探针：记录失败 ──
        import traceback
        self._track_agent_event('agent_execution', 'failed')
        self._report_agent_error(e, traceback.format_exc())
        raise
```

### 4.4 嵌入到 plugin_manager/manager.py（插件加载埋点）

在 `PluginManager.init_app()` 方法末尾追加：

```python
    # ── 探针：上报插件加载状态 ──
    try:
        import threading
        def _report():
            try:
                from services.license_service import LicenseService
                svc = LicenseService()
                svc._send_probe('heartbeat', {
                    'plugins_loaded': len(self._cache),
                    'status': 'active',
                })
            except:
                pass
        t = threading.Thread(target=_report, daemon=True)
        t.start()
    except:
        pass
```

### 4.5 嵌入到 site_builder/engine.py（建站埋点）

在 `site_builder/engine.py` 的建站方法中，建站完成后追加：

```python
    # ── 探针：上报建站事件 ──
    try:
        import threading
        def _report():
            try:
                from services.license_service import LicenseService
                svc = LicenseService()
                svc._send_probe('event', {
                    'event_name': 'site_built',
                    'event_action': 'completed',
                    'extra_data': json.dumps({'template': template_name}),
                })
            except:
                pass
        t = threading.Thread(target=_report, daemon=True)
        t.start()
    except:
        pass
```

---

## 五、全局错误捕获（嵌入到 admin/app.py 或 site/app.py）

在 Flask app 的 `before_request` 或 `errorhandler` 中追加全局错误上报：

```python
# ── 追加到 admin/app.py ──

@app.errorhandler(Exception)
def _probe_global_error_handler(e):
    """全局错误捕获 — 上报到探针系统"""
    import traceback
    try:
        import threading
        def _report():
            try:
                from services.license_service import LicenseService
                svc = LicenseService()
                svc._send_probe('error', {
                    'error_type': type(e).__name__,
                    'error_message': str(e)[:500],
                    'stack_trace': traceback.format_exc()[:2000],
                    'severity': 'error',
                    'component': 'admin',
                })
            except:
                pass
        t = threading.Thread(target=_report, daemon=True)
        t.start()
    except:
        pass
    # 继续原来的错误处理
    return original_error_handler(e)
```

---

## 六、环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VERORUN_PROBE_URL` | `https://api.verorun.com` | 探针接收地址 |
| `VERORUN_PROBE_SECRET` | `vr-probe-default-2026` | 探针加密密钥（生产环境**必须修改**） |

**用户实例不需要设置这些变量**——默认值指向你的服务器。只有你自己的服务器需要设置 `VERORUN_PROBE_SECRET`。

---

## 七、部署检查清单

- [ ] 在 VeroRun Cloud 的 PostgreSQL 中执行建表 SQL（第一节）
- [ ] 在 `admin/app.py` 中追加探针接收路由（第二节）
- [ ] 在 `admin/templates/partials/` 新建 `probe_monitor.html`（第三节）
- [ ] 在 `admin/templates/admin.html` 侧边栏添加菜单入口
- [ ] 修改 `auth-center/services/license_service.py` 嵌入探针核心函数（第四节 4.1-4.2）
- [ ] 修改 `agent_matrix/engine.py` 嵌入 Agent 执行埋点（第四节 4.3）
- [ ] 修改 `plugin_manager/manager.py` 嵌入插件加载埋点（第四节 4.4）
- [ ] 修改 `site_builder/engine.py` 嵌入建站埋点（第四节 4.5）
- [ ] 设置生产环境 `VERORUN_PROBE_SECRET`（第六节）
- [ ] 验证：启动一个用户实例，确认监控仪表盘能收到数据