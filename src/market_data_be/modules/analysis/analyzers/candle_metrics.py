"""Pure helpers to derive metrics from :class:`Candle` series and order books."""

import math
from collections.abc import Sequence
from statistics import pstdev
from typing import Any

from ..models.market import Candle, OrderBook


def _num(value: Any) -> float:
    return float(value)


def _book_sides(order_book: OrderBook | dict) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    if isinstance(order_book, OrderBook):
        bids = [(_num(level.price), _num(level.quantity)) for level in order_book.bids]
        asks = [(_num(level.price), _num(level.quantity)) for level in order_book.asks]
        return bids, asks

    bids = [(_num(price), _num(qty)) for price, qty in (order_book.get("bids") or [])]
    asks = [(_num(price), _num(qty)) for price, qty in (order_book.get("asks") or [])]
    return bids, asks


def latest_close(candles: Sequence[Candle]) -> float:
    if not candles:
        raise ValueError("candles must not be empty")
    return _num(candles[-1].close)


def close_n_bars_ago(candles: Sequence[Candle], n: int) -> float:
    if n < 1:
        raise ValueError("n must be >= 1")
    if len(candles) <= n:
        raise ValueError(f"need at least {n + 1} candles, got {len(candles)}")
    return _num(candles[-(n + 1)].close)


