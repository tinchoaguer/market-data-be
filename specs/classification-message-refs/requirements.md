# Requirements

## Overview

Replace the bare, unstructured `reason` values on classification HTTP signal DTOs (`regime`, `risk`, `economic`, `exposure`) with structured `MessageRef` values (`code` + typed `params`), reusing the same MessageRef shape and conventions introduced by `analysis-message-refs`. The closed reason-code sets already declared by `classification-reason-codes` remain the `code` values of each group's MessageRef — no reason-code renaming. Classification domain classifiers keep emitting only declared plain-string reason codes and continue to avoid interpolated display English. Where the classification endpoint's own route code today builds client-facing error copy as a hardcoded English sentence (invalid URL symbol format) or where its dedicated fail-closed exception handling returns only an English sentence (undeclared reason), responses instead carry a stable machine `code` from a declared closed set, so clients resolve display text outside the backend. The public contract change is reflected in the app OpenAPI schema generated from the classification response DTOs. Analysis HTTP DTOs, analysis routes, the shared `parse_url_symbol` function contract, and the shared market-data-not-found (404) handling are out of scope and remain unchanged.

## Goals

- Emit `MessageRef` (`code` + `params`) on classification HTTP signal DTOs for `regime`, `risk`, `economic`, and `exposure`, replacing today's bare reason string/enum value.
- Reuse the existing closed reason-code sets from `classification-reason-codes` as the MessageRef `code` values per signal group, without changing their wire values.
- Keep classification domain classifiers free of interpolated display English; they continue to emit only declared plain-string reason codes.
- Restrict MessageRef params to typed data only (enums, numbers, ids, booleans) — never prose — for any params a builder emits.
- Where the classification route or its dedicated fail-closed error handling today surfaces a hardcoded English sentence as the sole caller-facing signal (invalid URL symbol format on the classification endpoint; undeclared reason fail-closed 500), add a stable machine `code` from a declared closed set to the response body.
- Document the MessageRef shape and updated per-group signal `reason` field types in OpenAPI for `GET /markets/{symbol}/classification`.
- Preserve the existing classification endpoint path, status semantics, top-level JSON keys, and per-signal `source` / `score` fields.
- Leave analysis HTTP DTOs/routes, the shared `parse_url_symbol` function contract, and the shared market-data-not-found (404) handling out of this Feature.

## Functional Requirements

```text
REQ-001

When the classification HTTP response documents a signal `reason` field for the regime, risk, economic, or exposure signal group, the system shall emit that reason as a MessageRef object with at least `code` and `params`, not as a bare string or bare enum value.
```

```text
REQ-002

The system shall type each classification signal MessageRef `code` using the existing closed reason-code set declared for that signal's group by `classification-reason-codes` (regime: trend_up/trend_down/range/chaotic/news_spike; risk: low_risk/moderate_risk/elevated_risk/high_risk; economic: strong_edge/moderate_edge/neutral_edge/negative_edge; exposure: ample_capacity/limited_capacity/constrained_capacity), unchanged wire values.
```

```text
REQ-003

The system shall require the `params` property of every classification signal MessageRef to be an object; when a builder has no interpolated fact to carry for that MessageRef, `params` shall be an empty object, not omitted or null.
```

```text
REQ-004

When a classification signal MessageRef includes a non-empty `params` entry, every param value shall be typed data only: a JSON string machine token (no whitespace or sentence punctuation), a number, or a boolean. Param values shall never be prose sentences or interpolated display English.
```

```text
REQ-005

Classification domain classifiers (regime, risk, economic, exposure) shall continue to emit, on `ClassificationSignal.reason`, only plain-string reason codes belonging to the closed sets declared by `classification-reason-codes`, and shall not emit interpolated display English for that field.
```

```text
REQ-006

When the infrastructure HTTP mapper maps a domain classification signal to the HTTP response DTO, and the signal's `reason` is not a member of the closed set declared for that signal's group, the system shall fail closed: it shall not return HTTP 200 with a MessageRef built from that undeclared reason.
```

```text
REQ-007

When the infrastructure HTTP mapper builds a classification signal MessageRef and a param value violates REQ-004, the system shall fail closed: it shall not return HTTP 200 with that MessageRef.
```

```text
REQ-008

When mapping fails closed because of an undeclared reason code (REQ-006), the system shall respond with HTTP 500, the response body shall carry a stable machine `code` identifying the failure as an undeclared classification reason, and the response shall not include the undeclared reason string.
```

```text
REQ-009

When mapping fails closed because of an invalid MessageRef param (REQ-007), the system shall respond with HTTP 500 and the response body shall carry a stable machine `code` identifying the failure as an invalid classification message param.
```

```text
REQ-010

When the classification route (`GET /markets/{symbol}/classification` or its rejected slash-form path) rejects a request because the URL symbol does not match the BASE-QUOTE hyphen-separated format, the system shall respond with HTTP 422 and the response body shall carry a stable machine `code` identifying the failure as an invalid symbol format, in addition to any human-readable text.
```

```text
REQ-011

The system shall declare the closed set of classification HTTP error codes used by REQ-008, REQ-009, and REQ-010 as a typed closed set (Literal or Enum) on the classification HTTP error contract.
```

```text
REQ-012

When the OpenAPI schema for `GET /markets/{symbol}/classification` is generated from the response DTOs, the system shall document the MessageRef object shape and the updated `reason` field types for the regime, risk, economic, and exposure signal DTOs.
```

