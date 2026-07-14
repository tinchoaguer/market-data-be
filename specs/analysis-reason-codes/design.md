# Design

## Overview

Refine the existing analysis HTTP contract so `RegimeAssessmentResponse.regime` and `RegimeAssessmentResponse.reasons` items are closed sets documented in OpenAPI. Keep the `market-data-analysis-api` route, composition, and top-level response shape. Change infrastructure HTTP DTOs to use `StrEnum` (or `Literal`) for regime label and reason code types, update the infrastructure analysis mapper to validate regime and reasons against those sets and fail closed on undeclared values, and align `RegimeDetector` so it emits only the declared reason codes. Domain `RegimeAssessment.reasons` remains `tuple[str, ...]` (or equivalent plain strings). Domain may continue to use `MarketRegime` for the regime label; closed-set typing for the public contract lives on the HTTP DTO.

Mirror the fail-closed HTTP 500 pattern established by completed feature `classification-reason-codes`. Do not reopen or modify that feature.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|--------------------------------|
| Analysis domain | `src/market_data_be/modules/analysis/` | `RegimeDetector` emits only declared reason code strings; domain reasons stay plain strings; regime label remains domain `MarketRegime` (or equivalent) |
| Application | `src/market_data_be/application/` | Unchanged orchestration (`AnalyzeMarket`); no HTTP DTOs |
| Infrastructure — HTTP DTOs | `src/market_data_be/infrastructure/http/dtos/` | Closed-set regime and reason types on `RegimeAssessmentResponse`; OpenAPI enum surface |
| Infrastructure — HTTP mappers | `src/market_data_be/infrastructure/http/mappers/` | Map `AnalysisResult` → response DTOs; reject undeclared regime or reasons |
| Infrastructure — HTTP routes | `src/market_data_be/infrastructure/http/routes/` | Unchanged path/handler shape; undeclared-value failures surface as HTTP 500 |
| Classification domain / classification HTTP | — | **Out of scope** |

### Approach choice: closed sets on HTTP DTOs

| Option | Pros | Cons |
|--------|------|------|
| A. Keep `regime: str` and `reasons: list[str]` | No DTO churn | OpenAPI has no enums; FE cannot derive SoT from schema |
| **B. `StrEnum` / `Literal` on `RegimeAssessmentResponse` only (chosen)** | OpenAPI documents exact allowed values; domain stays framework-free; matches `classification-reason-codes` pattern | Mapper must validate and fail closed |
| C. Force domain `RegimeAssessment.reasons` to Enum | Single type everywhere | Couples domain to HTTP contract style; violates domain purity expectations for public API SoT |

**Decision:** Option B — closed sets on the HTTP DTO surface only. Justifies REQ-001, REQ-002, REQ-003, REQ-011, and REQ-012.

### Components to change

```
src/market_data_be/
├── modules/analysis/
│   ├── analyzers/ (or regime detector location)  # ENSURE: emit only declared reason strings
│   ├── models/                                   # UNCHANGED reasons typing: plain str collection
│   └── tests/                                    # ADD/EXTEND: reason-code membership tests
└── infrastructure/
    ├── http/
    │   ├── dtos/analysis.py                      # MODIFY: regime + reasons closed sets
    │   ├── mappers/analysis.py                   # MODIFY: validate regime/reasons; fail closed
    │   └── routes/analysis.py                    # KEEP path/response_model wiring; 500 on mapper failure
    └── tests/                                    # EXTEND: OpenAPI enums, success values, fail-closed
```

### Placement rationale

| Decision | Rationale | Requirements |
|----------|-----------|--------------|
| Closed sets on HTTP DTOs only | Public contract / OpenAPI SoT; domain stays framework-free | REQ-001, REQ-002, REQ-011, NFR-001, NFR-002 |
| Prefer `StrEnum` | OpenAPI emits named enum schemas; Literals acceptable if equivalent `enum` arrays appear | REQ-003, REQ-012 |
| Domain reasons remain plain strings | Avoid Pydantic/HTTP coupling in modules; detector uses stable string literals | REQ-006, REQ-011 |
| Mapper validates and fails closed | Never serialize undeclared codes on HTTP 200 | REQ-007, REQ-008, REQ-009 |
| HTTP 500 on undeclared values | Align with `classification-reason-codes` observable behavior | REQ-009 |
| No classification HTTP changes | Separate completed feature | NFR-003 |
| Preserve endpoint shape | Compatibility with existing FE consumers of `market-data-analysis-api` | REQ-010, NFR-004 |
| Leave catalog/hard_gate/strategy/component keys unconstrained | Acceptance focuses on regime + regime reasons only | NFR-007 |

