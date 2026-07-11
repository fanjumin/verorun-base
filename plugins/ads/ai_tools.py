#!/usr/bin/env python3
"""Ad Management Plugin — AI 可调用工具封装 (v0.2.0)

为 Agent Matrix / chat_tool 提供广告管理能力的内部封装。
所有函数返回 dict {'success': bool, 'data': any, 'error': str|None}，
便于上层统一处理。
"""
import json, os, sys

# 确保能找到项目根目录下的模块
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _get_db():
    """获取 ads 插件数据库连接"""
    from plugins.ads.models import get_ads_db
    return get_ads_db()


def list_ads(site_key=None, position=None, active_only=False):
    """列出广告"""
    try:
        conn = _get_db()
        where = []
        params = []
        if site_key:
            where.append('site_key=?')
            params.append(site_key)
        if position:
            where.append('position=?')
            params.append(position)
        if active_only:
            where.append('is_active=1')
        where_sql = f"WHERE {' AND '.join(where)}" if where else ''
        rows = conn.execute(
            f'SELECT * FROM ad_placements {where_sql} ORDER BY sort_order, id',
            params
        ).fetchall()
        data = []
        for r in rows:
            d = dict(r)
            try:
                d['targeting_rules'] = json.loads(d.get('targeting_rules') or '{}')
            except (json.JSONDecodeError, TypeError):
                d['targeting_rules'] = {}
            data.append(d)
        return {'success': True, 'data': data}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_ad(ad_id):
    """获取单个广告详情"""
    try:
        conn = _get_db()
        row = conn.execute('SELECT * FROM ad_placements WHERE id=?', (ad_id,)).fetchone()
        if not row:
            return {'success': False, 'error': '广告不存在'}
        d = dict(row)
        try:
            d['targeting_rules'] = json.loads(d.get('targeting_rules') or '{}')
        except (json.JSONDecodeError, TypeError):
            d['targeting_rules'] = {}
        return {'success': True, 'data': d}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def create_ad(data):
    """创建广告"""
    try:
        # 校验必填
        name = (data.get('name') or '').strip()
        if not name:
            return {'success': False, 'error': '广告名称不能为空'}

        targeting = data.get('targeting_rules') or {}
        if isinstance(targeting, str):
            try:
                targeting = json.loads(targeting)
            except (json.JSONDecodeError, TypeError):
                targeting = {}

        from plugins.ads.models import get_ads_db
        conn = get_ads_db()
        cur = conn.execute('''INSERT INTO ad_placements
            (name, site_key, zone_id, position, page, ad_type, image_url, link_url, ad_code,
             width, height, targeting_rules, schedule_start, schedule_end, weight, freq_cap,
             click_tag, utm_source, is_active, sort_order)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (name,
             data.get('site_key', 'default'),
             data.get('zone_id', 0),
             data.get('position', 'sidebar'),
             data.get('page', '*'),
             data.get('ad_type', 'image'),
             data.get('image_url', ''),
             data.get('link_url', ''),
             data.get('ad_code', ''),
             data.get('width', 320),
             data.get('height', 0),
             json.dumps(targeting, ensure_ascii=False),
             data.get('schedule_start', ''),
             data.get('schedule_end', ''),
             data.get('weight', 1),
             data.get('freq_cap', 0),
             data.get('click_tag', ''),
             data.get('utm_source', ''),
             data.get('is_active', 1),
             data.get('sort_order', 0)))
        conn.commit()
        return {'success': True, 'data': {'id': cur.lastrowid}}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def update_ad(ad_id, data):
    """更新广告"""
    try:
        from plugins.ads.models import get_ads_db
        conn = get_ads_db()
        existing = conn.execute('SELECT id FROM ad_placements WHERE id=?', (ad_id,)).fetchone()
        if not existing:
            return {'success': False, 'error': '广告不存在'}

        # 构建动态更新字段
        fields = []
        params = []
        mapping = {
            'name': 'name',
            'site_key': 'site_key',
            'zone_id': 'zone_id',
            'position': 'position',
            'page': 'page',
            'ad_type': 'ad_type',
            'image_url': 'image_url',
            'link_url': 'link_url',
            'ad_code': 'ad_code',
            'width': 'width',
            'height': 'height',
            'schedule_start': 'schedule_start',
            'schedule_end': 'schedule_end',
            'weight': 'weight',
            'freq_cap': 'freq_cap',
            'click_tag': 'click_tag',
            'utm_source': 'utm_source',
            'is_active': 'is_active',
            'sort_order': 'sort_order',
        }
        for key, col in mapping.items():
            if key in data:
                fields.append(f'{col}=?')
                params.append(data[key])

        if 'targeting_rules' in data:
            targeting = data['targeting_rules']
            if isinstance(targeting, dict):
                targeting = json.dumps(targeting, ensure_ascii=False)
            fields.append('targeting_rules=?')
            params.append(targeting)

        if not fields:
            return {'success': False, 'error': '没有要更新的字段'}

        fields.append('updated_at=datetime("now")')
        params.append(ad_id)
        conn.execute(f"UPDATE ad_placements SET {', '.join(fields)} WHERE id=?", params)
        conn.commit()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def delete_ad(ad_id):
    """删除广告"""
    try:
        from plugins.ads.models import get_ads_db
        conn = get_ads_db()
        conn.execute('DELETE FROM ad_placements WHERE id=?', (ad_id,))
        conn.commit()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_stats(ad_id=None, days=7):
    """获取广告统计"""
    try:
        from plugins.ads.models import get_ad_stats
        return {'success': True, 'data': get_ad_stats(ad_id=ad_id, days=days)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def list_zones(site_key=None, active_only=False):
    """列出广告区域"""
    try:
        from plugins.ads.models import list_zones as _list_zones
        return {'success': True, 'data': _list_zones(site_key=site_key or 'default', active_only=active_only)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def analyze_ads(days=7):
    """分析广告效果并返回文字洞察"""
    try:
        from plugins.ads.models import get_ad_stats
        stats = get_ad_stats(ad_id=None, days=days)
        ads_res = list_ads()
        ads = ads_res.get('data', []) if ads_res.get('success') else []

        total = stats.get('total', {})
        daily = stats.get('daily', [])

        lines = [
            f"=== 广告效果分析（最近 {days} 天）===",
            f"总展示量: {total.get('impressions', 0)}",
            f"总点击量: {total.get('clicks', 0)}",
            f"整体 CTR: {total.get('ctr', 0)}%",
            "",
            "按广告效果排序:"
        ]

        # 合并广告与累计数据（用当前累计 impressions/clicks）
        ranked = sorted(ads, key=lambda x: (x.get('clicks', 0), x.get('impressions', 0)), reverse=True)
        for i, a in enumerate(ranked[:10], 1):
            imp = a.get('impressions', 0)
            clk = a.get('clicks', 0)
            ctr = round(clk / imp * 100, 2) if imp else 0.0
            status = '运行中' if a.get('is_active') else '已暂停'
            lines.append(f"{i}. [{status}] {a.get('name')} | {a.get('position')} | 展示 {imp} | 点击 {clk} | CTR {ctr}%")

        # 找出异常：高展示低点击
        low_ctr = [a for a in ads if a.get('impressions', 0) > 100 and (a.get('clicks', 0) / a.get('impressions', 0)) < 0.005]
        if low_ctr:
            lines.append("")
            lines.append("需要优化的广告（展示>100 且 CTR<0.5%）:")
            for a in low_ctr:
                lines.append(f"- {a.get('name')} ({a.get('position')}): 建议更换素材或调整定向")

        # 趋势
        if daily:
            lines.append("")
            lines.append("最近趋势:")
            for r in daily[-7:]:
                lines.append(f"- {r['stat_date']}: 展示 {r.get('impressions', 0)}, 点击 {r.get('clicks', 0)}")

        return {'success': True, 'data': '\n'.join(lines)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def generate_render_snippet(position='sidebar', page='*', site_key='default', zone_id=None):
    """生成广告位渲染代码片段"""
    try:
        zone_attr = f' data-ad-zone-id="{zone_id}"' if zone_id is not None else ''
        snippet = (
            f'{{% from "plugins/ads/templates/render_ads.html" import render_ads %}}\n'
            f'{{{{ render_ads(position="{position}", page="{page}", site_key="{site_key}"{zone_attr}) }}}}'
        )
        return {'success': True, 'data': snippet}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def toggle_ad(ad_id, is_active):
    """启用/禁用广告"""
    return update_ad(ad_id, {'is_active': 1 if is_active else 0})
