"""URL path symbol parsing and validation."""


def parse_url_symbol(url_symbol: str) -> str:
    """Validate BASE-QUOTE URL path param and return internal BASE/QUOTE symbol.

    Raises ValueError for invalid format.
    """
    trimmed = url_symbol.strip()

    if "/" in trimmed:
        raise ValueError(
            "Invalid symbol format: expected BASE-QUOTE hyphen-separated pair"
        )

    parts = trimmed.split("-")
    if len(parts) != 2:
        raise ValueError(
            "Invalid symbol format: expected BASE-QUOTE hyphen-separated pair"
        )

    base, quote = parts
    if not base.strip() or not quote.strip():
        raise ValueError(
            "Invalid symbol format: expected BASE-QUOTE hyphen-separated pair"
        )

    return f"{base.strip().upper()}/{quote.strip().upper()}"
