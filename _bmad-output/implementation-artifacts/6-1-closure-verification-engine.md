# Story 6.1: Closure Verification Engine

Status: ready-for-dev

## Story

As a **developer**,
I want **a closure verification engine that checks all polylines for geometric closure**,
so that **non-closed polylines are caught before scrutiny and the AI agent can correct them using the suggested action (FR13)**.

## Acceptance Criteria

1. **AC1:** `VerificationService.check_closure()` iterates all POLYLINE entities in the active drawing session and evaluates whether the last vertex coordinate equals the first vertex coordinate within configurable tolerance.
2. **AC2:** The method returns `list[VerificationFailure]` where each failure carries `entity_id`, `failure_type="CLOSURE"`, `layer`, `description` (including the measured gap distance in drawing units), and `suggested_correction="Use entity_close_polyline(<handle>)"`.
3. **AC3:** Closure gap tolerance is configurable (default: 0.001 drawing units); the tolerance value is read from `Settings` or passed as a parameter to `check_closure(tolerance=0.001)`.
4. **AC4:** Zero false positives on correctly closed polylines — a drawing where all polylines have `first_vertex == last_vertex` within tolerance returns an empty failure list (NFR14).
5. **AC5:** The `verify_closure` MCP tool (in `tools.py`) wraps `check_closure()`, follows the 6-step handler pattern (session → validate → NO snapshot → service call → event_log → return), and returns a structured response with `passed: bool` and `failures: list`.
6. **AC6:** Unit tests cover: open polyline detected, closed polyline passes, boundary tolerance values (gap exactly at tolerance passes, gap just above fails), empty drawing (no polylines) returns empty failure list.

## Tasks / Subtasks

- [ ] Task 1: Define `VerificationFailure` Pydantic model and verification schemas in `schemas.py` (AC: 2)
  - [ ] 1.1: Create `VerificationFailure` model with fields: `entity_id: str`, `failure_type: Literal["CLOSURE", "CONTAINMENT", "NAMING", "MIN_ENTITY"]`, `layer: str`, `description: str`, `suggested_correction: str`
  - [ ] 1.2: Create `ClosureCheckResult` response schema with fields: `passed: bool`, `failures: list[VerificationFailure]`, `checked_entity_count: int`, `tolerance_used: float`
  - [ ] 1.3: Ensure all models use `model_config = ConfigDict(frozen=True)` for immutability (read-only verification results)
  - [ ] 1.4: Export `VerificationFailure`, `ClosureCheckResult` from `schemas.py` and expose via `modules/verification/__init__.py`

- [ ] Task 2: Implement `VerificationService.check_closure()` in `service.py` (AC: 1, 2, 3, 4)
  - [ ] 2.1: Create `VerificationService.__init__(self, session: DrawingSession)` — stores session reference; injects `EntityService(session)` and `LayerService(session)` directly (NOT via MCP tool calls)
  - [ ] 2.2: Implement `check_closure(self, tolerance: float = 0.001) -> list[VerificationFailure]`: call `EntityService.list_entities(entity_type="POLYLINE")` to retrieve all polylines in the active drawing
  - [ ] 2.3: For each polyline entity, extract vertex coordinates — compare `vertices[0]` to `vertices[-1]`; compute Euclidean gap distance: `gap = sqrt((x0-xn)^2 + (y0-yn)^2)`
  - [ ] 2.4: If `gap > tolerance`, construct a `VerificationFailure(entity_id=handle, failure_type="CLOSURE", layer=entity.layer, description=f"Polyline gap: {gap:.6f} units (tolerance: {tolerance})", suggested_correction=f"Use entity_close_polyline({handle})")` and append to failures list
  - [ ] 2.5: Return `failures` list (empty list if all polylines pass; never return `None`)

