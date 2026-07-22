# Design

## Overview

Wrap each classification signal's `reason` (regime, risk, economic, exposure) in a MessageRef object (`code` + `params`) on the classification HTTP response DTOs, reusing the closed reason-code sets already declared by `classification-reason-codes` as the MessageRef `code` values — no new domain reason strings, no reason-code renaming. Classification domain classifiers and models stay unchanged (`ClassificationSignal.reason: str`); only the infrastructure HTTP DTO and mapper layers change shape. The classification route's two invalid-URL-symbol-format 422 responses and the mapper's dedicated undeclared-reason 500 fail-closed path gain a stable machine `code` (nested inside the existing `detail` envelope) instead of relying solely on a hardcoded English sentence. A new fail-closed path covers invalid (non-scalar/prose) MessageRef params, mirroring `analysis-message-refs`, even though no current builder populates non-empty params. Analysis HTTP DTOs/routes, the shared `parse_url_symbol` function, and the shared market-data-not-found handler are untouched.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|--------------------------------|
| Classification domain | `src/market_data_be/modules/classification/` | Unchanged: classifiers emit only declared plain-string reason codes; `ClassificationSignal.reason` stays `str` |
| Application | `src/market_data_be/application/` | Unchanged orchestration (`ClassifyMarket`); no HTTP DTOs; no display-copy resolve |
| Infrastructure — HTTP DTOs | `src/market_data_be/infrastructure/http/dtos/classification.py` | Per-group `*SignalMessageRef` models; classification error-code enum; `ClassificationErrorDetail`; updated `*SignalResponse.reason` type |
| Infrastructure — HTTP mappers | `src/market_data_be/infrastructure/http/mappers/classification.py` | Wrap domain `reason` strings into MessageRefs; validate code membership and param constraints; fail closed |
| Infrastructure — HTTP routes | `src/market_data_be/infrastructure/http/routes/classification.py` | Same path/handlers; both 422 invalid-symbol-format responses carry a machine `code` |
| Infrastructure — app exception handling | `src/market_data_be/infrastructure/http/app.py` | Only the classification-specific handlers (`UndeclaredClassificationReasonError`, new `InvalidClassificationMessageParamsError`) gain a machine `code`; all other handlers (analysis, generic, 404) unchanged |
| Analysis HTTP / analysis domain | — | **Out of scope** (unchanged) |

### Approach choice: wrap existing closed reason codes as MessageRef, keep domain unchanged

| Option | Pros | Cons |
|--------|------|------|
| A. Leave `reason` as a bare enum string; do not introduce MessageRef on classification signals | No DTO churn | Inconsistent with the analysis MessageRef pattern; no room for future interpolated params without another breaking change |
| **B. Wrap `reason` as a per-group MessageRef object reusing the existing closed code sets; domain unchanged (chosen)** | Consistent MessageRef shape/conventions across analysis and classification; OpenAPI remains the per-group closed-set source of truth; no domain churn since classifiers already emit only declared plain codes | Breaking type change for signal `reason` (bare string → object) |
| C. Introduce a domain-level `MessageRef` value object in `modules/classification/` and have classifiers construct it directly | Mirrors analysis domain structure exactly | Unnecessary domain churn: classifiers have no interpolated facts to carry today; violates anti-bloat / "avoid unnecessary complexity" since the HTTP mapper can wrap a plain string with an empty-params MessageRef without any domain change |

**Decision:** Option B. Justifies REQ-001–REQ-005 and NFR-009. The mapper (not the domain) is the sole place that constructs classification MessageRefs, keeping architecture blast radius minimal.

### Components to change

