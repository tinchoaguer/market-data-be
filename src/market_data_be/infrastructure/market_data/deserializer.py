from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal

from market_data_be.modules.analysis.models import (
    Candle,
    CandleSeries,
    MarketData,
    OrderBook,
    OrderLevel,
    Timeframe,
)


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_optional_decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def candle_from_dict(data: Mapping[str, object]) -> Candle:
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
        trade_count=(
            None if data.get("trade_count") is None else int(data["trade_count"])  # type: ignore[arg-type]
        ),
        buy_volume=parse_optional_decimal(
            None if data.get("buy_volume") is None else str(data["buy_volume"])
        ),
        buy_quote_volume=parse_optional_decimal(
            None
            if data.get("buy_quote_volume") is None
            else str(data["buy_quote_volume"])
        ),
    )


def market_data_from_dict(data: Mapping[str, object]) -> MarketData:
    order_book = data["order_book"]
    if not isinstance(order_book, Mapping):
        raise TypeError("order_book must be a mapping")

    series_items = data["series"]
    if not isinstance(series_items, list):
        raise TypeError("series must be a list")

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
            for series in series_items
        ),
    )
