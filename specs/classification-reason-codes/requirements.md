# Requirements

## Overview

Tighten the classification HTTP response contract so each signal `reason` is a closed set of machine-readable codes, documented as OpenAPI enum values. Frontend clients use OpenAPI as the source of truth to map codes to localized human-readable copy. Domain `ClassificationSignal.reason` may remain a plain string; the public contract is the infrastructure HTTP DTO / OpenAPI surface. The existing `GET /markets/{symbol}/classification` endpoint and response shape (`symbol`, `regime` / `risk` / `economic` / `exposure` signal lists with `source`, `score`, `reason`) remain in place; this feature only constrains and documents allowed `reason` values.

This feature does not change analysis HTTP contracts (see separate feature `analysis-reason-codes`).

## Goals

- Expose classification signal reason codes as a closed typed set on HTTP response DTOs so OpenAPI lists allowed values.
- Keep the HTTP DTO layer as the sole public contract surface for reason codes (clients must not need domain source).
- Ensure classifiers emit only reason codes that belong to the declared contract.
- Fail closed when mapping domain output that contains an undeclared reason code (never serialize an unconstrained or unknown reason on success responses).
- Preserve the existing classification endpoint path, success/error status codes, and top-level JSON structure from `classification-api`.

## Functional Requirements

```text
REQ-001

When the classification HTTP response DTO defines signal `reason` fields, the system shall type each `reason` as a closed set of allowed string codes (Literal or Enum), not as an unconstrained string.
```

```text
REQ-002

When the OpenAPI schema for `GET /markets/{symbol}/classification` is generated from the response DTOs, the system shall document the allowed classification reason codes as enum values for each signal `reason` property.
```

```text
REQ-003

The system shall declare exactly the following allowed reason codes per signal group on the HTTP contract:

- regime: trend_up, trend_down, range, chaotic, news_spike
- risk: low_risk, moderate_risk, elevated_risk, high_risk
- economic: strong_edge, moderate_edge, neutral_edge, negative_edge
- exposure: ample_capacity, limited_capacity, constrained_capacity
```

```text
REQ-004

When a classifier produces a classification signal, the system shall emit a `reason` value that belongs to the declared closed set for that signal's group (regime, risk, economic, or exposure).
```

```text
REQ-005

When the infrastructure HTTP mapper maps a domain classification result to the HTTP response DTO, and any signal `reason` is not a member of the closed set declared for that signal's group, the system shall fail closed: it shall not return HTTP 200 with that undeclared reason value.
```

```text
REQ-006

When mapping fails closed because of an undeclared reason code, the system shall respond with HTTP 500 and shall not include the undeclared reason string in a successful classification body.
```

```text
REQ-007

The system shall keep `GET /markets/{symbol}/classification` operational with the same path pattern, hyphen-separated URL symbol rules, success JSON top-level keys (`symbol`, `regime`, `risk`, `economic`, `exposure`), and per-signal fields `source`, `score`, and `reason` established by `classification-api`.
```

```text
REQ-008

The system shall keep domain `ClassificationSignal.reason` free of infrastructure typing requirements: domain models may retain `reason` as `str`; closed-set typing for the public contract shall live on the HTTP response DTO surface.
```

```text
REQ-009

Clients shall be able to derive the complete set of allowed classification reason codes from the published OpenAPI schema for the classification endpoint without reading domain classifier source code.
```

```text
REQ-010

When classification succeeds for supported mock symbols, every returned signal `reason` shall be one of the codes declared in REQ-003 for that signal's group.
```

## Non-Functional Requirements

```text
NFR-001

Domain modules under `src/market_data_be/modules/` shall remain free of FastAPI and Pydantic dependencies.
```

```text
NFR-002

Closed-set reason typing for the public API shall be defined in infrastructure HTTP DTOs under `src/market_data_be/infrastructure/http/`; the application layer shall not define HTTP DTOs or OpenAPI schemas.
```

```text
NFR-003

The feature shall not modify the analysis HTTP DTOs, analysis OpenAPI reason/regime contracts, or the scope of feature `analysis-reason-codes`.
```

```text
NFR-004

The feature shall preserve existing classification HTTP status semantics for client and not-found errors (422 for invalid URL symbol format, 404 for missing market data) established by `classification-api`.
```

```text
NFR-005

HTTP and domain unit tests covering reason-code typing, OpenAPI enum exposure, classifier emission, and mapper fail-closed behavior shall reside under the appropriate module `tests/` directories and use pytest.
```

```text
NFR-006

Public HTTP DTO contracts shall use strict typing and shall avoid `Any`.
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001, REQ-003):** Classification HTTP signal DTO `reason` fields are typed as closed sets (Literal or Enum) matching exactly the codes listed in REQ-003 per group; unconstrained `str` is not used for those fields.
- [ ] **AC-002 (REQ-002, REQ-009):** The OpenAPI schema for the classification endpoint documents allowed `reason` values as enums; a client can list all allowed codes from that schema alone.
- [ ] **AC-003 (REQ-004, REQ-010):** Domain classifiers for regime, risk, economic, and exposure emit only reason codes from the corresponding REQ-003 sets; automated tests assert emission membership for each classifier.
- [ ] **AC-004 (REQ-005, REQ-006):** Mapping a domain result that contains an undeclared reason for a group does not produce HTTP 200 with that value; the observable outcome is HTTP 500 (or equivalent fail-closed path that never serializes the undeclared code on success).
- [ ] **AC-005 (REQ-007, NFR-004):** `GET /markets/BTC-USDT/classification` and `GET /markets/ETH-USDT/classification` still return HTTP 200 with `symbol`, four signal groups, and per-signal `source` / `score` / `reason`; invalid URL symbols still yield 422 and unknown symbols 404.
- [ ] **AC-006 (REQ-008, NFR-001, NFR-002):** Domain `ClassificationSignal.reason` remains string-typed (or otherwise free of Pydantic/FastAPI); closed sets live on HTTP DTOs only; no FastAPI/Pydantic imports under `modules/`.
- [ ] **AC-007 (NFR-003):** No changes introduce analysis-endpoint reason/regime closed sets as part of this feature.
- [ ] **AC-008 (NFR-005, NFR-006):** Automated tests cover DTO/OpenAPI enum documentation, classifier code membership, mapper reject/fail-closed behavior, and successful classification responses with declared reasons only.