```
src/market_data_be/
├── modules/classification/
│   └── tests/
│       └── test_classifier_reason_codes.py   # EXTEND: assert no whitespace/punctuation in emitted reason strings
└── infrastructure/
    ├── http/
    │   ├── dtos/classification.py             # MODIFY: per-group *SignalMessageRef; error code enum; ClassificationErrorDetail
    │   ├── mappers/classification.py          # MODIFY: wrap reason as MessageRef; validate params; new fail-closed error
    │   ├── routes/classification.py           # MODIFY: both 422 sites emit ClassificationErrorDetail with a code
    │   └── app.py                              # MODIFY: classification-only handlers gain `code`; add handler for new error
    └── tests/
        ├── test_classification_mapper.py      # EXTEND: MessageRef shape, param validation, fail-closed cases
        └── test_classification_route.py       # EXTEND: OpenAPI MessageRef shape, error-code bodies, success shape
```

No changes to `modules/classification/models/signal.py`, `models/classification_result.py`, `market_classification_engine.py`, `classifiers/*.py`, `reason_codes.py`, `contracts/classifier.py`, or any analysis path.

### Placement rationale

| Decision | Rationale | Requirements |
|----------|-----------|---------------|
| MessageRef wrapping happens only in the infrastructure mapper | Domain already emits only declared plain codes; no interpolated facts exist today; avoids unnecessary domain churn | REQ-001, REQ-005, NFR-001, NFR-009 |
| Reuse existing per-group closed reason-code sets as MessageRef `code` | No renaming churn; `classification-reason-codes` remains the source of the closed set; OpenAPI still documents exact per-group codes | REQ-002, REQ-012, REQ-014 |
| `params` always present, empty object by default | Stable `code` + `params` pair for clients even when no interpolated fact exists yet | REQ-003 |
| Fail closed on undeclared code / invalid param | Never ship an undeclared reason or non-scalar/prose param on HTTP 200 | REQ-006, REQ-007, REQ-008, REQ-009 |
| Machine `code` nested inside existing `detail` envelope for 422/500 | Minimal, backward-compatible change: existing clients/tests still find `"detail"` in the body; new machine `code` is nested at `detail.code` | REQ-008, REQ-009, REQ-010, REQ-011 |
| Only classification-specific route code and classification-specific exception handlers change | `parse_url_symbol`, the generic `Exception` handler, the 404 handler, and every analysis handler are shared or analysis-owned; touching them would widen blast radius beyond this Feature | NFR-003, NFR-004, NFR-005 |
| No OpenAPI schema required for the error envelope | Consistent with the precedent set by `classification-reason-codes` / `analysis-message-refs`, which do not register OpenAPI response models for fail-closed error bodies; error-code contract is verified by HTTP tests, not OpenAPI | REQ-011 (typed enum, not necessarily OpenAPI-documented) |

### Out of scope (explicit)

- Analysis HTTP DTOs, analysis routes, analysis OpenAPI contract (`analysis-message-refs`, `analysis-reason-codes`)
- Changing `parse_url_symbol`'s signature, raised exception type, or message text
- Changing the shared market-data-not-found (404) handler or its content
- Changing the generic unexpected-`Exception` (500) handler
- Introducing a domain-level `MessageRef` type or constants module under `modules/classification/`
- Changing classifier score/threshold logic or `source` values
- Renaming any existing reason-code wire value from `classification-reason-codes`
- Authentication, live providers, or fixture JSON content changes

## Data Flow

### Successful classification (MessageRef-wrapped reason)

```
Client
  │
  │  GET /markets/BTC-USDT/classification
  ▼
classification router
  │
  ├─► parse_url_symbol → internal "BTC/USDT"          (unchanged)
  ├─► ClassifyMarket.execute(...)
  │         → ClassificationResult (domain signals; reason: str, unchanged)
  ├─► map_market_classification_to_response(...)
  │         ├─► for each group, validate reason ∈ group closed set
  │         ├─► build <Group>SignalMessageRef(code=reason, params={})
  │         └─► build <Group>SignalResponse(source, score, reason=<ref>)
  ▼
HTTP 200 + MarketClassificationResponse
  (OpenAPI documents MessageRef shape + per-group code enums)
```

### Undeclared reason (fail closed)

```
ClassificationResult with signal.reason = "unknown_code" in a group list
  → mapper raises UndeclaredClassificationReasonError
  → app.py handler (classification-only) → HTTP 500
     body: {"detail": {"code": "classification.undeclared_reason", "message": "An unexpected error occurred"}}
  → no HTTP 200 body containing "unknown_code"
```