def true_range(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def _field_value(candle: Candle, field: str) -> float:
    return _num(getattr(candle, field))


def sma(candles: Sequence[Candle], period: int, field: str = "close") -> float:
    if period < 1:
        raise ValueError("period must be >= 1")
    if len(candles) < period:
        raise ValueError(f"need at least {period} candles for SMA({period})")
    window = candles[-period:]
    return sum(_field_value(k, field) for k in window) / period


def sma_slope(candles: Sequence[Candle], period: int, lookback: int = 5) -> float:
    if lookback < 1:
        raise ValueError("lookback must be >= 1")
    if len(candles) < period + lookback:
        raise ValueError(f"need at least {period + lookback} candles for SMA slope")
    current = sma(candles, period)
    past = sma(candles[:-lookback], period)
    return current - past


def candle_range(candle: Candle) -> float:
    return _num(candle.high) - _num(candle.low)


def relative_volume(candles: Sequence[Candle], period: int = 20) -> float:
    if period < 1:
        raise ValueError("period must be >= 1")
    if len(candles) < period:
        raise ValueError(f"need at least {period} candles for relative volume")
    avg_vol = sma(candles, period, "base_volume")
    if avg_vol == 0:
        return 0.0
    return _num(candles[-1].base_volume) / avg_vol


def relative_trades(candles: Sequence[Candle], period: int = 20) -> float:
    if period < 1:
        raise ValueError("period must be >= 1")
    if len(candles) < period:
        raise ValueError(f"need at least {period} candles for relative trades")
    avg_trades = sma(candles, period, "trade_count")
    if avg_trades == 0:
        return 0.0
    last_trades = candles[-1].trade_count
    if last_trades is None:
        return 0.0
    return last_trades / avg_trades


def taker_buy_ratio(candles: Sequence[Candle], last_n: int = 3) -> float:
    if last_n < 1:
        raise ValueError("last_n must be >= 1")
    if len(candles) < last_n:
        raise ValueError(f"need at least {last_n} candles for taker buy ratio")
    window = candles[-last_n:]
    total_vol = sum(_num(c.base_volume) for c in window)
    if total_vol == 0:
        return 0.5
    buy_vol = sum(_num(c.buy_volume or 0) for c in window)
    return buy_vol / total_vol


def higher_highs_higher_lows(candles: Sequence[Candle], window: int = 10) -> bool:
    if window < 2:
        raise ValueError("window must be >= 2")
    if len(candles) < window:
        raise ValueError(f"need at least {window} candles for HH/HL check")
    segment = candles[-window:]
    for i in range(1, len(segment)):
        if _num(segment[i].high) <= _num(segment[i - 1].high) or _num(segment[i].low) <= _num(
            segment[i - 1].low
        ):
            return False
    return True


def lower_highs_lower_lows(candles: Sequence[Candle], window: int = 10) -> bool:
    if window < 2:
        raise ValueError("window must be >= 2")
    if len(candles) < window:
        raise ValueError(f"need at least {window} candles for LH/LL check")
    segment = candles[-window:]
    for i in range(1, len(segment)):
        if _num(segment[i].high) >= _num(segment[i - 1].high) or _num(segment[i].low) >= _num(
            segment[i - 1].low
        ):
            return False
    return True


def direction_changes(candles: Sequence[Candle], window: int = 8) -> int:
    if window < 2:
        raise ValueError("window must be >= 2")
    if len(candles) < window + 1:
        raise ValueError(f"need at least {window + 1} candles for direction changes")
    segment = candles[-(window + 1) :]
    signs: list[int] = []
    for i in range(1, len(segment)):
        diff = _num(segment[i].close) - _num(segment[i - 1].close)
        if diff > 0:
            signs.append(1)
        elif diff < 0:
            signs.append(-1)
    changes = 0
    for i in range(1, len(signs)):
        if signs[i] != signs[i - 1]:
            changes += 1
    return changes


def sma_cross_count(candles: Sequence[Candle], period: int = 20, window: int = 10) -> int:
    if len(candles) < period + window:
        raise ValueError(f"need at least {period + window} candles for SMA cross count")
    full = candles[-(period + window) :]
    sides: list[int] = []
    for i in range(period, len(full)):
        sub = full[: i + 1]
        ma = sma(sub, period)
        close = _num(sub[-1].close)
        if close > ma:
            sides.append(1)
        elif close < ma:
            sides.append(-1)
        else:
            sides.append(0)
    crosses = 0
    for i in range(1, len(sides)):
        if sides[i] != sides[i - 1] and sides[i] != 0 and sides[i - 1] != 0:
            crosses += 1
    return crosses


def atr(candles: Sequence[Candle], period: int = 14) -> float:
    if period < 1:
        raise ValueError("period must be >= 1")
    if len(candles) < period + 1:
        raise ValueError(f"need at least {period + 1} candles for ATR({period})")

    window = candles[-(period + 1) :]
    ranges = [
        true_range(
            _num(window[i].high),
            _num(window[i].low),
            _num(window[i - 1].close),
        )
        for i in range(1, len(window))
    ]
    return sum(ranges) / len(ranges)


def atr_series(candles: Sequence[Candle], period: int = 14) -> list[float]:
    """Per-bar ATR values (simple average TR over rolling window)."""
    if len(candles) < period + 1:
        raise ValueError(f"need at least {period + 1} candles for ATR series")
    values: list[float] = []
    for end in range(period + 1, len(candles) + 1):
        window = candles[end - (period + 1) : end]
        ranges = [
            true_range(
                _num(window[i].high),
                _num(window[i].low),
                _num(window[i - 1].close),
            )
            for i in range(1, len(window))
        ]
        values.append(sum(ranges) / len(ranges))
    return values


def returns_volatility(candles: Sequence[Candle], period: int = 20) -> float:
    if period < 2:
        raise ValueError("period must be >= 2")
    if len(candles) < period + 1:
        raise ValueError(f"need at least {period + 1} candles for volatility({period})")

    window = candles[-(period + 1) :]
    log_returns = [
        math.log(_num(window[i].close) / _num(window[i - 1].close))
        for i in range(1, len(window))
        if _num(window[i - 1].close) > 0 and _num(window[i].close) > 0
    ]
    if len(log_returns) < 2:
        return 0.0
    return pstdev(log_returns)


def _wilder_smooth(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        raise ValueError(f"need at least {period} values for Wilder smooth")
    smoothed = [sum(values[:period]) / period]
    for value in values[period:]:
        smoothed.append(smoothed[-1] - (smoothed[-1] / period) + value)
    return smoothed


def wilder_di_adx(candles: Sequence[Candle], period: int = 14) -> tuple[float, float, float]:
    """Return (adx, plus_di, minus_di) for the latest bar using Wilder's method."""
    if period < 2:
        raise ValueError("period must be >= 2")
    min_len = period * 2 + 1
    if len(candles) < min_len:
        raise ValueError(f"need at least {min_len} candles for ADX({period})")

    tr_list: list[float] = []
    plus_dm_list: list[float] = []
    minus_dm_list: list[float] = []

    for i in range(1, len(candles)):
        cur = candles[i]
        prev = candles[i - 1]
        up_move = _num(cur.high) - _num(prev.high)
        down_move = _num(prev.low) - _num(cur.low)

        plus_dm = up_move if up_move > down_move and up_move > 0 else 0.0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0.0

        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
        tr_list.append(
            true_range(_num(cur.high), _num(cur.low), _num(prev.close))
        )

    smooth_tr = _wilder_smooth(tr_list, period)
    smooth_plus = _wilder_smooth(plus_dm_list, period)
    smooth_minus = _wilder_smooth(minus_dm_list, period)

    dx_values: list[float] = []
    plus_di_values: list[float] = []
    minus_di_values: list[float] = []

    for tr_s, p_s, m_s in zip(smooth_tr, smooth_plus, smooth_minus):
        if tr_s == 0:
            plus_di_values.append(0.0)
            minus_di_values.append(0.0)
            dx_values.append(0.0)
            continue
        pdi = 100.0 * p_s / tr_s
        mdi = 100.0 * m_s / tr_s
        plus_di_values.append(pdi)
        minus_di_values.append(mdi)
        denom = pdi + mdi
        dx_values.append(0.0 if denom == 0 else 100.0 * abs(pdi - mdi) / denom)

    if len(dx_values) < period:
        raise ValueError("insufficient data to compute ADX")

    adx_values = _wilder_smooth(dx_values, period)
    return adx_values[-1], plus_di_values[-1], minus_di_values[-1]


def total_volume(candles: Sequence[Candle], last_n: int = 1) -> float:
    if last_n < 1:
        raise ValueError("last_n must be >= 1")
    if not candles:
        return 0.0
    return sum(_num(k.base_volume) for k in candles[-last_n:])


def order_book_imbalance(order_book: OrderBook | dict[str, list]) -> float:
    """Return (bid_vol - ask_vol) / (bid_vol + ask_vol), or 0 if empty."""
    bids, asks = _book_sides(order_book)
    bid_vol = sum(qty for _, qty in bids)
    ask_vol = sum(qty for _, qty in asks)
    total = bid_vol + ask_vol
    if total == 0:
        return 0.0
    return (bid_vol - ask_vol) / total


def book_top_depth_base(order_book: OrderBook | dict[str, list], levels: int = 10) -> float:
    """Sum of top-N bid and ask quantities in base asset."""
    if levels < 1:
        raise ValueError("levels must be >= 1")
    bids, asks = _book_sides(order_book)
    return sum(qty for _, qty in bids[:levels]) + sum(qty for _, qty in asks[:levels])


def spread_bps(order_book: OrderBook | dict[str, list]) -> float:
    """Bid-ask spread in basis points from top-of-book, or 0 if unavailable."""
    bids, asks = _book_sides(order_book)
    if not bids or not asks:
        return 0.0
    best_bid = bids[0][0]
    best_ask = asks[0][0]
    mid = (best_bid + best_ask) / 2
    if mid <= 0:
        return 0.0
    return (best_ask - best_bid) / mid * 10_000