### Out of scope (explicit)

- Classification signal reason codes (`classification-reason-codes` — completed; do not reopen)
- Closed-set typing for `catalog_reason`, `hard_gate_reason`, strategy lists, or risk/economic component name keys
- Changing URL symbol parsing, 422/404 semantics, or route path
- Changing top-level keys of `MarketAnalysisResponse`
- Authentication, live providers, or fixture JSON content changes (unless a fixture-driven test needs no content change)
- Requiring domain `RegimeAssessment.reasons` to use Enum
- Changing risk/economic/exposure/catalog DTO shapes beyond what is required for the module to remain consistent after regime typing changes

## Data Flow

### Successful analysis (unchanged pipeline, tightened regime DTO)

```
Client
  │
  │  GET /markets/BTC-USDT/analysis
  ▼
analysis router
  │
  ├─► parse_url_symbol → internal "BTC/USDT"
  ├─► AnalyzeMarket.execute(...)
  │         → AnalysisResult (domain; RegimeAssessment with MarketRegime + str reasons)
  ├─► map_analysis_result_to_response(...)
  │         ├─► validate regime ∈ REQ-004 closed set
  │         ├─► validate each reason ∈ REQ-005 closed set
  │         └─► build RegimeAssessmentResponse (typed regime + reasons)
  ▼
HTTP 200 + MarketAnalysisResponse
  (OpenAPI enums document allowed regime and reason values)
```

### Undeclared regime or reason (fail closed)

```
AnalysisResult with regime label or reason code not in declared set
  → mapper raises UndeclaredAnalysisRegimeError / UndeclaredAnalysisReasonError
    (or a single dedicated undeclared-value exception type in infrastructure)
  → exception handler → HTTP 500
  → no HTTP 200 body containing the undeclared value
```

`RegimeDetector` emission is aligned so the fail-closed path is exceptional (defect), not normal fixture behavior.

## Interfaces

### HTTP: `GET /markets/{symbol}/analysis` (unchanged path)

| Attribute | Value |
|-----------|-------|
| Method | `GET` |
| Path | `/markets/{symbol}/analysis` |
| Success | `200` + `MarketAnalysisResponse` |
| Client validation failure | `422` (URL symbol format; unchanged) |
| Not found | `404` (unchanged) |
| Undeclared regime or reason / unexpected | `500` |

### HTTP response DTOs (regime subset)

**Location:** `src/market_data_be/infrastructure/http/dtos/analysis.py`

Use `enum.StrEnum` (Python 3.12+) **or** `typing.Literal` unions. Prefer `StrEnum` so OpenAPI emits named enum schemas; Literals are acceptable if they produce equivalent `enum` arrays in OpenAPI.

```python
from enum import StrEnum
from pydantic import BaseModel


class AnalysisRegimeLabel(StrEnum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    CHAOTIC = "CHAOTIC"
    NEWS_SPIKE = "NEWS_SPIKE"


class AnalysisRegimeReasonCode(StrEnum):
    INSUFFICIENT_CANDLES = "insufficient_candles"
    ADX_LOW_BAND = "adx_low_band"
    DEFAULT = "default"
    ABNORMAL_RANGE_OR_BODY = "abnormal_range_or_body"
    RELATIVE_VOLUME_SPIKE = "relative_volume_spike"
    RELATIVE_TRADES_SPIKE = "relative_trades_spike"
    VOLATILITY_EXPANSION = "volatility_expansion"
    LOW_ADX_HIGH_ATR = "low_adx_high_atr"
    FREQUENT_DIRECTION_CHANGES = "frequent_direction_changes"
    SMA_WHIPSAW = "sma_whipsaw"
    ADX_STRONG = "adx_strong"
    PLUS_DI_DOMINANT = "plus_di_dominant"
    MINUS_DI_DOMINANT = "minus_di_dominant"
    HH_HL_STRUCTURE = "hh_hl_structure"
    LH_LL_STRUCTURE = "lh_ll_structure"
    ABOVE_SMA_RISING = "above_sma_rising"
    BELOW_SMA_FALLING = "below_sma_falling"
    TAKER_BUY_FLOW = "taker_buy_flow"
    TAKER_SELL_FLOW = "taker_sell_flow"


class RegimeAssessmentResponse(BaseModel):
    regime: AnalysisRegimeLabel
    reasons: list[AnalysisRegimeReasonCode]
    # other existing public fields unchanged (e.g. insufficient_data)
    ...
```

**Member values** (wire strings) must match REQ-004 and REQ-005 exactly. Enum **member names** may be SCREAMING_SNAKE; JSON/OpenAPI values are the wire strings above.