### Invalid MessageRef param (fail closed)

```
Mapper builds a MessageRef whose param value is non-scalar or prose
  → mapper raises InvalidClassificationMessageParamsError
  → app.py handler (classification-only) → HTTP 500
     body: {"detail": {"code": "classification.invalid_message_params", "message": "An unexpected error occurred"}}
  → no HTTP 200 body containing that MessageRef
```

### Invalid URL symbol format (422, machine code added)

```
Client → GET /markets/BTC/classification  (or .../classification with base/quote segments)
  → parse_url_symbol raises ValueError (unchanged message, internal only)
  → classification route catches ValueError, builds ClassificationErrorDetail(
        code=ClassificationErrorCode.INVALID_SYMBOL_FORMAT, message=str(exc)
    )
  → raise HTTPException(422, detail=<ClassificationErrorDetail>.model_dump())
  body: {"detail": {"code": "classification.invalid_symbol_format", "message": "..."}}
```

## Interfaces

### HTTP: `GET /markets/{symbol}/classification` (unchanged path)

| Attribute | Value |
|-----------|-------|
| Method | `GET` |
| Path | `/markets/{symbol}/classification` |
| Success | `200` + `MarketClassificationResponse` (signal `reason` now a MessageRef object) |
| Client validation failure | `422`; body `detail.code = "classification.invalid_symbol_format"` |
| Not found | `404` (unchanged shared handler) |
| Undeclared reason | `500`; body `detail.code = "classification.undeclared_reason"` |
| Invalid MessageRef param | `500`; body `detail.code = "classification.invalid_message_params"` |

### MessageRef wire shape (classification signals)

**Location:** `src/market_data_be/infrastructure/http/dtos/classification.py`

```python
from enum import StrEnum

from pydantic import BaseModel, Field

MessageParamValue = str | int | float | bool


class RegimeSignalMessageRef(BaseModel):
    code: RegimeReasonCode
    params: dict[str, MessageParamValue] = Field(default_factory=dict)


class RiskSignalMessageRef(BaseModel):
    code: RiskReasonCode
    params: dict[str, MessageParamValue] = Field(default_factory=dict)


class EconomicSignalMessageRef(BaseModel):
    code: EconomicReasonCode
    params: dict[str, MessageParamValue] = Field(default_factory=dict)


class ExposureSignalMessageRef(BaseModel):
    code: ExposureReasonCode
    params: dict[str, MessageParamValue] = Field(default_factory=dict)


class RegimeSignalResponse(BaseModel):
    source: str
    score: float
    reason: RegimeSignalMessageRef


class RiskSignalResponse(BaseModel):
    source: str
    score: float
    reason: RiskSignalMessageRef


class EconomicSignalResponse(BaseModel):
    source: str
    score: float
    reason: EconomicSignalMessageRef


class ExposureSignalResponse(BaseModel):
    source: str
    score: float
    reason: ExposureSignalMessageRef


class MarketClassificationResponse(BaseModel):
    symbol: str
    regime: list[RegimeSignalResponse]
    risk: list[RiskSignalResponse]
    economic: list[EconomicSignalResponse]
    exposure: list[ExposureSignalResponse]
```

`RegimeReasonCode`, `RiskReasonCode`, `EconomicReasonCode`, `ExposureReasonCode` are the existing `StrEnum` closed sets from `classification-reason-codes` — unchanged member values. Per-group `*SignalMessageRef` classes keep OpenAPI documenting exactly the allowed codes for that group (continuing the per-group DTO decision from `classification-reason-codes`).

**Example success fragment:**

```json
{
  "symbol": "BTC/USDT",
  "regime": [{ "source": "regime", "score": 0.4, "reason": { "code": "trend_up", "params": {} } }],
  "risk": [{ "source": "risk", "score": 0.0, "reason": { "code": "low_risk", "params": {} } }],
  "economic": [{ "source": "economic", "score": 0.0, "reason": { "code": "neutral_edge", "params": {} } }],
  "exposure": [{ "source": "exposure", "score": 0.0, "reason": { "code": "ample_capacity", "params": {} } }]
}
```

