# Design

## Overview

Refine the existing classification HTTP contract so signal `reason` values are closed sets documented in OpenAPI. Keep the `classification-api` route, composition, and top-level response shape. Change infrastructure HTTP DTOs to use **per-group signal response models** with group-specific reason enums (or Literals), update the infrastructure mapper to validate reasons against those sets and fail closed on undeclared codes, and align domain classifiers so they emit only the declared codes. Domain `ClassificationSignal.reason` remains `str`.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|--------------------------------|
| Classification domain | `src/market_data_be/modules/classification/` | Classifiers emit only declared reason code strings; domain model `reason` stays `str` |
| Application | `src/market_data_be/application/` | Unchanged orchestration (`ClassifyMarket`); no HTTP DTOs |
| Infrastructure — HTTP DTOs | `src/market_data_be/infrastructure/http/dtos/` | Closed-set reason types; per-group signal DTOs; OpenAPI enum surface |
| Infrastructure — HTTP mappers | `src/market_data_be/infrastructure/http/mappers/` | Map `ClassificationResult` → response DTOs; reject undeclared reasons |
| Infrastructure — HTTP routes | `src/market_data_be/infrastructure/http/routes/` | Unchanged path/handler shape; undeclared-reason failures surface as HTTP 500 |
| Analysis domain / analysis HTTP | — | **Out of scope** |

### Approach choice: per-group signal DTOs

| Option | Pros | Cons |
|--------|------|------|
| A. Shared `ClassificationSignalResponse` with one union/enum of all reason codes | Single signal model; minimal DTO churn | OpenAPI lists every code on every group’s `reason`; FE cannot tell which codes belong to which group from schema alone |
| **B. Per-group signal DTOs with domain-specific reason enums (chosen)** | OpenAPI documents the exact allowed codes per `regime` / `risk` / `economic` / `exposure`; stricter FE mapping SoT; mapper can validate per group | Slightly more DTO types |

**Decision:** Option B — per-group signal response models, each with its own closed reason type. Justifies REQ-002, REQ-003, and REQ-009 (FE derives group-accurate codes from OpenAPI without reading domain code).

### Components to change

```
src/market_data_be/
├── modules/classification/
│   ├── classifiers/                 # ENSURE: emit only declared reason strings
│   ├── models/                      # UNCHANGED shape: ClassificationSignal.reason: str
│   └── tests/                       # ADD/EXTEND: reason-code membership tests
└── infrastructure/
    ├── http/
    │   ├── dtos/classification.py   # MODIFY: per-group reason types + signal DTOs
    │   ├── mappers/classification.py # MODIFY: validate reasons; fail closed
    │   └── routes/classification.py # KEEP path/response_model wiring; 500 on mapper failure
    └── tests/                       # EXTEND: OpenAPI enums, success reasons, fail-closed
```

### Placement rationale

| Decision | Rationale | Requirements |
|----------|-----------|--------------|
| Closed sets on HTTP DTOs only | Public contract / OpenAPI SoT; domain stays framework-free | REQ-001, REQ-008, NFR-001, NFR-002 |
| Per-group reason enums | Stricter OpenAPI; FE maps codes per signal group | REQ-002, REQ-003, REQ-009 |
| Domain `reason` remains `str` | Avoid Pydantic/HTTP coupling in modules; classifiers use stable string literals | REQ-004, REQ-008 |
| Mapper validates and fails closed | Never serialize undeclared codes on HTTP 200 | REQ-005, REQ-006 |
| No analysis HTTP changes | Separate feature `analysis-reason-codes` | NFR-003 |
| Preserve endpoint shape | Compatibility with existing FE consumers of `classification-api` | REQ-007, NFR-004 |

### Out of scope (explicit)

- Analysis regime labels and analysis reason codes (`analysis-reason-codes`)
- Changing URL symbol parsing, 422/404 semantics, or route path
- Changing top-level keys of `MarketClassificationResponse`
- Authentication, live providers, or fixture JSON content changes (unless a fixture-driven test needs no content change)
- Requiring domain models to use Enum for `reason`

## Data Flow

### Successful classification (unchanged pipeline, tightened DTO)

```
Client
  │
  │  GET /markets/BTC-USDT/classification
  ▼
classification router
  │
  ├─► parse_url_symbol → internal "BTC/USDT"
  ├─► ClassifyMarket.execute(...)
  │         → ClassificationResult (domain signals with str reasons)
  ├─► map_market_classification_to_response(...)
  │         ├─► for each group, validate reason ∈ group closed set
  │         └─► build per-group signal DTOs (typed reasons)
  ▼
HTTP 200 + MarketClassificationResponse
  (OpenAPI enums document allowed reasons per group)
```

### Undeclared reason (fail closed)

```
ClassificationResult with signal.reason = "unknown_code" in a group list
  → mapper raises UndeclaredClassificationReasonError (or dedicated ValueError subtype)
  → exception handler → HTTP 500
  → no HTTP 200 body containing "unknown_code"
```

