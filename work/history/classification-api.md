# Feature History: classification-api

```yaml
history:
  - date: 2026-07-08
    feature:
      id: 5
      slug: classification-api
    workflow_stage: Completed
```

## Summary

Exposed market classification results via REST API. URL uses hyphen-separated path params (`BTC-USDT`) with API-layer conversion to internal slash format (`BTC/USDT`). Responses use Pydantic HTTP DTOs.

## Deliverables

- `GET /markets/{symbol}/classification` — classification endpoint
- `src/infrastructure/http/validation/symbol.py` — `parse_url_symbol` (hyphen → slash)
- `src/infrastructure/http/dtos/classification.py` — Pydantic response DTOs
- `src/infrastructure/http/mappers/classification.py` — application → HTTP mapping
- `src/infrastructure/http/composition.py` — `build_classify_market()` wiring
- `src/infrastructure/http/routes/classification.py` — route handler
- `src/infrastructure/tests/test_classification_route.py` — integration tests

## Review

**Decision:** APPROVED

All 15 requirements, 6 NFRs, and 12 acceptance criteria passed. 90/90 tests green.

## Usage

```bash
uvicorn market_data_be.infrastructure.http.app:app --host 0.0.0.0 --port 8000
```

```http
GET /markets/BTC-USDT/classification
```

```json
{
  "symbol": "BTC/USDT",
  "regime": [{ "source": "regime", "score": 0.4, "reason": "trend_up" }],
  "risk": [...],
  "economic": [...],
  "exposure": [...]
}
```

## Specification revision

Initial spec used slash in URL path (`BTC/USDT`). Rejected by human; revised to hyphen format (`BTC-USDT`) with API conversion.
