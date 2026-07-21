# Design

## Overview

Introduce a structured `MessageRef` contract on the analysis HTTP surface and replace catalog narrative strings (`catalog_reason`, `hard_gate_reason`) with MessageRefs. Analysis domain catalog/assessment builders emit stdlib MessageRef facts (stable semantic `code` + typed `params`) instead of interpolated English. Infrastructure HTTP DTOs expose a Pydantic `MessageRefResponse`, type narrative codes as a closed `StrEnum`, validate params, and map domain refs to the wire. OpenAPI documents the shape from FastAPI DTOs. The backend does not resolve display copy. Classification HTTP MessageRefs remain out of scope.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|--------------------------------|
| Analysis domain | `src/market_data_be/modules/analysis/` | Define stdlib `MessageRef` value object; catalog/assessment builders emit MessageRefs (not English) for in-scope narrative; emit only declared codes and typed params |
| Application | `src/market_data_be/application/` | Unchanged orchestration (`AnalyzeMarket`); no HTTP DTOs; no display-copy resolve |
| Infrastructure — HTTP DTOs | `src/market_data_be/infrastructure/http/dtos/` | `MessageRefResponse`; closed narrative code enum; update `CatalogResultResponse` field types |
| Infrastructure — HTTP mappers | `src/market_data_be/infrastructure/http/mappers/` | Map domain MessageRefs → DTO; validate code membership and param constraints; fail closed |
| Infrastructure — HTTP routes | `src/market_data_be/infrastructure/http/routes/` | Unchanged path; undeclared/invalid MessageRef failures surface as HTTP 500 |
| Classification HTTP | — | **Out of scope** (unchanged DTOs) |

### Approach choice: MessageRef on narrative fields

| Option | Pros | Cons |
|--------|------|------|
| A. Keep English strings; clients keep ad-hoc labels | No BE churn | BE remains language-coupled |
| **B. MessageRef on catalog narrative fields; closed code enum on HTTP DTO (chosen)** | OpenAPI SoT; domain language-agnostic | Breaking type change for `catalog_reason` / `hard_gate_reason` |
| C. Resolve text in BE and return localized strings | Clients simpler short-term | Couples BE to copy catalogs; blocked by NFR-007 / REQ-013 |

**Decision:** Option B. Justifies REQ-001–REQ-013 and NFR-007.

### Components to change

```
src/market_data_be/
├── modules/analysis/
│   ├── models/ (or messaging/)     # NEW: MessageRef dataclass (stdlib)
│   ├── catalog / assessment builders  # MODIFY: emit MessageRef, remove English f-strings
│   └── tests/                      # ADD/EXTEND: no prose; code + param membership
└── infrastructure/
    ├── http/
    │   ├── dtos/analysis.py        # MODIFY: MessageRefResponse; catalog fields; code enum
    │   ├── mappers/analysis.py     # MODIFY: map MessageRefs; validate; fail closed
    │   └── routes/analysis.py      # KEEP path; ensure 500 on mapper contract failures
    └── tests/                      # EXTEND: OpenAPI, success refs, fail-closed, regression
```

### Placement rationale

| Decision | Rationale | Requirements |
|----------|-----------|--------------|
| Stdlib MessageRef in analysis domain | Domain emits facts without frameworks; matches architecture purity | REQ-004, NFR-001, NFR-008 |
| Closed code enum on HTTP DTO | OpenAPI SoT for clients; domain may use plain string constants that match wire values | REQ-008, REQ-009, REQ-012, NFR-002 |
| Keep field names `catalog_reason` / `hard_gate_reason` | Minimize rename churn; type change alone signals the new contract | REQ-002, REQ-003, REQ-014 |
| Params as object of scalar typed values | Carries former interpolants without prose | REQ-005 |
| Optional `severity` / `channel` | Aligns with product MessageRef contract; not required for UI v1 emission | REQ-006 |
| No display-copy resolve in BE | Backend emits MessageRefs only | REQ-013, NFR-007 |
| Leave strategy lists and numeric assessments as data | Already machine-structured; clients may label codes later without wrapping every id as MessageRef | REQ-015 |
| Fail closed on undeclared code / prose params | Never ship invalid narrative on HTTP 200 | REQ-010, REQ-011 |

