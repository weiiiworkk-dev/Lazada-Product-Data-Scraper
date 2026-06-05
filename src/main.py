import asyncio
import json
import re
from urllib.parse import urlencode, urlparse

from apify import Actor
from curl_cffi.requests import AsyncSession

SITES = {'sg': 'sg', 'my': 'com.my', 'th': 'co.th', 'ph': 'com.ph', 'id': 'co.id', 'vn': 'vn'}
CURRENCY_MAP = {'sg': 'SGD', 'my': 'MYR', 'th': 'THB', 'ph': 'PHP', 'id': 'IDR', 'vn': 'VND'}
SYMBOL_MAP = {'S$': 'SGD', 'RM': 'MYR', '฿': 'THB', '₱': 'PHP', 'Rp': 'IDR', '₫': 'VND', '$': 'USD'}
SORT_PARAMS = {'relevance': '', 'priceAsc': 'sort=priceasc', 'priceDesc': 'sort=pricedesc',
               'ratingDesc': 'sort=rating', 'newest': 'sort=newest', 'soldDesc': 'sort=sold'}
MAX_RETRIES = 3
UA = 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 Chrome/124.0.6422.113 Mobile Safari/537.36'


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
            'reviewCount': _s(i.get('review')),
            'sales': _i(i.get('sold')),
            'location': i.get('location', ''),
            'sellerName': i.get('sellerName', ''),
            'sellerId': i.get('sellerId', ''),
            'brandName': i.get('brandName', ''),
            'isLazMall': bool(i.get('premiumBrand', False) or i.get('isLazMall', False)),
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


def _s(v):
    if v is None:
        return None
    v = str(v).strip()
    return v if v else None


def _country_from_url(url):
    host = urlparse(url).hostname or ''
    for code, tld in SITES.items():
        if f'lazada.{tld}' in host:
            return code
    return None


def _filter_products(products, min_price, max_price, min_rating):
    if min_price is not None:
        products = [x for x in products if x['price'] is not None and x['price'] >= min_price]
    if max_price is not None:
        products = [x for x in products if x['price'] is not None and x['price'] <= max_price]
    if min_rating is not None:
        products = [x for x in products if x['rating'] is not None and x['rating'] >= min_rating]
    return products


async def _bootstrap_session(session, tld):
    try:
        resp = await session.get(f'https://www.lazada.{tld}/', impersonate='chrome124', timeout=15)
        Actor.log.info(f'Homepage {tld}: HTTP {resp.status_code}')
    except Exception as e:
        Actor.log.warning(f'Homepage visit failed for {tld}: {e}')


def _extract_punish_url(html):
    import re
    m = re.search(r"window\.location\.replace\(['\"]([^'\"]+)['\"]\)", html)
    if m:
        return m.group(1)
    return None


async def _solve_challenge(session, html, origin_url):
    punish_url = _extract_punish_url(html)
    if not punish_url:
        Actor.log.warning(f'Could not extract punish URL from challenge response')
        return False
    if punish_url.startswith('//'):
        punish_url = 'https:' + punish_url
    try:
        resp = await session.get(punish_url, impersonate='chrome124', timeout=15)
        Actor.log.info(f'Challenge solved: HTTP {resp.status_code}')
        return True
    except Exception as e:
        Actor.log.warning(f'Challenge solve failed: {e}')
        return False


async def _fetch_with_session(session, url, referer=None, retries=MAX_RETRIES):
    headers = {
        'User-Agent': UA,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'x-requested-with': 'XMLHttpRequest',
    }
    if referer:
        headers['Referer'] = referer
    for attempt in range(1, retries + 1):
        try:
            resp = await session.get(url, impersonate='chrome124', timeout=30, headers=headers)
            if resp.status_code == 429:
                await asyncio.sleep(2 ** attempt)
                continue
            if resp.status_code != 200:
                Actor.log.warning(f'HTTP {resp.status_code} — retry {attempt}/{retries}')
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)
                continue
            raw = resp.text
            if not raw or len(raw) < 50:
                Actor.log.warning(f'Response too short ({len(raw)}B) — retry {attempt}/{retries}')
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)
                continue
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                if attempt == 1:
                    solved = await _solve_challenge(session, raw, url)
                    if solved:
                        continue
                preview = raw[:120].replace('\n', ' ')
                Actor.log.warning(f'Non-JSON response ({preview}...) — retry {attempt}/{retries}')
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)
                continue
        except Exception as e:
            Actor.log.warning(f'Request failed: {e} — retry {attempt}/{retries}')
            if attempt < retries:
                await asyncio.sleep(2 ** attempt)
    Actor.log.error(f'All {retries} retries exhausted for URL: {url}')
    return None


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

        proxy_kwargs = {}
        if proxy_url:
            proxy_kwargs['proxies'] = {"http": proxy_url, "https": proxy_url}

        all_products = []

        async with AsyncSession(**proxy_kwargs) as session:
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
                    tld = SITES[c]
                    await _bootstrap_session(session, tld)
                    sep = '&' if '?' in raw_url else '?'
                    ajax_url = f'{raw_url}{sep}ajax=true'
                    data = await _fetch_with_session(session, ajax_url, referer=f'https://www.lazada.{tld}/')
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
                seen_tlds = set()
                sort_param = SORT_PARAMS.get(sort_by, '')
                total = len(keywords) * len(countries) * max_pages
                done = 0

                for kw in keywords:
                    for c in countries:
                        tld = SITES[c]
                        if tld not in seen_tlds:
                            await _bootstrap_session(session, tld)
                            seen_tlds.add(tld)
                        for p in range(1, max_pages + 1):
                            done += 1
                            url = f'https://www.lazada.{tld}/catalog/?{urlencode({"q": kw, "page": p, "ajax": "true"})}'
                            if sort_param:
                                url += f'&{sort_param}'
                            data = await _fetch_with_session(session, url, referer=f'https://www.lazada.{tld}/')
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
