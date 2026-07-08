import json
from pathlib import Path

import pytest

from market_data_be.infrastructure.market_data.errors import (
    MarketDataDeserializationError,
    MarketDataNotFoundError,
)
from market_data_be.infrastructure.market_data.mock_provider import MockMarketDataProvider

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURES_DIR = PROJECT_ROOT / "resources" / "market_data"


@pytest.fixture
def provider() -> MockMarketDataProvider:
    return MockMarketDataProvider()


def test_get_market_data_btc_usdt(provider: MockMarketDataProvider) -> None:
    market_data = provider.get_market_data("BTC/USDT")
    assert market_data.symbol == "BTC/USDT"


def test_get_market_data_eth_usdt(provider: MockMarketDataProvider) -> None:
    market_data = provider.get_market_data("ETH/USDT")
    assert market_data.symbol == "ETH/USDT"


def test_get_market_data_not_found_invalid_symbol(
    provider: MockMarketDataProvider,
) -> None:
    with pytest.raises(MarketDataNotFoundError) as exc_info:
        provider.get_market_data("BTC-USDT")

    assert exc_info.value.symbol == "BTC-USDT"


def test_get_market_data_not_found_missing_fixture(
    provider: MockMarketDataProvider,
) -> None:
    with pytest.raises(MarketDataNotFoundError) as exc_info:
        provider.get_market_data("SOL/USDT")

    assert exc_info.value.symbol == "SOL/USDT"
    assert exc_info.value.path is not None


def test_get_market_data_deserialization_error(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    malformed_path = fixtures_dir / "btc_usdt.json"
    malformed_path.write_text("{ invalid json", encoding="utf-8")

    provider = MockMarketDataProvider(fixtures_dir=fixtures_dir)

    with pytest.raises(MarketDataDeserializationError) as exc_info:
        provider.get_market_data("BTC/USDT")

    assert exc_info.value.symbol == "BTC/USDT"
    assert exc_info.value.cause is not None


def test_get_market_data_deserialization_error_invalid_payload(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    malformed_path = fixtures_dir / "btc_usdt.json"
    malformed_path.write_text(
        json.dumps({"symbol": "BTC/USDT"}),
        encoding="utf-8",
    )

    provider = MockMarketDataProvider(fixtures_dir=fixtures_dir)

    with pytest.raises(MarketDataDeserializationError) as exc_info:
        provider.get_market_data("BTC/USDT")

    assert exc_info.value.symbol == "BTC/USDT"
    assert exc_info.value.cause is not None


def test_default_fixtures_dir_points_to_project_resources() -> None:
    provider = MockMarketDataProvider()
    assert provider._fixtures_dir == DEFAULT_FIXTURES_DIR
