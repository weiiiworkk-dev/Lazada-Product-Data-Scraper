import asyncio
import urllib.parse

from apify import Actor

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

        from crawlee.crawlers import BeautifulSoupCrawler

        proxy_input = actor_input.get('proxyConfiguration') or {}
        Actor.log.info(f'Proxy input: {proxy_input}')
        use_proxy = proxy_input.get('useApifyProxy', True)
        groups = proxy_input.get('apifyProxyGroups') if use_proxy else None
        proxy_configuration = await Actor.create_proxy_configuration(groups=groups)
        if proxy_configuration:
            Actor.log.info(f'Proxy created with groups: {groups}')
        else:
            Actor.log.warning('No proxy created')

        crawler = BeautifulSoupCrawler(
            request_handler=router,
            proxy_configuration=proxy_configuration,
            max_request_retries=MAX_RETRIES,
            max_requests_per_crawl=max_pages,
            additional_http_error_status_codes=[404, 429, 503],
        )

        search_url = _build_search_url(site['domain'], keyword)
        await crawler.run([search_url])


def _build_search_url(domain: str, keyword: str) -> str:
    params = urllib.parse.urlencode({'q': keyword, 'ajax': 'true'})
    return f'https://{domain}{SEARCH_PATH}?{params}'


if __name__ == '__main__':
    asyncio.run(main())
