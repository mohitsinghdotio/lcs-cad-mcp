# Story 6.5: verify_all MCP Tool — Full Verification Pass

Status: ready-for-dev

## Story

As an **AI client**,
I want **to run all verification checks in a single tool call**,
so that **the AI can confirm drawing readiness before AutoDCR scrutiny without multiple round-trips (FR18)**.

## Acceptance Criteria

1. **AC1:** `verify_all(building_type: str)` runs all four checks in order: closure, containment, naming, minimum entity counts — delegating to `VerificationService.check_closure()`, `check_containment()`, `check_naming()`, and `check_minimum_entities(building_type)`.
2. **AC2:** Returns an aggregated `VerificationReport` containing: `overall_pass: bool`, `total_failure_count: int`, `closure_failures: list[VerificationFailure]`, `containment_failures: list[VerificationFailure]`, `naming_failures: list[VerificationFailure]`, `min_entity_failures: list[VerificationFailure]`, and `short_circuited: bool` with `short_circuit_reason: str | None`.
3. **AC3:** Short-circuit behavior: if closure check produces any failures, skip containment check and set `short_circuited=True`, `short_circuit_reason="Closure failures detected: containment requires closed polylines"` — containment results are meaningless on open polylines. Naming and min-entity checks still run (they are independent).
4. **AC4:** A clean, correctly prepared PreDCR drawing returns `overall_pass=True` with all four failure lists empty and `short_circuited=False` (NFR14).
5. **AC5:** The `verify_all` MCP tool follows the 6-step handler pattern (session → validate → NO snapshot → service call → event_log → return) and accepts `building_type: str` as input.
6. **AC6:** The event log entry for `verify_all` records: tool name, building_type, total_failure_count, each individual check's failure count, and whether short-circuit was triggered.
7. **AC7:** Unit and integration tests confirm: all-pass drawing returns `overall_pass=True`; drawing with open polyline correctly short-circuits containment; each individual check failure propagates correctly into the report.

## Tasks / Subtasks

- [ ] Task 1: Define `VerificationReport` Pydantic model in `schemas.py` (AC: 2)
  - [ ] 1.1: Create `VerificationReport` model with fields: `overall_pass: bool`, `total_failure_count: int`, `closure_failures: list[VerificationFailure]`, `containment_failures: list[VerificationFailure]`, `naming_failures: list[VerificationFailure]`, `min_entity_failures: list[VerificationFailure]`, `short_circuited: bool`, `short_circuit_reason: str | None`, `building_type: str`
  - [ ] 1.2: Add computed property or validator: `overall_pass` is `True` iff all four failure lists are empty and `short_circuited` is `False`
  - [ ] 1.3: Add `total_failure_count` as a computed field: `len(closure_failures) + len(containment_failures) + len(naming_failures) + len(min_entity_failures)`
  - [ ] 1.4: Use `model_config = ConfigDict(frozen=True)` for immutability
  - [ ] 1.5: Export `VerificationReport` from `schemas.py` and from `modules/verification/__init__.py`

- [ ] Task 2: Implement `VerificationService.run_full_verification()` aggregation method in `service.py` (AC: 1, 2, 3)
  - [ ] 2.1: Define `run_full_verification(self, building_type: str) -> VerificationReport`
  - [ ] 2.2: Step A — run closure check: `closure_failures = self.check_closure()`
  - [ ] 2.3: Step B — short-circuit decision: if `closure_failures` is non-empty, set `containment_failures = []`, `short_circuited = True`, `short_circuit_reason = f"Closure failures detected ({len(closure_failures)} polylines open): containment check requires all polylines to be closed"` — skip `check_containment()` call entirely
  - [ ] 2.4: Step C — if no closure failures: `containment_failures = self.check_containment()`; `short_circuited = False`; `short_circuit_reason = None`
  - [ ] 2.5: Step D — always run naming: `naming_failures = self.check_naming()`
  - [ ] 2.6: Step E — always run min entity: `min_entity_failures = self.check_minimum_entities(building_type)`
  - [ ] 2.7: Assemble and return `VerificationReport(overall_pass=..., total_failure_count=..., closure_failures=closure_failures, containment_failures=containment_failures, naming_failures=naming_failures, min_entity_failures=min_entity_failures, short_circuited=short_circuited, short_circuit_reason=short_circuit_reason, building_type=building_type)`

