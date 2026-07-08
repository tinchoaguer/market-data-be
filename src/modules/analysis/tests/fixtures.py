"""Shared test fixtures for engine unit tests."""

from datetime import datetime, timezone
from decimal import Decimal

from market_data_be.modules.analysis.models import (
    Candle,
    CandleSeries,
    MarketData,
    OrderBook,
    OrderLevel,
    PortfolioState,
    Timeframe,
)

_TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candle(
    open_: float,
    high: float,
    low: float,
    close: float,
    *,
    base_volume: float = 100.0,
    trade_count: int = 10,
    taker_ratio: float = 0.5,
) -> Candle:
    buy_volume = base_volume * taker_ratio
    return Candle(
        start_time=_TS,
        end_time=_TS,
        open=Decimal(str(open_)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        base_volume=Decimal(str(base_volume)),
        quote_volume=Decimal(str(base_volume * close)),
        trade_count=trade_count,
        buy_volume=Decimal(str(buy_volume)),
        buy_quote_volume=Decimal(str(buy_volume * close)),
    )


def _order_book(
    bids: list[tuple[str, str]] | None = None,
    asks: list[tuple[str, str]] | None = None,
) -> OrderBook:
    def levels(pairs: list[tuple[str, str]]) -> tuple[OrderLevel, ...]:
        return tuple(OrderLevel(price=Decimal(p), quantity=Decimal(q)) for p, q in pairs)

    return OrderBook(
        bids=levels(bids or []),
        asks=levels(asks or []),
    )


def _market_data(
    candles: list[Candle],
    *,
    symbol: str = "BTCUSDT",
    price: float | None = None,
    order_book: OrderBook | None = None,
    timeframe: Timeframe = Timeframe.M15,
) -> MarketData:
    close = float(candles[-1].close) if candles else 0.0
    return MarketData(
        symbol=symbol,
        current_price=Decimal(str(price if price is not None else close)),
        order_book=order_book
        or _order_book(
            bids=[("100", "10")],
            asks=[("100.05", "10")],
        ),
        series=(CandleSeries(timeframe=timeframe, candles=tuple(candles)),),
    )


def _portfolio_state(
    *,
    total_value: float = 10_000.0,
    allocations: list[tuple[str, float]] | None = None,
) -> PortfolioState:
    return PortfolioState(
        total_value=total_value,
        allocations=tuple(allocations or ()),
    )
