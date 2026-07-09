"""商品评价系统插件"""
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from plugin_manager.base import BasePlugin
from plugin_manager.event_bus import EventName, get_event_bus
from .models import get_db, get_main_db, init_db

logger = logging.getLogger(__name__)


class ReviewsPlugin(BasePlugin):
    name = 'reviews'
    version = '1.0.0'
    description = '商品评价系统 — 用户对已购商品打分、写评价、晒图'

    def on_install(self, registry) -> bool:
        """安装时创建插件表"""
        init_db()
        return True

    def on_enable(self, registry) -> bool:
        """订阅事件：支付成功后提示评价"""
        bus = get_event_bus()
        bus.on(EventName.ORDER_PAID, self._on_order_paid)
        return True

    def on_disable(self, registry) -> bool:
        bus = get_event_bus()
        bus.off(EventName.ORDER_PAID, self._on_order_paid)
        return True

    def _on_order_paid(self, **kwargs):
        """支付成功后记录——用户可在订单页写评价"""
        logger.info(f"[Reviews] 订单 {kwargs.get('order_id')} 已支付，可评价")

    def register_routes(self) -> List:
        from flask import Blueprint, jsonify, request
        bp = Blueprint('reviews', __name__, url_prefix='/plugin/reviews')
        _t = self.t  # bind to local var for closure safety

        @bp.route('/api/<int:product_id>', methods=['GET'])
        def get_reviews(product_id):
            """获取商品评价列表"""
            page = request.args.get('page', 1, type=int)
            size = min(request.args.get('size', 20, type=int), 50)
            rating_filter = request.args.get('rating', type=int)
            has_image = request.args.get('has_image', type=int)
            offset = (page - 1) * size

            with get_db() as conn:
                where = ['r.is_active=1', 'r.product_id=?']
                params = [product_id]
                if rating_filter:
                    where.append('r.rating=?')
                    params.append(rating_filter)
                if has_image:
                    where.append("r.images != '[]' AND r.images != ''")

                total = conn.execute(
                    f'SELECT COUNT(*) FROM product_reviews r WHERE {" AND ".join(where)}',
                    params
                ).fetchone()[0]

                rows = conn.execute(
                    f'''SELECT * FROM product_reviews r
                        WHERE {" AND ".join(where)}
                        ORDER BY r.created_at DESC LIMIT ? OFFSET ?''',
                    params + [size, offset]
                ).fetchall()

                # 统计
                stats = conn.execute('''
                    SELECT COUNT(*) as total,
                           AVG(rating) as avg_rating,
                           SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive,
                           SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as neutral,
                           SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as negative,
                           SUM(CASE WHEN images != '[]' AND images != '' THEN 1 ELSE 0 END) as with_images
                    FROM product_reviews WHERE product_id=? AND is_active=1
                ''', (product_id,)).fetchone()

            # 跨库查用户信息
            user_ids = [r['user_id'] for r in rows if r['user_id']]
            user_map = {}
            if user_ids:
                with get_main_db() as main:
                    for uid in set(user_ids):
                        u = main.execute(
                            'SELECT id, username, avatar FROM users WHERE id=?', (uid,)
                        ).fetchone()
                        if u:
                            user_map[uid] = dict(u)

            reviews = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get('images'), str):
                    try:
                        d['images'] = json.loads(d['images'])
                    except:
                        d['images'] = []
                # 填充用户信息
                uinfo = user_map.get(d['user_id'], {})
                d['username'] = uinfo.get('username', '')
                d['avatar'] = uinfo.get('avatar', '')
                d['is_anonymous'] = bool(d['is_anonymous'])
                if d['is_anonymous']:
                    d['username'] = '匿***'
                    d['avatar'] = ''
                reviews.append(d)

            return jsonify({
                'success': True,
                'data': {
                    'reviews': reviews,
                    'total': total,
                    'page': page,
                    'size': size,
                    'stats': dict(stats) if stats else {}
                }
            })

        @bp.route('/api/<int:product_id>/create', methods=['POST'])
        def create_review(product_id):
            """用户提交评价（需已购买）"""
            from services.jwt_service import validate_token
            auth = request.headers.get('Authorization', '')
            payload = validate_token(auth.replace('Bearer ', ''))
            if not payload:
                return jsonify({'success': False, 'error': '请先登录'}), 401
            uid = payload['user_id']
            data = request.get_json() or {}

            rating = data.get('rating', 5)
            content = (data.get('content') or '').strip()
            images = data.get('images', [])
            is_anonymous = 1 if data.get('is_anonymous') else 0
            order_id = (data.get('order_id') or '').strip()

            if rating < 1 or rating > 5:
                return jsonify({'success': False, 'error': '评分需在1-5之间'}), 400
            if not content:
                return jsonify({'success': False, 'error': '请填写评价内容'}), 400

            # 跨库检查是否购买过
            if order_id:
                with get_main_db() as main:
                    purchase = main.execute(
                        'SELECT id FROM order_items WHERE user_id=? AND product_id=? AND order_id=? AND status="paid"',
                        (uid, product_id, order_id)
                    ).fetchone()
                if not purchase:
                    return jsonify({'success': False, 'error': _t('请先购买商品再评价')}), 400

            with get_db() as conn:
                # 检查是否已评价
                existing = conn.execute(
                    'SELECT id FROM product_reviews WHERE user_id=? AND product_id=? AND order_id=?',
                    (uid, product_id, order_id)
                ).fetchone()
                if existing:
                    return jsonify({'success': False, 'error': _t('您已评价过该商品')}), 400

                conn.execute(
                    '''INSERT INTO product_reviews (user_id, product_id, order_id, rating, content,
                       images, is_anonymous, is_verified, created_at)
                       VALUES (?,?,?,?,?,?,?,1,datetime('now','localtime'))''',
                    (uid, product_id, order_id, rating, content,
                     json.dumps(images, ensure_ascii=False), is_anonymous)
                )
                conn.commit()

            return jsonify({'success': True, 'message': _t('评价成功')})

        @bp.route('/api/<int:review_id>', methods=['DELETE'])
        def delete_review(review_id):
            """删除自己的评价"""
            from services.jwt_service import validate_token
            auth = request.headers.get('Authorization', '')
            payload = validate_token(auth.replace('Bearer ', ''))
            if not payload:
                return jsonify({'success': False, 'error': '请先登录'}), 401
            uid = payload['user_id']
            with get_db() as conn:
                row = conn.execute(
                    'SELECT id FROM product_reviews WHERE id=? AND user_id=?',
                    (review_id, uid)
                ).fetchone()
                if not row:
                    return jsonify({'success': False, 'error': '评价不存在'}), 404
                conn.execute("UPDATE product_reviews SET is_active=0 WHERE id=?", (review_id,))
                conn.commit()
            return jsonify({'success': True, 'message': _t('评价删除成功')})

        @bp.route('/api/user/reviews', methods=['GET'])
        def my_reviews():
            """获取我的评价列表"""
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
                    'SELECT COUNT(*) FROM product_reviews WHERE user_id=? AND is_active=1',
                    (uid,)
                ).fetchone()[0]
                rows = conn.execute(
                    '''SELECT * FROM product_reviews r
                        WHERE r.user_id=? AND r.is_active=1
                        ORDER BY r.created_at DESC LIMIT ? OFFSET ?''',
                    (uid, size, offset)
                ).fetchall()

            # 跨库查商品信息
            product_ids = [r['product_id'] for r in rows if r['product_id']]
            product_map = {}
            if product_ids:
                with get_main_db() as main:
                    for pid in set(product_ids):
                        p = main.execute(
                            'SELECT id, title, thumbnail FROM products WHERE id=?', (pid,)
                        ).fetchone()
                        if p:
                            product_map[pid] = dict(p)

            reviews = []
            for r in rows:
                d = dict(r)
                p = product_map.get(d['product_id'], {})
                d['product_title'] = p.get('title', '')
                d['thumbnail'] = p.get('thumbnail', '')
                reviews.append(d)

            return jsonify({
                'success': True,
                'data': {
                    'reviews': reviews,
                    'total': total,
                    'page': page,
                    'size': size,
                }
            })

        # ── 管理端 ──
        @bp.route('/admin/reviews', methods=['GET'])
        def admin_reviews():
            """管理端：评价审核列表"""
            from services.jwt_service import validate_token
            auth = request.headers.get('Authorization', '')
            payload = validate_token(auth.replace('Bearer ', ''))
            if not payload or not payload.get('is_admin'):
                return jsonify({'success': False, 'error': '无权限'}), 403
            page = request.args.get('page', 1, type=int)
            size = request.args.get('size', 20, type=int)
            offset = (page - 1) * size

            with get_db() as conn:
                total = conn.execute('SELECT COUNT(*) FROM product_reviews').fetchone()[0]
                rows = conn.execute(
                    '''SELECT * FROM product_reviews r
                        ORDER BY r.created_at DESC LIMIT ? OFFSET ?''',
                    (size, offset)
                ).fetchall()

            # 跨库查用户+商品信息
            user_ids = [r['user_id'] for r in rows if r['user_id']]
            product_ids = [r['product_id'] for r in rows if r['product_id']]
            user_map = {}
            product_map = {}
            with get_main_db() as main:
                for uid in set(user_ids):
                    u = main.execute('SELECT id, username FROM users WHERE id=?', (uid,)).fetchone()
                    if u:
                        user_map[uid] = dict(u)
                for pid in set(product_ids):
                    p = main.execute('SELECT id, title FROM products WHERE id=?', (pid,)).fetchone()
                    if p:
                        product_map[pid] = dict(p)

            data = []
            for r in rows:
                d = dict(r)
                d['username'] = user_map.get(d['user_id'], {}).get('username', '')
                d['product_title'] = product_map.get(d['product_id'], {}).get('title', '')
                data.append(d)

            return jsonify({
                'success': True,
                'data': {'reviews': data, 'total': total}
            })

        @bp.route('/admin/reviews/<int:rid>/reply', methods=['POST'])
        def reply_review(rid):
            """管理端回复评价"""
            from services.jwt_service import validate_token
            auth = request.headers.get('Authorization', '')
            payload = validate_token(auth.replace('Bearer ', ''))
            if not payload or not payload.get('is_admin'):
                return jsonify({'success': False, 'error': '无权限'}), 403
            reply = (request.get_json() or {}).get('reply', '').strip()
            if not reply:
                return jsonify({'success': False, 'error': '请输入回复内容'}), 400
            with get_db() as conn:
                conn.execute(
                    "UPDATE product_reviews SET reply_content=?, reply_at=datetime('now','localtime') WHERE id=?",
                    (reply, rid)
                )
                conn.commit()
            return jsonify({'success': True, 'message': '回复成功'})

        return [bp]
