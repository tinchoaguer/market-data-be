# Testing Policy

Project-specific testing rules for `market-data-be`. Spec Writer, Implementer, and Reviewer must follow this document when producing or evaluating Feature tests.

Authority: project `knowledge/` (below harness governance). This policy refines — and does not replace — “unit tests under `*/tests/`” in `architecture.md`.

---

## Purpose

Tests exist to **catch real defects** in:

1. **Domain outcomes** — regime, risk, edge, exposure, catalog gates, reason/narrative codes
2. **HTTP / OpenAPI contracts** — shapes, enums, fail-closed mapping, status codes

Tests do **not** exist to maximize file count, line coverage, or one-to-one AC↔test-file symmetry.

Primary metric: **oracle strength** — would this test fail if the important logic were wrong?

---

## Allowed techniques (priority order)

| Priority | Technique | When to use | Status |
|----------|-----------|-------------|--------|
| 1 | Example-based unit tests (pytest) | Default for all layers | **Required** |
| 2 | Strong oracles (exact outcome, bounds, ordering, closed-set membership **with expected value**) | Domain rules and contracts | **Required** where applicable |
| 3 | Property-based (e.g. Hypothesis) | Pure numeric helpers (`candle_metrics`, score bounds, empty/short series) | **Optional**, prefer when adding/changing pure math |
| 4 | Mutation testing (e.g. mutmut) | Periodic check that domain tests kill mutants | **Optional**, not a Feature gate |
| 5 | Fuzzing | Malformed JSON / deserializer when inputs are untrusted or provider expands beyond controlled fixtures | **Optional**, deferred until needed |
| 6 | Line/branch coverage % | Local/CI report only | **Never** a Feature success criterion |
| 7 | Symbolic execution | — | **Out of scope** |

Do not introduce coverage thresholds, mutation gates, or fuzz suites in Feature specs unless product explicitly expands this policy.

---

## What to test by layer

| Layer | Path | Must test | Must not test (unless fixing a real bug) |
|-------|------|-----------|------------------------------------------|
| Domain | `modules/<bc>/tests/` | Canonical scenarios; thresholds; invariants (e.g. score ∈ [0,1]); exact reason/narrative codes for given inputs; hard-gate outcomes | Facade “called worker X”; recording doubles that only prove wiring |
| Application | `application/tests/` | One happy-path pipeline (real or lightweight fakes at ports); port error propagation when specified | `call_count` / `last_input is` orchestration-only asserts as the sole oracle |
| HTTP mapper | `infrastructure/tests/` | Declared mapping; fail-closed on undeclared regime/reason/code; invalid MessageRef params | Re-asserting full domain semantics already covered in domain tests |
| HTTP route | `infrastructure/tests/` | Status codes (200/404/422/500 as specified); OpenAPI enum/schema SoT; **one** success body shape check | Duplicating every mapper fail-closed case already unit-tested |
| Resources | `resources/tests/` | Fixture schema conformance for mock market data | Business outcomes of analysis/classification |

Domain tests must remain free of FastAPI/Pydantic/httpx. Route tests may use `TestClient`.

---

## Oracle rules (anti-bloat)

An automated test is **acceptable** only if at least one oracle is strong:

**Strong oracles (prefer)**

- Exact enum / reason / narrative `code` for a given input
- Numeric equality or `approx` with a justified expected value
- Bounds or ordering (e.g. `range_score < trend_score < spike_score`)
- HTTP status + stable error envelope
- OpenAPI `enum` set equals the declared closed set
- Fail-closed: undeclared value → specific exception or HTTP 500

**Weak oracles (insufficient alone)**

- `assert x is not None`
- `assert len(x) >= 1` without checking content
- `assert reason in ALLOWED_CODES` without asserting **which** reason
- `assert provider.call_count == 1` / stub `last_input is` as the only assertion
- Asserting top-level keys exist without validating contract-critical fields

**Anti-patterns**

- New test file per AC when an existing file in the same layer can host the case
- Copy-pasting large `AnalysisResult` / DTO builders; extend shared fixtures instead (`modules/analysis/tests/fixtures.py` or a single helper module)
- Triple-testing the same fail-closed case in domain + mapper + route without a reason (mapper unit + **one** route 500 path for the contract is enough)
- Spec text that requires “coverage expectations” as a percentage

