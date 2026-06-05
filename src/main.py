import asyncio
import json
from urllib.parse import urlencode, urlparse

from apify import Actor
from curl_cffi import requests as curl

SITES = {'sg': 'sg', 'my': 'com.my', 'th': 'co.th', 'ph': 'com.ph', 'id': 'co.id', 'vn': 'vn'}
CURRENCY_MAP = {'sg': 'SGD', 'my': 'MYR', 'th': 'THB', 'ph': 'PHP', 'id': 'IDR', 'vn': 'VND'}
SYMBOL_MAP = {'S$': 'SGD', 'RM': 'MYR', '฿': 'THB', '₱': 'PHP', 'Rp': 'IDR', '₫': 'VND', '$': 'USD'}
SORT_PARAMS = {'relevance': '', 'priceAsc': 'sort=priceasc', 'priceDesc': 'sort=pricedesc',
               'ratingDesc': 'sort=rating', 'newest': 'sort=newest', 'soldDesc': 'sort=sold'}
MAX_RETRIES = 3


def _parse_currency(price_show, country):
    if not price_show:
        return CURRENCY_MAP.get(country, '')
    if country == 'sg' and '$' in price_show:
        return 'SGD'
    if country == 'my' and 'RM' in price_show:
        return 'MYR'
    for sym, code in SYMBOL_MAP.items():
        if sym in price_show:
            return code
    return CURRENCY_MAP.get(country, '')


def parse_items(data, kw, c):
    items = data.get('mods', {}).get('listItems', [])
    results = []
    for i in items:
        if not i.get('name'):
            continue
        u = (i.get('productUrl', '') or i.get('itemUrl', '') or i.get('pageUrl', ''))
        if u.startswith('//'):
            u = 'https:' + u
        results.append({
            'type': 'product', 'keyword': kw, 'country': c.upper(),
            'currency': _parse_currency(i.get('priceShow', ''), c),
            'title': i.get('name', ''), 'url': u,
            'imageUrl': i.get('image', ''),
            'price': _f(i.get('price')),
            'originalPrice': _f(i.get('originalPrice')),
            'rating': _f(i.get('ratingScore')),
            'reviewCount': _i(i.get('review')),
            'sales': _i(i.get('sold')),
            'location': i.get('location', ''),
            'sellerName': i.get('sellerName', ''),
            'sellerId': i.get('sellerId', ''),
            'brandName': i.get('brandName', ''),
            'isLazMall': i.get('premiumBrand', False) or i.get('isLazMall', False),
        })
    return results


def _f(v):
    if v is None:
        return None
    try:
        return round(float(v), 2)
    except (ValueError, TypeError):
        return None


def _i(v):
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _country_from_url(url):
    host = urlparse(url).hostname or ''
    for code, tld in SITES.items():
        if f'lazada.{tld}' in host:
            return code
    return None


async def _fetch_json(url, proxy_url=None):
    kwargs = dict(impersonate='chrome131', timeout=30, headers={
        'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 Chrome/131.0.6422.113 Mobile Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'x-requested-with': 'XMLHttpRequest',
    })
    if proxy_url:
        kwargs['proxies'] = {"http": proxy_url, "https": proxy_url}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = curl.get(url, **kwargs)
            if resp.status_code == 429:
                wait = 2 ** attempt
                Actor.log.warning(f'Rate limited (429) — retry {attempt}/{MAX_RETRIES} in {wait}s')
                await asyncio.sleep(wait)
                continue
            if resp.status_code != 200:
                Actor.log.warning(f'HTTP {resp.status_code} — retry {attempt}/{MAX_RETRIES}')
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)
                continue
            raw = resp.text
            if not raw or len(raw) < 50:
                Actor.log.warning(f'Response too short ({len(raw)}B) — retry {attempt}/{MAX_RETRIES}')
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)
                continue
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                preview = raw[:200].replace('\n', ' ')
                Actor.log.warning(f'Non-JSON response (status={resp.status_code}, preview={preview}...) — retry {attempt}/{MAX_RETRIES}')
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)
                continue
        except Exception as e:
            Actor.log.warning(f'Request failed: {e} — retry {attempt}/{MAX_RETRIES}')
            if attempt < MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)
    Actor.log.error(f'All {MAX_RETRIES} retries exhausted for URL: {url}')
    return None


def _filter_products(products, min_price, max_price, min_rating):
    if min_price is not None:
        products = [x for x in products if x['price'] is not None and x['price'] >= min_price]
    if max_price is not None:
        products = [x for x in products if x['price'] is not None and x['price'] <= max_price]
    if min_rating is not None:
        products = [x for x in products if x['rating'] is not None and x['rating'] >= min_rating]
    return products


