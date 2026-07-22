# Tasks

## Implementation Tasks

- [x] **T-001** In `src/market_data_be/infrastructure/http/dtos/classification.py`, add `MessageParamValue`, per-group `RegimeSignalMessageRef` / `RiskSignalMessageRef` / `EconomicSignalMessageRef` / `ExposureSignalMessageRef` models (`code` typed to the existing group `*ReasonCode` enum, `params: dict[str, MessageParamValue] = Field(default_factory=dict)`), and update `RegimeSignalResponse` / `RiskSignalResponse` / `EconomicSignalResponse` / `ExposureSignalResponse` so `reason` uses the corresponding `*SignalMessageRef` type instead of a bare `*ReasonCode`. *(REQ-001, REQ-002, REQ-003, NFR-002, NFR-007)*

- [x] **T-002** In the same file, add `ClassificationErrorCode` (`StrEnum`: `INVALID_SYMBOL_FORMAT`, `UNDECLARED_REASON`, `INVALID_MESSAGE_PARAMS` with dotted `classification.*` wire values) and `ClassificationErrorDetail` (`code`, `message`). *(REQ-010, REQ-011, NFR-002, NFR-007)*

- [x] **T-003** In `src/market_data_be/infrastructure/http/mappers/classification.py`, add `InvalidClassificationMessageParamsError` and a typed-scalar / no-prose param validator (reuse the `analysis-message-refs` machine-token check pattern); update each `_map_<group>_signals` function to build `params = {}` (validating any future non-empty entries) and construct the corresponding `*SignalMessageRef`, then wrap it as `reason` on the group's `*SignalResponse`. Keep the existing `UndeclaredClassificationReasonError` / `_parse_reason` behavior unchanged. *(REQ-001, REQ-003, REQ-004, REQ-006, REQ-007)*

- [x] **T-004** In `src/market_data_be/infrastructure/http/routes/classification.py`, update both 422 sites (`get_market_classification_slash_rejected` and the `parse_url_symbol` `except ValueError` branch in `get_market_classification`) to raise `HTTPException(422, detail=ClassificationErrorDetail(code=ClassificationErrorCode.INVALID_SYMBOL_FORMAT, message=...).model_dump())`. Do not modify `parse_url_symbol` or the analysis route. *(REQ-010, NFR-004)*

- [x] **T-005** In `src/market_data_be/infrastructure/http/app.py`, update the existing `undeclared_classification_reason_handler` to return `detail={"code": ClassificationErrorCode.UNDECLARED_REASON, "message": "An unexpected error occurred"}`, and register a new handler for `InvalidClassificationMessageParamsError` returning `detail={"code": ClassificationErrorCode.INVALID_MESSAGE_PARAMS, "message": "An unexpected error occurred"}`. Do not modify any analysis handler, the generic `Exception` handler, or the 404 handler. *(REQ-008, REQ-009, NFR-003, NFR-005)*

- [x] **T-006** Extend `src/market_data_be/modules/classification/tests/test_classifier_reason_codes.py` with an assertion (e.g. a regex/whitespace-punctuation check, reusing the `analysis-message-refs` machine-token pattern) that every classifier's emitted `reason` contains no whitespace or sentence punctuation, in addition to the existing closed-set membership checks. *(REQ-005)*

- [x] **T-007** Extend `src/market_data_be/infrastructure/tests/test_classification_mapper.py` with cases asserting: mapped `reason` is the expected `*SignalMessageRef` with `code` equal to the expected enum member and `params == {}`; a param violating the typed-scalar/no-prose rule raises `InvalidClassificationMessageParamsError`; existing undeclared-reason cases still raise `UndeclaredClassificationReasonError` with the updated response shape. *(REQ-001, REQ-002, REQ-003, REQ-004, REQ-006, REQ-007, REQ-016)*

- [x] **T-008** Extend `src/market_data_be/infrastructure/tests/test_classification_route.py`: update `_assert_classification_body` (and `test_openapi_documents_group_reason_enums`) for the new `reason` object shape (`{"code": ..., "params": {}}`) and updated OpenAPI `$ref` resolution (signal schema → message-ref schema → `code` enum); add cases asserting HTTP 422 with `response.json()["detail"]["code"] == "classification.invalid_symbol_format"` for both invalid-symbol paths; add/extend the undeclared-reason 500 test and a new invalid-param 500 test to assert `detail.code` equals the expected `ClassificationErrorCode` member. *(REQ-006 through REQ-014, REQ-016, NFR-006)*

- [x] **T-009** Confirm no analysis HTTP DTO, analysis route, analysis exception handler, `parse_url_symbol`, the 404 handler, or the generic `Exception` handler was modified; confirm no domain-level MessageRef type or copy-resolution logic was added under `modules/classification/`. *(REQ-015, NFR-001, NFR-003, NFR-004, NFR-005, NFR-008, NFR-009)*

## Task order

1. T-001 → T-002 (HTTP DTO shapes: signal MessageRefs, error contract)
2. T-003 (mapper: build MessageRefs, validate, fail closed)
3. T-004 → T-005 (route + app exception handling wiring)
4. T-006 → T-007 → T-008 (domain, mapper, and route/OpenAPI tests)
5. T-009 (scope check)

## Traceability summary

| Requirement | Tasks |
|-------------|-------|
| REQ-001 | T-001, T-003, T-007, T-008 |
| REQ-002 | T-001, T-007, T-008 |
| REQ-003 | T-001, T-003, T-007 |
| REQ-004 | T-003, T-007 |
| REQ-005 | T-006 |
| REQ-006 | T-003, T-007, T-008 |
| REQ-007 | T-003, T-007, T-008 |
| REQ-008 | T-005, T-008 |
| REQ-009 | T-005, T-008 |
| REQ-010 | T-002, T-004, T-008 |
| REQ-011 | T-002, T-008 |
| REQ-012 | T-001, T-008 |
| REQ-013 | T-008 |
| REQ-014 | T-008 |
| REQ-015 | T-009 |
| REQ-016 | T-007, T-008 |
| NFR-001 | T-009 |
| NFR-002 | T-001, T-002 |
| NFR-003 | T-005, T-009 |
| NFR-004 | T-004, T-009 |
| NFR-005 | T-005, T-009 |
| NFR-006 | T-006, T-007, T-008 |
| NFR-007 | T-001, T-002 |
| NFR-008 | T-009 |
| NFR-009 | T-009 |
