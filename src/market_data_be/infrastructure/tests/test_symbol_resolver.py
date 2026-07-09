import pytest

from market_data_be.infrastructure.market_data.symbol_resolver import (
    symbol_to_fixture_filename,
)


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("BTC/USDT", "btc_usdt.json"),
        ("ETH/USDT", "eth_usdt.json"),
        ("btc/usdt", "btc_usdt.json"),
    ],
)
def test_symbol_to_fixture_filename_valid(symbol: str, expected: str) -> None:
    assert symbol_to_fixture_filename(symbol) == expected


@pytest.mark.parametrize(
    "symbol",
    [
        "BTC-USDT",
        "BTC",
        "",
        "BTC/USDT/EXTRA",
        "/USDT",
        "BTC/",
    ],
)
def test_symbol_to_fixture_filename_invalid(symbol: str) -> None:
    with pytest.raises(ValueError):
        symbol_to_fixture_filename(symbol)