### Classification HTTP error contract

**Location:** `src/market_data_be/infrastructure/http/dtos/classification.py`

```python
class ClassificationErrorCode(StrEnum):
    INVALID_SYMBOL_FORMAT = "classification.invalid_symbol_format"
    UNDECLARED_REASON = "classification.undeclared_reason"
    INVALID_MESSAGE_PARAMS = "classification.invalid_message_params"


class ClassificationErrorDetail(BaseModel):
    code: ClassificationErrorCode
    message: str
```

`ClassificationErrorDetail` is used as the `detail` value of `HTTPException` (422 sites) and as the `detail` value of the classification-only `JSONResponse` handlers (500 sites), so existing `"detail" in response.json()` checks keep passing while `response.json()["detail"]["code"]` becomes the machine-resolvable field. `message` remains a non-authoritative, human-readable string; clients are not required to parse it.

### Infrastructure mapper

**Location:** `src/market_data_be/infrastructure/http/mappers/classification.py`

```python
class UndeclaredClassificationReasonError(ValueError):
    ...  # unchanged from classification-reason-codes


class InvalidClassificationMessageParamsError(ValueError):
    """Raised when a classification MessageRef param violates typed-scalar / no-prose rules."""

    def __init__(self, group: str, detail: str) -> None:
        self.group = group
        self.detail = detail
        super().__init__(f"invalid classification message params for group {group!r}: {detail}")
```

**Mapper behavior per group** (regime/risk/economic/exposure):

