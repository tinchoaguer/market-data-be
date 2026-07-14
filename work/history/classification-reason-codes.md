# Feature History: classification-reason-codes

```yaml
history:
  - date: 2026-07-14
    feature:
      id: 8
      slug: classification-reason-codes
    workflow_stage: Completed
```

## Summary

Declared closed classification signal reason codes on per-group HTTP response DTOs so OpenAPI exposes them as the FE source of truth. Domain `ClassificationSignal.reason` remains `str`. Mapper fails closed with HTTP 500 on undeclared reasons.

## Deliverables

- Per-group reason `StrEnum`s and signal response DTOs in `infrastructure/http/dtos/classification.py`
- Fail-closed mapper + `UndeclaredClassificationReasonError` → HTTP 500
- Domain `reason_codes` constants and classifier alignment
- OpenAPI, mapper, route, and classifier tests

## Review

**Decision:** APPROVED

All REQ-001–REQ-010, NFR-001–NFR-006, AC-001–AC-008, and T-001–T-008 passed. Related pytest: 43 passed.