**Regime wire values** are the SCREAMING_SNAKE labels from REQ-004 (not lowercase). If domain `MarketRegime` currently serializes with different casing, the mapper shall convert via an explicit, total mapping to REQ-004 wire values, or domain emission shall be aligned so `.value` matches REQ-004 character-for-character. Do not silently accept undeclared casing variants on success responses.

**Example success fragment (regime object only):**

```json
{
  "regime": "TREND_UP",
  "reasons": ["adx_strong", "plus_di_dominant", "hh_hl_structure"],
  "insufficient_data": false
}
```

Other nested assessment fields (`risk`, `economic`, `exposure`, `catalog`) remain as established by `market-data-analysis-api`; this feature does not introduce closed sets for those objects’ free-form or component-key fields.

### OpenAPI contract expectation

For the regime assessment schema:

- The `regime` property shall appear with an `enum` array listing exactly the REQ-004 labels.
- The `reasons` items (or items schema) shall appear with an `enum` array listing exactly the REQ-005 codes.

Clients treat these enums as the source of truth for localization maps.

### Infrastructure mapper

**Location:** `src/market_data_be/infrastructure/http/mappers/analysis.py`

```python
def map_analysis_result_to_response(
    analysis_result: AnalysisResult,
) -> MarketAnalysisResponse:
    ...
```

**Behavior for regime:**

1. Map other assessment/catalog fields as today (unchanged for out-of-scope fields).
2. Convert domain regime label to `AnalysisRegimeLabel`:
   - If the string equals a declared enum value (after any explicit total mapping from domain enum), accept.
   - If not, raise a dedicated undeclared-regime exception; do not coerce, strip, or substitute a default regime.
3. Convert each domain reason string to `AnalysisRegimeReasonCode`:
   - If the string equals a declared enum value, accept.
   - If not, raise a dedicated undeclared-reason exception; do not coerce, strip, substitute, or drop the offending item while returning 200.
4. Never return a `MarketAnalysisResponse` that contains an undeclared regime or reason.

**Observable fail-closed outcome:** route/exception handling maps the mapper exception to **HTTP 500** with a generic `detail` (do not require echoing the undeclared value to the client). Tests assert status 500 and absence of a 200 body with the bad value.

Preferred exception names (infrastructure-local): `UndeclaredAnalysisRegimeError` and `UndeclaredAnalysisReasonError`, or one shared `UndeclaredAnalysisContractValueError` with a clear message for tests. Align registration style with `classification-reason-codes` undeclared-reason handling.

### Domain: RegimeDetector

**Location:** under `src/market_data_be/modules/analysis/` (existing detector / analyzer that emits regime reasons)

- Keep emitting stable machine codes as plain strings on `RegimeAssessment.reasons`.
- Align emitted strings with REQ-005 exactly.
- Optional (recommended): module-level string constants in the analysis domain (stdlib only) that duplicate the wire values for detector use — **must match** HTTP enum values character-for-character. Domain must **not** import infrastructure DTOs.

Domain `RegimeAssessment` remains conceptually:

```text
regime: MarketRegime   # or equivalent domain enum
reasons: tuple[str, ...]
# other fields unchanged
```

### Exception handling

| Condition | HTTP | Notes |
|-----------|------|-------|
| Undeclared regime or reason during mapping | 500 | New fail-closed path for this feature |
| Invalid URL symbol | 422 | Unchanged (`market-data-analysis-api`) |
| Market data not found | 404 | Unchanged |
| Other unexpected errors | 500 | Unchanged |

Register handling for the mapper’s undeclared-value exception if it is not already covered by a generic `Exception` → 500 handler. Prefer an explicit handler for clarity in tests (same pattern as classification).

## Data Model

### Public (HTTP) — regime closed sets

```
MarketAnalysisResponse
├── symbol: str
├── regime: RegimeAssessmentResponse
│   ├── regime: AnalysisRegimeLabel          # closed set (REQ-004)
│   ├── reasons: AnalysisRegimeReasonCode[]  # closed set (REQ-005)
│   └── ... existing fields unchanged
├── risk: ...                                # out of scope for closed sets
├── economic: ...                            # out of scope for closed sets
├── exposure: ...                            # out of scope for closed sets
└── catalog: ...                             # out of scope for closed sets
```

### Closed sets (wire values)

| Field | Allowed values |
|-------|----------------|
| `regime.regime` | `TREND_UP`, `TREND_DOWN`, `RANGE`, `CHAOTIC`, `NEWS_SPIKE` |
| `regime.reasons[]` | `insufficient_candles`, `adx_low_band`, `default`, `abnormal_range_or_body`, `relative_volume_spike`, `relative_trades_spike`, `volatility_expansion`, `low_adx_high_atr`, `frequent_direction_changes`, `sma_whipsaw`, `adx_strong`, `plus_di_dominant`, `minus_di_dominant`, `hh_hl_structure`, `lh_ll_structure`, `above_sma_rising`, `below_sma_falling`, `taker_buy_flow`, `taker_sell_flow` |

