import asyncio
import os
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

        from datetime import timedelta
        from crawlee.crawlers import PlaywrightCrawler, GotoOptions

        proxy_configuration = await Actor.create_proxy_configuration()
        if proxy_configuration:
            Actor.log.info('Using default Apify proxy')
        else:
            Actor.log.warning('No proxy configuration available')

        crawler = PlaywrightCrawler(
            request_handler=router,
            proxy_configuration=proxy_configuration,
            max_request_retries=MAX_RETRIES,
            max_requests_per_crawl=max_pages,
            headless=True,
            browser_type='chromium',
            use_incognito_pages=True,
            retry_on_blocked=True,
            goto_options=GotoOptions(wait_until='domcontentloaded'),
            navigation_timeout=timedelta(seconds=30),
        )

        search_url = _build_search_url(site['domain'], keyword)
        await crawler.run([search_url])


def _build_search_url(domain: str, keyword: str) -> str:
    params = urllib.parse.urlencode({'q': keyword})
    return f'https://{domain}{SEARCH_PATH}?{params}'


if __name__ == '__main__':
    asyncio.run(main())