### Out of scope (explicit)

- Classification HTTP MessageRefs
- Display-copy catalogs, templates, or resolve in this repository
- Reworking `regime.regime` / `regime.reasons` closed sets into MessageRefs (already machine codes from `analysis-reason-codes`)
- Wrapping strategy id lists or numeric component pairs as MessageRefs when they are not English prose
- Authentication, live providers, fixture JSON content changes (unless a test needs no content change)
- Email/push/SMS channel delivery

### Code inventory process (deterministic)

Before finalizing the HTTP code enum, inventory every analysis catalog/assessment emission site that today builds English for `catalog_reason` or `hard_gate_reason` (and any other analysis HTTP field found to carry interpolated English). For each distinct narrative intent:

1. Assign one stable semantic code using dotted naming: `catalog.<intent>` or `catalog.hard_gate.<intent>` (e.g. `catalog.strategy_allowed`).
2. Move former format interpolants into `params` as typed scalars (strategy ids, regime labels, numbers, booleans).
3. Add the code to the HTTP closed enum and to domain string constants (must match character-for-character).

The definitive closed set is the complete inventory result. Do not leave any English-producing branch for in-scope fields.

## Data Flow

### Successful analysis (MessageRef narrative)

```
Client
  │
  │  GET /markets/BTC-USDT/analysis
  ▼
analysis router
  │
  ├─► parse_url_symbol → internal "BTC/USDT"
  ├─► AnalyzeMarket.execute(...)
  │         → AnalysisResult
  │              catalog builders emit MessageRef (code + typed params)
  │              (no interpolated English on narrative fields)
  ├─► map_analysis_result_to_response(...)
  │         ├─► validate MessageRef.code ∈ closed narrative code set
  │         ├─► validate params are typed scalars (no prose)
  │         └─► CatalogResultResponse.catalog_reason / hard_gate_reason as MessageRefResponse
  ▼
HTTP 200 + MarketAnalysisResponse
  (OpenAPI documents MessageRef + code enums)
```

### Undeclared code or prose params (fail closed)

```
Domain MessageRef with undeclared code
  OR params containing prose / non-scalar display English
  → mapper raises dedicated contract error
  → exception handler → HTTP 500
  → no HTTP 200 body containing the invalid narrative
```

## Interfaces

### HTTP: `GET /markets/{symbol}/analysis` (unchanged path)

| Attribute | Value |
|-----------|-------|
| Method | `GET` |
| Path | `/markets/{symbol}/analysis` |
| Success | `200` + `MarketAnalysisResponse` |
| Client validation failure | `422` (URL symbol format; unchanged) |
| Not found | `404` (unchanged) |
| Undeclared MessageRef code / invalid params / undeclared regime-reason (prior feature) | `500` |

### MessageRef wire shape

**Product contract (v1):**

```text
MessageRef = { code, params?, severity?, channel? }
```

**HTTP DTO (this Feature):** `params` is always present (may be empty object) so OpenAPI and clients have a stable required pair `code` + `params`.

**Location:** `src/market_data_be/infrastructure/http/dtos/analysis.py` (shared MessageRef model may live in the same module or a small sibling DTO module under `http/dtos/`).

```python
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field


class AnalysisNarrativeMessageCode(StrEnum):
    # Closed set = inventory of catalog/hard-gate narrative intents.
    # Member *values* are wire codes (e.g. "catalog.strategy_allowed").
    ...


MessageParamValue = str | int | float | bool


class MessageRefResponse(BaseModel):
    code: AnalysisNarrativeMessageCode
    params: dict[str, MessageParamValue] = Field(default_factory=dict)
    severity: Literal["info", "warning", "error"] | None = None
    channel: Literal["ui", "email", "push", "sms", "log"] | None = None
```

**Param rules (enforced in mapper and/or domain builders):**

| Allowed | Forbidden |
|---------|-----------|
| Enum/id wire tokens (e.g. strategy ids, `TREND_UP`) | Multi-word display English sentences |
| Numbers (int/float) | Nested objects/arrays in params for v1 |
| Booleans | HTML/markdown/prose strings |

