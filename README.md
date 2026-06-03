# Lazada Product Scraper

Scrape product data from Lazada (Singapore, Malaysia, Thailand, Philippines, Indonesia, Vietnam).

## Features

- Search by keyword across all 6 Lazada country sites
- Extracts: title, price, original price, sales, rating, seller, location, images, specifications
- **Data normalization**: prices → float, sales → int, currency detection
- Stealth anti-detection (browser fingerprint randomization)
- Apify Proxy (RESIDENTIAL) support
- Pagination support

## Input

| Field | Type | Description |
|-------|------|-------------|
| keyword | string | Search keyword (required) |
| country | string | Site: sg/my/th/ph/id/vn |
| maxPages | integer | Max search result pages |
| proxyConfiguration | object | Proxy settings |

## Output

Each item in the dataset contains cleaned/normalized fields:
- `title`, `url`, `imageUrl`
- `price` (float), `originalPrice` (float), `currency`
- `sales` (int), `rating` (float)
- `location`, `sellerName`, `specifications`
