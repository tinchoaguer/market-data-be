# Feature History: analysis-message-refs

```yaml
history:
  - date: 2026-07-21
    feature:
      id: 10
      slug: analysis-message-refs
    workflow_stage: Completed
```

## Summary

Replaced analysis catalog narrative English with structured MessageRef (code + typed params) on analysis HTTP DTOs. Domain CatalogBuilder emits closed narrative codes; mapper fail-closes undeclared codes and prose params to HTTP 500. OpenAPI documents MessageRefResponse and AnalysisNarrativeMessageCode. Classification DTOs and display-copy resolve remain out of scope.

## Deliverables

- Domain `MessageRef` VO and closed narrative code set
- CatalogBuilder MessageRef emission (no interpolated English)
- HTTP `MessageRefResponse` / `AnalysisNarrativeMessageCode` DTOs + fail-closed mapper
- OpenAPI contract documentation and unit/route tests (T-001–T-009)

## Review

**Decision:** APPROVED

All REQ-001–REQ-016, NFR-001–NFR-008, AC-001–AC-008, and T-001–T-009 passed. Recommendations only (OpenAPI `params` required metadata; shared/openapi.json release handoff).