Classifier emission is aligned so this path is exceptional (defect), not normal fixture behavior.

## Interfaces

### HTTP: `GET /markets/{symbol}/classification` (unchanged path)

| Attribute | Value |
|-----------|-------|
| Method | `GET` |
| Path | `/markets/{symbol}/classification` |
| Success | `200` + `MarketClassificationResponse` |
| Client validation failure | `422` (URL symbol format; unchanged) |
| Not found | `404` (unchanged) |
| Undeclared reason / unexpected | `500` |

### HTTP response DTOs

**Location:** `src/market_data_be/infrastructure/http/dtos/classification.py`

Use `enum.StrEnum` (Python 3.12+) **or** `typing.Literal` unions. Prefer `StrEnum` so OpenAPI emits named enum schemas; Literals are acceptable if they produce equivalent `enum` arrays in OpenAPI.

```python
from enum import StrEnum
from pydantic import BaseModel


class RegimeReasonCode(StrEnum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    CHAOTIC = "chaotic"
    NEWS_SPIKE = "news_spike"


class RiskReasonCode(StrEnum):
    LOW_RISK = "low_risk"
    MODERATE_RISK = "moderate_risk"
    ELEVATED_RISK = "elevated_risk"
    HIGH_RISK = "high_risk"


class EconomicReasonCode(StrEnum):
    STRONG_EDGE = "strong_edge"
    MODERATE_EDGE = "moderate_edge"
    NEUTRAL_EDGE = "neutral_edge"
    NEGATIVE_EDGE = "negative_edge"


class ExposureReasonCode(StrEnum):
    AMPLE_CAPACITY = "ample_capacity"
    LIMITED_CAPACITY = "limited_capacity"
    CONSTRAINED_CAPACITY = "constrained_capacity"


class RegimeSignalResponse(BaseModel):
    source: str
    score: float
    reason: RegimeReasonCode


class RiskSignalResponse(BaseModel):
    source: str
    score: float
    reason: RiskReasonCode


class EconomicSignalResponse(BaseModel):
    source: str
    score: float
    reason: EconomicReasonCode


class ExposureSignalResponse(BaseModel):
    source: str
    score: float
    reason: ExposureReasonCode


class MarketClassificationResponse(BaseModel):
    symbol: str
    regime: list[RegimeSignalResponse]
    risk: list[RiskSignalResponse]
    economic: list[EconomicSignalResponse]
    exposure: list[ExposureSignalResponse]
```

**Member values** (wire strings) must match REQ-003 exactly. Enum **member names** may be SCREAMING_SNAKE; JSON/OpenAPI values are the lowercase codes above.

**Example success fragment:**

```json
{
  "symbol": "BTC/USDT",
  "regime": [{ "source": "regime", "score": 0.4, "reason": "trend_up" }],
  "risk": [{ "source": "risk", "score": 0.0, "reason": "low_risk" }],
  "economic": [{ "source": "economic", "score": 0.0, "reason": "neutral_edge" }],
  "exposure": [{ "source": "exposure", "score": 0.0, "reason": "ample_capacity" }]
}
```

### OpenAPI contract expectation

For each group’s signal schema, the `reason` property shall appear with an `enum` array listing that group’s codes (and only those codes). Clients treat this as the source of truth for localization maps.

### Infrastructure mapper

**Location:** `src/market_data_be/infrastructure/http/mappers/classification.py`

```python
def map_market_classification_to_response(
    classification: ClassificationResult,
) -> MarketClassificationResponse:
    ...
```

**Behavior:**

1. Map `symbol` unchanged (slash-separated).
2. For each domain signal in `regime`, `risk`, `economic`, `exposure`, map `source` and `score` as today.
3. Convert `reason` to the corresponding group enum:
   - If the string equals a declared enum value, accept.
   - If not, raise `UndeclaredClassificationReasonError` (preferred) or a dedicated exception type defined in infrastructure; do not coerce, strip, or substitute a default reason.
4. Never return a `MarketClassificationResponse` that contains an undeclared reason.

**Observable fail-closed outcome:** route/exception handling maps the mapper exception to **HTTP 500** with a generic `detail` (do not require echoing the undeclared code to the client). Tests assert status 500 and absence of a 200 body with the bad code.

### Domain classifiers

**Location:** `src/market_data_be/modules/classification/classifiers/`

- Keep emitting stable machine codes as plain strings on `ClassificationSignal.reason`.
- Align emitted strings with REQ-003 for each classifier’s group.
- Optional (recommended): module-level string constants in the classification domain (stdlib only) that duplicate the wire values for classifier use — **must match** HTTP enum values character-for-character. Domain must **not** import infrastructure DTOs.

`ClassificationSignal` remains:

```text
source: str
score: float
reason: str
```

