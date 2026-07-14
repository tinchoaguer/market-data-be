---
feature:
  slug: classification-reason-codes

decision: APPROVED

summary: >
  Per-group StrEnum reason codes and signal DTOs match REQ-003; OpenAPI
  documents group-specific enums; mapper raises UndeclaredClassificationReasonError
  and app maps it to HTTP 500 with a generic detail; classifiers use domain
  reason_codes constants; ClassificationSignal.reason remains str; analysis
  DTOs unchanged. All acceptance criteria and tasks T-001–T-008 verified.
  pytest: 43 passed.
---

# Code Review: classification-reason-codes

## Requirements

REQ-001 through REQ-010: **pass**

## Non-Functional Requirements

NFR-001 through NFR-006: **pass**

## Acceptance Criteria

AC-001 through AC-008: **pass**

## Findings

### Recommendations (non-blocking)

1. **test_classification_route.py** — OpenAPI expected sets are derived from DTO enums; a hardcoded REQ-003 literal table would make contract drift more obvious.
2. **test_classification_mapper.py** — optional cross-group undeclared case (e.g. `low_risk` on regime) would document per-group isolation more explicitly.

## Tasks

T-001 through T-008: **done**