async def main():
    async with Actor:
        inp = await Actor.get_input() or {}
        mode = inp.get('mode', 'keyword')
        keywords = [kw.strip() for kw in (inp.get('keywords', []) or []) if kw.strip()]
        urls = [u.strip() for u in (inp.get('urls', []) or []) if u.strip()]
        country = inp.get('country', 'my')
        search_all = inp.get('searchAllCountries', False)
        max_pages = min(int(inp.get('maxPages', 1)), 20)
        sort_by = inp.get('sortBy', 'relevance')
        min_price = inp.get('minPrice')
        max_price = inp.get('maxPrice')
        min_rating = inp.get('minRating')
        compare_prices = inp.get('comparePrices', False)

        proxy_url = None
        pi = inp.get('proxyConfiguration') or {}
        if pi.get('useApifyProxy', False):
            pc = await Actor.create_proxy_configuration(groups=pi.get('apifyProxyGroups'))
            proxy_url = await pc.new_url() if pc else None

        all_products = []

        if mode == 'url':
            if not urls:
                Actor.log.error('URL mode selected but no URLs provided')
                return
            total = len(urls)
            for idx, raw_url in enumerate(urls, 1):
                c = _country_from_url(raw_url)
                if not c:
                    Actor.log.warning(f'Cannot detect country from URL, skipping: {raw_url}')
                    continue
                sep = '&' if '?' in raw_url else '?'
                ajax_url = f'{raw_url}{sep}ajax=true'
                data = await _fetch_json(ajax_url, proxy_url)
                if not data:
                    continue
                products = parse_items(data, raw_url, c)
                products = _filter_products(products, min_price, max_price, min_rating)
                all_products.extend(products)
                Actor.log.info(f'[{idx}/{total}] {c.upper()}: {len(products)} products')
        else:
            if not keywords:
                Actor.log.error('At least one keyword required')
                return

            countries = list(SITES.keys()) if search_all else ([country] if country in SITES else ['my'])
            sort_param = SORT_PARAMS.get(sort_by, '')
            total = len(keywords) * len(countries) * max_pages
            done = 0

            for kw in keywords:
                for c in countries:
                    for p in range(1, max_pages + 1):
                        done += 1
                        tld = SITES[c]
                        url = f'https://www.lazada.{tld}/catalog/?{urlencode({"q": kw, "page": p, "ajax": "true"})}'
                        if sort_param:
                            url += f'&{sort_param}'
                        data = await _fetch_json(url, proxy_url)
                        if not data:
                            continue
                        products = parse_items(data, kw, c)
                        products = _filter_products(products, min_price, max_price, min_rating)
                        all_products.extend(products)
                        if products:
                            Actor.log.info(f'[{done}/{total}] {kw}/{c.upper()} p{p}: {len(products)} products')

        if all_products:
            await Actor.push_data(all_products)
            Actor.log.info(f'Total: {len(all_products)} products')

        countries_with_data = list(set(p['country'] for p in all_products))
        if compare_prices and len(countries_with_data) > 1 and all_products:
            by_c = {}
            for x in all_products:
                by_c.setdefault(x['country'], []).append(x)
            summary = {}
            for c_code, items in by_c.items():
                prices = [x['price'] for x in items if x['price'] is not None]
                summary[c_code] = {
                    'count': len(items),
                    'minPrice': min(prices) if prices else None,
                    'maxPrice': max(prices) if prices else None,
                    'avgPrice': round(sum(prices) / len(prices), 2) if prices else None,
                }
            cheapest = min(all_products, key=lambda x: x['price'] if x['price'] is not None else float('inf'))
            all_p = [x['price'] for x in all_products if x['price'] is not None]
            await Actor.push_data({
                'type': 'price_comparison',
                'keyword': ', '.join(keywords) if mode == 'keyword' else 'URL mode',
                'totalProducts': len(all_products),
                'countries': list(by_c.keys()),
                'summary': summary,
                'cheapestCountry': cheapest['country'] if cheapest else None,
                'cheapestProduct': cheapest,
                'priceRange': {
                    'min': min(all_p) if all_p else None,
                    'max': max(all_p) if all_p else None,
                },
            })
            Actor.log.info(f'Comparison report for {len(by_c)} countries')

        Actor.log.info('Done')


if __name__ == '__main__':
    asyncio.run(main())
