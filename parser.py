from playwright.async_api import Page


async def extract_product_links(page: Page) -> list[str]:
    urls = await page.eval_on_selector_all(
        'div[data-qa-locator="product-item"] a[href*=".html"]',
        'els => els.map(el => el.href)',
    )
    return list(set(urls))


async def extract_product_data(page: Page) -> dict:
    name = await _get_attribute(page, 'h1', 'innerText')
    price_text = await _get_attribute(page, 'span.pdp-price', 'innerText')
    original_text = await _get_attribute(page, 'span.pdp-price-original', 'innerText')

    rating = await _get_attribute(page, 'span.pdp-review-rating', 'innerText')
    sales = await _get_attribute(page, 'span.pdp-review-sold', 'innerText')

    location = await _get_attribute(page, 'span.pdp-seller-info-location', 'innerText')
    seller = await _get_attribute(page, 'a.pdp-seller-name', 'innerText')

    image = await page.eval_on_selector(
        'div.pdp-gallery img.pdp-gallery__main-image',
        'el => el.src',
    )

    specifications = await _extract_specs(page)

    return {
        'title': name,
        'price': price_text,
        'originalPrice': original_text,
        'rating': rating,
        'sales': sales,
        'location': location,
        'sellerName': seller,
        'imageUrl': image,
        'specifications': specifications,
    }


async def extract_search_results(page: Page) -> list[dict]:
    products = await page.eval_on_selector_all(
        'div[data-qa-locator="product-item"]',
        '''
        (cards) => cards.map(card => {
            const titleEl = card.querySelector('a[href*=".html"]');
            const priceEl = card.querySelector('span.ooOxS');
            const originalEl = card.querySelector('span[class*="original"]');
            const ratingEl = card.querySelector('div.rate i');
            const salesEl = card.querySelector('span[class*="sale"]');
            const imageEl = card.querySelector('img[class*="image"]');
            return {
                title: titleEl?.innerText?.trim() || null,
                url: titleEl?.href || null,
                price: priceEl?.innerText?.trim() || null,
                originalPrice: originalEl?.innerText?.trim() || null,
                rating: ratingEl?.parentElement?.innerText?.trim() || null,
                sales: salesEl?.innerText?.trim() || null,
                imageUrl: imageEl?.src || null,
            };
        })
        ''',
    )
    return products


async def has_next_page(page: Page) -> bool:
    next_disabled = await page.eval_on_selector(
        'li.ant-pagination-next:not(.ant-pagination-disabled)',
        'el => true',
        default_value=False,
    )
    return bool(next_disabled)


async def get_current_page(page: Page) -> int:
    active = await page.eval_on_selector(
        'li.ant-pagination-item-active',
        'el => parseInt(el.innerText, 10)',
        default_value=1,
    )
    return active


async def _get_attribute(page: Page, selector: str, attr: str) -> str | None:
    try:
        value = await page.eval_on_selector(selector, f'el => el["{attr}"]?.trim() || null')
        return value
    except Exception:
        return None


async def _extract_specs(page: Page) -> dict:
    try:
        specs = await page.eval_on_selector_all(
            'div.pdp-product-table tr',
            '''
            (rows) => Object.fromEntries(
                rows.map(row => {
                    const cells = row.querySelectorAll('td');
                    return cells.length === 2
                        ? [cells[0].innerText?.trim(), cells[1].innerText?.trim()]
                        : null;
                }).filter(Boolean)
            )
            ''',
        )
        return specs or {}
    except Exception:
        return {}
