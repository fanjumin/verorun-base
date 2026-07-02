#!/usr/bin/env python3
"""
阿里巴巴API数据模型

包含：
1. ali_api_items - 阿里巴巴商品缓存表
2. ali_api_logs - API调用日志表
3. ali_api_user_stats - 用户调用统计表
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

# 导入主项目数据库配置
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'auth-center'))
try:
    from models import get_db as get_main_db
    USE_MAIN_DB = True
except ImportError:
    USE_MAIN_DB = False

@contextmanager
def get_db():
    """获取数据库连接"""
    if USE_MAIN_DB:
        with get_main_db() as conn:
            yield conn
    else:
        # 独立数据库连接（开发测试用）
        db_path = os.environ.get("ALIBABA_DB_PATH", os.path.join(os.path.dirname(__file__), "ali_api.db"))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

# ===== 数据模型类 =====

class AliApiItem:
    """阿里巴巴商品缓存"""
    
    @staticmethod
    def create_table(conn):
        """创建商品缓存表"""
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ali_api_items (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER DEFAULT 0,
                product_id          TEXT UNIQUE NOT NULL,
                source_url          TEXT DEFAULT '',
                title               TEXT NOT NULL DEFAULT '',
                original_title      TEXT DEFAULT '',
                price               DECIMAL(10,2) DEFAULT 0,
                original_price      DECIMAL(10,2) DEFAULT 0,
                currency            TEXT DEFAULT 'CNY',
                category            TEXT DEFAULT '',
                images              TEXT DEFAULT '[]',
                specs               TEXT DEFAULT '{}',
                product_sku         TEXT DEFAULT '[]',
                description         TEXT DEFAULT '',
                -- AI 处理结果
                ai_title            TEXT DEFAULT '',
                ai_title_options    TEXT DEFAULT '[]',
                selected_title      TEXT DEFAULT '',
                ai_description      TEXT DEFAULT '',
                -- 发布状态
                publish_status      TEXT DEFAULT 'draft',
                target_product_id   INTEGER DEFAULT NULL,
                -- 统计
                api_call_count      INTEGER DEFAULT 0,
                -- 原始API响应
                api_response        TEXT DEFAULT '{}',
                status              TEXT DEFAULT 'active',
                last_synced_at      TEXT DEFAULT NULL,
                error_msg           TEXT DEFAULT '',
                created_at          TEXT DEFAULT (datetime('now','localtime')),
                updated_at          TEXT DEFAULT (datetime('now','localtime')),
                processed_at        TEXT DEFAULT NULL
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ali_items_product_id ON ali_api_items(product_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ali_items_status ON ali_api_items(status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ali_items_category ON ali_api_items(category)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ali_items_user ON ali_api_items(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ali_items_publish ON ali_api_items(publish_status)')
    
    @staticmethod
    def insert_or_update(conn, item_data: Dict[str, Any]) -> int:
        """插入或更新商品数据"""
        now = datetime.now().isoformat()
        
        # 准备数据
        product_id = item_data.get('product_id')
        if not product_id:
            raise ValueError("product_id 不能为空")
        
        # 检查是否存在
        cursor = conn.execute('SELECT id FROM ali_api_items WHERE product_id = ?', (product_id,))
        existing = cursor.fetchone()
        
        now_iso = datetime.now().isoformat()
        
        # 通用字段处理
        _title = item_data.get('title', '')
        _original_title = item_data.get('original_title', '') or _title
        _ai_title = item_data.get('ai_title', '')
        _ai_title_options = json.dumps(item_data.get('ai_title_options', []), ensure_ascii=False)
        _selected_title = item_data.get('selected_title', '')
        _description = item_data.get('description', '')
        _ai_description = item_data.get('ai_description', '')
        _price = item_data.get('price', 0)
        _original_price = item_data.get('original_price', 0)
        _currency = item_data.get('currency', 'CNY')
        _category = item_data.get('category', '')
        _images = json.dumps(item_data.get('images', []), ensure_ascii=False)
        _specs = json.dumps(item_data.get('specs', {}), ensure_ascii=False)
        _product_sku = json.dumps(item_data.get('product_sku', []), ensure_ascii=False)
        _source_url = item_data.get('source_url', '')
        _api_response = json.dumps(item_data.get('api_response', {}), ensure_ascii=False)
        _status = item_data.get('status', 'active')
        _publish_status = item_data.get('publish_status', 'draft')
        _target_product_id = item_data.get('target_product_id')
        _api_call_count = item_data.get('api_call_count', 0)
        _user_id = item_data.get('user_id', 0)
        _error_msg = item_data.get('error_msg', '')
        _processed_at = item_data.get('processed_at')
        
        if existing:
            # 更新
            conn.execute('''
                UPDATE ali_api_items SET
                    user_id = ?, title = ?, original_title = ?,
                    ai_title = ?, ai_title_options = ?, selected_title = ?,
                    description = ?, ai_description = ?,
                    price = ?, original_price = ?, currency = ?,
                    category = ?, images = ?, specs = ?, product_sku = ?,
                    source_url = ?, api_response = ?, status = ?,
                    publish_status = ?, target_product_id = ?,
                    api_call_count = api_call_count + ?,
                    last_synced_at = ?, error_msg = ?,
                    processed_at = COALESCE(?, processed_at),
                    updated_at = ?
                WHERE product_id = ?
            ''', (
                _user_id, _title, _original_title,
                _ai_title, _ai_title_options, _selected_title,
                _description, _ai_description,
                _price, _original_price, _currency,
                _category, _images, _specs, _product_sku,
                _source_url, _api_response, _status,
                _publish_status, _target_product_id,
                _api_call_count,
                now_iso, _error_msg,
                _processed_at,
                now_iso,
                product_id
            ))
            return existing['id']
        else:
            # 插入
            cursor = conn.execute('''
                INSERT INTO ali_api_items (
                    user_id, product_id, source_url,
                    title, original_title,
                    ai_title, ai_title_options, selected_title,
                    description, ai_description,
                    price, original_price, currency,
                    category, images, specs, product_sku,
                    api_response, status,
                    publish_status, target_product_id,
                    api_call_count, error_msg,
                    last_synced_at, processed_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?)
            ''', (
                _user_id, product_id, _source_url,
                _title, _original_title,
                _ai_title, _ai_title_options, _selected_title,
                _description, _ai_description,
                _price, _original_price, _currency,
                _category, _images, _specs, _product_sku,
                _api_response, _status,
                _publish_status, _target_product_id,
                _api_call_count, _error_msg,
                now_iso, _processed_at,
                now_iso, now_iso
            ))
            return cursor.lastrowid
    
    @staticmethod
    def get_by_id(conn, item_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取商品"""
        row = conn.execute('SELECT * FROM ali_api_items WHERE id = ?', (item_id,)).fetchone()
        if not row:
            return None
        return dict(row)
    
    @staticmethod
    def get_by_product_id(conn, product_id: str) -> Optional[Dict[str, Any]]:
        """根据阿里巴巴商品ID获取"""
        row = conn.execute('SELECT * FROM ali_api_items WHERE product_id = ?', (product_id,)).fetchone()
        if not row:
            return None
        return dict(row)
    
    @staticmethod
    def list_items(conn, status: str = 'active', limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """列出商品"""
        query = 'SELECT * FROM ali_api_items WHERE status = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?'
        rows = conn.execute(query, (status, limit, offset)).fetchall()
        return [dict(row) for row in rows]
    
    @staticmethod
    def search_items(conn, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """搜索商品（已转义 LIKE 通配符）"""
        # 转义 LIKE 中的特殊字符 % 和 _
        escaped = keyword.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = '''
            SELECT * FROM ali_api_items 
            WHERE (title LIKE ? ESCAPE '\\' OR original_title LIKE ? ESCAPE '\\' 
                   OR ai_title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')
            AND status = 'active'
            ORDER BY updated_at DESC LIMIT ?
        '''
        pattern = f'%{escaped}%'
        rows = conn.execute(query, (pattern, pattern, pattern, pattern, limit)).fetchall()
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_publish_status(conn, item_id: int, publish_status: str, target_product_id: int = None) -> bool:
        """更新发布状态"""
        now_iso = datetime.now().isoformat()
        if target_product_id:
            conn.execute('''
                UPDATE ali_api_items SET
                    publish_status = ?, target_product_id = ?,
                    processed_at = ?, updated_at = ?
                WHERE id = ?
            ''', (publish_status, target_product_id, now_iso, now_iso, item_id))
        else:
            conn.execute('''
                UPDATE ali_api_items SET
                    publish_status = ?, processed_at = ?, updated_at = ?
                WHERE id = ?
            ''', (publish_status, now_iso, now_iso, item_id))
        return conn.rowcount > 0
    
    @staticmethod
    def update_ai_titles(conn, item_id: int, ai_title_options: list, selected_title: str = '') -> bool:
        """更新AI生成的标题选项"""
        now_iso = datetime.now().isoformat()
        conn.execute('''
            UPDATE ali_api_items SET
                ai_title_options = ?, selected_title = ?,
                ai_title = ?, updated_at = ?
            WHERE id = ?
        ''', (
            json.dumps(ai_title_options, ensure_ascii=False),
            selected_title,
            selected_title or (ai_title_options[0]['title'] if ai_title_options else ''),
            now_iso,
            item_id
        ))
        return conn.rowcount > 0
    
    @staticmethod
    def list_by_publish_status(conn, publish_status: str = 'draft', limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """按发布状态列出商品"""
        rows = conn.execute(
            'SELECT * FROM ali_api_items WHERE publish_status = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?',
            (publish_status, limit, offset)
        ).fetchall()
        return [dict(row) for row in rows]

class AliApiLog:
    """API调用日志"""
    
    @staticmethod
    def create_table(conn):
        """创建API日志表"""
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ali_api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                api_key_id INTEGER REFERENCES api_keys(id),
                endpoint TEXT NOT NULL,
                params TEXT DEFAULT '{}',
                response_code INTEGER,
                response_time INTEGER,
                success INTEGER DEFAULT 0,
                error_msg TEXT,
                ip_address TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ali_logs_user ON ali_api_logs(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ali_logs_endpoint ON ali_api_logs(endpoint)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ali_logs_created ON ali_api_logs(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ali_logs_success ON ali_api_logs(success)')
    
    @staticmethod
    def log_request(conn, log_data: Dict[str, Any]) -> int:
        """记录API请求日志"""
        cursor = conn.execute('''
            INSERT INTO ali_api_logs (
                user_id, api_key_id, endpoint, params,
                response_code, response_time, success,
                error_msg, ip_address, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            log_data.get('user_id'),
            log_data.get('api_key_id'),
            log_data.get('endpoint', ''),
            json.dumps(log_data.get('params', {}), ensure_ascii=False),
            log_data.get('response_code'),
            log_data.get('response_time'),
            1 if log_data.get('success', False) else 0,
            log_data.get('error_msg', ''),
            log_data.get('ip_address', ''),
            datetime.now().isoformat()
        ))
        return cursor.lastrowid
    
    @staticmethod
    def get_stats(conn, hours: int = 24) -> Dict[str, Any]:
        """获取统计信息"""
        # 总调用次数
        total = conn.execute('SELECT COUNT(*) as count FROM ali_api_logs').fetchone()['count']
        
        # 成功/失败次数
        success = conn.execute('SELECT COUNT(*) as count FROM ali_api_logs WHERE success = 1').fetchone()['count']
        failed = conn.execute('SELECT COUNT(*) as count FROM ali_api_logs WHERE success = 0').fetchone()['count']
        
        # 最近24小时调用
        recent = conn.execute('''
            SELECT COUNT(*) as count FROM ali_api_logs 
            WHERE datetime(created_at) > datetime('now', ?)
        ''', (f'-{hours} hours',)).fetchone()['count']
        
        # 按端点统计
        endpoint_stats = conn.execute('''
            SELECT endpoint, COUNT(*) as count, 
                   AVG(response_time) as avg_time,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
            FROM ali_api_logs 
            GROUP BY endpoint 
            ORDER BY count DESC
        ''').fetchall()
        
        return {
            'total_calls': total,
            'success_calls': success,
            'failed_calls': failed,
            'recent_calls_24h': recent,
            'success_rate': success / total if total > 0 else 0,
            'endpoint_stats': [dict(row) for row in endpoint_stats]
        }

class AliApiUserStats:
    """用户调用统计"""
    
    @staticmethod
    def create_table(conn):
        """创建用户统计表"""
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ali_api_user_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE REFERENCES users(id),
                calls_today INTEGER DEFAULT 0,
                calls_total INTEGER DEFAULT 0,
                last_reset_date TEXT,
                last_call_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ali_user_stats_user ON ali_api_user_stats(user_id)')
    
    @staticmethod
    def increment_user_calls(conn, user_id: int) -> bool:
        """增加用户调用计数，检查是否超限"""
        from config import config
        daily_limit = config['rate_limit']['user_daily_limit']
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 获取或创建用户统计
        row = conn.execute(
            'SELECT * FROM ali_api_user_stats WHERE user_id = ?', 
            (user_id,)
        ).fetchone()
        
        if not row:
            # 新用户
            conn.execute('''
                INSERT INTO ali_api_user_stats (user_id, calls_today, calls_total, last_reset_date, last_call_at)
                VALUES (?, 1, 1, ?, ?)
            ''', (user_id, today, datetime.now().isoformat()))
            return True
        
        # 检查是否需要重置
        if row['last_reset_date'] != today:
            # 重置每日计数
            conn.execute('''
                UPDATE ali_api_user_stats SET
                    calls_today = 1,
                    calls_total = calls_total + 1,
                    last_reset_date = ?,
                    last_call_at = ?,
                    updated_at = ?
                WHERE user_id = ?
            ''', (today, datetime.now().isoformat(), datetime.now().isoformat(), user_id))
            return True
        
        # 检查是否超限
        if row['calls_today'] >= daily_limit:
            return False
        
        # 增加计数
        conn.execute('''
            UPDATE ali_api_user_stats SET
                calls_today = calls_today + 1,
                calls_total = calls_total + 1,
                last_call_at = ?,
                updated_at = ?
            WHERE user_id = ?
        ''', (datetime.now().isoformat(), datetime.now().isoformat(), user_id))
        return True
    
    @staticmethod
    def get_user_stats(conn, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户统计信息"""
        row = conn.execute(
            'SELECT * FROM ali_api_user_stats WHERE user_id = ?', 
            (user_id,)
        ).fetchone()
        if not row:
            return None
        return dict(row)


class AliApiToken:
    """1688 OAuth Token 存储"""
    
    @staticmethod
    def create_table(conn):
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ali_api_tokens (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER DEFAULT 0,
                app_key         TEXT NOT NULL DEFAULT '',
                access_token    TEXT NOT NULL DEFAULT '',
                refresh_token   TEXT NOT NULL DEFAULT '',
                ali_id          TEXT DEFAULT '',
                resource_owner  TEXT DEFAULT '',
                expires_in      INTEGER DEFAULT 0,
                token_type      TEXT DEFAULT 'bearer',
                scope           TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now','localtime')),
                updated_at      TEXT DEFAULT (datetime('now','localtime'))
            )
        ''')
    
    @staticmethod
    def save(conn, token_data: dict, user_id: int = 0):
        now = datetime.now().isoformat()
        conn.execute('DELETE FROM ali_api_tokens WHERE user_id=?', (user_id,))
        conn.execute('''
            INSERT INTO ali_api_tokens 
                (user_id, app_key, access_token, refresh_token, ali_id, 
                 resource_owner, expires_in, token_type, scope, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            user_id,
            token_data.get('app_key', ''),
            token_data.get('access_token', ''),
            token_data.get('refresh_token', ''),
            token_data.get('ali_id', ''),
            token_data.get('resource_owner', ''),
            token_data.get('expires_in', 0),
            token_data.get('token_type', 'bearer'),
            token_data.get('scope', ''),
            now, now
        ))
        conn.commit()
    
    @staticmethod
    def get(conn, user_id: int = 0):
        row = conn.execute(
            'SELECT * FROM ali_api_tokens WHERE user_id=? ORDER BY id DESC LIMIT 1',
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    
    @staticmethod
    def delete(conn, user_id: int = 0):
        conn.execute('DELETE FROM ali_api_tokens WHERE user_id=?', (user_id,))
        conn.commit()


class OAuthState:
    """OAuth state 存储（CSRF 防护）"""
    
    @staticmethod
    def create_table(conn):
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ali_oauth_states (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                state       TEXT UNIQUE NOT NULL,
                redirect_uri TEXT NOT NULL DEFAULT '',
                user_id     INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now', 'localtime')),
                used        INTEGER DEFAULT 0
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_oauth_state ON ali_oauth_states(state)')
    
    @staticmethod
    def save(conn, state: str, redirect_uri: str, user_id: int = 0):
        conn.execute(
            'INSERT INTO ali_oauth_states (state, redirect_uri, user_id) VALUES (?, ?, ?)',
            (state, redirect_uri, user_id)
        )
        conn.commit()
    
    @staticmethod
    def validate_and_consume(conn, state: str, max_age_seconds: int = 600) -> bool:
        """验证 state 并标记为已使用（防止重放攻击）"""
        row = conn.execute(
            'SELECT * FROM ali_oauth_states WHERE state = ? AND used = 0', (state,)
        ).fetchone()
        if not row:
            return False
        # 检查是否过期
        from datetime import datetime, timedelta
        created = datetime.fromisoformat(row['created_at'])
        if datetime.now() - created > timedelta(seconds=max_age_seconds):
            conn.execute('DELETE FROM ali_oauth_states WHERE id = ?', (row['id'],))
            conn.commit()
            return False
        # 标记已使用
        conn.execute('UPDATE ali_oauth_states SET used = 1 WHERE id = ?', (row['id'],))
        conn.commit()
        return True
    
    @staticmethod
    def clean_expired(conn, max_age_seconds: int = 3600):
        """清理过期 state"""
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(seconds=max_age_seconds)).isoformat()
        conn.execute('DELETE FROM ali_oauth_states WHERE created_at < ?', (cutoff,))
        conn.commit()


# ===== 数据库初始化 =====

def init_tables():
    """初始化所有表"""
    with get_db() as conn:
        AliApiItem.create_table(conn)
        AliApiLog.create_table(conn)
        AliApiUserStats.create_table(conn)
        AliApiToken.create_table(conn)
        OAuthState.create_table(conn)
        conn.commit()
        print("[AliApi] 数据表初始化完成")

if __name__ == "__main__":
    # 测试数据库初始化
    init_tables()
    print("AliApi 数据表初始化完成")