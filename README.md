# Lazada Product Data Scraper

Scrape product data from **Lazada** across 6 Southeast Asian countries. Uses Lazada's internal API directly with browser TLS fingerprint impersonation — no headless browser needed, lower cost, higher speed.

## Key Features

- **6 Country Sites**: Singapore, Malaysia, Thailand, Philippines, Indonesia, Vietnam
- **Keyword Search**: Search any product keyword with pagination (up to 20 pages, ~40 products/page)
- **URL Mode**: Paste any Lazada search or category URL directly
- **Cross-Country Price Comparison**: Compare prices across all 6 countries in one run
- **Advanced Filters**: Sort by price/rating/sales, filter by min/max price, min rating
- **Structured JSON Output**: Price, rating, sales, seller, brand, location, LazMall status
- **Anti-Bot Bypass**: Chrome TLS fingerprint impersonation + x5sec challenge auto-solving
- **Lightweight**: No browser needed — direct HTTP API calls, fast and cheap

## How It Works

This Actor calls Lazada's AJAX catalog API with a browser-emulated TLS handshake and automatic cookie session management. When Lazada's WAF (x5sec) serves a challenge page, the Actor automatically extracts and follows the punish redirect to obtain a valid session cookie before retrying.

- **Faster**: ~3-5 seconds per page vs 30+ seconds with browser automation
- **Cheaper**: Lower compute usage = lower cost per run
- **More Reliable**: Data comes as clean JSON, no HTML parsing fragility

## Input

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `mode` | string | | `keyword` | Search mode: `keyword` (search by product name) or `url` (paste Lazada URLs) |
| `keywords` | string[] | in keyword mode | — | Product keywords to search (e.g. "smartphone", "xiaomi 14") |
| `urls` | string[] | in url mode | — | Lazada search/category URLs (e.g. `https://www.lazada.sg/catalog/?q=laptop`) |
| `country` | string | | `my` | Country site: `sg`, `my`, `th`, `ph`, `id`, `vn` |
| `searchAllCountries` | boolean | | `false` | Search this keyword across ALL 6 countries in one run |
| `maxPages` | integer | | `1` | Pages to scrape per country (~40 products/page, max: 20) |
| `sortBy` | string | | `relevance` | Sort order: `relevance`, `priceAsc`, `priceDesc`, `ratingDesc`, `newest`, `soldDesc` |
| `minPrice` | number | | — | Minimum price in local currency (optional) |
| `maxPrice` | number | | — | Maximum price in local currency (optional) |
| `minRating` | number | | — | Minimum rating 1.0-5.0 (optional) |
| `comparePrices` | boolean | | `false` | Generate a price comparison report (requires `searchAllCountries: true`) |
| `proxyConfiguration` | proxy | | — | Proxy settings. Use RESIDENTIAL if you encounter WAF blocks. |

### Example: Basic keyword search

```json
{
  "mode": "keyword",
  "keywords": ["wireless earphone"],
  "country": "sg",
  "maxPages": 2,
  "sortBy": "ratingDesc"
}
```

### Example: Search all countries with cross-country price comparison

```json
{
  "mode": "keyword",
  "keywords": ["iphone 16"],
  "searchAllCountries": true,
  "maxPages": 1,
  "comparePrices": true
}
```

### Example: URL mode

```json
{
  "mode": "url",
  "urls": ["https://www.lazada.sg/catalog/?q=gaming+chair"],
  "maxPages": 1
}
```

## Output

Each product is saved as a dataset item:

```json
{
  "type": "product",
  "keyword": "smartphone",
  "country": "MY",
  "currency": "MYR",
  "title": "Apple iPhone 17 Pro Max 1TB",
  "url": "https://www.lazada.com.my/products/pdp-i1234567890.html",
  "imageUrl": "https://my-live-01.slatic.net/p/...",
  "price": 6453.00,
  "originalPrice": 6699.00,
  "rating": 4.97,
  "reviewCount": "483",
  "sales": 1500,
  "location": "Selangor",
  "sellerName": "UR bySwitch",
  "sellerId": "12345678",
  "brandName": "Apple",
  "isLazMall": true
}
```

When `comparePrices` is enabled, an additional price comparison item is pushed:

```json
{
  "type": "price_comparison",
  "keyword": "iphone 16",
  "totalProducts": 320,
  "countries": ["SG", "MY", "TH", "PH", "ID", "VN"],
  "cheapestCountry": "MY",
  "summary": {
    "SG": { "count": 55, "minPrice": 1299, "maxPrice": 2899, "avgPrice": 1899 },
    "MY": { "count": 48, "minPrice": 1199, "maxPrice": 2799, "avgPrice": 1799 }
  },
  "priceRange": { "min": 1199, "max": 2899 }
}
```

## Quick Start

### Apify CLI

```bash
npm -g install apify-cli

apify call lazada-product-scraper \
  --input '{"mode":"keyword","keywords":["smartphone"],"country":"my","maxPages":1}'
```

### API (Python)

```python
import requests

response = requests.post(
    "https://api.apify.com/v2/acts/aa5734814~lazada-product-scraper/runs",
    headers={"Authorization": "Bearer YOUR_API_TOKEN"},
    json={
        "mode": "keyword",
        "keywords": ["smartphone"],
        "country": "my",
        "maxPages": 1
    }
)
```

### API (cURL)

```bash
curl -X POST "https://api.apify.com/v2/acts/aa5734814~lazada-product-scraper/runs" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"keyword","keywords":["smartphone"],"country":"sg","maxPages":1}'
```

## Use Cases

- **Competitor price monitoring** — Track pricing changes across Lazada
- **Market research** — Analyze product trends in SEA markets
- **Cross-border price arbitrage** — Find cheapest country for any product
- **Brand protection** — Monitor authorized vs unauthorized sellers
- **Inventory tracking** — Check stock status and seller locations

## Notes

- Some keywords may trigger Lazada's x5sec WAF. If you consistently get empty results, enable Apify RESIDENTIAL proxy or try different keywords.
- The actor uses Lazada's AJAX API (`/catalog/?ajax=true`). Rate limiting may apply at high page counts.

## Countries Supported

| Code | Country | Domain |
|------|---------|--------|
| `sg` | Singapore | Lazada.sg |
| `my` | Malaysia | Lazada.my |
| `th` | Thailand | Lazada.co.th |
| `ph` | Philippines | Lazada.ph |
| `id` | Indonesia | Lazada.co.id |
| `vn` | Vietnam | Lazada.vn |
