import re


def normalize_price(raw: str | None) -> float | None:
    if not raw:
        return None
    raw = raw.strip()
    # Remove currency symbols and abbreviations: RM, Rp, S$, ₱, ₫, ฿, etc.
    raw = re.sub(r'[A-Za-z$\u20b1\u20ab\u0e3fRp\s]+', '', raw)
    # Handle Indonesian format: "150.000" (dot as thousands separator)
    # Detect if dots are thousands separators (followed by exactly 3 digits)
    if re.search(r'\.\d{3}[,\.]?', raw):
        # Remove dots (thousands separators), then replace comma with dot
        raw = raw.replace('.', '')
        raw = raw.replace(',', '.')
    else:
        # Standard format: replace comma with dot
        raw = raw.replace(',', '.')
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def normalize_sales(raw: str | None) -> int | None:
    if not raw:
        return None
    raw = raw.strip().lower()
    # Remove common suffixes
    raw = re.sub(r'(sold|terjual|đã bán|ขายแล้ว|已售| terjual)\s*', '', raw)
    raw = raw.strip()
    # Handle "1.5k", "2rb+", "5rb", etc.
    multiplier = 1
    if 'rb' in raw or 'k' in raw:
        multiplier = 1000
        raw = raw.replace('rb', '').replace('k', '').replace('+', '')
    # Remove any remaining non-numeric chars except dot/comma
    raw = re.sub(r'[^\d.,]', '', raw)
    raw = raw.replace(',', '.')
    try:
        value = float(raw)
        return int(value * multiplier)
    except (ValueError, TypeError):
        return None


def normalize_rating(raw: str | None) -> float | None:
    if not raw:
        return None
    raw = raw.strip()
    # Remove "/5" suffix if present
    raw = re.sub(r'\s*/?\s*5$', '', raw)
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def extract_currency(raw: str | None) -> str | None:
    if not raw:
        return None
    symbol_map = {
        'RM': 'MYR',
        'Rp': 'IDR',
        'S$': 'SGD',
        '₱': 'PHP',
        '₫': 'VND',
        '฿': 'THB',
        '$': 'USD',
    }
    raw = raw.strip()
    for symbol, code in symbol_map.items():
        if symbol in raw:
            return code
    return None


def normalize_product(product: dict) -> dict:
    raw_price = product.get('price')
    raw_original = product.get('originalPrice')
    raw_sales = product.get('sales')
    raw_rating = product.get('rating')

    normalized = dict(product)
    normalized['price'] = normalize_price(raw_price)
    normalized['originalPrice'] = normalize_price(raw_original)
    normalized['sales'] = normalize_sales(raw_sales)
    normalized['rating'] = normalize_rating(raw_rating)
    normalized['currency'] = extract_currency(raw_price) or product.get('currency')
    return normalized
