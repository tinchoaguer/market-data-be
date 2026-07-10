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
- `src/market_data_be/infrastructure/http/validation/symbol.py` — `parse_url_symbol` (hyphen → slash)
- `src/market_data_be/infrastructure/http/dtos/classification.py` — Pydantic response DTOs
- `src/market_data_be/infrastructure/http/mappers/classification.py` — `ClassificationResult` → HTTP mapping
- `src/market_data_be/infrastructure/http/composition.py` — `build_classify_market()` wiring
- `src/market_data_be/infrastructure/http/routes/classification.py` — route handler
- `src/market_data_be/infrastructure/tests/test_classification_route.py` — integration tests

> **2026-07-09:** Paths under `src/market_data_be/`; HTTP mapper input is `ClassificationResult`. See [ADR-0001](../../knowledge/adr/0001-package-layout-and-domain-facades.md).

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