```text
REQ-013

The system shall keep `GET /markets/{symbol}/classification` operational with the same path pattern, hyphen-separated URL symbol rules, success JSON top-level keys (`symbol`, `regime`, `risk`, `economic`, `exposure`), and per-signal `source` and `score` fields established by `classification-api` and `classification-reason-codes`, except for the `reason` field type change defined by this Feature.
```

```text
REQ-014

Clients shall be able to consume classification signal MessageRefs from the published OpenAPI schema and HTTP responses for the classification endpoint without reading classification domain source code.
```

```text
REQ-015

The system shall not resolve display copy or call any copy-resolution service when producing classification HTTP responses or classification HTTP error bodies; the backend shall emit MessageRefs and machine error codes only.
```

```text
REQ-016

When classification succeeds for supported mock symbols, every returned signal MessageRef shall have `code` belonging to the REQ-002 closed set for that signal's group and `params` satisfying REQ-003 and REQ-004.
```

## Non-Functional Requirements

```text
NFR-001

Domain modules under `src/market_data_be/modules/` shall remain free of FastAPI and Pydantic dependencies.
```

```text
NFR-002

Classification MessageRef and HTTP-error-code typing for the public API shall be defined in infrastructure HTTP DTOs under `src/market_data_be/infrastructure/http/`; the application layer shall not define HTTP DTOs or OpenAPI schemas.
```

```text
NFR-003

The feature shall not modify analysis HTTP DTOs, the analysis OpenAPI contract, analysis routes, or the error-handling behavior introduced by `analysis-message-refs` / `analysis-reason-codes`.
```

```text
NFR-004

The feature shall not change the `parse_url_symbol` function's contract (signature, raised exception type, or message text) in `src/market_data_be/infrastructure/http/validation/symbol.py`; only the classification route's handling of the resulting failure may change to add a machine error code, and the analysis and market-data routes' use of that function remains unaffected.
```

```text
NFR-005

The feature shall preserve existing classification HTTP status semantics for not-found errors (404) established by `classification-api`; the shared market-data-not-found exception handler content is unchanged.
```

```text
NFR-006

HTTP and domain unit tests covering MessageRef emission, param constraints, fail-closed behavior (undeclared reason, invalid param, invalid symbol format), OpenAPI documentation, and successful classification responses shall reside under the appropriate module `tests/` directories and use pytest.
```

```text
NFR-007

Public HTTP DTO contracts shall use strict typing and shall avoid `Any`.
```

```text
NFR-008

The feature shall not introduce copy catalogs, templates, or display-copy resolve logic into the backend repository.
```

```text
NFR-009

Domain `ClassificationSignal` shall remain `@dataclass(frozen=True, slots=True)` with `reason: str`; this Feature does not require a domain-level MessageRef type.
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001, REQ-002, REQ-003):** Successful classification responses expose every `regime[].reason`, `risk[].reason`, `economic[].reason`, and `exposure[].reason` as a MessageRef object (`code` + `params`) whose `code` belongs to that group's declared closed set; none of these fields is a bare string or bare enum value.
- [ ] **AC-002 (REQ-004, REQ-016):** For supported mock symbols, every returned classification signal MessageRef has typed-scalar-only `params` (or an empty object) and a `code` in the declared closed set for its group; automated tests assert no prose params.
- [ ] **AC-003 (REQ-005):** Classification classifiers (regime, risk, economic, exposure) continue to emit only declared plain-string reason codes with no interpolated English; automated tests assert membership and absence of whitespace/punctuation in emitted reason strings.
- [ ] **AC-004 (REQ-006, REQ-008):** Mapping a classification result containing an undeclared reason never produces HTTP 200 with that reason; the observable outcome is HTTP 500 with a response body carrying the declared undeclared-reason machine `code` and no undeclared reason string.
- [ ] **AC-005 (REQ-007, REQ-009):** Mapping a classification signal MessageRef with an invalid (non-scalar or prose) param never produces HTTP 200 with that MessageRef; the observable outcome is HTTP 500 with a response body carrying the declared invalid-param machine `code`.
- [ ] **AC-006 (REQ-010, REQ-011):** Requests to the classification endpoint with an invalid URL symbol format (including the rejected slash-form path) return HTTP 422 with a response body carrying the declared invalid-symbol-format machine `code`.
- [ ] **AC-007 (REQ-012, REQ-014):** OpenAPI for `GET /markets/{symbol}/classification` documents the MessageRef shape and the updated per-group `reason` field types; a client can derive the full success MessageRef contract from that schema plus HTTP responses without reading classification domain source.
- [ ] **AC-008 (REQ-013, NFR-003, NFR-004, NFR-005):** Endpoint path, top-level keys, and per-signal `source` / `score` fields remain intact aside from the in-scope `reason` type change; analysis HTTP contracts, the `parse_url_symbol` function contract, and the shared 404 not-found handling are unchanged; 404 semantics preserved.
- [ ] **AC-009 (REQ-015, NFR-008):** The backend classification path does not resolve display copy or embed copy catalogs/templates for success or error responses.
- [ ] **AC-010 (NFR-001, NFR-002, NFR-006, NFR-007, NFR-009):** Domain stays free of FastAPI/Pydantic; classification HTTP DTOs own the public MessageRef and error-code types; `ClassificationSignal` keeps its existing frozen, slotted, string-`reason` shape; automated tests cover the behaviors above; DTO contracts avoid `Any`.
