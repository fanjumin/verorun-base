"""商品评价系统插件"""
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from plugins.base import BasePlugin
from plugins.hooks import EventName, get_event_bus
from models import get_db

logger = logging.getLogger(__name__)


class ReviewsPlugin(BasePlugin):
    name = 'reviews'
    version = '1.0.0'
    description = '商品评价系统 — 用户对已购商品打分、写评价、晒图'

    def on_install(self, registry) -> bool:
        """安装时创建表"""
        with get_db() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS product_reviews (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         INTEGER NOT NULL,
                    product_id      INTEGER NOT NULL,
                    order_id        TEXT DEFAULT '',
                    rating          INTEGER NOT NULL DEFAULT 5 CHECK(rating >= 1 AND rating <= 5),
                    content         TEXT DEFAULT '',
                    images          TEXT DEFAULT '[]',
                    spec_info       TEXT DEFAULT '',
                    is_anonymous    INTEGER DEFAULT 0,
                    is_verified     INTEGER DEFAULT 0,
                    reply_content   TEXT DEFAULT '',
                    reply_at        TEXT,
                    is_active       INTEGER DEFAULT 1,
                    created_at      TEXT DEFAULT (datetime('now','localtime')),
                    updated_at      TEXT DEFAULT (datetime('now','localtime')),
                    UNIQUE(user_id, product_id, order_id)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_reviews_product ON product_reviews(product_id, is_active)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_reviews_user ON product_reviews(user_id)')
            conn.commit()
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
                    f'''SELECT r.*, u.username, u.avatar
                        FROM product_reviews r
                        LEFT JOIN users u ON r.user_id=u.id
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

            reviews = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get('images'), str):
                    try:
                        d['images'] = json.loads(d['images'])
                    except:
                        d['images'] = []
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

            with get_db() as conn:
                # 检查是否已评价
                existing = conn.execute(
                    'SELECT id FROM product_reviews WHERE user_id=? AND product_id=? AND order_id=?',
                    (uid, product_id, order_id)
                ).fetchone()
                if existing:
                    return jsonify({'success': False, 'error': self.t('您已评价过该商品')}), 400

                # 检查是否购买过（允许仅购买未评价的情况）
                if order_id:
                    purchase = conn.execute(
                        'SELECT id FROM order_items WHERE user_id=? AND product_id=? AND order_id=? AND status="paid"',
                        (uid, product_id, order_id)
                    ).fetchone()
                    if not purchase:
                        return jsonify({'success': False, 'error': self.t('请先购买商品再评价')}), 400

                conn.execute(
                    '''INSERT INTO product_reviews (user_id, product_id, order_id, rating, content,
                       images, is_anonymous, is_verified, created_at)
                       VALUES (?,?,?,?,?,?,?,1,datetime('now','localtime'))''',
                    (uid, product_id, order_id, rating, content,
                     json.dumps(images, ensure_ascii=False), is_anonymous)
                )
                conn.commit()

            return jsonify({'success': True, 'message': self.t('评价成功')})

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
            return jsonify({'success': True, 'message': self.t('评价删除成功')})

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
                    '''SELECT r.*, p.title as product_title, p.thumbnail
                        FROM product_reviews r
                        LEFT JOIN products p ON r.product_id=p.id
                        WHERE r.user_id=? AND r.is_active=1
                        ORDER BY r.created_at DESC LIMIT ? OFFSET ?''',
                    (uid, size, offset)
                ).fetchall()
            return jsonify({
                'success': True,
                'data': {
                    'reviews': [dict(r) for r in rows],
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
                    '''SELECT r.*, u.username, p.title as product_title
                        FROM product_reviews r
                        LEFT JOIN users u ON r.user_id=u.id
                        LEFT JOIN products p ON r.product_id=p.id
                        ORDER BY r.created_at DESC LIMIT ? OFFSET ?''',
                    (size, offset)
                ).fetchall()
            return jsonify({
                'success': True,
                'data': {'reviews': [dict(r) for r in rows], 'total': total}
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