- [ ] Task 3: Implement `verify_all` MCP tool handler in `tools.py` (AC: 4, 5, 6)
  - [ ] 3.1: Define `@mcp.tool()` decorated async function `verify_all(ctx: Context, building_type: str) -> dict`
  - [ ] 3.2: Step 1 — retrieve session: `session = ctx.get_state("drawing_session")`; if missing, return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 3.3: Step 2 — validate: confirm `building_type` is non-empty; validate against `KNOWN_BUILDING_TYPES`; return `MCPError(INVALID_PARAMS)` if invalid
  - [ ] 3.4: Step 3 — NO snapshot (read-only tool)
  - [ ] 3.5: Step 4 — call `VerificationService(session).run_full_verification(building_type=building_type)`; receive `report: VerificationReport`
  - [ ] 3.6: Step 5 — append to event log: `{"tool": "verify_all", "building_type": building_type, "overall_pass": report.overall_pass, "total_failures": report.total_failure_count, "closure_failures": len(report.closure_failures), "containment_failures": len(report.containment_failures), "naming_failures": len(report.naming_failures), "min_entity_failures": len(report.min_entity_failures), "short_circuited": report.short_circuited}`
  - [ ] 3.7: Step 6 — return `{"success": True, "data": report.model_dump()}`

- [ ] Task 4: Register `verify_all` tool and finalize `__init__.py` (AC: 5)
  - [ ] 4.1: Add `verify_all` to the `register(mcp)` call chain in `tools.py`
  - [ ] 4.2: Confirm `modules/verification/__init__.py` `register()` function now registers all five verify tools: `verify_closure`, `verify_containment`, `verify_naming`, `verify_minimum_entities`, `verify_all`
  - [ ] 4.3: Confirm the verification module is registered in `server.py` / `__main__.py` module registration loop

- [ ] Task 5: Write unit tests for `verify_all` and `VerificationReport` (AC: 4, 7)
  - [ ] 5.1: Create `tests/unit/modules/verification/test_verify_all.py`
  - [ ] 5.2: Build `MockCADBackend` fixture for an all-passing drawing: all polylines closed, all entities contained, all names valid, all required layers populated
  - [ ] 5.3: Test `run_full_verification()` on all-passing drawing returns `overall_pass=True`, `total_failure_count=0`, `short_circuited=False`
  - [ ] 5.4: Build fixture for a drawing with one open polyline: test that `containment_failures == []`, `short_circuited=True`, `overall_pass=False`
  - [ ] 5.5: Build fixture with naming failure only: test `overall_pass=False`, `naming_failures` non-empty, `short_circuited=False`, other failure lists empty
  - [ ] 5.6: Build fixture with min entity failure only: test `overall_pass=False`, `min_entity_failures` non-empty, `short_circuited=False`
  - [ ] 5.7: Test `VerificationReport.total_failure_count` correctly sums all four failure lists
  - [ ] 5.8: Write Hypothesis property-based test: `@given(...)` constructs a fully valid drawing → `run_full_verification()` always returns `overall_pass=True` (NFR14 property for the aggregate gate)

- [ ] Task 6: Write integration test for `verify_all` tool handler end-to-end (AC: 5, 7)
  - [ ] 6.1: Create `tests/integration/test_verify_all_tool.py`
  - [ ] 6.2: Set up a mock MCP session with `ctx.get_state("drawing_session")` returning a pre-populated `MockDrawingSession`
  - [ ] 6.3: Call `verify_all(ctx=mock_ctx, building_type="residential")` directly (not via MCP protocol)
  - [ ] 6.4: Assert response structure: `success: True`, `data.overall_pass`, `data.closure_failures`, `data.containment_failures`, `data.naming_failures`, `data.min_entity_failures`, `data.short_circuited`
  - [ ] 6.5: Assert event_log receives one entry with all required fields (AC6)

