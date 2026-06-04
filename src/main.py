import asyncio
import urllib.parse

from apify import Actor
from crawlee.crawlers import PlaywrightCrawler
from crawlee.proxy_configuration import ProxyConfiguration

from src.config import LAZADA_SITES, SEARCH_PATH, MAX_RETRIES
from src.routes import router


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        keyword = actor_input.get('keyword', '').strip()
        country = actor_input.get('country', 'my')
        max_pages = actor_input.get('maxPages', 3)

        if not keyword:
            await Actor.fail('Search keyword is required')
            return

        site = LAZADA_SITES.get(country)
        if not site:
            await Actor.fail(f'Unsupported country: {country}')
            return

        proxy_config = None
        proxy_input = actor_input.get('proxyConfiguration')
        if proxy_input and proxy_input.get('useApifyProxy'):
            proxy_config = ProxyConfiguration(
                apify_proxy_groups=proxy_input.get('apifyProxyGroups', ['RESIDENTIAL']),
            )

        crawler = PlaywrightCrawler(
            request_handler=router,
            proxy_configuration=proxy_config,
            max_request_retries=MAX_RETRIES,
            max_requests_per_crawl=max_pages,
            headless=True,
            browser_type='chromium',
        )

        search_url = _build_search_url(site['domain'], keyword)
        await crawler.run([search_url])


def _build_search_url(domain: str, keyword: str) -> str:
    params = urllib.parse.urlencode({'q': keyword})
    return f'https://{domain}{SEARCH_PATH}?{params}'


if __name__ == '__main__':
    asyncio.run(main())
