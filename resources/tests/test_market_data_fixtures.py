"""Conformance tests for static MarketData JSON fixtures."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import sys
import types

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _ensure_market_data_be_packages() -> None:
    """Register setuptools package-dir mappings for sibling src layout."""
    src = PROJECT_ROOT / "src"
    if "market_data_be.modules" not in sys.modules:
        modules_pkg = types.ModuleType("market_data_be.modules")
        modules_pkg.__path__ = [str(src / "modules")]
        sys.modules["market_data_be.modules"] = modules_pkg
    if "market_data_be.modules.analysis" not in sys.modules:
        analysis_pkg = types.ModuleType("market_data_be.modules.analysis")
        analysis_pkg.__path__ = [str(src / "modules" / "analysis")]
        sys.modules["market_data_be.modules.analysis"] = analysis_pkg
    if "market_data_be.infrastructure" not in sys.modules:
        infrastructure_pkg = types.ModuleType("market_data_be.infrastructure")
        infrastructure_pkg.__path__ = [str(src / "infrastructure")]
        sys.modules["market_data_be.infrastructure"] = infrastructure_pkg
    if "market_data_be.infrastructure.market_data" not in sys.modules:
        market_data_pkg = types.ModuleType("market_data_be.infrastructure.market_data")
        market_data_pkg.__path__ = [str(src / "infrastructure" / "market_data")]
        sys.modules["market_data_be.infrastructure.market_data"] = market_data_pkg


_ensure_market_data_be_packages()

from market_data_be.infrastructure.market_data.deserializer import market_data_from_dict
from market_data_be.modules.analysis.models import (
    Candle,
    CandleSeries,
    MarketData,
    OrderBook,
    Timeframe,
)

FIXTURES_DIR = PROJECT_ROOT / "resources" / "market_data"
README_PATH = FIXTURES_DIR / "README.md"

FIXTURE_CASES = (
    ("btc_usdt.json", "BTC/USDT"),
    ("eth_usdt.json", "ETH/USDT"),
)

DECIMAL_ROOT_FIELDS = ("current_price",)
DECIMAL_CANDLE_FIELDS = ("open", "high", "low", "close", "base_volume")
DECIMAL_OPTIONAL_CANDLE_FIELDS = ("quote_volume", "buy_volume", "buy_quote_volume")
DECIMAL_ORDER_LEVEL_FIELDS = ("price", "quantity")


def load_fixture(filename: str) -> dict[str, object]:
    path = FIXTURES_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


def assert_decimal_strings(obj: object, path: str = "root") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            child_path = f"{path}.{key}"
            if key in DECIMAL_ROOT_FIELDS or key in DECIMAL_CANDLE_FIELDS:
                assert isinstance(value, str), f"{child_path} must be a JSON string"
            elif key in DECIMAL_OPTIONAL_CANDLE_FIELDS:
                assert value is None or isinstance(value, str), (
                    f"{child_path} must be a JSON string or null"
                )
            elif key in DECIMAL_ORDER_LEVEL_FIELDS:
                assert isinstance(value, str), f"{child_path} must be a JSON string"
            else:
                assert_decimal_strings(value, child_path)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            assert_decimal_strings(item, f"{path}[{index}]")


def m15_series(market_data: MarketData) -> CandleSeries:
    for series in market_data.series:
        if series.timeframe == Timeframe.M15:
            return series
    raise AssertionError("fixture missing M15 candle series")


def assert_ohlc_invariants(candle: Candle) -> None:
    assert candle.low <= candle.open <= candle.high
    assert candle.low <= candle.close <= candle.high
    assert candle.low <= candle.high


@pytest.mark.parametrize(("filename", "symbol"), FIXTURE_CASES)
def test_fixture_file_exists(filename: str, symbol: str) -> None:
    path = FIXTURES_DIR / filename
    assert path.is_file(), f"missing fixture file: {path}"


def test_readme_exists() -> None:
    assert README_PATH.is_file()


@pytest.mark.parametrize(("filename", "symbol"), FIXTURE_CASES)
def test_fixture_deserializes_to_market_data(filename: str, symbol: str) -> None:
    payload = load_fixture(filename)
    market_data = market_data_from_dict(payload)

    assert market_data.symbol == symbol
    assert isinstance(market_data.current_price, Decimal)
    assert isinstance(market_data.order_book, OrderBook)
    assert len(market_data.series) >= 1


@pytest.mark.parametrize(("filename", "symbol"), FIXTURE_CASES)
def test_decimal_fields_are_json_strings(filename: str, symbol: str) -> None:
    payload = load_fixture(filename)
    assert_decimal_strings(payload)


@pytest.mark.parametrize(("filename", "symbol"), FIXTURE_CASES)
def test_m15_series_has_at_least_thirty_contiguous_candles(
    filename: str, symbol: str
) -> None:
    market_data = market_data_from_dict(load_fixture(filename))
    series = m15_series(market_data)

    assert len(series.candles) >= 30
    for previous, current in zip(series.candles, series.candles[1:]):
        assert previous.end_time == current.start_time


@pytest.mark.parametrize(("filename", "symbol"), FIXTURE_CASES)
def test_order_book_depth_and_ordering(filename: str, symbol: str) -> None:
    market_data = market_data_from_dict(load_fixture(filename))
    order_book = market_data.order_book

    assert len(order_book.bids) >= 5
    assert len(order_book.asks) >= 5

    for left, right in zip(order_book.bids, order_book.bids[1:]):
        assert left.price > right.price

    for left, right in zip(order_book.asks, order_book.asks[1:]):
        assert left.price < right.price


@pytest.mark.parametrize(("filename", "symbol"), FIXTURE_CASES)
def test_current_price_matches_last_close_and_spread(
    filename: str, symbol: str
) -> None:
    market_data = market_data_from_dict(load_fixture(filename))
    last_close = m15_series(market_data).candles[-1].close
    best_bid = market_data.order_book.bids[0].price
    best_ask = market_data.order_book.asks[0].price

    assert market_data.current_price == last_close
    assert best_bid < market_data.current_price < best_ask


@pytest.mark.parametrize(("filename", "symbol"), FIXTURE_CASES)
def test_candle_ohlc_invariants(filename: str, symbol: str) -> None:
    market_data = market_data_from_dict(load_fixture(filename))
    for series in market_data.series:
        for candle in series.candles:
            assert_ohlc_invariants(candle)
