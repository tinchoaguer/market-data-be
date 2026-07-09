def symbol_to_fixture_filename(symbol: str) -> str:
    """Map 'BTC/USDT' to 'btc_usdt.json'. Raises ValueError for invalid format."""
    if "/" not in symbol:
        raise ValueError(f"invalid symbol format: {symbol!r}")

    parts = symbol.split("/")
    if len(parts) != 2:
        raise ValueError(f"invalid symbol format: {symbol!r}")

    base, quote = parts
    if not base or not quote:
        raise ValueError(f"invalid symbol format: {symbol!r}")

    return f"{base.lower()}_{quote.lower()}.json"
