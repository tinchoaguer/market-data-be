# Requirements

## Overview

Replace user-facing analysis narrative that today is free-text prose or interpolated English with structured `MessageRef` values (`code` + typed `params`) on the analysis HTTP response DTOs. Catalog and assessment builders in the analysis domain must emit machine-readable message references instead of display English for those narrative fields. The backend does not resolve display copy; clients consume MessageRefs from the HTTP contract. The public contract change is reflected in the app OpenAPI schema generated from HTTP DTOs. Closed regime labels and regime reason codes from `analysis-reason-codes` remain as typed codes (not prose) and are not reworked into MessageRefs by this Feature.

## Goals

- Emit `MessageRef` (code + params) on analysis HTTP DTOs for in-scope user-facing narrative fields that currently carry free-text or interpolated English.
- Keep analysis domain catalog/assessment builders free of interpolated display English for those fields.
- Restrict MessageRef params to typed data only (enums, numbers, ids, booleans) — never prose.
- Document the MessageRef shape and updated narrative fields in OpenAPI for `GET /markets/{symbol}/analysis`.
- Preserve the existing analysis endpoint path, status semantics, and non-narrative structured fields (scores, closed reason codes, strategy id lists, numeric components).
- Leave display-copy resolve and classification HTTP MessageRefs out of this Feature.

## Functional Requirements

```text
REQ-001

When the analysis HTTP response documents user-facing narrative that today is free-text prose or interpolated English on the analysis success body, the system shall emit that narrative as a MessageRef object with at least `code` and `params` on the corresponding HTTP response DTO fields, not as a free-text English string.
```

```text
REQ-002

The system shall replace `CatalogResultResponse.catalog_reason` so its wire type is MessageRef (object with `code` and `params`), not an unconstrained string.
```

```text
REQ-003

The system shall replace `CatalogResultResponse.hard_gate_reason` so its wire type is MessageRef or null, not an unconstrained string or null-with-prose; when no hard-gate narrative applies, the value shall be null.
```

```text
REQ-004

When analysis catalog or assessment builders produce values for the in-scope narrative fields identified by REQ-002 and REQ-003, the system shall emit MessageRef facts (stable semantic code plus typed params) and shall not interpolate display English into those fields.
```

```text
REQ-005

When a MessageRef includes `params`, every param value shall be typed data only: JSON string machine tokens (enums, ids, codes), numbers, or booleans. Param values shall never be prose sentences or interpolated display English.
```

```text
REQ-006

The system shall define a reusable MessageRef shape on the analysis HTTP contract with required properties `code` (string) and `params` (object). Optional properties `severity` and `channel` may be present when set by domain emission; when omitted, clients treat them as unset.
```

```text
REQ-007

When the OpenAPI schema for `GET /markets/{symbol}/analysis` is generated from the response DTOs, the system shall document the MessageRef object shape and the updated types of `catalog.catalog_reason` and `catalog.hard_gate_reason`.
```

```text
REQ-008

The system shall type MessageRef `code` values emitted for in-scope analysis narrative as a closed set on the HTTP DTO (Literal or Enum), documenting every code the analysis endpoint may return for those fields as OpenAPI enum values.
```

```text
REQ-009

When analysis catalog/assessment builders emit MessageRef codes for in-scope narrative fields, the system shall emit only codes that belong to the closed set declared in REQ-008.
```

```text
REQ-010

When the infrastructure HTTP mapper maps domain analysis output to the HTTP response DTO, and an in-scope MessageRef code is not a member of the closed set declared in REQ-008, the system shall fail closed: it shall not return HTTP 200 with that undeclared code.
```

```text
REQ-011

When mapping fails closed because of an undeclared MessageRef code or because a param value violates REQ-005, the system shall respond with HTTP 500 and shall not include the invalid narrative payload in a successful analysis body.
```

```text
REQ-012

Clients shall be able to consume in-scope analysis MessageRefs from the published OpenAPI schema and HTTP responses without reading analysis domain source code.
```

```text
REQ-013

The system shall not resolve display copy or call any copy-resolution service when producing analysis HTTP responses; the backend shall emit MessageRefs only.
```