1. Parse `signal.reason` against the group's closed `*ReasonCode` enum; on failure raise `UndeclaredClassificationReasonError(group, reason)` (unchanged from `classification-reason-codes`).
2. Build `params: dict[str, MessageParamValue] = {}` (no current domain source of interpolated facts).
3. Validate any param value present (defensive; reuses the same typed-scalar / no-whitespace-punctuation check as `analysis-message-refs`'s `_validate_param_value`); on violation raise `InvalidClassificationMessageParamsError(group, detail)`.
4. Construct `<Group>SignalMessageRef(code=<parsed reason>, params=params)` and wrap it into `<Group>SignalResponse(source=signal.source, score=signal.score, reason=<ref>)`.
5. Never return a `MarketClassificationResponse` containing an undeclared code or an invalid param.

### Classification route

**Location:** `src/market_data_be/infrastructure/http/routes/classification.py`

Both 422 sites (`get_market_classification_slash_rejected` and the `parse_url_symbol` `except ValueError` branch in `get_market_classification`) build:

```python
raise HTTPException(
    status_code=422,
    detail=ClassificationErrorDetail(
        code=ClassificationErrorCode.INVALID_SYMBOL_FORMAT,
        message=str(exc),  # or the fixed slash-rejected message
    ).model_dump(),
)
```

No change to `parse_url_symbol` itself, its signature, or the analysis route's use of it.

### App exception handling

**Location:** `src/market_data_be/infrastructure/http/app.py`

Only the classification-owned handlers change; every analysis handler, the generic `Exception` handler, and the 404 handler are untouched:

```python
@application.exception_handler(UndeclaredClassificationReasonError)
async def undeclared_classification_reason_handler(_r: Request, _e) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "detail": ClassificationErrorDetail(
                code=ClassificationErrorCode.UNDECLARED_REASON,
                message="An unexpected error occurred",
            ).model_dump()
        },
    )


@application.exception_handler(InvalidClassificationMessageParamsError)
async def invalid_classification_message_params_handler(_r: Request, _e) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "detail": ClassificationErrorDetail(
                code=ClassificationErrorCode.INVALID_MESSAGE_PARAMS,
                message="An unexpected error occurred",
            ).model_dump()
        },
    )
```

### Exception handling summary

| Condition | HTTP | Body (`detail`) | Notes |
|-----------|------|------------------|-------|
| Undeclared classification reason | 500 | `{"code": "classification.undeclared_reason", "message": "..."}` | Classification-only handler |
| Invalid classification MessageRef param | 500 | `{"code": "classification.invalid_message_params", "message": "..."}` | New; classification-only handler |
| Invalid URL symbol format (classification route) | 422 | `{"code": "classification.invalid_symbol_format", "message": "..."}` | Both 422 sites in `routes/classification.py` |
| Market data not found | 404 | unchanged | Shared handler; out of scope |
| Other unexpected errors | 500 | unchanged (`"An unexpected error occurred"`) | Generic handler; out of scope |
| Any analysis-path failure | — | unchanged | Analysis handlers untouched (NFR-003) |

## Data Model

### Public (HTTP)

```
MarketClassificationResponse
├── symbol: str
├── regime: RegimeSignalResponse[]
│     ├── source: str
│     ├── score: float
│     └── reason: RegimeSignalMessageRef        # WAS RegimeReasonCode (bare enum)
│           ├── code: RegimeReasonCode
│           └── params: { [key: string]: string | number | boolean }
├── risk: RiskSignalResponse[]          # reason: RiskSignalMessageRef      (same shape)
├── economic: EconomicSignalResponse[]  # reason: EconomicSignalMessageRef  (same shape)
└── exposure: ExposureSignalResponse[]  # reason: ExposureSignalMessageRef  (same shape)
```

### Classification HTTP error body

```
{ "detail": { "code": ClassificationErrorCode, "message": string } }
```

### Internal (domain, unchanged)

```
ClassificationResult
└── regime | risk | economic | exposure: tuple[ClassificationSignal, ...]

ClassificationSignal
├── source: str
├── score: float
└── reason: str   # must be a member of the group's closed set at emission time (unchanged)
```

No persistence or state transitions; each request remains compute-on-demand.

## Error Handling

| Scenario | Component | Observable result |
|----------|-----------|--------------------|
| Classifier emits declared code | Classifier + mapper | HTTP 200; `reason` is a MessageRef object with declared `code` |
| Undeclared reason code | Mapper | Fail closed → HTTP 500, `detail.code = classification.undeclared_reason` |
| Invalid/prose MessageRef param | Mapper | Fail closed → HTTP 500, `detail.code = classification.invalid_message_params` |
| Malformed URL symbol | Classification route | HTTP 422, `detail.code = classification.invalid_symbol_format` |
| Unknown symbol | Provider | HTTP 404 (unchanged) |
| Analysis-path failure | Analysis route/handlers | Unchanged (out of scope) |

Recovery: no retries, no defaulting an undeclared reason to a fallback code, no silent coercion of prose into params, no partial 200 for the remaining signals when one group fails closed.

## Testing Strategy

| Behavior | Layer | Oracle | Location |
|----------|-------|--------|----------|
| Success signal `reason` is a MessageRef with declared `code` per group | HTTP mapper | Exact object shape (`code`, `params`) + code equals expected enum member | `infrastructure/tests/test_classification_mapper.py` |
| Empty `params` by default; typed-scalar validation on non-empty params | HTTP mapper | Exact param dict; reject non-scalar/prose via raised exception | `infrastructure/tests/test_classification_mapper.py` |
| Undeclared reason → fail closed | HTTP mapper + route | Raises `UndeclaredClassificationReasonError`; route → HTTP 500 with `detail.code == "classification.undeclared_reason"` | `infrastructure/tests/test_classification_mapper.py`, `test_classification_route.py` |
| Invalid MessageRef param → fail closed | HTTP mapper + route | Raises `InvalidClassificationMessageParamsError`; route → HTTP 500 with `detail.code == "classification.invalid_message_params"` | `infrastructure/tests/test_classification_mapper.py`, `test_classification_route.py` |
| Invalid URL symbol format → 422 with machine code | HTTP route | HTTP 422 + `detail.code == "classification.invalid_symbol_format"` for both the primary and slash-rejected paths | `infrastructure/tests/test_classification_route.py` |
| OpenAPI documents MessageRef shape and per-group `reason` enums | HTTP / OpenAPI | Response schema's `reason` property (`$ref`) resolves to a schema with `code` enum equal to the group's declared set | `infrastructure/tests/test_classification_route.py` |
| Success responses for BTC-USDT / ETH-USDT | HTTP route | 200; every signal `reason` is an object with `code` ∈ group set and `params == {}` | `infrastructure/tests/test_classification_route.py` |
| Classifiers keep emitting only declared, non-prose plain-string codes | Domain | Exact membership (existing) + new "no whitespace/punctuation" assertion on emitted reason strings | `modules/classification/tests/test_classifier_reason_codes.py` |
| Domain purity (no FastAPI/Pydantic under `modules/`) | Guard | Existing AST-based import guard | `infrastructure/tests/test_classification_route.py` (`test_domain_modules_have_no_framework_imports`) |
| Regression: 404, top-level keys, `source`/`score` fields | HTTP route | Existing assertions unchanged | `infrastructure/tests/test_classification_route.py` |

**Coverage expectations:**

- AC-001 through AC-010 each have at least one automated test with a strong oracle (exact shape, exact code, or fail-closed status).
- OpenAPI MessageRef/per-group enum documentation is mandatory, extending the existing `test_openapi_documents_group_reason_enums` test rather than duplicating it.
- Fail-closed behavior is mandatory for undeclared reason, invalid param, and invalid symbol format — each asserts both the HTTP status and the machine `code`.
- No new test file per REQ; extend the four existing classification test modules (`test_classifier_reason_codes.py`, `test_classification_mapper.py`, `test_classification_route.py`) per `knowledge/testing-policy.md`.

## Requirement Traceability

| Requirement | Design decision |
|-------------|------------------|
| REQ-001 | `reason` becomes `<Group>SignalMessageRef` on each signal response |
| REQ-002 | MessageRef `code` typed as the existing per-group `*ReasonCode` enum |
| REQ-003 | `params: dict[...] = Field(default_factory=dict)`; mapper always sets it |
| REQ-004 | Mapper param validator (typed scalar / no-prose), reused pattern from `analysis-message-refs` |
| REQ-005 | Domain classifiers/models unchanged; extended domain test asserts no prose |
| REQ-006 | Mapper raises `UndeclaredClassificationReasonError` on unknown code (unchanged) |
| REQ-007 | Mapper raises `InvalidClassificationMessageParamsError` on invalid param |
| REQ-008 | Classification-only 500 handler adds `detail.code = classification.undeclared_reason` |
| REQ-009 | Classification-only 500 handler adds `detail.code = classification.invalid_message_params` |
| REQ-010 | Both classification route 422 sites emit `ClassificationErrorDetail` with `code = classification.invalid_symbol_format` |
| REQ-011 | `ClassificationErrorCode` `StrEnum` on the classification HTTP error contract |
| REQ-012 | FastAPI `response_model=MarketClassificationResponse` regenerates OpenAPI from the updated DTOs |
| REQ-013 | Route path, top-level keys, `source`/`score` fields, hyphen rules unchanged |
| REQ-014 | OpenAPI + HTTP responses are the documented client-facing contract |
| REQ-015 | No copy-resolution call added anywhere in the classification path |
| REQ-016 | Success-path tests for BTC-USDT / ETH-USDT assert MessageRef shape and membership |
| NFR-001 | No FastAPI/Pydantic in `modules/` (unchanged; existing guard test) |
| NFR-002 | DTOs and error codes live under `infrastructure/http/dtos/classification.py` |
| NFR-003 | No edits to analysis DTOs/routes/handlers |
| NFR-004 | `parse_url_symbol` signature/behavior/message unchanged; only route-level handling of its exception changes |
| NFR-005 | 404 handler untouched |
| NFR-006 | Tests extend existing modules under `modules/classification/tests/` and `infrastructure/tests/` |
| NFR-007 | Strict typed DTOs; no `Any` |
| NFR-008 | No copy catalogs/resolve logic added |
| NFR-009 | `ClassificationSignal` stays frozen/slotted with `reason: str` |
