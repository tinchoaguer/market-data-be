# market-data-be

Python backend that turns raw market data into deterministic analysis and trading-oriented classification signals, exposed over a read-only HTTP API.

## Business

This service helps traders and downstream clients understand **what the market looks like right now** for a given symbol (for example `BTC/USDT`).

1. **Market data** — OHLCV candles, order book, and related fields for a trading pair.
2. **Analysis** — Deterministic interpretation of that data: regime, risk, economic context, exposure, and a strategy catalog.
3. **Classification** — Discrete signals derived from those assessments (regime, risk, economic, exposure) that are easier for UIs and other systems to consume.

Today the API serves mock fixtures for `BTC/USDT` and `ETH/USDT`. The domain pipeline is provider-agnostic so live market-data adapters can replace the mock source without changing analysis or classification logic.

## Architecture

Modular monolith (`market_data_be`) with DDD-style layers:


| Layer          | Path                                 | Role                                            |
| -------------- | ------------------------------------ | ----------------------------------------------- |
| Domain         | `src/market_data_be/modules/`        | Pure analysis & classification (stdlib only)    |
| Application    | `src/market_data_be/application/`    | Use cases, ports, cross-context mappers         |
| Infrastructure | `src/market_data_be/infrastructure/` | FastAPI, DTOs, mock market-data provider        |
| Resources      | `resources/`                         | JSON fixtures (outside the installable package) |


**Pipeline:**

```
MarketDataProvider → MarketAnalysisEngine → mapper → MarketClassificationEngine → ClassificationResult
```

Bounded contexts (`analysis`, `classification`) do not import each other. Framework code (FastAPI, Pydantic) stays outside the domain.

More detail: `[knowledge/architecture.md](knowledge/architecture.md)`.

## How to run

**Requirements:** Python 3.12+

```bash
# from market-data-be/
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

**Start the API:**

```bash
# Prefer python -m (avoids a Windows reload/multiprocessing crash with uvicorn.exe)
python -m uvicorn market_data_be.infrastructure.http.app:app --reload
```

Without auto-reload: `python -m uvicorn market_data_be.infrastructure.http.app:app`

- Health: `GET http://127.0.0.1:8000/health`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

**Example endpoints** (symbol as `BASE-QUOTE`):


| Endpoint       | Example                                |
| -------------- | -------------------------------------- |
| Market data    | `GET /markets/BTC-USDT/market-data`    |
| Analysis       | `GET /markets/BTC-USDT/analysis`       |
| Classification | `GET /markets/BTC-USDT/classification` |


**Tests:**

```bash
pytest
```