```text
REQ-014

The system shall keep `GET /markets/{symbol}/analysis` operational with the same path pattern, hyphen-separated URL symbol rules, success JSON top-level keys (`symbol`, `regime`, `risk`, `economic`, `exposure`, `catalog`), and existing non-narrative field contracts established by `market-data-analysis-api` and `analysis-reason-codes`, except for the in-scope narrative field type changes defined by this Feature.
```

```text
REQ-015

The system shall keep strategy identifier lists (`allowed_strategies`, `forbidden_strategies`, `preferred_strategy`), regime closed sets, risk/economic numeric scores and component value pairs, and exposure numeric fields as structured data (not wrapped as MessageRefs), unless a field is discovered during inventory to currently carry interpolated English narrative — in which case that field shall be converted under REQ-001.
```

```text
REQ-016

When analysis succeeds for supported mock symbols, every returned in-scope narrative field shall be a well-formed MessageRef (or null for `hard_gate_reason` when applicable), with `code` belonging to the REQ-008 closed set and `params` satisfying REQ-005.
```

## Non-Functional Requirements

```text
NFR-001

Domain modules under `src/market_data_be/modules/` shall remain free of FastAPI and Pydantic dependencies.
```

```text
NFR-002

HTTP MessageRef typing and OpenAPI surface for the public API shall be defined in infrastructure HTTP DTOs under `src/market_data_be/infrastructure/http/`; the application layer shall not define HTTP DTOs or OpenAPI schemas.
```

```text
NFR-003

The feature shall not modify the classification HTTP DTOs.
```

```text
NFR-004

The feature shall preserve existing analysis HTTP status semantics for client and not-found errors (422 for invalid URL symbol format, 404 for missing market data) established by `market-data-analysis-api`, and preserve fail-closed HTTP 500 behavior for undeclared regime/reason codes established by `analysis-reason-codes`.
```

```text
NFR-005

HTTP and domain unit tests covering MessageRef emission, param constraints, OpenAPI documentation, mapper fail-closed behavior, and successful analysis responses shall reside under the appropriate module `tests/` directories and use pytest.
```

```text
NFR-006

Public HTTP DTO contracts shall use strict typing and shall avoid `Any`.
```

```text
NFR-007

The feature shall not introduce copy catalogs, templates, or display-copy resolve logic into the backend repository.
```

```text
NFR-008

Domain MessageRef models (if introduced under `modules/analysis/`) shall use stdlib-only constructs consistent with project architecture (`@dataclass(frozen=True, slots=True)` by default).
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001, REQ-002, REQ-003):** Successful analysis responses expose `catalog.catalog_reason` as a MessageRef object and `catalog.hard_gate_reason` as MessageRef or null; neither field is a free-text English string.
- [ ] **AC-002 (REQ-004, REQ-005, REQ-016):** Catalog/assessment builders that feed those fields emit MessageRef code + typed params only; automated tests assert params contain no prose and codes belong to the declared closed set.
- [ ] **AC-003 (REQ-006, REQ-007, REQ-008, REQ-012):** OpenAPI for the analysis endpoint documents the MessageRef shape (`code`, `params`, optional `severity`/`channel`) and enum values for narrative `code`; clients can derive the contract from OpenAPI alone.
- [ ] **AC-004 (REQ-009, REQ-010, REQ-011):** Undeclared MessageRef codes or invalid prose params fail closed (HTTP 500); success responses never include them.
- [ ] **AC-005 (REQ-013, NFR-007):** Backend analysis path does not resolve display copy or embed copy catalogs/templates.
- [ ] **AC-006 (REQ-014, REQ-015, NFR-003, NFR-004):** Endpoint path, top-level keys, regime closed sets, strategy id lists, and classification HTTP contracts remain intact aside from in-scope narrative type changes; 422/404 semantics preserved.
- [ ] **AC-007 (NFR-001, NFR-002, NFR-006, NFR-008):** Domain stays free of FastAPI/Pydantic; HTTP DTOs own the public MessageRef types; domain MessageRef (if any) is stdlib-only and frozen.
- [ ] **AC-008 (NFR-005):** Automated tests cover domain emission, HTTP/OpenAPI contract, success MessageRefs for BTC-USDT/ETH-USDT, and fail-closed mapper behavior.
