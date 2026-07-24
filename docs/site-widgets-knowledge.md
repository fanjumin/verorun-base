# VeroRun Site Widgets — RAG Knowledge Base

> Knowledge base for AI-powered site building and mini-program generation.  
> Embed this document into the RAG vector store so the system LLM can retrieve widget endpoints and parameters.

---

## 1. Widget System Overview

VeroRun's site builder supports 18 pluggable widgets (W01-W18) organized into 5 categories:

- **Content**: W01 Latest Articles, W02 Hot Articles, W03 Article Categories, W14 Content Feed
- **Commerce**: W04 Product List, W05 Hot/Featured Products, W06 Product Detail Card, W10 Coupon Entry, W11 Wishlist Button
- **Interaction**: W07 Product Reviews, W09 Chatbot
- **Marketing**: W08 Ad Placement, W15 Social Share
- **Infrastructure**: W12 Search Box, W13 Knowledge Base Search, W16 Navigation Bar, W17 Footer, W18 Contact Info

Each widget has a `widget_type` identifier (e.g. `latest_articles`, `hot_products`) used in the `data-widget` HTML attribute and `VeroWidgets.registry`.

---

## 2. All API Endpoints by Widget

### W01 — Latest Articles (latest_articles)
- **Endpoint**: `GET /api/v1/insights/latest`
- **Auth**: No
- **Params**: count (int, default 3), category (string), show_cover (bool, default true), show_excerpt (bool, default true), layout (enum: list/grid/card, default list), title (string)
- **Response**: `{"posts": [...], "count": N}`

### W02 — Hot Articles (hot_articles)
- **Endpoint**: `GET /docs/<cat_slug>/` (frontend sorts by views/published_at)
- **Auth**: No
- **Params**: count (int, default 5), category (string), sort_by (enum: published_at/views/manual), layout (enum: list/ranked), show_cover (bool, default false), title (string)

### W03 — Article Categories (article_categories)
- **Endpoint**: `GET /api/v1/categories`
- **Auth**: No
- **Params**: layout (enum: list/grid/tag, default list), show_count (bool, default true), parent_only (bool, default true), title (string)
- **Response**: `{"categories": [...], "count": N}`

### W04 — Product List (product_list)
- **Endpoint**: `GET /shop/api/products?category=xxx&category_id=xxx&search=xxx`
- **Auth**: No
- **Params**: count (int, default 8), category (string), category_id (int), layout (enum: grid/list/card), columns (int, default 4), show_price (bool, default true), show_original_price (bool, default false), sort_by (enum: sort_order/sales_count/price_asc/price_desc), title (string)
- **Response**: `{"products": [{id, title, subtitle, product_type, category, price, original_price, sales_count, thumbnail, is_active}]}`

### W05 — Hot/Featured Products (hot_products)
- **Endpoint**: `GET /shop/api/products` (frontend sorts by sales_count DESC)
- **Auth**: No
- **Params**: count (int, default 4), category (string), sort_by (enum: sales_count/manual), layout (enum: grid/card/horizontal), columns (int, default 4), show_badge (bool, default true), show_price (bool, default true), title (string)

### W06 — Product Detail Card (product_detail)
- **Endpoint**: `GET /shop/api/products/<pid>`
- **Auth**: No
- **Params**: product_id (int, required), show_sku (bool, default false), show_features (bool, default true), show_cta (bool, default true), cta_text (string, default "Buy Now")

### W07 — Product Reviews (product_reviews)
- **Endpoint**: `GET /plugin/reviews/api/<product_id>?page=1&size=10&rating=5&has_image=true`
- **Auth**: No
- **Params**: product_id (int, required), count (int, default 10), rating (int, 1-5), has_image (bool, default false), show_stats (bool, default true), layout (enum: list/card), sort_by (enum: created_at/rating/hot), title (string)
- **Response**: `{"reviews": [{id, user_id, product_id, rating, content, images, is_verified, reply_content, created_at}], "stats": {total, avg_rating, positive, neutral, negative, with_images}}`

