# Feature History: classification-message-refs

```yaml
history:
  - date: 2026-07-21
    feature:
      id: 11
      slug: classification-message-refs
    workflow_stage: Completed
```

## Summary

Replaced classification signal display-English reasons with structured MessageRef (code + typed params) on classification HTTP DTOs, reusing the existing closed reason-code enums as the MessageRef `code`. Mapper fails closed on undeclared reasons and invalid params via dedicated machine error codes. Both classification 422 sites and the two classification-only 500 handlers now carry a machine `ClassificationErrorCode`. OpenAPI documents the MessageRef shape and per-group code enums. Analysis DTOs/routes, the shared `parse_url_symbol`, the 404 handler, and domain classifiers/`ClassificationSignal` remain untouched.

## Deliverables

- `*SignalMessageRef` (code + params) DTOs for regime/risk/economic/exposure reasons
- `ClassificationErrorCode` / `ClassificationErrorDetail` machine error codes for 422/500 classification paths
- Mapper fail-closed validation (`UndeclaredClassificationReasonError`, `InvalidClassificationMessageParamsError`)
- OpenAPI contract documentation and extended unit/route/classifier tests (T-001–T-009)

## Review

**Decision:** APPROVED

All REQ-001–REQ-016, NFR-001–NFR-009, AC-001–AC-010, and T-001–T-009 passed. No required fixes or recommendations. Full suite (200 tests) passed.
