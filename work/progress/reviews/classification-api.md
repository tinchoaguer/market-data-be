---
feature:
  slug: classification-api

decision: APPROVED

summary: >
  Classification REST API satisfies all requirements. Hyphen URL params convert to slash
  internal symbols. DTO boundary and error mapping (404/422/500) match approved design.
---

# Code Review: classification-api

## Requirements

REQ-001 through REQ-015: **pass**

## Non-Functional Requirements

NFR-001 through NFR-006: **pass**

## Acceptance Criteria

AC-001 through AC-012: **pass**

## Findings

### Recommendations (non-blocking)

1. **test_classification_route.py** — slash-path 422 case (`/markets/BTC/USDT/classification`) works but lacks automated test.
2. **test_classification_route.py** — multi-hyphen input (`BTC-USDT-EXTRA`) not covered by dedicated test.

## Tests

```
pytest src/ — 90 passed
```

## API

| Request | Response |
|---------|----------|
| `GET /markets/BTC-USDT/classification` | 200 + classification DTO |
| `GET /markets/SOL-USDT/classification` | 404 |
| `GET /markets/BTC/classification` | 422 |
| `GET /markets/BTC%2FUSDT/classification` | 422 |

Response `symbol` uses slash format (`BTC/USDT`).

> **Note (2026-07-09):** HTTP mapper input type is now `ClassificationResult` (domain). Paths under `src/market_data_be/`. See [ADR-0001](../../../knowledge/adr/0001-package-layout-and-domain-facades.md).