### W08 — Ad Placement (ad_placement)
- **Endpoint**: `GET /admin/ads/api/v1/ads?page=*&position=sidebar&site_key=default&zone_id=0`
- **Tracking**: `POST /admin/ads/api/v1/stats/impression`, `POST /admin/ads/api/v1/stats/click`
- **Auth**: No
- **Params**: position (string, required), page (string, default *), width (int, default 320), height (int, default 0=auto), ad_type (enum: image/ad_code), zone_id (int, default 0), count (int, default 1), title (string)
- **Position identifiers**: home_banner, home_mid, sidebar_top, sidebar_bottom, post_top, post_mid, post_bottom, product_sidebar, global_popup, mobile_bottom

### W09 — Chatbot (chatbot)
- **Endpoint**: `POST /api/v1/chat` (SSE streaming)
- **Auth**: No
- **Params**: enabled (bool, default true), title (string, default "AI Assistant"), subtitle (string), welcome_message (string), float_button_text (string), agent_id (string), source (enum: website/douyin/tiktok), max_history (int, default 20), position (enum: bottom-right/bottom-left), theme_color (string, default #4F46E5)
- **Rendering**: `<div id="chatbot-widget" data-title="..." ...></div><script src="/static/chatbot/widget.js"></script>`

### W10 — Coupon Entry (coupon_entry)
- **Endpoint**: `POST /plugin/coupons/validate` (auth required)
- **Recommend API**: `POST /plugin/coupons/ai/recommend` (auth required)
- **Params**: scene (enum: shop/subscription/promo/new_user, default shop), show_available (bool, default true), show_input (bool, default true), title (string)

### W11 — Wishlist Button (wishlist_button)
- **Endpoints** (all auth required):
  - `GET /plugin/wishlist/api/list` — get user wishlist
  - `POST /plugin/wishlist/api/toggle` — add/remove item
  - `POST /plugin/wishlist/api/check` — batch check items
  - `GET /plugin/wishlist/api/count` — get count
- **Params**: product_id (int, required), button_style (enum: icon/text/both), button_text (string, default "Save"), show_count (bool, default false), show_tooltip (bool, default true)

### W12 — Search Box (search_box)
- **Product search**: `GET /shop/api/products?search=xxx`
- **Knowledge base search**: `POST /api/v1/rag/search`
- **Semantic search**: `GET /api/v1/search?q=xxx` (requires Nginx proxy to cognition-service:8091)
- **Auth**: No (all endpoints)
- **Params**: scope (enum: all/products/articles/knowledge), placeholder (string, default "Search..."), position (enum: navbar/inline/hero), show_suggestions (bool, default true), min_chars (int, default 2)

### W13 — Knowledge Base Search (knowledge_search)
- **Endpoint**: `POST /api/v1/rag/search` (hybrid semantic retrieval)
- **Auth**: No
- **Params**: top_k (int, default 5), category (string), placeholder (string), show_results_inline (bool, default true), title (string)

### W14 — Content Feed (content_feed)
- **Endpoint**: `GET /admin/content-factory/api/v1/skills?agent=hermes`
- **Auth**: No
- **Params**: count (int, default 10), source (string), platform (string), auto_refresh (bool, default false), refresh_interval (int, default 300), title (string)

### W15 — Social Share (social_share)
- **No backend API** — pure frontend component
- Opens platform share URLs in new windows (e.g. `https://service.weibo.com/share/share.php?url=...`)
- **Params**: platforms (array, default ["wechat","weibo"]), layout (enum: inline/floating), show_count (bool, default false), title (string)

### W16 — Navigation Bar (navigation)
- **Data source**: `design_tokens.draft_json.navigation`
- **Params**: items (array, required), style (enum: default/sticky/transparent), logo_position (enum: left/center), show_search (bool), show_cta (bool), cta_text (string), cta_url (string), mobile_style (enum: hamburger/bottom_tab)

### W17 — Footer (footer)
- **Data source**: `design_tokens.draft_json.footer`
- **Params**: groups (array), copyright (string, default "© {year} {site_name}"), show_social (bool, default true), social_links (array), show_back_to_top (bool, default true), style (enum: default/minimal/dark)

### W18 — Contact Info (contact_info)
- **Static HTML template** — no API
- **Params**: show_form (bool, default false), show_email (bool, default true), show_phone (bool, default false), show_address (bool, default false), show_wechat (bool, default false), show_map (bool, default false), title (string)

---

## 3. Natural Language → Widget Mapping

When a user says one of the following, match the corresponding widget with the listed default parameters:

| User Phrase | Widget | Default Config |
|---|---|---|
| "add an ad", "place a banner" | W08 Ad Placement | position=home_banner, width=728 |
| "add customer service", "AI chat", "chatbot" | W09 Chatbot | position=bottom-right |
| "show latest articles", "news feed", "blog posts" | W01 Latest Articles | count=3, layout=card |
| "hot picks", "reading rankings", "popular posts" | W02 Hot Articles | count=5, layout=ranked |
| "best sellers", "featured products", "hot products" | W05 Hot Products | count=4, layout=grid |
| "product list", "all products", "shop" | W04 Product List | count=8, layout=grid |
| "user reviews", "testimonials", "ratings" | W07 Product Reviews | count=10, show_stats=true |
| "search box", "search function", "search bar" | W12 Search Box | scope=all, position=navbar |
| "coupons", "discount codes", "promo" | W10 Coupon Entry | scene=shop |
| "favorites", "wishlist", "save for later" | W11 Wishlist Button | button_style=icon |
| "knowledge base", "doc search", "help center" | W13 Knowledge Search | top_k=5 |
| "industry news", "news aggregation", "RSS feed" | W14 Content Feed | count=10 |
| "categories", "article sections", "taxonomy" | W03 Article Categories | layout=list |
| "share", "social media", "forward" | W15 Social Share | platforms=["wechat","weibo"] |

---

## 4. Widget Insertion Positions

When the AI generates page layout JSON, widget position is specified using one of these identifiers:

- `after_hero` — after the hero section
- `after_features` — after feature highlights
- `before_footer` — before the footer
- `sidebar` — in the sidebar
- `inline_section` — as a standalone section
- `modal` — as a modal popup
- `floating` — as a floating button

---

## 5. Complete Endpoint Quick Reference

| Widget ID | Endpoint | Method | Auth Required |
|---|---|---|---|
| W01 | `/api/v1/insights/latest` | GET | No |
| W02 | `/docs/<cat_slug>/` (frontend sort) | GET | No |
| W03 | `/api/v1/categories` | GET | No |
| W04 | `/shop/api/products` | GET | No |
| W05 | `/shop/api/products` (sorted by sales_count) | GET | No |
| W06 | `/shop/api/products/<pid>` | GET | No |
| W07 | `/plugin/reviews/api/<product_id>` | GET | No |
| W08 | `/admin/ads/api/v1/ads` | GET | No |
| W08 tracking | `/admin/ads/api/v1/stats/impression` | POST | No |
| W08 tracking | `/admin/ads/api/v1/stats/click` | POST | No |
| W09 | `/api/v1/chat` (SSE streaming) | POST | No |
| W10 | `/plugin/coupons/validate` | POST | Yes |
| W10 recommend | `/plugin/coupons/ai/recommend` | POST | Yes |
| W11 | `/plugin/wishlist/api/list` | GET | Yes |
| W11 | `/plugin/wishlist/api/toggle` | POST | Yes |
| W11 | `/plugin/wishlist/api/check` | POST | Yes |
| W11 | `/plugin/wishlist/api/count` | GET | Yes |
| W12 product | `/shop/api/products?search=` | GET | No |
| W12 semantic | `/api/v1/search?q=` (cognition-service:8091 proxy) | GET | No |
| W13 | `/api/v1/rag/search` | POST | No |
| W14 | `/admin/content-factory/api/v1/skills` | GET | No |
| W15 | Pure frontend JS (no API) | — | No |

---

## 6. Widget Output Format for AI Generation

When the AI generates page content, widgets are included in the JSON response as:

```json
{
  "widgets": [
    {
      "widget_id": "W01",
      "widget_type": "latest_articles",
      "count": 3,
      "layout": "card",
      "position": "after_features"
    }
  ]
}
```

The frontend uses `data-widget="<widget_type>"` attributes and `VeroWidgets.init('<widget_type>')` to render each widget. The `VeroWidgets.registry` maps each `widget_type` to the correct API endpoint and HTTP method.
