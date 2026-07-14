# Requirements

## Overview

Tighten the analysis HTTP response contract so `RegimeAssessmentResponse.regime` and each item of `RegimeAssessmentResponse.reasons` are closed sets of machine-readable values, documented as OpenAPI enum values. Frontend clients use OpenAPI as the source of truth to map regime labels and reason codes to localized human-readable copy. Domain `RegimeAssessment.reasons` may remain a plain string collection; the public contract is the infrastructure HTTP DTO / OpenAPI surface. The existing `GET /markets/{symbol}/analysis` endpoint and top-level response shape (`symbol`, `regime`, `risk`, `economic`, `exposure`, `catalog`) remain in place; this feature only constrains and documents allowed `regime` and regime `reasons` values on the regime assessment object.

This feature does not change classification HTTP contracts (see completed feature `classification-reason-codes`). Free-form prose fields such as `catalog_reason` and `hard_gate_reason`, strategy lists, and risk/economic component name keys are out of scope.

## Goals

- Expose analysis regime labels and regime reason codes as closed typed sets on the HTTP response DTO so OpenAPI lists allowed values.
- Keep the HTTP DTO layer as the sole public contract surface for these codes (clients must not need domain source).
- Ensure `RegimeDetector` emits only reason codes that belong to the declared contract.
- Fail closed when mapping domain output that contains an undeclared regime or reason code (never serialize an unconstrained or unknown value on success responses).
- Preserve the existing analysis endpoint path, success/error status codes, and top-level JSON structure from `market-data-analysis-api`.

## Functional Requirements

```text
REQ-001

When the analysis HTTP response DTO defines `RegimeAssessmentResponse.regime`, the system shall type `regime` as a closed set of allowed string labels (Literal or Enum), not as an unconstrained string.
```

```text
REQ-002

When the analysis HTTP response DTO defines `RegimeAssessmentResponse.reasons`, the system shall type each list item as a closed set of allowed reason codes (Literal or Enum), not as an unconstrained string.
```

```text
REQ-003

When the OpenAPI schema for `GET /markets/{symbol}/analysis` is generated from the response DTOs, the system shall document the allowed regime labels and regime reason codes as enum values for `regime.regime` and `regime.reasons` items respectively.
```

```text
REQ-004

The system shall declare exactly the following allowed regime labels on the HTTP contract wire values:

- TREND_UP
- TREND_DOWN
- RANGE
- CHAOTIC
- NEWS_SPIKE
```

```text
REQ-005

The system shall declare exactly the following allowed regime reason codes on the HTTP contract wire values:

- insufficient_candles
- adx_low_band
- default
- abnormal_range_or_body
- relative_volume_spike
- relative_trades_spike
- volatility_expansion
- low_adx_high_atr
- frequent_direction_changes
- sma_whipsaw
- adx_strong
- plus_di_dominant
- minus_di_dominant
- hh_hl_structure
- lh_ll_structure
- above_sma_rising
- below_sma_falling
- taker_buy_flow
- taker_sell_flow
```

```text
REQ-006

When `RegimeDetector` produces regime reason codes, the system shall emit only reason code strings that belong to the closed set declared in REQ-005.
```

```text
REQ-007

When the infrastructure HTTP mapper maps a domain analysis result to the HTTP response DTO, and the domain regime label is not a member of the closed set declared in REQ-004, the system shall fail closed: it shall not return HTTP 200 with that undeclared regime value.
```

```text
REQ-008

When the infrastructure HTTP mapper maps a domain analysis result to the HTTP response DTO, and any regime reason code is not a member of the closed set declared in REQ-005, the system shall fail closed: it shall not return HTTP 200 with that undeclared reason value.
```

```text
REQ-009

When mapping fails closed because of an undeclared regime label or undeclared regime reason code, the system shall respond with HTTP 500 and shall not include the undeclared value in a successful analysis body.
```

```text
REQ-010

The system shall keep `GET /markets/{symbol}/analysis` operational with the same path pattern, hyphen-separated URL symbol rules, success JSON top-level keys (`symbol`, `regime`, `risk`, `economic`, `exposure`, `catalog`), and regime assessment field names established by `market-data-analysis-api`.
```

