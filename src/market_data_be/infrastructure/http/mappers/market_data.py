from datetime import datetime, timezone
from decimal import Decimal

from market_data_be.infrastructure.http.dtos.market_data import (
    CandleResponse,
    CandleSeriesResponse,
    MarketDataResponse,
    OrderBookResponse,
    OrderLevelResponse,
)
from market_data_be.modules.analysis.models.market import (
    Candle,
    CandleSeries,
    MarketData,
    OrderBook,
    OrderLevel,
)


def _decimal_to_str(value: Decimal) -> str:
    return str(value)


def _optional_decimal_to_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _to_iso8601_utc(value: datetime) -> str:
    if value.tzinfo is None:
        aware = value.replace(tzinfo=timezone.utc)
    else:
        aware = value.astimezone(timezone.utc)
    return aware.isoformat().replace("+00:00", "Z")


def _map_order_level(level: OrderLevel) -> OrderLevelResponse:
    return OrderLevelResponse(
        price=_decimal_to_str(level.price),
        quantity=_decimal_to_str(level.quantity),
    )


def _map_order_book(order_book: OrderBook) -> OrderBookResponse:
    return OrderBookResponse(
        bids=[_map_order_level(level) for level in order_book.bids],
        asks=[_map_order_level(level) for level in order_book.asks],
    )


def _map_candle(candle: Candle) -> CandleResponse:
    return CandleResponse(
        start_time=_to_iso8601_utc(candle.start_time),
        end_time=_to_iso8601_utc(candle.end_time),
        open=_decimal_to_str(candle.open),
        high=_decimal_to_str(candle.high),
        low=_decimal_to_str(candle.low),
        close=_decimal_to_str(candle.close),
        base_volume=_decimal_to_str(candle.base_volume),
        quote_volume=_optional_decimal_to_str(candle.quote_volume),
        trade_count=candle.trade_count,
        buy_volume=_optional_decimal_to_str(candle.buy_volume),
        buy_quote_volume=_optional_decimal_to_str(candle.buy_quote_volume),
    )


def _map_candle_series(series: CandleSeries) -> CandleSeriesResponse:
    return CandleSeriesResponse(
        timeframe=series.timeframe.value,
        candles=[_map_candle(candle) for candle in series.candles],
    )


def map_market_data_to_response(market_data: MarketData) -> MarketDataResponse:
    return MarketDataResponse(
        symbol=market_data.symbol,
        current_price=_decimal_to_str(market_data.current_price),
        order_book=_map_order_book(market_data.order_book),
        series=[_map_candle_series(item) for item in market_data.series],
    )