- [ ] Task 7: Validate `VerificationReport` model correctness (AC: 2)
  - [ ] 7.1: Confirm `overall_pass` is computed — not passed as a constructor argument — to prevent caller from setting it inconsistently; use Pydantic `@model_validator(mode="after")` or `@computed_field`
  - [ ] 7.2: Confirm `total_failure_count` is a computed field using `@computed_field` (Pydantic v2 syntax) rather than a manually assigned field
  - [ ] 7.3: Write a test proving that `VerificationReport` with empty failure lists always has `overall_pass=True` regardless of any constructor argument

## Dev Notes

### Critical Architecture Constraints

1. **READ-ONLY tool — no snapshot.** `verify_all` never mutates drawing state. Skip Step 3 (snapshot) of the 6-step handler pattern entirely. This applies even though `verify_all` orchestrates multiple sub-checks.
2. **Short-circuit is mandatory for containment.** Open polylines cannot form valid Shapely polygons. If `check_closure()` returns any failures, `check_containment()` MUST NOT be called — it would produce meaningless or erroneous results. The short-circuit must be documented in the response via `short_circuited` and `short_circuit_reason` fields.
3. **Naming and min-entity checks are always independent.** Even when closure or containment fail, naming and min-entity checks must still run and their results included in the report. Only containment is gated on closure.
4. **`overall_pass` must be a computed value** — derived from the actual failure lists, never a caller-assigned field. Use Pydantic v2 `@computed_field` or `@model_validator(mode="after")` to enforce this invariant.
5. **`verify_all` delegates entirely to `VerificationService`.** The tool handler (in `tools.py`) must not contain any verification logic — it only calls `run_full_verification()`, logs, and returns. This keeps tools thin and business logic testable.

### Module/Component Notes

**`VerificationReport` schema with computed fields (Pydantic v2):**

```python
from pydantic import BaseModel, ConfigDict, computed_field, model_validator


class VerificationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    building_type: str
    closure_failures: list[VerificationFailure]
    containment_failures: list[VerificationFailure]
    naming_failures: list[VerificationFailure]
    min_entity_failures: list[VerificationFailure]
    short_circuited: bool
    short_circuit_reason: str | None

    @computed_field  # type: ignore[misc]
    @property
    def total_failure_count(self) -> int:
        return (
            len(self.closure_failures)
            + len(self.containment_failures)
            + len(self.naming_failures)
            + len(self.min_entity_failures)
        )

    @computed_field  # type: ignore[misc]
    @property
    def overall_pass(self) -> bool:
        return self.total_failure_count == 0 and not self.short_circuited
```

**`service.py` — run_full_verification() full implementation:**

```python
def run_full_verification(self, building_type: str) -> VerificationReport:
    # Step A: Closure (always runs first)
    closure_failures = self.check_closure()

    # Step B: Containment (short-circuit if closure failed)
    if closure_failures:
        containment_failures = []
        short_circuited = True
        short_circuit_reason = (
            f"Closure failures detected ({len(closure_failures)} open polyline(s)): "
            "containment check skipped — open polylines cannot form valid boundaries"
        )
    else:
        containment_failures = self.check_containment()
        short_circuited = False
        short_circuit_reason = None

    # Step C: Naming (always runs — independent of geometry)
    naming_failures = self.check_naming()

    # Step D: Minimum entity counts (always runs — independent of geometry)
    min_entity_failures = self.check_minimum_entities(building_type)

    return VerificationReport(
        building_type=building_type,
        closure_failures=closure_failures,
        containment_failures=containment_failures,
        naming_failures=naming_failures,
        min_entity_failures=min_entity_failures,
        short_circuited=short_circuited,
        short_circuit_reason=short_circuit_reason,
    )
```

**`tools.py` — verify_all handler:**

