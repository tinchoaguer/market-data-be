from pydantic import BaseModel


class OrderLevelResponse(BaseModel):
    price: str
    quantity: str


class OrderBookResponse(BaseModel):
    bids: list[OrderLevelResponse]
    asks: list[OrderLevelResponse]


class CandleResponse(BaseModel):
    start_time: str
    end_time: str
    open: str
    high: str
    low: str
    close: str
    base_volume: str
    quote_volume: str | None = None
    trade_count: int | None = None
    buy_volume: str | None = None
    buy_quote_volume: str | None = None


class CandleSeriesResponse(BaseModel):
    timeframe: str
    candles: list[CandleResponse]


class MarketDataResponse(BaseModel):
    symbol: str
    current_price: str
    order_book: OrderBookResponse
    series: list[CandleSeriesResponse]
