# Feature History: market-data-analysis-api

```yaml
history:
  - date: 2026-07-11
    feature:
      id: 7
      slug: market-data-analysis-api
    workflow_stage: Completed
```

## Summary

Exposed market data analysis via REST API. URL uses hyphen-separated path params (`BTC-USDT`) with API-layer conversion to internal slash format (`BTC/USDT`). `AnalyzeMarket` orchestrates provider + `MarketAnalysisEngine`; HTTP responses use Pydantic DTOs mapped from domain `AnalysisResult`.

## Deliverables

- `GET /markets/{symbol}/analysis` — market data analysis endpoint
- `src/market_data_be/application/use_cases/analyze_market.py` — AnalyzeMarket use case
- `src/market_data_be/application/tests/test_analyze_market.py` — use case tests
- `src/market_data_be/infrastructure/http/dtos/analysis.py` — Pydantic response DTOs
- `src/market_data_be/infrastructure/http/mappers/analysis.py` — domain → HTTP mapping
- `src/market_data_be/infrastructure/http/routes/analysis.py` — route handler
- `src/market_data_be/infrastructure/http/composition.py` — `build_analyze_market()` wiring
- `src/market_data_be/infrastructure/http/app.py` — router registration
- `src/market_data_be/infrastructure/tests/test_analysis_route.py` — integration tests

## Review

**Decision:** APPROVED

All REQ-001–018, NFR-001–008, and AC-001–012 passed. Full suite: 131 passed.

## Usage

```bash
uvicorn market_data_be.infrastructure.http.app:app --host 0.0.0.0 --port 8000
```

```http
GET /markets/BTC-USDT/analysis
```
