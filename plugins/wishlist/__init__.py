"""收藏/心愿单插件"""
import json
import logging
from typing import List

from plugin_manager.base import BasePlugin
from .models import get_db, get_main_db, init_db

logger = logging.getLogger(__name__)


class WishlistPlugin(BasePlugin):
    name = 'wishlist'
    version = '1.0.0'
    description = '收藏/心愿单 — 用户收藏商品、管理心愿清单'

    def on_install(self, registry) -> bool:
        """安装时创建插件表"""
        init_db()
        return True

    def register_routes(self) -> List:
        from flask import Blueprint, jsonify, request
        bp = Blueprint('wishlist', __name__, url_prefix='/plugin/wishlist')
        _t = self.t  # bind to local var for closure safety

        @bp.route('/api/list', methods=['GET'])
        def get_wishlist():
            """获取我的收藏列表"""
            from services.jwt_service import validate_token
            auth = request.headers.get('Authorization', '')
            payload = validate_token(auth.replace('Bearer ', ''))
            if not payload:
                return jsonify({'success': False, 'error': _t('请先登录')}), 401
            uid = payload['user_id']

            page = request.args.get('page', 1, type=int)
            size = min(request.args.get('size', 20, type=int), 50)
            offset = (page - 1) * size

            with get_db() as conn:
                total = conn.execute(
                    'SELECT COUNT(*) FROM wishlist WHERE user_id=?', (uid,)
                ).fetchone()[0]
                rows = conn.execute(
                    '''SELECT * FROM wishlist WHERE user_id=?
                       ORDER BY created_at DESC LIMIT ? OFFSET ?''',
                    (uid, size, offset)
                ).fetchall()

            # 跨库查商品信息
            product_ids = [r['product_id'] for r in rows if r['product_id']]
            product_map = {}
            if product_ids:
                with get_main_db() as main:
                    for pid in set(product_ids):
                        p = main.execute(
                            '''SELECT id, title, price, original_price, thumbnail,
                                      stock, is_active, sales_count FROM products WHERE id=?''',
                            (pid,)
                        ).fetchone()
                        if p:
                            product_map[pid] = dict(p)

            items = []
            for r in rows:
                d = dict(r)
                p = product_map.get(d['product_id'], {})
                d['title'] = p.get('title', '')
                d['price'] = p.get('price', 0)
                d['original_price'] = p.get('original_price', 0)
                d['thumbnail'] = p.get('thumbnail', '')
                d['stock'] = p.get('stock', 0)
                d['is_active'] = p.get('is_active', 0)
                d['sales_count'] = p.get('sales_count', 0)
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
                return jsonify({'success': False, 'error': _t('请先登录')}), 401
            uid = payload['user_id']
            data = request.get_json() or {}
            pid = data.get('product_id')
            if not pid:
                return jsonify({'success': False, 'error': _t('缺少商品ID')}), 400

            with get_db() as conn:
                existing = conn.execute(
                    'SELECT id FROM wishlist WHERE user_id=? AND product_id=?', (uid, pid)
                ).fetchone()
                if existing:
                    conn.execute('DELETE FROM wishlist WHERE id=?', (existing['id'],))
                    conn.commit()
                    return jsonify({'success': True, 'favorited': False,
                                    'message': _t('已取消收藏')})
                else:
                    conn.execute(
                        'INSERT INTO wishlist (user_id, product_id) VALUES (?,?)',
                        (uid, pid)
                    )
                    conn.commit()
                    return jsonify({'success': True, 'favorited': True,
                                    'message': _t('收藏成功')})

        @bp.route('/api/check', methods=['POST'])
        def check_wishlist():
            """批量检查商品是否已收藏"""
            from services.jwt_service import validate_token
            auth = request.headers.get('Authorization', '')
            payload = validate_token(auth.replace('Bearer ', ''))
            if not payload:
                return jsonify({'success': False, 'error': _t('请先登录')}), 401
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
                return jsonify({'success': False, 'error': _t('请先登录')}), 401
            uid = payload['user_id']
            with get_db() as conn:
                count = conn.execute(
                    'SELECT COUNT(*) FROM wishlist WHERE user_id=%s', (uid,)
                ).fetchone()[0]
            return jsonify({'success': True, 'data': {'count': count}})

        return [bp]
