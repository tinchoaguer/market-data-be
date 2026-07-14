# Tasks

## Implementation Tasks

- [x] **T-001** Define `AnalysisRegimeLabel` and `AnalysisRegimeReasonCode` as `StrEnum` or `Literal` in `src/market_data_be/infrastructure/http/dtos/analysis.py` with wire values exactly matching REQ-004 and REQ-005. *(REQ-001, REQ-002, REQ-004, REQ-005, NFR-002)*

- [x] **T-002** Update `RegimeAssessmentResponse` so `regime` uses `AnalysisRegimeLabel` and `reasons` uses `list[AnalysisRegimeReasonCode]` (or equivalent Literal closed sets); keep other regime assessment fields and top-level `MarketAnalysisResponse` keys unchanged. *(REQ-001, REQ-002, REQ-010)*

- [x] **T-003** Update `map_analysis_result_to_response` to convert domain regime label and each reason into the corresponding enums and raise dedicated undeclared-value errors when a value is not in the closed set (no defaulting, passthrough, or partial omission). *(REQ-007, REQ-008, REQ-009)*

- [x] **T-004** Ensure analysis route / app exception handling maps undeclared-regime and undeclared-reason mapper failures to HTTP 500 without returning HTTP 200 containing the undeclared value; preserve existing 422 and 404 behavior. *(REQ-009, REQ-010, NFR-004)*

- [x] **T-005** Align `RegimeDetector` so every emitted reason string is a member of the REQ-005 set; keep domain `RegimeAssessment.reasons` as a plain string collection (optional domain string constants allowed; no infrastructure imports). *(REQ-006, REQ-011, NFR-001)*

- [x] **T-006** Ensure domain regime label serialization (or mapper mapping from `MarketRegime`) produces REQ-004 wire values character-for-character on successful responses. *(REQ-004, REQ-007, REQ-013)*

- [x] **T-007** Add analysis domain unit tests asserting `RegimeDetector` only emits reasons belonging to the REQ-005 closed set. *(REQ-006, REQ-013, NFR-005)*

- [x] **T-008** Add infrastructure tests that: (a) assert OpenAPI documents `regime` and `reasons` enums matching REQ-004 and REQ-005; (b) assert successful GET analysis for BTC-USDT and ETH-USDT returns only declared regime and reasons; (c) assert mapper/route fail-closed yields HTTP 500 for undeclared regime and for undeclared reason; (d) regression-check 422/404 and top-level response shape. *(REQ-003, REQ-009, REQ-010, REQ-012, REQ-013, NFR-004, NFR-005, NFR-006)*

- [x] **T-009** Confirm classification HTTP DTOs and classification reason contracts are untouched, and that `catalog_reason`, `hard_gate_reason`, strategy lists, and risk/economic component keys were not brought into closed-set scope. *(NFR-003, NFR-007)*

## Task order

1. T-001 → T-002 (DTO contract first)
2. T-003 → T-004 (mapper + HTTP error path)
3. T-005 → T-006 → T-007 (domain emission alignment + tests)
4. T-008 (integration / OpenAPI / regression)
5. T-009 (scope check)

## Traceability summary

| Requirement | Tasks |
|-------------|-------|
| REQ-001 | T-001, T-002 |
| REQ-002 | T-001, T-002 |
| REQ-003 | T-008 |
| REQ-004 | T-001, T-006 |
| REQ-005 | T-001 |
| REQ-006 | T-005, T-007 |
| REQ-007 | T-003, T-006 |
| REQ-008 | T-003 |
| REQ-009 | T-003, T-004, T-008 |
| REQ-010 | T-002, T-004, T-008 |
| REQ-011 | T-005 |
| REQ-012 | T-008 |
| REQ-013 | T-006, T-007, T-008 |
| NFR-001 | T-005 |
| NFR-002 | T-001, T-002 |
| NFR-003 | T-009 |
| NFR-004 | T-004, T-008 |
| NFR-005 | T-007, T-008 |
| NFR-006 | T-008 |
| NFR-007 | T-009 |
