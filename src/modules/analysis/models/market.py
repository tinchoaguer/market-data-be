from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .enums import Timeframe


@dataclass(frozen=True, slots=True)
class Candle:
    start_time: datetime
    end_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    base_volume: Decimal
    quote_volume: Decimal | None = None
    trade_count: int | None = None
    buy_volume: Decimal | None = None
    buy_quote_volume: Decimal | None = None


@dataclass(frozen=True, slots=True)
class OrderLevel:
    price: Decimal
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class OrderBook:
    bids: tuple[OrderLevel, ...]
    asks: tuple[OrderLevel, ...]


@dataclass(frozen=True, slots=True)
class CandleSeries:
    timeframe: Timeframe
    candles: tuple[Candle, ...]


@dataclass(frozen=True, slots=True)
class MarketData:
    symbol: str
    current_price: Decimal
    order_book: OrderBook
    series: tuple[CandleSeries, ...]

    def candles_for(self, timeframe: Timeframe = Timeframe.M15) -> tuple[Candle, ...]:
        for item in self.series:
            if item.timeframe == timeframe:
                return item.candles
        raise ValueError(f"no candle series for timeframe {timeframe.value}")

    @property
    def candles(self) -> tuple[Candle, ...]:
        """Primary analysis series (15m)."""
        return self.candles_for(Timeframe.M15)
