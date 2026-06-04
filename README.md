# Lazada Product Data Scraper

Scrape product data from **Lazada** across 6 Southeast Asian countries. Extracts product titles, prices, sales, ratings, seller info, and more — with automatic **data normalization** so prices are floats, sales are integers, and currencies are detected.

## Features

- **6 Country Sites**: Singapore, Malaysia, Thailand, Philippines, Indonesia, Vietnam
- **Product Search**: Search by keyword with pagination support
- **Rich Data**: title, price, original price, sales, rating, seller, location, image, specifications
- **Data Normalization**: Multi-currency price → float, sales count → int, auto currency detection
- **Pagination**: Automatic page-to-page navigation
- **Lightweight HTTP Crawler**: Uses Lazada's internal AJAX endpoint (no headless browser needed)
- **Apify Proxy Integration**: Supports Residential proxies

## Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| keyword | string | ✅ | Search keyword (e.g. "smartphone", "xiaomi") |
| country | string | | Country site: `sg`, `my`, `th`, `ph`, `id`, `vn` (default: `my`) |
| maxPages | integer | | Max pages to scrape, ~40 products/page (default: 3, max: 50) |
| proxyConfiguration | object | | Apify proxy settings. **Residential** recommended for reliable access |

## Output

Each product is saved as an item in the default dataset:

```json
{
  "title": "Xiaomi Redmi Note 13 Pro",
  "url": "https://www.lazada.my/products/...",
  "price": 1099.00,
  "originalPrice": 1399.00,
  "currency": "MYR",
  "sales": 5200,
  "rating": 4.7,
  "location": "Kuala Lumpur",
  "sellerName": "Xiaomi Official Store",
  "imageUrl": "https://...",
  "specifications": { "RAM": "8 GB", "Storage": "256 GB" }
}
```

### Normalized Fields

| Raw (from page) | Normalized |
|----------------|------------|
| `RM 89.00` | `price: 89.0`, `currency: "MYR"` |
| `Rp 150.000` | `price: 150000.0`, `currency: "IDR"` |
| `"已售 1.5k"` | `sales: 1500` |
| `"4.8/5"` | `rating: 4.8` |

## Proxy Recommendation

Lazada actively blocks datacenter IP addresses. For reliable scraping:

- ✅ **Apify Residential Proxy** (`groups: ["RESIDENTIAL"]`) — lowest block rate
- ⚠️ **Apify Datacenter Proxy** — may work for light usage
- ❌ **No proxy** — almost certainly blocked

## How to Run

1. Open the Actor in Apify Console
2. Enter a search **keyword**
3. Select a **country** (optional)
4. Configure **proxy** (Residential recommended)
5. Click **Run**

## Output Formats

Results can be exported from the Dataset in JSON, CSV, Excel, XML, or HTML formats.