```python
async def verify_all(ctx: Context, building_type: str) -> dict:
    # Step 1: Session
    session = ctx.get_state("drawing_session")
    if session is None:
        return MCPError(ErrorCode.SESSION_NOT_STARTED, "No active drawing session").to_response()
    # Step 2: Validate
    if not building_type or building_type.lower() not in {bt.lower() for bt in KNOWN_BUILDING_TYPES}:
        return MCPError(
            ErrorCode.INVALID_PARAMS,
            f"Unknown building_type: '{building_type}'",
            suggested_action=f"Valid types: {sorted(KNOWN_BUILDING_TYPES)}",
        ).to_response()
    # Step 3: No snapshot (read-only)
    # Step 4: Service call
    svc = VerificationService(session)
    report = svc.run_full_verification(building_type=building_type)
    # Step 5: Event log
    session.event_log.append({
        "tool": "verify_all",
        "building_type": building_type,
        "overall_pass": report.overall_pass,
        "total_failures": report.total_failure_count,
        "closure_failures": len(report.closure_failures),
        "containment_failures": len(report.containment_failures),
        "naming_failures": len(report.naming_failures),
        "min_entity_failures": len(report.min_entity_failures),
        "short_circuited": report.short_circuited,
    })
    # Step 6: Return
    return {"success": True, "data": report.model_dump()}
```

**Complete `schemas.py` export list after all Epic 6 stories:**

```python
# schemas.py exports (all verification result types)
__all__ = [
    "VerificationFailure",        # base failure model (6-1)
    "ClosureCheckResult",         # 6-1
    "ContainmentCheckResult",     # 6-2
    "NamingCheckResult",          # 6-3
    "MinEntityCheckResult",       # 6-4
    "VerificationReport",         # 6-5 — aggregated full report
]
```

### Project Structure Notes

Files modified or created for this story:

```
src/lcs_cad_mcp/modules/verification/
├── __init__.py       # finalized: register() includes all 5 verify tools
├── schemas.py        # updated: add VerificationReport with computed fields
├── service.py        # updated: add run_full_verification()
└── tools.py          # updated: add verify_all handler

tests/unit/modules/verification/
├── __init__.py       # already exists from Story 6-1
└── test_verify_all.py    # NEW

tests/integration/
└── test_verify_all_tool.py   # NEW — end-to-end tool handler test
```

### Dependencies

- **Story 6-1** (closure check — `check_closure()` must be implemented and tested)
- **Story 6-2** (containment check — `check_containment()` must be implemented and tested)
- **Story 6-3** (naming check — `check_naming()` must be implemented and tested)
- **Story 6-4** (minimum entity check — `check_minimum_entities()` must be implemented and tested; `KNOWN_BUILDING_TYPES` must be importable)
- **Story 4-1** (PreDCR layer catalog — `KNOWN_BUILDING_TYPES` must be available in `layer_registry.py`)
- **Story 2-1** (CAD Backend — `DrawingSession` accessible via `ctx.get_state()`)
- **Story 1-2** (FastMCP server — `mcp` instance and `ctx.get_state()` / `ctx.set_state()` session pattern)

### References

- FR18: verify_all single-call gate requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 6, Story 6-5]
- NFR14: Zero false positives on correctly prepared PreDCR drawings — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 6 NFR coverage]
- Short-circuit rationale: open polylines produce invalid Shapely geometries — [Source: Architecture mandatory context — EPIC 6 SPECIFIC CONTEXT]
- `@computed_field` Pydantic v2 pattern — [Pydantic v2 documentation: Computed Fields]
- 6-step tool handler pattern — [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- VerificationReport design — [Source: Architecture mandatory context — EPIC 6 SPECIFIC CONTEXT: "VerificationReport (total_failures, closure_failures, containment_failures, naming_failures, min_entity_failures, overall_pass: bool)"]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/verification/__init__.py`
- `src/lcs_cad_mcp/modules/verification/schemas.py`
- `src/lcs_cad_mcp/modules/verification/service.py`
- `src/lcs_cad_mcp/modules/verification/tools.py`
- `tests/unit/modules/verification/test_verify_all.py`
- `tests/integration/test_verify_all_tool.py`
