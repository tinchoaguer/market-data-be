# Tasks

## Implementation Tasks

- [x] **T-001** Define group-specific reason closed sets (`RegimeReasonCode`, `RiskReasonCode`, `EconomicReasonCode`, `ExposureReasonCode`) as `StrEnum` or `Literal` in `src/market_data_be/infrastructure/http/dtos/classification.py` with wire values exactly matching REQ-003. *(REQ-001, REQ-003)*

- [x] **T-002** Replace shared unconstrained signal `reason: str` with per-group signal response models (`RegimeSignalResponse`, `RiskSignalResponse`, `EconomicSignalResponse`, `ExposureSignalResponse`) and update `MarketClassificationResponse` list field types accordingly; keep `source`, `score`, and top-level keys unchanged. *(REQ-001, REQ-007)*

- [x] **T-003** Update `map_market_classification_to_response` to convert each domain signal `reason` into the corresponding group enum and raise a dedicated undeclared-reason error when the value is not in that group’s closed set (no defaulting or passthrough of unknown strings). *(REQ-005, REQ-006)*

- [x] **T-004** Ensure classification route / app exception handling maps undeclared-reason mapper failures to HTTP 500 without returning HTTP 200 containing the undeclared code; preserve existing 422 and 404 behavior. *(REQ-006, REQ-007, NFR-004)*

- [x] **T-005** Align regime, risk, economic, and exposure classifiers so every emitted `ClassificationSignal.reason` is a string from the corresponding REQ-003 set; keep domain `ClassificationSignal.reason` as `str` (optional domain string constants allowed; no infrastructure imports). *(REQ-004, REQ-008, NFR-001)*

- [x] **T-006** Add classification domain unit tests asserting each classifier only emits reasons belonging to its group’s closed set. *(REQ-004, REQ-010, NFR-005)*

- [x] **T-007** Add infrastructure tests that: (a) assert OpenAPI documents `reason` enums per group matching REQ-003; (b) assert successful GET classification for BTC-USDT and ETH-USDT returns only declared reasons; (c) assert mapper/route fail-closed yields HTTP 500 for an undeclared reason; (d) regression-check 422/404 and response shape. *(REQ-002, REQ-006, REQ-007, REQ-009, REQ-010, NFR-004, NFR-005, NFR-006)*

- [x] **T-008** Confirm analysis HTTP DTOs and analysis reason/regime contracts are untouched (no scope creep into `analysis-reason-codes`). *(NFR-003)*

## Task order

1. T-001 → T-002 (DTO contract first)
2. T-003 → T-004 (mapper + HTTP error path)
3. T-005 → T-006 (domain emission + tests)
4. T-007 (integration / OpenAPI / regression)
5. T-008 (scope check)

## Traceability summary

| Requirement | Tasks |
|-------------|-------|
| REQ-001 | T-001, T-002 |
| REQ-002 | T-007 |
| REQ-003 | T-001 |
| REQ-004 | T-005, T-006 |
| REQ-005 | T-003 |
| REQ-006 | T-003, T-004, T-007 |
| REQ-007 | T-002, T-004, T-007 |
| REQ-008 | T-005 |
| REQ-009 | T-007 |
| REQ-010 | T-006, T-007 |
| NFR-001 | T-005 |
| NFR-002 | T-001, T-002 |
| NFR-003 | T-008 |
| NFR-004 | T-004, T-007 |
| NFR-005 | T-006, T-007 |
| NFR-006 | T-007 |
