# Feature History: analysis-reason-codes

```yaml
history:
  - date: 2026-07-14
    feature:
      id: 9
      slug: analysis-reason-codes
    workflow_stage: Completed
```

## Summary

Declared closed analysis regime labels and regime reason codes on HTTP response DTOs so OpenAPI exposes them as the FE source of truth. Domain `RegimeAssessment.reasons` remains a plain string collection. Mapper fails closed with HTTP 500 on undeclared regime or reason. Catalog/hard_gate/strategies out of scope.

## Deliverables

- `AnalysisRegimeLabel` and `AnalysisRegimeReasonCode` StrEnums on `RegimeAssessmentResponse`
- Fail-closed mapper + undeclared regime/reason errors → HTTP 500
- Domain `reason_codes` constants and `RegimeDetector` alignment
- OpenAPI, mapper, route, and detector tests

## Review

**Decision:** APPROVED

All requirements, NFRs, acceptance criteria, and T-001–T-009 passed. Related pytest: 70 passed.
