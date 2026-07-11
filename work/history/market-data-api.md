# Feature History: market-data-api

```yaml
history:
  - date: 2026-07-10
    feature:
      id: 6
      slug: market-data-api
    workflow_stage: Completed
```

## Summary

Exposed market data via REST API. URL uses hyphen-separated path params (`BTC-USDT`) with API-layer conversion to internal slash format (`BTC/USDT`). Responses use Pydantic HTTP DTOs mapped from domain `MarketData`.

## Deliverables

- `GET /markets/{symbol}/market-data` — market data endpoint
- `src/market_data_be/infrastructure/http/dtos/market_data.py` — Pydantic response DTOs
- `src/market_data_be/infrastructure/http/mappers/market_data.py` — domain → HTTP mapping
- `src/market_data_be/infrastructure/http/routes/market_data.py` — route handler
- `src/market_data_be/infrastructure/http/composition.py` — `build_get_market_data()` wiring
- `src/market_data_be/infrastructure/http/app.py` — router registration
- `src/market_data_be/infrastructure/tests/test_market_data_route.py` — integration tests

## Review

**Decision:** APPROVED

All REQ-001–020, NFR-001–007, and AC-001–012 passed. Full suite: 118 passed.

## Usage

```bash
uvicorn market_data_be.infrastructure.http.app:app --host 0.0.0.0 --port 8000
```

```http
GET /markets/BTC-USDT/market-data
```
