from pathlib import Path


class MarketDataNotFoundError(Exception):
    def __init__(self, symbol: str, path: Path | None = None) -> None:
        self.symbol = symbol
        self.path = path
        message = f"market data not found for symbol {symbol!r}"
        if path is not None:
            message = f"{message} (path: {path})"
        super().__init__(message)


class MarketDataDeserializationError(Exception):
    def __init__(self, symbol: str, cause: Exception) -> None:
        self.symbol = symbol
        self.cause = cause
        super().__init__(
            f"failed to deserialize market data for symbol {symbol!r}: {cause}"
        )
