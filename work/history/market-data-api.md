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

Exposed market data via REST API. URL uses hyphen-separated path params (`BTC-USDT`) with API-layer conversion to internal slash format (`BTC/USDT`). Responses use Pydantic HTTP DTOs rather than domain models.

## Deliverables

- `GET /markets/{symbol}/market-data` — market data endpoint
- `src/market_data_be/infrastructure/http/dtos/market_data.py` — Pydantic response DTOs
- `src/market_data_be/infrastructure/http/mappers/market_data.py` — domain → HTTP mapping
- `src/market_data_be/infrastructure/http/composition.py` — `build_get_market_data()` wiring
- `src/market_data_be/infrastructure/http/routes/market_data.py` — route handler
- `src/market_data_be/infrastructure/http/app.py` — router registration
- `src/market_data_be/infrastructure/tests/test_market_data_route.py` — integration tests

## Review

**Decision:** APPROVED

All functional requirements (REQ-001–REQ-017), NFRs (NFR-001–NFR-007), and acceptance criteria (AC-001–AC-012) passed. 11/11 market-data route tests green.

## Spec artifacts

- `specs/market-data-api/requirements.md`
- `specs/market-data-api/design.md`
- `specs/market-data-api/tasks.md`