Practical check for string params: values must be machine tokens (no whitespace; prefer `snake_case`, `SCREAMING_SNAKE`, or existing strategy/regime wire tokens). Reject strings that contain spaces or sentence punctuation used for display English.

### Catalog DTO update

```python
class CatalogResultResponse(BaseModel):
    allowed_strategies: list[str]
    forbidden_strategies: list[str]
    preferred_strategy: str
    catalog_reason: MessageRefResponse
    hard_gate_reason: MessageRefResponse | None
```

**Example success fragment (catalog only):**

```json
{
  "allowed_strategies": ["trend_following"],
  "forbidden_strategies": ["mean_reversion"],
  "preferred_strategy": "trend_following",
  "catalog_reason": {
    "code": "catalog.strategy_allowed",
    "params": {
      "strategy": "trend_following",
      "regime": "TREND_UP"
    }
  },
  "hard_gate_reason": null
}
```

Exact codes and param keys are those produced by the inventory; the example illustrates shape only. Tests assert shape, closed-set membership, and absence of English strings on those fields.

### Domain MessageRef

**Location:** under `src/market_data_be/modules/analysis/` (e.g. `models/message_ref.py`)

```python
@dataclass(frozen=True, slots=True)
class MessageRef:
    code: str
    params: tuple[tuple[str, str | int | float | bool], ...] = ()
    severity: str | None = None
    channel: str | None = None
```

- Catalog/assessment models that previously held `str` narrative shall hold `MessageRef` (and `MessageRef | None` for hard gate).
- Domain may define string constants for codes that match `AnalysisNarrativeMessageCode` wire values character-for-character.
- Domain must **not** import infrastructure DTOs.

### Infrastructure mapper

**Location:** `src/market_data_be/infrastructure/http/mappers/analysis.py`

Extend `map_analysis_result_to_response`:

1. Map non-narrative fields as today (including regime closed-set validation from `analysis-reason-codes`).
2. Convert each in-scope domain `MessageRef` to `MessageRefResponse`:
   - Resolve `code` to `AnalysisNarrativeMessageCode`; if missing → raise undeclared-code error.
   - Convert params to `dict[str, MessageParamValue]`; reject non-scalars and prose string values.
3. Never return HTTP 200 with English narrative strings on `catalog_reason` / `hard_gate_reason`.

Preferred exception names (infrastructure-local): `UndeclaredAnalysisMessageCodeError`, `InvalidAnalysisMessageParamsError`, or one shared `UndeclaredAnalysisContractValueError`. Map to HTTP 500 consistently with existing undeclared-regime/reason handling.

### OpenAPI

1. FastAPI `response_model=MarketAnalysisResponse` generates MessageRef schema and code enums.
2. Infrastructure tests assert the app OpenAPI document includes `MessageRefResponse` (or equivalent title) and catalog narrative fields reference it (REQ-007, REQ-012).

### Exception handling

| Condition | HTTP | Notes |
|-----------|------|-------|
| Undeclared MessageRef code or invalid params | 500 | New fail-closed path |
| Undeclared regime/reason (prior feature) | 500 | Unchanged |
| Invalid URL symbol | 422 | Unchanged |
| Market data not found | 404 | Unchanged |
| Other unexpected errors | 500 | Unchanged |

## Data Model

### Public (HTTP) — narrative subset

```
MarketAnalysisResponse
├── symbol: str
├── regime: RegimeAssessmentResponse          # unchanged closed sets
├── risk: RiskAssessmentResponse              # structured data unchanged
├── economic: EconomicAssessmentResponse      # structured data unchanged
├── exposure: ExposureProfileResponse         # structured data unchanged
└── catalog: CatalogResultResponse
    ├── allowed_strategies: string[]          # machine strategy ids
    ├── forbidden_strategies: string[]
    ├── preferred_strategy: string
    ├── catalog_reason: MessageRefResponse    # WAS string prose
    └── hard_gate_reason: MessageRefResponse | null  # WAS string | null
```

### MessageRefResponse

