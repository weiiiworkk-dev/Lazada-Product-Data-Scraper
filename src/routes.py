from crawlee.router import Router
from crawlee.crawlers import BeautifulSoupCrawlingContext
from src.normalizer import normalize_product

router = Router[BeautifulSoupCrawlingContext]()


@router.default_handler
async def search_handler(context: BeautifulSoupCrawlingContext) -> None:
    context.log.info(f'Fetching: {context.request.url}')

    products = []
    for card in context.soup.select('div[data-qa-locator="product-item"], div.Bm3ON, div[class*="card"]'):
        title_el = card.select_one('a[href*=".html"]')
        price_el = card.select_one('span.ooOxS, span[class*="price"]')
        original_el = card.select_one('span[class*="original"], del')
        rating_el = card.select_one('div.rate i, span[class*="rating"]')
        sales_el = card.select_one('span[class*="sale"], span[class*="sold"]')
        image_el = card.select_one('img[class*="image"], img[src*="lazada"]')

        if not title_el:
            continue

        products.append({
            'title': title_el.get('title') or title_el.get_text(strip=True),
            'url': title_el.get('href', ''),
            'price': price_el.get_text(strip=True) if price_el else None,
            'originalPrice': original_el.get_text(strip=True) if original_el else None,
            'rating': rating_el.parent.get_text(strip=True) if rating_el else None,
            'sales': sales_el.get_text(strip=True) if sales_el else None,
            'imageUrl': image_el.get('src') if image_el else None,
        })

    cleaned = [normalize_product(p) for p in products if p.get('title')]
    context.log.info(f'Found {len(cleaned)} products')

    if cleaned:
        await context.push_data(cleaned)

    next_page = context.soup.select_one(
        'li.ant-pagination-next:not(.ant-pagination-disabled) a, '
        'a[rel="next"]:not([disabled]), '
        'button.next:not([disabled])'
    )
    if next_page:
        href = next_page.get('href')
        if href:
            from urllib.parse import urljoin
            await context.add_requests([urljoin(context.request.url, href)])
