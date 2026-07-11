import ast
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from market_data_be.application.use_cases.get_market_data import GetMarketData
from market_data_be.infrastructure.http.app import create_app
from market_data_be.infrastructure.http.dtos.market_data import MarketDataResponse
from market_data_be.infrastructure.http.validation.symbol import parse_url_symbol

APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "application"
MODULES_ROOT = Path(__file__).resolve().parents[2] / "modules"
FORBIDDEN_PREFIXES = ("fastapi", "pydantic", "uvicorn")

REQUIRED_CANDLE_FIELDS = (
    "start_time",
    "end_time",
    "open",
    "high",
    "low",
    "close",
    "base_volume",
)
DECIMAL_CANDLE_FIELDS = (
    "open",
    "high",
    "low",
    "close",
    "base_volume",
)
OPTIONAL_DECIMAL_CANDLE_FIELDS = (
    "quote_volume",
    "buy_volume",
    "buy_quote_volume",
)


def _assert_iso8601_utc(value: str) -> None:
    assert isinstance(value, str)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


def _assert_market_data_body(body: dict[str, object], expected_symbol: str) -> None:
    assert body["symbol"] == expected_symbol
    assert isinstance(body["current_price"], str)

    order_book = body["order_book"]
    assert isinstance(order_book, dict)
    bids = order_book["bids"]
    asks = order_book["asks"]
    assert isinstance(bids, list) and len(bids) > 0
    assert isinstance(asks, list) and len(asks) > 0
    for level in [*bids, *asks]:
        assert isinstance(level["price"], str)
        assert isinstance(level["quantity"], str)

    series = body["series"]
    assert isinstance(series, list) and len(series) > 0
    for series_item in series:
        assert isinstance(series_item["timeframe"], str)
        candles = series_item["candles"]
        assert isinstance(candles, list) and len(candles) > 0
        for candle in candles:
            for field in REQUIRED_CANDLE_FIELDS:
                assert field in candle
            _assert_iso8601_utc(candle["start_time"])
            _assert_iso8601_utc(candle["end_time"])
            for field in DECIMAL_CANDLE_FIELDS:
                assert isinstance(candle[field], str)
            for field in OPTIONAL_DECIMAL_CANDLE_FIELDS:
                value = candle.get(field)
                assert value is None or isinstance(value, str)
            trade_count = candle.get("trade_count")
            assert trade_count is None or isinstance(trade_count, int)


@pytest.mark.parametrize(
    ("url_symbol", "expected_symbol"),
    [
        ("BTC-USDT", "BTC/USDT"),
        ("ETH-USDT", "ETH/USDT"),
    ],
)
def test_market_data_success(url_symbol: str, expected_symbol: str) -> None:
    client = TestClient(create_app())
    response = client.get(f"/markets/{url_symbol}/market-data")

    assert response.status_code == 200
    body = response.json()
    _assert_market_data_body(body, expected_symbol)
    # Response model is the HTTP DTO, not domain MarketData.
    assert MarketDataResponse.model_validate(body)


def test_parse_url_symbol_converts_hyphen_to_slash() -> None:
    assert parse_url_symbol("BTC-USDT") == "BTC/USDT"
    assert parse_url_symbol("btc-usdt") == "BTC/USDT"


def test_market_data_url_param_converted_to_internal_symbol() -> None:
    captured: list[str] = []

    original_execute = GetMarketData.execute

    def spy_execute(self: GetMarketData, symbol: str) -> object:
        captured.append(symbol)
        return original_execute(self, symbol)

    with patch.object(GetMarketData, "execute", spy_execute):
        client = TestClient(create_app())
        response = client.get("/markets/BTC-USDT/market-data")

    assert response.status_code == 200
    assert captured == ["BTC/USDT"]
    assert response.json()["symbol"] == "BTC/USDT"


def test_market_data_not_found_returns_404() -> None:
    client = TestClient(create_app())
    response = client.get("/markets/SOL-USDT/market-data")

    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.parametrize("url_symbol", ["BTC", "BTC%2FUSDT"])
def test_market_data_invalid_symbol_format_returns_422(url_symbol: str) -> None:
    client = TestClient(create_app())
    response = client.get(f"/markets/{url_symbol}/market-data")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_market_data_slash_separated_path_returns_422() -> None:
    client = TestClient(create_app())
    response = client.get("/markets/BTC/USDT/market-data")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_market_data_unexpected_error_returns_500() -> None:
    application = create_app()
    application.state.get_market_data = MagicMock()
    application.state.get_market_data.execute.side_effect = RuntimeError("boom")

    client = TestClient(application, raise_server_exceptions=False)
    response = client.get("/markets/BTC-USDT/market-data")

    assert response.status_code == 500
    assert "detail" in response.json()


def test_domain_and_application_have_no_framework_imports() -> None:
    for root in (MODULES_ROOT, APPLICATION_ROOT):
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not any(
                            alias.name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES
                        ), f"{path} imports forbidden module {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module is not None:
                    assert not any(
                        node.module.startswith(prefix) for prefix in FORBIDDEN_PREFIXES
                    ), f"{path} imports forbidden module {node.module}"