---

## Spec Writer rules

In `design.md` → **Testing Strategy**:

1. Map each risk to a **layer** and an **oracle type** (not “add unit tests”).
2. Prefer a table: `| Behavior | Layer | Oracle | Location |`.
3. “Coverage expectations” means **which behaviors/ACs have an automated oracle**, not line coverage.
4. Do **not** require a new test module per REQ. Require that each AC has a **verifiable oracle** (may share a parametrized test).
5. Do not mandate property-based, mutation, or fuzz unless this policy’s optional rows apply to the Feature.
6. Keep HTTP success tests focused on **contract shape**; put market logic asserts in domain tests.

In `tasks.md`:

- Prefer tasks like “Extend `test_risk_engine.py` with threshold oracle for …” over “Create tests for REQ-00N”.
- Avoid separate tasks that only add wiring/smoke tests.

---

## Implementer rules

1. Follow the Feature Testing Strategy **and** this policy. If they conflict, follow this policy and report BLOCKED for spec fix.
2. Extend existing test modules in the affected layer before adding files.
3. Reuse fixtures; do not duplicate 50+ line sample builders across files.
4. For closed-set / classifier changes: assert the **expected** code at boundaries, not only set membership.
5. For pure numeric changes: example tests required; add a small property-based test when bounds/emptiness matter and Hypothesis is already a project dependency (do not add Hypothesis solely for one trivial case).
6. Do not add coverage config, mutation CI, or fuzz harnesses unless the Feature explicitly adopts an optional technique from this policy.
7. A Feature may ship with **fewer** tests than ACs if one parametrized test covers multiple ACs with strong oracles — traceability is via behavior, not file count.

---

## Reviewer rules

Approve tests only if:

1. Every AC has a **strong oracle** somewhere (domain, mapper, or route as appropriate).
2. No new test relies solely on weak oracles listed above.
3. Contract Features (OpenAPI enums, MessageRef, fail-closed) have mapper and/or OpenAPI tests as specified.
4. Domain Features assert outcomes, not wiring.
5. Duplication across mapper and route is limited to what the design required.

Reject (or mark required fix) when:

- Tests only prove orchestration/`is not None`
- Large duplicated fixtures instead of shared helpers
- Spec claimed domain behavior but only HTTP smoke exists
- Line-coverage or mutation score is treated as an AC

Recommendations (non-blocking): suggest consolidating duplicated route/mapper cases; suggest Hypothesis for pure math hotspots.

---

## Decision matrix (Feature design)

| Question | If yes → |
|----------|----------|
| Does it change FE/OpenAPI closed sets or MessageRef shapes? | Mapper + OpenAPI tests (required) |
| Does it change a market rule, threshold, or gate? | Domain example with **exact** outcome (required) |
| Is it a pure numeric helper? | Example + optional property (bounds / empty input) |
| Is it a 3-line use-case wire-up? | At most one pipeline smoke; no call-count-only tests |
| Is it display copy / localization strings? | No BE resolve tests (codes + params only) |
| Is input untrusted JSON beyond fixtures? | Consider deserializer fuzz (optional) |

---

## Tooling baseline

- Runner: `pytest` (`pyproject.toml` → `[tool.pytest.ini_options]`)
- Dev deps today: `pytest`, `httpx` (for TestClient)
- Optional later: `hypothesis` (property-based), `mutmut` (offline mutation), coverage report without gate

Do not expand `dev` dependencies in a Feature unless the Testing Strategy explicitly adopts an optional technique.

---

## Relationship to existing suites

Historical tests may include weak oracles or duplicated builders. Do **not** mass-refactor them inside unrelated Features.

When touching a module:

- Prefer strengthening oracles in the tests you edit
- Prefer extending shared fixtures over new copies
- Leave unrelated weak tests alone unless the Feature’s review requires cleanup

---

## Related documents

- `knowledge/architecture.md` — layer layout and unit-test location
- `knowledge/conventions.md` — short test bullet points (defer to this policy)
- `governance/spec_guidelines.md` — Testing Strategy section shape
- Feature `specs/<slug>/design.md` — per-Feature test plan (must align with this policy)