- [ ] Task 3: Implement `verify_closure` MCP tool handler in `tools.py` (AC: 5)
  - [ ] 3.1: Define `@mcp.tool()` decorated async function `verify_closure(ctx: Context, tolerance: float = 0.001) -> dict`
  - [ ] 3.2: Step 1 — retrieve session: `session = ctx.get_state("drawing_session")`; if missing, return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 3.3: Step 2 — validate params: ensure `0 < tolerance <= 1.0`; return `MCPError(INVALID_PARAMS)` if out of range
  - [ ] 3.4: Step 3 — NO snapshot (read-only tool, skip mutation snapshot entirely)
  - [ ] 3.5: Step 4 — call `VerificationService(session).check_closure(tolerance=tolerance)`; collect `failures`
  - [ ] 3.6: Step 5 — append to event log: `session.event_log.append({"tool": "verify_closure", "tolerance": tolerance, "failure_count": len(failures)})`
  - [ ] 3.7: Step 6 — return `{"success": True, "data": {"passed": len(failures) == 0, "failures": [f.model_dump() for f in failures], "checked_entity_count": ..., "tolerance_used": tolerance}}`

- [ ] Task 4: Register `verify_closure` tool in the verification module `__init__.py` (AC: 5)
  - [ ] 4.1: In `src/lcs_cad_mcp/modules/verification/__init__.py`, implement `register(mcp: FastMCP) -> None` that calls `tools.register(mcp)`
  - [ ] 4.2: In `tools.py`, implement `register(mcp: FastMCP) -> None` that decorates and binds `verify_closure` to the passed `mcp` instance
  - [ ] 4.3: Confirm `verify_closure` is included in the tool list exported from `server.py` module registration loop

- [ ] Task 5: Write unit tests for closure verification in `tests/unit/modules/verification/` (AC: 4, 6)
  - [ ] 5.1: Create `tests/unit/modules/verification/__init__.py` and `test_closure.py`
  - [ ] 5.2: Build `MockCADBackend` fixture providing: one open polyline (gap = 0.5 units), one closed polyline (gap = 0.0), one polyline at exact tolerance boundary (gap = 0.001)
  - [ ] 5.3: Test `check_closure(tolerance=0.001)` detects only the open polyline; closed and boundary polylines pass
  - [ ] 5.4: Test empty drawing (zero polylines) returns `failures == []`
  - [ ] 5.5: Write Hypothesis property-based test: `@given(...)` generates random closed polylines (first == last vertex) and asserts `check_closure()` always returns zero failures (NFR14 property)

- [ ] Task 6: Verify integration with existing EntityService (AC: 1)
  - [ ] 6.1: Confirm `EntityService.list_entities(entity_type="POLYLINE")` is callable and returns entities with `handle`, `layer`, and `vertices` attributes — coordinate with Story 5-6 interface contract
  - [ ] 6.2: If `vertices` attribute name differs in EntityService output, add an adapter in `VerificationService` (do NOT modify EntityService)
  - [ ] 6.3: Run the full test suite (`pytest tests/unit/modules/verification/`) and confirm zero failures

## Dev Notes

### Critical Architecture Constraints

1. **READ-ONLY tool — no snapshot.** `verify_closure` never mutates drawing state. Skip Step 3 (snapshot) of the 6-step handler pattern entirely. Only mutation tools take snapshots.
2. **VerificationService calls EntityService DIRECTLY** — never call `entity_list_entities` as an MCP tool within the service. Instantiate `EntityService(session)` and call its methods as plain Python. This avoids network overhead and circular MCP calls.
3. **Pydantic v2 models required.** Use `model_config = ConfigDict(...)`, `model_dump()` (not `.dict()`), `model_validate()` (not `.from_orm()`). FastMCP 3.x integration depends on Pydantic v2 serialization.
4. **`failure_type` must be a string literal union** — `Literal["CLOSURE", "CONTAINMENT", "NAMING", "MIN_ENTITY"]` — so downstream aggregation in Story 6-5 can discriminate failure types without isinstance checks.

### Module/Component Notes

**`schemas.py` — VerificationFailure model (complete definition):**

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict


