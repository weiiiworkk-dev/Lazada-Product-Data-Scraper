from crawlee.router import Router
from crawlee.crawlers import PlaywrightCrawlingContext
from src.config import PAGE_PARAM, SEARCH_PATH, STALE_ELEMENT_RETRIES
from src.parser import extract_search_results, has_next_page
from src.normalizer import normalize_product

router = Router[PlaywrightCrawlingContext]()


@router.default_handler
async def search_handler(context: PlaywrightCrawlingContext) -> None:
    context.log.info(f'Searching: {context.request.url}')

    await context.page.wait_for_load_state('networkidle', timeout=30000)
    await context.page.wait_for_selector('div[data-qa-locator="product-item"]', timeout=15000)

    products = await extract_search_results(context.page)

    cleaned = [normalize_product(p) for p in products if p.get('title')]
    context.log.info(f'Found {len(cleaned)} products on {context.request.url}')

    if cleaned:
        await context.push_data(cleaned)

    more = await has_next_page(context.page)
    if more:
        current = _page_from_url(context.request.url)
        await context.add_requests([
            _next_page_url(context.request.url, current)
        ])


def _page_from_url(url: str) -> int:
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    return int(params.get(PAGE_PARAM, [1])[0])


def _next_page_url(url: str, current: int) -> str:
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    params[PAGE_PARAM] = [str(current + 1)]
    new_query = urllib.parse.urlencode(params, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))
