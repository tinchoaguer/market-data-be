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


def _ensure_market_data_be_modules() -> None:
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


_ensure_market_data_be_modules()

from market_data_be.modules.analysis.models import (
    Candle,
    CandleSeries,
    MarketData,
    OrderBook,
    OrderLevel,
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


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_optional_decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def candle_from_dict(data: dict[str, object]) -> Candle:
    return Candle(
        start_time=parse_datetime(str(data["start_time"])),
        end_time=parse_datetime(str(data["end_time"])),
        open=Decimal(str(data["open"])),
        high=Decimal(str(data["high"])),
        low=Decimal(str(data["low"])),
        close=Decimal(str(data["close"])),
        base_volume=Decimal(str(data["base_volume"])),
        quote_volume=parse_optional_decimal(
            None if data.get("quote_volume") is None else str(data["quote_volume"])
        ),
        trade_count=None if data.get("trade_count") is None else int(data["trade_count"]),  # type: ignore[arg-type]
        buy_volume=parse_optional_decimal(
            None if data.get("buy_volume") is None else str(data["buy_volume"])
        ),
        buy_quote_volume=parse_optional_decimal(
            None
            if data.get("buy_quote_volume") is None
            else str(data["buy_quote_volume"])
        ),
    )


def market_data_from_dict(data: dict[str, object]) -> MarketData:
    order_book = data["order_book"]
    assert isinstance(order_book, dict)
    series_items = data["series"]
    assert isinstance(series_items, list)

    return MarketData(
        symbol=str(data["symbol"]),
        current_price=Decimal(str(data["current_price"])),
        order_book=OrderBook(
            bids=tuple(
                OrderLevel(
                    Decimal(str(level["price"])),
                    Decimal(str(level["quantity"])),
                )
                for level in order_book["bids"]  # type: ignore[index]
            ),
            asks=tuple(
                OrderLevel(
                    Decimal(str(level["price"])),
                    Decimal(str(level["quantity"])),
                )
                for level in order_book["asks"]  # type: ignore[index]
            ),
        ),
        series=tuple(
            CandleSeries(
                timeframe=Timeframe(str(series["timeframe"])),
                candles=tuple(
                    candle_from_dict(candle)  # type: ignore[arg-type]
                    for candle in series["candles"]  # type: ignore[index]
                ),
            )
            for series in series_items  # type: ignore[union-attr]
        ),
    )


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
