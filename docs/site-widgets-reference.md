# Site Widgets Reference — Pluggable Component Parameter Catalog

> Version: v1.1 | Updated: 2026-07-22  
> Purpose: Pluggable component reference for AI site building & mini-program generation. All prompts extract parameters from this document.  
> Related: `site_builder/prompts/*.yml`, `site_builder/mini_app/generators/*.py`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Widget Category Overview](#2-widget-category-overview)
3. [Content Widgets](#3-content-widgets)
4. [Commerce Widgets](#4-commerce-widgets)
5. [Interaction Widgets](#5-interaction-widgets)
6. [Marketing Widgets](#6-marketing-widgets)
7. [Infrastructure Widgets](#7-infrastructure-widgets)
8. [AI Prompt Integration Specification](#8-ai-prompt-integration-specification)
9. [Frontend Rendering Templates](#9-frontend-rendering-templates)

---

## 1. Overview

### 1.1 What is a Widget

A Widget is a **functional component** that can be inserted into website/mini-program pages. Each widget has independent API endpoints, rendering methods, and parameter configurations. During AI site building, users describe requirements in natural language, and the AI matches corresponding widgets from this document and extracts parameters.

### 1.2 Usage Flow

```
User: "Add a hot-selling products section to the homepage, show 4 products, with an ad banner"
         │
         ▼
AI Parsing: Matches → W05 (hot_products) + W08 (ad_placement)
         → Extracts params: count=4, position=home_top, ad_position=home_banner
         → Generates HTML placeholders + API call code
```

### 1.3 Widget Inventory

| ID | Widget | Category | Public API | Web Embed | Mini-App Embed |
|------|------|------|:---:|:---:|:---:|
| W01 | Latest Articles | Content | Yes | Yes | Yes |
| W02 | Hot Articles | Content | Yes | Yes | Yes |
| W03 | Article Categories | Content | Yes | Yes | Yes |
| W04 | Product List | Commerce | Yes | Yes | Yes |
| W05 | Hot/Featured Products | Commerce | Yes | Yes | Yes |
| W06 | Product Detail Card | Commerce | Yes | Yes | Yes |
| W07 | Product Reviews | Interaction | Yes | Yes | Yes |
| W08 | Ad Placement | Marketing | Yes | Yes | Partial |
| W09 | Chatbot | Interaction | Yes | Yes | Yes |
| W10 | Coupon Entry | Commerce | Auth Required | Yes | Yes |
| W11 | Wishlist Button | Commerce | Auth Required | Yes | Yes |
| W12 | Search Box | Infrastructure | Yes | Yes | Yes |
| W13 | Knowledge Base Search | Infrastructure | Yes | Yes | Yes |
| W14 | Content Feed | Content | Yes | Yes | Yes |
| W15 | Social Share | Marketing | No | Yes | No |
| W16 | Navigation Bar | Infrastructure | N/A | Yes | Yes |
| W17 | Footer | Infrastructure | N/A | Yes | Yes |
| W18 | Contact Info | Infrastructure | N/A | Yes | Yes |

---

## 2. Widget Category Overview

```
┌─────────────────────────────────────────────────────────┐
│                Pluggable Widget System                    │
├──────────────┬──────────────┬──────────────┬────────────┤
│   Content    │   Commerce   │ Interaction  │  Marketing  │
├──────────────┼──────────────┼──────────────┼────────────┤
│ Latest Posts │ Product List │ Chatbot      │ Ad Placement│
│ Hot Posts    │ Hot Products │ Reviews      │ Social Share│
│ Categories   │ Product Card │ Search Box   │             │
│ Content Feed │ Coupons      │ KB Search    │             │
│              │ Wishlist     │              │             │
├──────────────┴──────────────┴──────────────┴────────────┤
│                   Infrastructure                         │
│       Navigation  │  Footer  │  Contact  │  Copyright    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Content Widgets

### W01 — Latest Articles (latest_articles)

**API Endpoint**: `GET /api/v1/insights/latest`

**Description**: Displays the site's most recently published public articles. Suitable for homepage "Latest Updates" section.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| count | int | No | 3 | Number of articles to display |
| category | string | No | — | Filter by category (e.g. `product-updates`, `insights`) |
| show_cover | bool | No | true | Whether to show cover image |
| show_excerpt | bool | No | true | Whether to show excerpt |
| layout | enum | No | `list` | Layout: `list` / `grid` / `card` |
| title | string | No | `Latest Updates` | Section title |

**API Response Format**:

```json
{
  "posts": [
    {
      "id": 1,
      "slug": "hermes-v2-release",
      "title": "Hermes V2 Release",
      "excerpt": "Next-gen AI Agent framework...",
      "cover_image": "/uploads/cover.jpg",
      "category": "insights",
      "published_at": "2026-07-20T10:00:00"
    }
  ]
}
```

**Frontend Rendering HTML**:

```html
<div class="widget-latest-articles"
     data-widget="latest_articles"
     data-count="3"
     data-category="insights"
     data-layout="card"
     data-show-cover="true"
     data-show-excerpt="true">
  <h2 class="widget-title">Latest Updates</h2>
  <div class="widget-loading">Loading...</div>
</div>
<script>VeroWidgets.init('latest_articles')</script>
```

**AI Prompt Keywords**: `latest articles`, `latest updates`, `news`, `recently published`, `blog`, `latest`

---

### W02 — Hot Articles (hot_articles)

**API Endpoint**: Via `GET /docs/<cat_slug>/` or CMS public API, sorted by `views` / `published_at` on frontend

**Description**: Displays popular articles. Suitable for homepage "Hot Picks" or sidebar "Reading Rankings".

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| count | int | No | 5 | Number of articles to display |
| category | string | No | — | Filter by category |
| sort_by | enum | No | `published_at` | Sort: `published_at` / `views` / `manual` |
| layout | enum | No | `list` | Layout: `list` / `ranked` (numbered) |
| show_cover | bool | No | false | Whether to show cover image |
| title | string | No | `Hot Picks` | Section title |

**AI Prompt Keywords**: `hot articles`, `popular`, `reading rankings`, `featured`, `hot`, `trending`

---

### W03 — Article Categories (article_categories)

**API Endpoint**: `GET /api/v1/categories`

**Description**: Displays article category navigation. Suitable for knowledge base or blog sidebar.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| layout | enum | No | `list` | Layout: `list` / `grid` / `tag` |
| show_count | bool | No | true | Whether to show article count |
| parent_only | bool | No | true | Show top-level categories only |
| title | string | No | `Categories` | Section title |

**API Response Format**:

```json
{
  "categories": [
    {
      "id": 1,
      "name": "Product Updates",
      "slug": "insights",
      "icon": "📄",
      "sort_order": 5,
      "is_active": 1
    }
  ],
  "count": 1
}
```

**AI Prompt Keywords**: `article categories`, `sections`, `knowledge base navigation`, `categories`, `taxonomy`

---

### W14 — Content Feed (content_feed)

**API Endpoint**: `GET /admin/content-factory/api/v1/skills?agent=hermes`

**Description**: Displays auto-collected and processed content from the Content Factory. Suitable for "Industry News" or "Information Aggregation" sections.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| count | int | No | 10 | Number of items to display |
| source | string | No | — | Filter by source (RSS feed name) |
| platform | string | No | — | Filter by platform |
| auto_refresh | bool | No | false | Whether to auto-refresh |
| refresh_interval | int | No | 300 | Refresh interval (seconds) |
| title | string | No | `Industry News` | Section title |

**AI Prompt Keywords**: `content feed`, `information aggregation`, `industry news`, `RSS`, `feed`, `news`

---

## 4. Commerce Widgets

### W04 — Product List (product_list)

**API Endpoint**: `GET /shop/api/products?category=xxx&category_id=xxx&search=xxx`

**Description**: Displays shop product listing. Suitable for "All Products" page or homepage "Product Showcase" section.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| count | int | No | 8 | Number of products to display |
| category | string | No | — | Category name (e.g. `Cloud Services`, `Physical Goods`) |
| category_id | int | No | — | Category ID |
| layout | enum | No | `grid` | Layout: `grid` / `list` / `card` |
| columns | int | No | 4 | Grid columns (desktop) |
| show_price | bool | No | true | Whether to show price |
| show_original_price | bool | No | false | Whether to show original price |
| sort_by | enum | No | `sort_order` | Sort: `sort_order` / `sales_count` / `price_asc` / `price_desc` |
| title | string | No | `Products` | Section title |

**API Response Format**:

```json
{
  "products": [
    {
      "id": 1,
      "title": "AI Site Builder Service",
      "subtitle": "Generate professional sites in one click",
      "product_type": "service",
      "category": "Cloud Services",
      "price": 299,
      "original_price": 599,
      "sales_count": 1280,
      "thumbnail": "/uploads/product.jpg",
      "is_active": 1
    }
  ]
}
```

**AI Prompt Keywords**: `product`, `products`, `service`, `shop`, `store`, `merchandise`

---

### W05 — Hot/Featured Products (hot_products)

**API Endpoint**: `GET /shop/api/products` (sorted by `sales_count DESC` on frontend)

**Description**: Displays best-selling or featured products. Suitable for homepage "Hot Sellers" or "Recommended Products" section.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| count | int | No | 4 | Number of products to display |
| category | string | No | — | Filter by category |
| sort_by | enum | No | `sales_count` | Sort: `sales_count` (best-selling) / `manual` (curated) |
| layout | enum | No | `grid` | Layout: `grid` / `card` / `horizontal` |
| columns | int | No | 4 | Grid columns |
| show_badge | bool | No | true | Whether to show "Hot" badge |
| show_price | bool | No | true | Whether to show price |
| title | string | No | `Hot Picks` | Section title |

**AI Prompt Keywords**: `hot selling`, `bestseller`, `recommended`, `popular`, `hot`, `featured`

---

### W06 — Product Detail Card (product_detail)

**API Endpoint**: `GET /shop/api/products/<pid>`

**Description**: Embeds a single product detail card. Suitable for landing page "Product Highlights" section.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| product_id | int | Yes | — | Product ID |
| show_sku | bool | No | false | Whether to show SKU selector |
| show_features | bool | No | true | Whether to show feature list |
| show_cta | bool | No | true | Whether to show buy button |
| cta_text | string | No | `Buy Now` | Button text |

**AI Prompt Keywords**: `product detail`, `product introduction`, `detail`, `product card`

---

### W10 — Coupon Entry (coupon_entry)

**API Endpoint**: `POST /plugin/coupons/validate` (auth required)  
**Recommended API**: `POST /plugin/coupons/ai/recommend` (auth required)

**Description**: Inserts a coupon claim/validation entry point. Suitable for checkout or campaign pages.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| scene | string | No | `shop` | Scene: `shop` / `subscription` / `promo` / `new_user` |
| show_available | bool | No | true | Whether to show available coupon list |
| show_input | bool | No | true | Whether to show coupon code input |
| title | string | No | `Coupons` | Section title |

**Note**: Coupon validation and claiming require user authentication.

**AI Prompt Keywords**: `coupon`, `discount code`, `promo code`, `coupon`, `discount`, `voucher`

---

### W11 — Wishlist Button (wishlist_button)

**API Endpoints**:
- `GET /plugin/wishlist/api/list` — Get user's wishlist (auth required)
- `POST /plugin/wishlist/api/toggle` — Toggle wishlist (add/remove, auth required)
- `POST /plugin/wishlist/api/check` — Batch check if products are in wishlist (auth required)
- `GET /plugin/wishlist/api/count` — Get wishlist item count (auth required)

**Description**: Adds a "Favorite/Wishlist" button on product cards. Users click to add items to their wishlist.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| product_id | int | Yes | — | Product ID |
| button_style | enum | No | `icon` | Style: `icon` (heart icon) / `text` (text button) / `both` |
| button_text | string | No | `Save` | Button text |
| show_count | bool | No | false | Whether to show wishlist count |
| show_tooltip | bool | No | true | Whether to show tooltip |

**Note**: Requires user authentication.

**AI Prompt Keywords**: `favorite`, `wishlist`, `save for later`, `bookmark`

---

## 5. Interaction Widgets

### W07 — Product Reviews (product_reviews)

**API Endpoint**: `GET /plugin/reviews/api/<product_id>?page=1&size=10&rating=5&has_image=true`

**Description**: Displays product review list with rating filtering and featured reviews. Suitable for product detail page "User Reviews" section.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| product_id | int | Yes | — | Product ID |
| count | int | No | 10 | Number of reviews to display |
| rating | int | No | — | Filter by rating (1-5) |
| has_image | bool | No | false | Show reviews with images only |
| show_stats | bool | No | true | Whether to show rating stats (avg, distribution) |
| layout | enum | No | `list` | Layout: `list` / `card` |
| sort_by | enum | No | `created_at` | Sort: `created_at` / `rating` / `hot` |
| title | string | No | `Reviews` | Section title |

**API Response Format**:

```json
{
  "reviews": [
    {
      "id": 1,
      "user_id": 100,
      "product_id": 5,
      "rating": 5,
      "content": "Excellent product, highly recommended!",
      "images": ["/uploads/review1.jpg"],
      "is_verified": true,
      "reply_content": "Thank you for your support!",
      "created_at": "2026-07-20"
    }
  ],
  "stats": {
    "total": 128,
    "avg_rating": 4.8,
    "positive": 120,
    "neutral": 5,
    "negative": 3,
    "with_images": 45
  }
}
```

**AI Prompt Keywords**: `review`, `rating`, `testimonial`, `user feedback`, `comments`

---

### W09 — Chatbot (chatbot)

**API Endpoint**: `POST /api/v1/chat` (SSE streaming, no auth required)

**Description**: Embeds an AI chat floating button at the bottom-right corner of the page. Supports RAG knowledge enhancement, intent classification, and multi-agent routing.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| enabled | bool | No | true | Whether to enable |
| title | string | No | `AI Assistant` | Chat window title |
| subtitle | string | No | — | Subtitle |
| welcome_message | string | No | `Hello! How can I help you?` | Welcome message |
| float_button_text | string | No | `💬` | Floating button text |
| agent_id | string | No | — | Specify agent (auto-route if not set) |
| source | string | No | `website` | Source identifier: `website` / `douyin` / `tiktok` |
| max_history | int | No | 20 | Maximum conversation history turns |
| position | enum | No | `bottom-right` | Position: `bottom-right` / `bottom-left` |
| theme_color | string | No | `#4F46E5` | Theme color |

**Frontend Rendering**:

```html
<div id="chatbot-widget"
     data-title="AI Assistant"
     data-welcome="Hello! How can I help you?"
     data-source="website"
     data-position="bottom-right"
     data-theme-color="#4F46E5">
</div>
<script src="/static/chatbot/widget.js"></script>
```

**AI Prompt Keywords**: `chat`, `customer service`, `AI assistant`, `chatbot`, `bot`, `intelligent Q&A`, `live support`

---

## 6. Marketing Widgets

### W08 — Ad Placement (ad_placement)

**API Endpoint**: `GET /admin/ads/api/v1/ads?page=*&position=sidebar&site_key=default&zone_id=0`  
**Tracking**: `POST /admin/ads/api/v1/stats/impression` (impression report), `POST /admin/ads/api/v1/stats/click` (click report)

**Description**: Inserts ad placements at specified page positions. Supports image ads and code ads.

**Ad Types**:

| Type | Identifier | Description |
|------|------|------|
| Image Ad | `image` | Display ad image + redirect link |
| Code Ad | `ad_code` | Directly inject ad code (e.g. Google AdSense) |

**Common Ad Sizes**:

| Name | Width | Height | Suggested Position |
|------|------|------|----------|
| Banner | 728 | 90 | Page top/bottom |
| Medium Banner | 468 | 60 | Content area top |
| Sidebar | 300 | 250 | Sidebar |
| Rectangle | 336 | 280 | Content area |
| Full-width Banner | 970 | 90 | Page top |
| Mobile Banner | 320 | 50 | Mobile page |
| Interstitial | 300 | 400 | Popup/interstitial |
| Custom | Any | Any | Custom position |

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| position | string | Yes | — | Ad position identifier (e.g. `home_banner`, `sidebar`, `content_mid`) |
| page | string | No | `*` | Page identifier (`*` matches all pages) |
| width | int | No | 320 | Ad width |
| height | int | No | 0 | Ad height (0 = auto) |
| ad_type | enum | No | `image` | Type: `image` / `ad_code` |
| zone_id | int | No | 0 | Zone ID |
| count | int | No | 1 | Number of ads (for carousel) |
| title | string | No | — | Section title (e.g. "Partners") |

**Position Identifier Naming Convention**:

| Position | Identifier | Description |
|------|------|------|
| Homepage Top Banner | `home_banner` | Below navigation |
| Homepage Mid | `home_mid` | Middle of content |
| Sidebar Top | `sidebar_top` | Top of sidebar |
| Sidebar Bottom | `sidebar_bottom` | Bottom of sidebar |
| Post Top | `post_top` | Above article title |
| Post Mid | `post_mid` | Middle of article content |
| Post Bottom | `post_bottom` | End of article |
| Product Sidebar | `product_sidebar` | Product detail sidebar |
| Global Popup | `global_popup` | Site-wide popup |
| Mobile Bottom | `mobile_bottom` | Fixed mobile bottom |

**Frontend Rendering**:

```html
<!-- Method 1: Placeholder container -->
<div data-ad-position="home_banner"
     data-ad-page="home"
     data-ad-width="728"
     data-ad-height="90">
</div>

<!-- Method 2: Ad block with title -->
<div class="widget-ad" data-widget="ad" data-position="sidebar_top">
  <h2 class="widget-title">Partners</h2>
  <div data-ad-position="sidebar_top" data-ad-page="*"></div>
</div>

<script src="/static/ads/ads.js"></script>
```

**AI Prompt Keywords**: `ad`, `advertisement`, `banner`, `promotion`, `sponsored`, `placement`

---

### W15 — Social Share (social_share)

**Description**: Inserts social share buttons on pages. Supports WeChat, Weibo, Toutiao and other platforms.

**Note**: This is a **pure frontend component** with no backend API required. Share actions open platform share URLs (e.g. `https://service.weibo.com/share/share.php?url=...`) in new windows. A public share component JS module needs to be developed.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| platforms | array | No | `["wechat","weibo"]` | Share platforms |
| layout | enum | No | `inline` | Layout: `inline` / `floating` (side floating) |
| show_count | bool | No | false | Whether to show share count |
| title | string | No | — | Custom share title |

**AI Prompt Keywords**: `share`, `forward`, `social`, `share`, `social media`

---

## 7. Infrastructure Widgets

### W12 — Search Box (search_box)

**Search Endpoints**:
- Product search: `GET /shop/api/products?search=xxx`
- Knowledge base search: `POST /api/v1/rag/search`
- Semantic search: `GET /api/v1/search?q=xxx` (requires Nginx proxy to cognition-service:8091)

**Description**: Inserts a search box on pages. Supports global search or scoped search.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| scope | enum | No | `all` | Search scope: `all` / `products` / `articles` / `knowledge` |
| placeholder | string | No | `Search...` | Input placeholder text |
| position | enum | No | `navbar` | Position: `navbar` (in navigation) / `inline` (content area) / `hero` (hero area) |
| show_suggestions | bool | No | true | Whether to show search suggestions |
| min_chars | int | No | 2 | Minimum characters to trigger search |

**Frontend Rendering**:

```html
<!-- Navbar search -->
<div class="widget-search"
     data-widget="search"
     data-scope="all"
     data-placeholder="Search products, articles..."
     data-position="navbar">
</div>

<!-- Hero area large search -->
<div class="widget-search-hero"
     data-widget="search"
     data-scope="all"
     data-placeholder="Enter keywords, explore the AI world..."
     data-position="hero">
</div>
```

**AI Prompt Keywords**: `search`, `search box`, `find`, `search`, `search bar`

---

### W13 — Knowledge Base Search (knowledge_search)

**API Endpoint**: `POST /api/v1/rag/search` (hybrid semantic retrieval)  
**Parameters**: `query`, `topK`, `category`

**Description**: Inserts a knowledge base search entry point. Suitable for documentation sites or help centers.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| top_k | int | No | 5 | Number of results to return |
| category | string | No | — | Knowledge base category filter |
| placeholder | string | No | `Search knowledge base...` | Input placeholder text |
| show_results_inline | bool | No | true | Whether to display results inline |
| title | string | No | `Knowledge Search` | Section title |

**AI Prompt Keywords**: `knowledge base`, `documentation search`, `help center`, `knowledge`, `docs`

---

### W16 — Navigation Bar (navigation)

**Data Source**: `design_tokens.draft_json.navigation`

**Description**: Site main navigation bar, auto-generated during AI site building. Supports top-level menu items + dropdown submenus.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| items | array | Yes | — | Navigation item list |
| style | enum | No | `default` | Style: `default` / `sticky` (fixed top) / `transparent` |
| logo_position | enum | No | `left` | Logo position: `left` / `center` |
| show_search | bool | No | false | Whether to show search icon in nav |
| show_cta | bool | No | false | Whether to show CTA button |
| cta_text | string | No | — | CTA button text |
| cta_url | string | No | — | CTA button link |
| mobile_style | enum | No | `hamburger` | Mobile style: `hamburger` / `bottom_tab` |

**Navigation Item Format**:

```json
{
  "items": [
    {"label": "Home", "href": "/", "order": 1},
    {"label": "Products", "href": "/products", "order": 2,
     "children": [
       {"label": "AI Site Builder", "href": "/products/site-builder"},
       {"label": "Mini Program", "href": "/products/mini-app"}
     ]},
    {"label": "About", "href": "/about", "order": 3}
  ]
}
```

**AI Prompt Keywords**: `navigation`, `menu`, `nav`, `menu`, `navbar`

---

### W17 — Footer (footer)

**Data Source**: `design_tokens.draft_json.footer`

**Description**: Site global footer, containing link groups, copyright info, and social media links.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| groups | array | No | [] | Link groups |
| copyright | string | No | `© {year} {site_name}` | Copyright text |
| show_social | bool | No | true | Whether to show social media icons |
| social_links | array | No | [] | Social media links |
| show_back_to_top | bool | No | true | Whether to show back-to-top button |
| style | enum | No | `default` | Style: `default` / `minimal` / `dark` |

**AI Prompt Keywords**: `footer`, `bottom`, `footer`, `copyright`

---

### W18 — Contact Info (contact_info)

**Description**: Embeds contact information block. Suitable for "Contact Us" page or above-footer area.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|------|------|:---:|--------|------|
| show_form | bool | No | false | Whether to show contact form |
| show_email | bool | No | true | Whether to show email |
| show_phone | bool | No | false | Whether to show phone |
| show_address | bool | No | false | Whether to show address |
| show_wechat | bool | No | false | Whether to show WeChat QR code |
| show_map | bool | No | false | Whether to show map |
| title | string | No | `Contact Us` | Section title |

**AI Prompt Keywords**: `contact`, `contact us`, `support`, `address`, `get in touch`

---

## 8. AI Prompt Integration Specification

### 8.1 Referencing Widgets in YAML Templates

In each page's `prompts.page_xxx`, the AI should automatically match widgets based on user requirements:

```yaml
prompts:
  page_home: |
    You are a website designer. Generate homepage content for [{brand_name}].

    Industry: {industry}, Style: {style_preference}, User requirements: {user_input}

    Homepage section design:
    1. Hero area: product value proposition + CTA
    2. Core features: 3-4 highlights
    3. [Optional] If user mentions "show latest updates", insert W01(latest_articles, count=3)
    4. [Optional] If user mentions "hot selling" or "shop", insert W05(hot_products, count=4)
    5. [Optional] If user mentions "ad", insert W08(ad_placement, position=home_mid)
    6. [Optional] If user mentions "customer service" or "AI", insert W09(chatbot)
    7. Trust indicators: user count, satisfaction rate, etc.

    Return JSON format with widgets array:
    {{
      "sections": [...],
      "widgets": [
        {{
          "widget_id": "W01",
          "widget_type": "latest_articles",
          "count": 3,
          "layout": "card",
          "position": "after_features"
        }}
      ]
    }}
```

### 8.2 Widget Insertion Positions

| Position Identifier | Description |
|----------|------|
| `after_hero` | After hero section |
| `after_features` | After feature highlights |
| `before_footer` | Before footer |
| `sidebar` | Sidebar |
| `inline_section` | As standalone section |
| `modal` | Modal popup |
| `floating` | Floating button |

### 8.3 Natural Language → Widget Mapping Table

| User Says | Matched Widget | Default Parameters |
|--------|----------|----------|
| "add an ad" / "place a banner" | W08 (Ad Placement) | position=home_banner, width=728 |
| "add customer service" / "AI chat" | W09 (Chatbot) | position=bottom-right |
| "show latest articles" / "news feed" | W01 (Latest Articles) | count=3, layout=card |
| "hot picks" / "reading rankings" | W02 (Hot Articles) | count=5, layout=ranked |
| "best sellers" / "featured products" | W05 (Hot Products) | count=4, layout=grid |
| "product list" / "all products" | W04 (Product List) | count=8, layout=grid |
| "user reviews" / "testimonials" | W07 (Product Reviews) | count=10, show_stats=true |
| "search box" / "search function" | W12 (Search Box) | scope=all, position=navbar |
| "coupons" / "discount codes" | W10 (Coupon Entry) | scene=shop |
| "favorites" / "wishlist" | W11 (Wishlist Button) | button_style=icon |
| "knowledge base" / "doc search" | W13 (Knowledge Search) | top_k=5 |
| "industry news" / "news aggregation" | W14 (Content Feed) | count=10 |
| "categories" / "article sections" | W03 (Article Categories) | layout=list |
| "share" / "social" | W15 (Social Share) | platforms=["wechat","weibo"] |

---

## 9. Frontend Rendering Templates

### 9.1 Unified Widget Rendering JS

All widgets are initialized through `VeroWidgets`:

```javascript
// VeroWidgets core logic
var VeroWidgets = {
  registry: {
    'latest_articles':   { api: '/api/v1/insights/latest', method: 'GET' },
    'article_categories': { api: '/api/v1/categories', method: 'GET' },
    'hot_products':      { api: '/shop/api/products', method: 'GET' },
    'product_list':      { api: '/shop/api/products', method: 'GET' },
    'product_reviews':   { api: '/plugin/reviews/api/{product_id}', method: 'GET' },
    'ad':                { api: '/admin/ads/api/v1/ads', method: 'GET' },
    'chatbot':           { init: 'chatbotWidget' },
    'search':            { init: 'searchWidget' },
    'knowledge_search':  { api: '/api/v1/rag/search', method: 'POST' },
    'content_feed':      { api: '/admin/content-factory/api/v1/skills', method: 'GET' },
    'coupon_entry':      { api: '/plugin/coupons/ai/recommend', method: 'POST', auth: true },
    'wishlist_button':   { api: '/plugin/wishlist/api/toggle', method: 'POST', auth: true },
  },

  init: function(widgetType) {
    var els = document.querySelectorAll('[data-widget="' + widgetType + '"]');
    els.forEach(function(el) {
      var cfg = this.registry[widgetType];
      if (cfg.init) {
        window[cfg.init](el);
      } else if (cfg.api) {
        this.fetchAndRender(el, cfg);
      }
    }.bind(this));
  },

  fetchAndRender: function(el, cfg) {
    var params = {};
    for (var attr of el.attributes) {
      if (attr.name.startsWith('data-')) {
        params[attr.name.replace('data-', '')] = attr.value;
      }
    }
    var url = cfg.api;
    for (var key in params) {
      url = url.replace('{' + key + '}', params[key]);
    }
    fetch(url, { method: cfg.method })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var loading = el.querySelector('.widget-loading');
        if (loading) loading.remove();
        el.innerHTML += this.renderWidget(el, data);
      }.bind(this));
  }
};
```

### 9.2 Mini-Program Rendering

Mini-program widget rendering logic is consistent with the web side but uses each platform's native components. API calls go through `POST /api/v1/mini-program/` unified entry point.

---

## Appendix A: API Endpoint Quick Reference

| Widget | Endpoint | Method | Auth |
|------|------|:---:|:---:|
| W01 | `/api/v1/insights/latest` | GET | No |
| W02 | `/docs/<cat_slug>/` | GET | No |
| W03 | `/api/v1/categories` | GET | No |
| W04 | `/shop/api/products` | GET | No |
| W05 | `/shop/api/products` (sorted by sales_count) | GET | No |
| W06 | `/shop/api/products/<pid>` | GET | No |
| W07 | `/plugin/reviews/api/<product_id>` | GET | No |
| W08 | `/admin/ads/api/v1/ads` | GET | No |
| W08 (tracking) | `/admin/ads/api/v1/stats/impression` | POST | No |
| W08 (tracking) | `/admin/ads/api/v1/stats/click` | POST | No |
| W09 | `/api/v1/chat` (SSE streaming) | POST | No |
| W10 | `/plugin/coupons/validate` | POST | Yes |
| W10 (recommend) | `/plugin/coupons/ai/recommend` | POST | Yes |
| W11 | `/plugin/wishlist/api/list` | GET | Yes |
| W11 | `/plugin/wishlist/api/toggle` | POST | Yes |
| W11 | `/plugin/wishlist/api/check` | POST | Yes |
| W11 | `/plugin/wishlist/api/count` | GET | Yes |
| W12 | `/shop/api/products?search=` | GET | No |
| W12 (semantic) | `/api/v1/search?q=` (proxied to cognition-service:8091) | GET | No |
| W13 | `/api/v1/rag/search` | POST | No |
| W14 | `/admin/content-factory/api/v1/skills` | GET | No |
| W15 | Pure frontend JS component | — | No |
| W16 | `design_tokens.navigation` | — | N/A |
| W17 | `design_tokens.footer` | — | N/A |
| W18 | Static HTML template | — | N/A |

---

## Appendix B: Mini-Program Adaptation Notes

| Widget | Mini-Program Support | Adaptation Method |
|------|:---:|------|
| W01 Latest Articles | Yes | Via `/api/v1/mini-program/site/pages` |
| W03 Categories | Yes | Direct call to `/api/v1/categories` |
| W04 Product List | Yes | Direct call to `/shop/api/products` |
| W05 Hot Products | Yes | Same as above, frontend sort |
| W07 Product Reviews | Yes | Direct call to `/plugin/reviews/api/<product_id>` |
| W08 Ad Placement | Partial | Image ads only; code ads need platform review |
| W09 Chatbot | Yes | Call `/api/v1/chat` (WebSocket in mini-program) |
| W12 Search Box | Yes | Mini-program native `<input>` + API call |
| W10 Coupons | Yes | Auth required |
| W11 Wishlist | Yes | Auth required |

---

> **Document Maintenance**  
> This document is generated based on v2026.07 codebase. When adding new widgets, synchronize updates to:
> 1. This document's widget inventory
> 2. YAML prompt templates' widget references
> 3. `VeroWidgets.registry` table
> 4. Mini-program corresponding rendering components
