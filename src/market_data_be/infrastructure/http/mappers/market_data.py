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


def _format_datetime_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _optional_decimal_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _map_order_level(level: OrderLevel) -> OrderLevelResponse:
    return OrderLevelResponse(
        price=str(level.price),
        quantity=str(level.quantity),
    )


def _map_order_book(order_book: OrderBook) -> OrderBookResponse:
    return OrderBookResponse(
        bids=[_map_order_level(level) for level in order_book.bids],
        asks=[_map_order_level(level) for level in order_book.asks],
    )


def _map_candle(candle: Candle) -> CandleResponse:
    return CandleResponse(
        start_time=_format_datetime_utc(candle.start_time),
        end_time=_format_datetime_utc(candle.end_time),
        open=str(candle.open),
        high=str(candle.high),
        low=str(candle.low),
        close=str(candle.close),
        base_volume=str(candle.base_volume),
        quote_volume=_optional_decimal_str(candle.quote_volume),
        trade_count=candle.trade_count,
        buy_volume=_optional_decimal_str(candle.buy_volume),
        buy_quote_volume=_optional_decimal_str(candle.buy_quote_volume),
    )


def _map_candle_series(series: CandleSeries) -> CandleSeriesResponse:
    return CandleSeriesResponse(
        timeframe=series.timeframe.value,
        candles=[_map_candle(candle) for candle in series.candles],
    )


def map_market_data_to_response(market_data: MarketData) -> MarketDataResponse:
    return MarketDataResponse(
        symbol=market_data.symbol,
        current_price=str(market_data.current_price),
        order_book=_map_order_book(market_data.order_book),
        series=[_map_candle_series(item) for item in market_data.series],
    )
