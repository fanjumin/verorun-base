"""收藏/心愿单插件"""
import json
import logging
from typing import List

from plugins.base import BasePlugin
from models import get_db

logger = logging.getLogger(__name__)


class WishlistPlugin(BasePlugin):
    name = 'wishlist'
    version = '1.0.0'
    description = '收藏/心愿单 — 用户收藏商品、管理心愿清单'

    def on_install(self, registry) -> bool:
        """安装时创建表"""
        with get_db() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS wishlist (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    product_id  INTEGER NOT NULL,
                    created_at  TEXT DEFAULT (datetime('now','localtime')),
                    UNIQUE(user_id, product_id)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_wishlist_user ON wishlist(user_id)')
            conn.commit()
        return True

    def register_routes(self) -> List:
        from flask import Blueprint, jsonify, request
        bp = Blueprint('wishlist', __name__, url_prefix='/plugin/wishlist')

        @bp.route('/api/list', methods=['GET'])
        def get_wishlist():
            """获取我的收藏列表"""
            from services.jwt_service import validate_token
            auth = request.headers.get('Authorization', '')
            payload = validate_token(auth.replace('Bearer ', ''))
            if not payload:
                return jsonify({'success': False, 'error': '请先登录'}), 401
            uid = payload['user_id']

            page = request.args.get('page', 1, type=int)
            size = min(request.args.get('size', 20, type=int), 50)
            offset = (page - 1) * size

            with get_db() as conn:
                total = conn.execute(
                    'SELECT COUNT(*) FROM wishlist WHERE user_id=?', (uid,)
                ).fetchone()[0]
                rows = conn.execute(
                    '''SELECT w.*, p.title, p.price, p.original_price, p.thumbnail,
                              p.stock, p.is_active, p.sales_count
                       FROM wishlist w
                       JOIN products p ON w.product_id=p.id
                       WHERE w.user_id=?
                       ORDER BY w.created_at DESC LIMIT ? OFFSET ?''',
                    (uid, size, offset)
                ).fetchall()

            items = []
            for r in rows:
                d = dict(r)
                items.append(d)

            return jsonify({
                'success': True,
                'data': {'items': items, 'total': total, 'page': page, 'size': size}
            })

        @bp.route('/api/toggle', methods=['POST'])
        def toggle_wishlist():
            """切换收藏/取消收藏"""
            from services.jwt_service import validate_token
            auth = request.headers.get('Authorization', '')
            payload = validate_token(auth.replace('Bearer ', ''))
            if not payload:
                return jsonify({'success': False, 'error': '请先登录'}), 401
            uid = payload['user_id']
            data = request.get_json() or {}
            pid = data.get('product_id')
            if not pid:
                return jsonify({'success': False, 'error': '缺少商品ID'}), 400

            with get_db() as conn:
                existing = conn.execute(
                    'SELECT id FROM wishlist WHERE user_id=? AND product_id=?', (uid, pid)
                ).fetchone()
                if existing:
                    conn.execute('DELETE FROM wishlist WHERE id=?', (existing['id'],))
                    conn.commit()
                    return jsonify({'success': True, 'favorited': False,
                                    'message': self.t('已取消收藏')})
                else:
                    conn.execute(
                        'INSERT INTO wishlist (user_id, product_id) VALUES (?,?)',
                        (uid, pid)
                    )
                    conn.commit()
                    return jsonify({'success': True, 'favorited': True,
                                    'message': self.t('收藏成功')})

        @bp.route('/api/check', methods=['POST'])
        def check_wishlist():
            """批量检查商品是否已收藏"""
            from services.jwt_service import validate_token
            auth = request.headers.get('Authorization', '')
            payload = validate_token(auth.replace('Bearer ', ''))
            if not payload:
                return jsonify({'success': False, 'error': '请先登录'}), 401
            uid = payload['user_id']
            data = request.get_json() or {}
            product_ids = data.get('product_ids', [])
            if not product_ids:
                return jsonify({'success': True, 'data': {}})

            with get_db() as conn:
                placeholders = ','.join(['?'] * len(product_ids))
                rows = conn.execute(
                    f'SELECT product_id FROM wishlist WHERE user_id=? AND product_id IN ({placeholders})',
                    [uid] + product_ids
                ).fetchall()
            favorited = {str(r['product_id']): True for r in rows}
            return jsonify({'success': True, 'data': favorited})

        @bp.route('/api/count', methods=['GET'])
        def wishlist_count():
            """获取收藏数量"""
            from services.jwt_service import validate_token
            auth = request.headers.get('Authorization', '')
            payload = validate_token(auth.replace('Bearer ', ''))
            if not payload:
                return jsonify({'success': False, 'error': '请先登录'}), 401
            uid = payload['user_id']
            with get_db() as conn:
                count = conn.execute(
                    'SELECT COUNT(*) FROM wishlist WHERE user_id=?', (uid,)
                ).fetchone()[0]
            return jsonify({'success': True, 'data': {'count': count}})

        return [bp]
