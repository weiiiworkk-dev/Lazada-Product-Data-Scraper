# Lazada Product Data Scraper

Scrape product data from **Lazada** across 6 Southeast Asian countries. Uses Lazada's internal mobile API directly with browser TLS fingerprint impersonation — no headless browser needed, lower cost, higher speed.

## Key Features

- **6 Country Sites**: Singapore, Malaysia, Thailand, Philippines, Indonesia, Vietnam
- **Keyword Search**: Search any product keyword with pagination
- **Structured JSON Output**: Price, rating, sales, seller, brand, location, LazMall status
- **Data Normalized**: Prices as floats, ratings scored, ready for analysis
- **Anti-Bot Bypass**: Uses `curl_cffi` with Chrome TLS fingerprint to bypass Cloudflare
- **Lightweight**: No Playwright/Puppeteer — direct HTTP API calls, fast and cheap

## How It Works

Instead of scraping HTML or running a headless browser, this Actor calls Lazada's internal mobile API endpoint with a browser-emulated TLS handshake. This means:

- **Faster**: ~4 seconds per page vs 30+ seconds with browser automation
- **Cheaper**: Lower platform compute usage = lower cost per run
- **More Reliable**: Data comes as clean JSON, no HTML parsing fragility

## Input

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `keyword` | string | ✅ | — | Product to search for (e.g. "smartphone", "xiaomi") |
| `country` | string | | `my` | Country site: `sg`, `my`, `th`, `ph`, `id`, `vn` |
| `maxPages` | integer | | `1` | Pages to scrape (~40 products/page, max: 20) |

## Output

Each product is saved as an item in the default dataset:

```json
{
  "title": "Apple iPhone 17 Pro Max",
  "price": 6453,
  "originalPrice": 6699,
  "currency": "",
  "rating": 4.97,
  "reviewCount": "483",
  "sales": null,
  "location": "Selangor",
  "sellerName": "UR bySwitch",
  "brandName": "Apple",
  "isLazMall": false,
  "imageUrl": "https://my-live-01.slatic.net/p/..."
}
```

## Quick Start

```bash
# Install Apify CLI
npm -g install apify-cli

# Run the Actor
apify call lazada-product-scraper \
  --input '{"keyword":"smartphone","country":"my","maxPages":1}'
```

Or use the API:

```python
import requests

response = requests.post(
    "https://api.apify.com/v2/acts/aa5734814~lazada-product-scraper/runs",
    headers={"Authorization": "Bearer YOUR_API_TOKEN"},
    json={
        "keyword": "smartphone",
        "country": "my",
        "maxPages": 1
    }
)
```

## Use Cases

- **Competitor price monitoring** — Track pricing changes across Lazada
- **Market research** — Analyze product trends in SEA markets
- **Brand protection** — Monitor authorized vs unauthorized sellers
- **Inventory tracking** — Check stock status and seller locations

## Pricing

Pay Per Result — you only pay for the results you use.

## Countries Supported

| Code | Country | Domain |
|------|---------|--------|
| `sg` | Singapore | Lazada.sg |
| `my` | Malaysia | Lazada.my |
| `th` | Thailand | Lazada.co.th |
| `ph` | Philippines | Lazada.ph |
| `id` | Indonesia | Lazada.co.id |
| `vn` | Vietnam | Lazada.vn |
