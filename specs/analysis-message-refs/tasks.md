# Tasks

## Implementation Tasks

- [x] **T-001** Add a stdlib domain `MessageRef` value object under `src/market_data_be/modules/analysis/` (`@dataclass(frozen=True, slots=True)`) with `code`, typed `params`, and optional `severity` / `channel`. *(REQ-004, REQ-006, NFR-001, NFR-008)*

- [x] **T-002** Inventory analysis catalog/assessment builders that emit English for `catalog_reason` / `hard_gate_reason` (and any other analysis HTTP narrative English found); define the closed set of wire codes and param keys; replace English emission with domain `MessageRef` construction using typed params only. *(REQ-001, REQ-004, REQ-005, REQ-009, REQ-015)*

- [x] **T-003** Update domain catalog/assessment models so in-scope narrative fields hold `MessageRef` / `MessageRef | None` instead of prose strings; keep strategy id lists and non-narrative assessment fields as structured data. *(REQ-002, REQ-003, REQ-004, REQ-015)*

- [x] **T-004** Define `MessageRefResponse` and `AnalysisNarrativeMessageCode` (`StrEnum` or equivalent Literal closed set) in infrastructure HTTP DTOs; update `CatalogResultResponse.catalog_reason` and `hard_gate_reason` to MessageRef types. *(REQ-002, REQ-003, REQ-006, REQ-008, NFR-002, NFR-006)*

- [x] **T-005** Update `map_analysis_result_to_response` to map domain MessageRefs to `MessageRefResponse`, reject undeclared codes, reject prose/non-scalar params, and never serialize English strings on in-scope narrative fields. *(REQ-005, REQ-010, REQ-011)*

- [x] **T-006** Ensure analysis route / app exception handling maps MessageRef contract failures to HTTP 500 without returning HTTP 200 containing invalid narrative; preserve 422/404 and existing undeclared-regime/reason 500 behavior. *(REQ-011, REQ-014, NFR-004)*

- [x] **T-007** Add analysis domain unit tests asserting builders emit only MessageRefs for in-scope narrative, codes belong to the closed set, and params are typed scalars without prose. *(REQ-004, REQ-005, REQ-009, REQ-016, NFR-005)*

- [x] **T-008** Add infrastructure tests that: (a) assert OpenAPI documents MessageRef shape and narrative code enums; (b) assert successful GET analysis for BTC-USDT and ETH-USDT returns MessageRefs (or null hard gate) on catalog narrative fields; (c) assert mapper/route fail-closed yields HTTP 500 for undeclared codes and for prose params; (d) regression-check 422/404, top-level response shape, and regime closed sets. *(REQ-007, REQ-008, REQ-012, REQ-014, REQ-016, NFR-004, NFR-005)*

- [x] **T-009** Confirm classification HTTP DTOs are untouched, no display-copy catalogs/resolve were added to the backend, and strategy/numeric structured fields were not unnecessarily wrapped as MessageRefs. *(REQ-013, REQ-015, NFR-003, NFR-007)*

## Task order

1. T-001 → T-002 → T-003 (domain MessageRef + emission inventory)
2. T-004 → T-005 → T-006 (HTTP DTO + mapper + error path)
3. T-007 → T-008 (domain and infrastructure tests)
4. T-009 (scope check)

## Traceability summary

| Requirement | Tasks |
|-------------|-------|
| REQ-001 | T-002 |
| REQ-002 | T-003, T-004 |
| REQ-003 | T-003, T-004 |
| REQ-004 | T-001, T-002, T-003, T-007 |
| REQ-005 | T-002, T-005, T-007 |
| REQ-006 | T-001, T-004 |
| REQ-007 | T-008 |
| REQ-008 | T-004, T-008 |
| REQ-009 | T-002, T-007 |
| REQ-010 | T-005 |
| REQ-011 | T-005, T-006 |
| REQ-012 | T-008 |
| REQ-013 | T-009 |
| REQ-014 | T-006, T-008 |
| REQ-015 | T-002, T-003, T-009 |
| REQ-016 | T-007, T-008 |
| NFR-001 | T-001 |
| NFR-002 | T-004 |
| NFR-003 | T-009 |
| NFR-004 | T-006, T-008 |
| NFR-005 | T-007, T-008 |
| NFR-006 | T-004 |
| NFR-007 | T-009 |
| NFR-008 | T-001 |