No other regime labels or regime reason strings are part of the public contract for those fields.

### Internal (domain, unchanged typing for reasons)

```
AnalysisResult
└── regime: RegimeAssessment
    ├── regime: MarketRegime
    ├── reasons: tuple[str, ...]   # must be members of REQ-005 at emission time
    └── ...
```

No persistence or state transitions; each request remains compute-on-demand.

## Error Handling

| Scenario | Component | Observable result |
|----------|-----------|-------------------|
| Detector emits declared codes; regime in set | Detector + mapper | HTTP 200; typed enum values |
| Detector emits undeclared reason | Mapper | Fail closed → HTTP 500; no success body with that code |
| Domain regime not in REQ-004 | Mapper | Fail closed → HTTP 500; no success body with that label |
| Pydantic validation of crafted DTO with bad value | DTO construction | Validation error (mapper must not swallow by using unconstrained `str`) |
| Malformed URL symbol | `parse_url_symbol` | HTTP 422 (unchanged) |
| Unknown symbol | Provider | HTTP 404 (unchanged) |

Recovery: no retries, no defaulting unknown regimes/reasons to a fallback code, no partial omission of offending reasons while returning 200 for the rest.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| OpenAPI enum documentation | `infrastructure/tests/` | Load app OpenAPI; assert `regime.regime` enum equals REQ-004 set; assert `regime.reasons` items enum equals REQ-005 set |
| Success membership | `infrastructure/tests/` | GET BTC-USDT / ETH-USDT analysis → 200; `regime.regime` ∈ REQ-004; every `regime.reasons` item ∈ REQ-005 |
| Mapper fail-closed (regime) | `infrastructure/tests/` (unit) | Feed mapper an `AnalysisResult` with undeclared regime → raises; route test with patched result → HTTP 500 |
| Mapper fail-closed (reason) | `infrastructure/tests/` (unit) | Feed mapper an undeclared reason → raises; route test → HTTP 500 |
| RegimeDetector emission | `modules/analysis/.../tests/` | Assert produced reason values are subset of REQ-005 (table-driven over inputs as needed) |
| Domain purity | infrastructure or existing guard | No new FastAPI/Pydantic imports under `modules/` |
| Regression | `infrastructure/tests/` | 422 / 404 paths still pass; top-level response keys unchanged |

**Coverage expectations:**

- AC-001 through AC-009 each have at least one automated test or static assertion.
- OpenAPI enum presence is mandatory (not only runtime 200 smoke).
- Fail-closed mapper behavior is mandatory for both undeclared regime and undeclared reason.
- RegimeDetector membership tests cover emitted codes against REQ-005.

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | `RegimeAssessmentResponse.regime: AnalysisRegimeLabel` (`StrEnum` / Literal) |
| REQ-002 | `RegimeAssessmentResponse.reasons: list[AnalysisRegimeReasonCode]` |
| REQ-003 | FastAPI/`response_model` generates OpenAPI enums from those types |
| REQ-004 | `AnalysisRegimeLabel` member values exactly match the five labels |
| REQ-005 | `AnalysisRegimeReasonCode` member values exactly match the nineteen codes |
| REQ-006 | `RegimeDetector` emits only those string codes; domain tests enforce membership |
| REQ-007 | Mapper validates regime against closed set; rejects undeclared |
| REQ-008 | Mapper validates each reason against closed set; rejects undeclared |
| REQ-009 | Undeclared value → HTTP 500; no 200 with undeclared value |
| REQ-010 | Path, top-level keys, and regime field names unchanged from `market-data-analysis-api` |
| REQ-011 | Domain reasons stay plain strings; enums live in HTTP DTOs |
| REQ-012 | OpenAPI is the documented SoT; no domain import required for clients |
| REQ-013 | Integration tests assert success responses only use declared values |
| NFR-001 | No FastAPI/Pydantic in `modules/` |
| NFR-002 | DTO closed sets under `infrastructure/http/dtos/` |
| NFR-003 | Classification HTTP / classification reason codes untouched |
| NFR-004 | 422/404 behavior preserved |
| NFR-005 | Tests under module and infrastructure `tests/` with pytest |
| NFR-006 | Strict typed DTOs; no `Any` |
| NFR-007 | catalog_reason, hard_gate_reason, strategies, component keys out of closed-set scope |