### Exception handling

| Condition | HTTP | Notes |
|-----------|------|-------|
| Undeclared reason during mapping | 500 | New fail-closed path for this feature |
| Invalid URL symbol | 422 | Unchanged (`classification-api`) |
| Market data not found | 404 | Unchanged |
| Other unexpected errors | 500 | Unchanged |

Register handling for the mapper’s undeclared-reason exception if it is not already covered by a generic `Exception` → 500 handler. Prefer an explicit handler for clarity in tests.

## Data Model

### Public (HTTP)

```
MarketClassificationResponse
├── symbol: str
├── regime: RegimeSignalResponse[]      # reason: RegimeReasonCode
├── risk: RiskSignalResponse[]          # reason: RiskReasonCode
├── economic: EconomicSignalResponse[]  # reason: EconomicReasonCode
└── exposure: ExposureSignalResponse[]  # reason: ExposureReasonCode
```

### Closed reason sets (wire values)

| Group | Allowed `reason` values |
|-------|-------------------------|
| regime | `trend_up`, `trend_down`, `range`, `chaotic`, `news_spike` |
| risk | `low_risk`, `moderate_risk`, `elevated_risk`, `high_risk` |
| economic | `strong_edge`, `moderate_edge`, `neutral_edge`, `negative_edge` |
| exposure | `ample_capacity`, `limited_capacity`, `constrained_capacity` |

No other reason strings are part of the public contract.

### Internal (domain, unchanged typing)

```
ClassificationResult
└── regime | risk | economic | exposure: tuple[ClassificationSignal, ...]

ClassificationSignal
├── source: str
├── score: float
└── reason: str   # must be a member of the group’s closed set at emission time
```

No persistence or state transitions; each request remains compute-on-demand.

## Error Handling

| Scenario | Component | Observable result |
|----------|-----------|-------------------|
| Classifier emits declared code | Classifier + mapper | HTTP 200; `reason` is enum value |
| Classifier emits undeclared code | Mapper | Fail closed → HTTP 500; no success body with that code |
| Pydantic validation of crafted DTO with bad reason | DTO construction | Validation error (mapper must not swallow by using unconstrained `str`) |
| Malformed URL symbol | `parse_url_symbol` | HTTP 422 (unchanged) |
| Unknown symbol | Provider | HTTP 404 (unchanged) |

Recovery: no retries, no defaulting unknown reasons to a fallback code, no partial omission of the offending signal while returning 200 for the rest.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| OpenAPI enum documentation | `infrastructure/tests/` | Load app OpenAPI; assert each group signal schema’s `reason.enum` (or equivalent `$ref` enum) equals the REQ-003 set for that group |
| Success reasons membership | `infrastructure/tests/` | GET BTC-USDT / ETH-USDT classification → 200; every signal `reason` ∈ group set |
| Mapper fail-closed | `infrastructure/tests/` (unit) | Feed mapper a `ClassificationResult` with undeclared reason → raises; route test with patched result → HTTP 500 |
| Classifier emission | `modules/classification/.../tests/` | For each classifier, assert produced `reason` values are subset of the group’s declared set (table-driven over inputs as needed) |
| Domain purity | infrastructure or existing guard | No new FastAPI/Pydantic imports under `modules/` |
| Regression | `infrastructure/tests/` | 422 / 404 paths still pass; response still has four groups and `source` / `score` / `reason` |

**Coverage expectations:**

- AC-001 through AC-008 each have at least one automated test or static assertion.
- OpenAPI enum presence is mandatory (not only runtime 200 smoke).
- Fail-closed mapper behavior is mandatory.
- Classifier membership tests cover all four groups.

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | Per-group signal DTOs with `StrEnum` / Literal `reason` fields |
| REQ-002 | FastAPI/`response_model` generates OpenAPI enums from those types |
| REQ-003 | Enum member values exactly match the four group tables |
| REQ-004 | Classifier implementations emit only those string codes; domain tests enforce membership |
| REQ-005 | Mapper validates reason against group enum; rejects undeclared |
| REQ-006 | Undeclared reason → HTTP 500; no 200 with undeclared code |
| REQ-007 | Path, top-level keys, and signal field names unchanged from `classification-api` |
| REQ-008 | Domain `ClassificationSignal.reason` stays `str`; enums live in HTTP DTOs |
| REQ-009 | OpenAPI is the documented SoT; no domain import required for clients |
| REQ-010 | Integration tests assert success responses only use declared codes |
| NFR-001 | No FastAPI/Pydantic in `modules/` |
| NFR-002 | DTO closed sets under `infrastructure/http/dtos/` |
| NFR-003 | Analysis HTTP / analysis reason codes untouched |
| NFR-004 | 422/404 behavior preserved |
| NFR-005 | Tests under module and infrastructure `tests/` with pytest |
| NFR-006 | Strict typed DTOs; no `Any` |