class VerificationFailure(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_id: str                  # entity handle from CAD backend
    failure_type: Literal["CLOSURE", "CONTAINMENT", "NAMING", "MIN_ENTITY"]
    layer: str                      # layer name the entity belongs to
    description: str                # human-readable failure description with numeric detail
    suggested_correction: str       # actionable MCP tool call string


class ClosureCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    failures: list[VerificationFailure]
    checked_entity_count: int
    tolerance_used: float
```

**`service.py` — VerificationService skeleton:**

```python
from lcs_cad_mcp.modules.entities.service import EntityService
from lcs_cad_mcp.modules.layers.service import LayerService
from lcs_cad_mcp.modules.verification.schemas import VerificationFailure
import math


class VerificationService:
    def __init__(self, session) -> None:
        self._session = session
        self._entity_svc = EntityService(session)
        self._layer_svc = LayerService(session)

    def check_closure(self, tolerance: float = 0.001) -> list[VerificationFailure]:
        failures: list[VerificationFailure] = []
        polylines = self._entity_svc.list_entities(entity_type="POLYLINE")
        for entity in polylines:
            verts = entity.vertices
            if len(verts) < 2:
                continue
            x0, y0 = verts[0][0], verts[0][1]
            xn, yn = verts[-1][0], verts[-1][1]
            gap = math.sqrt((xn - x0) ** 2 + (yn - y0) ** 2)
            if gap > tolerance:
                failures.append(VerificationFailure(
                    entity_id=entity.handle,
                    failure_type="CLOSURE",
                    layer=entity.layer,
                    description=f"Polyline not closed: gap={gap:.6f} units (tolerance={tolerance})",
                    suggested_correction=f"Use entity_close_polyline({entity.handle})",
                ))
        return failures
```

**`tools.py` — verify_closure handler skeleton:**

```python
from fastmcp import Context
from lcs_cad_mcp.errors import MCPError, ErrorCode
from lcs_cad_mcp.modules.verification.service import VerificationService


def register(mcp) -> None:
    @mcp.tool()
    async def verify_closure(ctx: Context, tolerance: float = 0.001) -> dict:
        # Step 1: Session
        session = ctx.get_state("drawing_session")
        if session is None:
            return MCPError(ErrorCode.SESSION_NOT_STARTED, "No active drawing session").to_response()
        # Step 2: Validate
        if not (0 < tolerance <= 1.0):
            return MCPError(ErrorCode.INVALID_PARAMS, "tolerance must be between 0 and 1.0").to_response()
        # Step 3: No snapshot (read-only)
        # Step 4: Service call
        svc = VerificationService(session)
        failures = svc.check_closure(tolerance=tolerance)
        # Step 5: Event log
        session.event_log.append({
            "tool": "verify_closure",
            "tolerance": tolerance,
            "failure_count": len(failures),
        })
        # Step 6: Return
        return {
            "success": True,
            "data": {
                "passed": len(failures) == 0,
                "failures": [f.model_dump() for f in failures],
                "checked_entity_count": len(failures),  # replace with actual count
                "tolerance_used": tolerance,
            },
        }
```

### Project Structure Notes

Files to create or modify for this story:

```
src/lcs_cad_mcp/modules/verification/
├── __init__.py       # register(mcp) → tools.register(mcp)
├── schemas.py        # VerificationFailure, ClosureCheckResult (+ future result types)
├── service.py        # VerificationService with check_closure()
└── tools.py          # verify_closure MCP tool handler

tests/unit/modules/verification/
├── __init__.py
└── test_closure.py   # unit + property-based tests
```

### Dependencies

- **Story 5-6** (Entity listing — `EntityService.list_entities(entity_type)` must return entities with `handle`, `layer`, `vertices` attributes)
- **Story 2-1** (CAD Backend base — `DrawingSession` must be accessible via `ctx.get_state("drawing_session")`)
- **Story 1-2** (FastMCP server — `mcp` instance available for tool registration)
- **Story 1-5** (`Settings` model — for potential tolerance env var override in future)
- `shapely` is available in `pyproject.toml` but direct coordinate comparison is preferred for closure (avoids shapely overhead for a simple distance check); `math.sqrt` is sufficient

### References

- FR13: Closure check requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 6, Story 6-1]
- NFR14: Zero false positives — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 6 NFR coverage]
- 6-step tool handler pattern — [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- VerificationFailure model design — [Source: Architecture mandatory context — EPIC 6 SPECIFIC CONTEXT]
- EntityService interface — [Source: `_bmad-output/implementation-artifacts/` — Story 5-x files]

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
- `tests/unit/modules/verification/__init__.py`
- `tests/unit/modules/verification/test_closure.py`