```text
REQ-011

The system shall keep domain `RegimeAssessment.reasons` free of infrastructure typing requirements: domain models may retain reasons as `tuple[str, ...]` (or equivalent plain strings); closed-set typing for the public contract shall live on the HTTP response DTO surface.
```

```text
REQ-012

Clients shall be able to derive the complete set of allowed regime labels and regime reason codes from the published OpenAPI schema for the analysis endpoint without reading domain analysis source code.
```

```text
REQ-013

When analysis succeeds for supported mock symbols, every returned `regime.regime` value shall be one of the labels declared in REQ-004, and every returned `regime.reasons` item shall be one of the codes declared in REQ-005.
```

## Non-Functional Requirements

```text
NFR-001

Domain modules under `src/market_data_be/modules/` shall remain free of FastAPI and Pydantic dependencies.
```

```text
NFR-002

Closed-set regime and reason typing for the public API shall be defined in infrastructure HTTP DTOs under `src/market_data_be/infrastructure/http/`; the application layer shall not define HTTP DTOs or OpenAPI schemas.
```

```text
NFR-003

The feature shall not modify the classification HTTP DTOs, classification OpenAPI reason contracts, or the completed scope of feature `classification-reason-codes`.
```

```text
NFR-004

The feature shall preserve existing analysis HTTP status semantics for client and not-found errors (422 for invalid URL symbol format, 404 for missing market data) established by `market-data-analysis-api`.
```

```text
NFR-005

HTTP and domain unit tests covering regime/reason closed-set typing, OpenAPI enum exposure, RegimeDetector emission, and mapper fail-closed behavior shall reside under the appropriate module `tests/` directories and use pytest.
```

```text
NFR-006

Public HTTP DTO contracts shall use strict typing and shall avoid `Any`.
```

```text
NFR-007

The feature shall not expand closed-set typing to `catalog_reason`, `hard_gate_reason`, strategy lists, or risk/economic component name keys unless required to keep the analysis endpoint compiling; prefer leaving those fields typed as they are today.
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001, REQ-004):** `RegimeAssessmentResponse.regime` is typed as a closed set (Literal or Enum) matching exactly the labels listed in REQ-004; unconstrained `str` is not used for that field.
- [ ] **AC-002 (REQ-002, REQ-005):** `RegimeAssessmentResponse.reasons` items are typed as a closed set (Literal or Enum) matching exactly the codes listed in REQ-005; unconstrained `str` is not used for those items.
- [ ] **AC-003 (REQ-003, REQ-012):** The OpenAPI schema for the analysis endpoint documents allowed `regime` and `reasons` values as enums; a client can list all allowed labels and codes from that schema alone.
- [ ] **AC-004 (REQ-006, REQ-013):** `RegimeDetector` emits only reason codes from the REQ-005 set; automated tests assert emission membership.
- [ ] **AC-005 (REQ-007, REQ-008, REQ-009):** Mapping a domain result that contains an undeclared regime label or undeclared regime reason does not produce HTTP 200 with that value; the observable outcome is HTTP 500 (or equivalent fail-closed path that never serializes the undeclared code on success).
- [ ] **AC-006 (REQ-010, NFR-004):** `GET /markets/BTC-USDT/analysis` and `GET /markets/ETH-USDT/analysis` still return HTTP 200 with top-level `symbol`, `regime`, `risk`, `economic`, `exposure`, and `catalog`; invalid URL symbols still yield 422 and unknown symbols 404.
- [ ] **AC-007 (REQ-011, NFR-001, NFR-002):** Domain regime reasons remain string-typed collections (or otherwise free of Pydantic/FastAPI); closed sets live on HTTP DTOs only; no FastAPI/Pydantic imports under `modules/`.
- [ ] **AC-008 (NFR-003, NFR-007):** No changes introduce classification-endpoint reason closed sets as part of this feature; `catalog_reason`, `hard_gate_reason`, strategy lists, and risk/economic component keys remain outside the closed-set scope of this feature.
- [ ] **AC-009 (NFR-005, NFR-006):** Automated tests cover DTO/OpenAPI enum documentation, RegimeDetector code membership, mapper reject/fail-closed behavior, and successful analysis responses with declared regime and reasons only.