```
MessageRefResponse
├── code: AnalysisNarrativeMessageCode   # closed set (REQ-008)
├── params: { [key: string]: string | number | boolean }
├── severity?: "info" | "warning" | "error"
└── channel?: "ui" | "email" | "push" | "sms" | "log"
```

### Internal (domain)

```
CatalogResult (conceptual)
├── ... strategy id fields ...
├── catalog_reason: MessageRef
└── hard_gate_reason: MessageRef | None
```

No persistence or state transitions; each request remains compute-on-demand.

## Error Handling

| Scenario | Component | Observable result |
|----------|-----------|-------------------|
| Builders emit declared MessageRefs with typed params | Domain + mapper | HTTP 200; MessageRef objects on catalog narrative fields |
| Undeclared MessageRef code | Mapper | Fail closed → HTTP 500 |
| Prose or non-scalar params | Mapper (and preferably domain tests) | Fail closed → HTTP 500 |
| Malformed URL symbol | `parse_url_symbol` | HTTP 422 (unchanged) |
| Unknown symbol | Provider | HTTP 404 (unchanged) |

Recovery: no retries, no defaulting unknown codes to a fallback English string, no silent coercion of prose into params.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| Domain emission | `modules/analysis/.../tests/` | Catalog/assessment builders produce MessageRef for narrative fields; codes ⊆ declared set; params are typed scalars; no English sentence strings |
| OpenAPI documentation | `infrastructure/tests/` | Analysis OpenAPI includes MessageRef schema; `catalog_reason` / `hard_gate_reason` reference it; code property has enum equal to closed set |
| Success membership | `infrastructure/tests/` | GET BTC-USDT / ETH-USDT analysis → 200; narrative fields are objects with `code`/`params`; `hard_gate_reason` null or MessageRef |
| Mapper fail-closed (code) | `infrastructure/tests/` | Undeclared code → raises / route → HTTP 500 |
| Mapper fail-closed (params) | `infrastructure/tests/` | Prose param → raises / route → HTTP 500 |
| Regression | `infrastructure/tests/` | 422 / 404; top-level keys; regime enums still present; classification routes untouched |
| Domain purity | guard | No new FastAPI/Pydantic imports under `modules/` |

**Coverage expectations:**

- AC-001 through AC-008 each have at least one automated test.
- OpenAPI MessageRef documentation is mandatory (app schema).
- Fail-closed behavior is mandatory for undeclared codes and prose params.
- Success tests assert MessageRef shape, not English substrings, on in-scope fields.

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | Narrative English → MessageRef on analysis HTTP DTOs |
| REQ-002 | `catalog_reason: MessageRefResponse` |
| REQ-003 | `hard_gate_reason: MessageRefResponse \| None` |
| REQ-004 | Domain builders emit MessageRef; remove f-string English |
| REQ-005 | Param scalar + no-prose validation |
| REQ-006 | `MessageRefResponse` with `code`, `params`, optional severity/channel |
| REQ-007 | FastAPI OpenAPI generation from updated DTOs |
| REQ-008 | `AnalysisNarrativeMessageCode` StrEnum on HTTP DTO |
| REQ-009 | Domain constants / emission ⊆ closed set |
| REQ-010 | Mapper rejects undeclared codes |
| REQ-011 | HTTP 500 fail-closed path |
| REQ-012 | OpenAPI is client SoT |
| REQ-013 | No display-copy resolve in analysis path |
| REQ-014 | Path, top-level keys, prior regime contracts preserved |
| REQ-015 | Strategy lists / numerics remain structured data |
| REQ-016 | Integration tests for mock symbols |
| NFR-001 | No FastAPI/Pydantic in `modules/` |
| NFR-002 | DTOs under `infrastructure/http/dtos/` |
| NFR-003 | Classification HTTP untouched |
| NFR-004 | 422/404 + prior 500 semantics preserved |
| NFR-005 | Tests under module/infrastructure `tests/` |
| NFR-006 | Strict typed DTOs; no `Any` |
| NFR-007 | No copy catalogs/resolve in BE |
| NFR-008 | Domain `MessageRef` frozen dataclass |
