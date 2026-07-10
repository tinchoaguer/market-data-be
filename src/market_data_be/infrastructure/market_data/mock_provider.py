import json
from pathlib import Path

from market_data_be.modules.analysis.models.market import MarketData

from .deserializer import market_data_from_dict
from .errors import MarketDataDeserializationError, MarketDataNotFoundError
from .symbol_resolver import symbol_to_fixture_filename

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_FIXTURES_DIR = _PROJECT_ROOT / "resources" / "market_data"


class MockMarketDataProvider:
    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self._fixtures_dir = fixtures_dir if fixtures_dir is not None else _DEFAULT_FIXTURES_DIR

    def get_market_data(self, symbol: str) -> MarketData:
        try:
            filename = symbol_to_fixture_filename(symbol)
        except ValueError as exc:
            raise MarketDataNotFoundError(symbol) from exc

        fixture_path = self._fixtures_dir / filename
        if not fixture_path.is_file():
            raise MarketDataNotFoundError(symbol, fixture_path)

        try:
            payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MarketDataDeserializationError(symbol, exc) from exc

        try:
            return market_data_from_dict(payload)
        except Exception as exc:
            raise MarketDataDeserializationError(symbol, exc) from exc
