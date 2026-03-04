# Story 5.7: `entity_close_polyline` MCP Tool

Status: ready-for-dev

## Story

As an **AI client**,
I want **to close an open polyline by connecting its last vertex to its first vertex and setting its closed flag**,
so that **PreDCR closure requirements are met for plot boundaries, building footprints, and room polygons without requiring the AI to redraw the entire polyline, fulfilling FR11**.

## Acceptance Criteria

1. **AC1:** `entity_close_polyline(entity_id: str)` MCP tool sets the polyline's closed flag to True and ensures its geometry is closed; returns `{"success": true, "data": {"entity_id": "<id>", "closed": true, "closure_gap": <float>, "was_already_closed": <bool>}}`
2. **AC2:** The response includes `closure_gap: float` — the Euclidean distance between the polyline's first and last vertex BEFORE closing (in drawing units); this allows the AI to assess whether the gap was a minor drafting error or a significant geometry problem
3. **AC3:** If the polyline was already closed (`closed=True` flag set and `closure_gap=0.0`), the tool still succeeds and returns `was_already_closed: True` with `closure_gap: 0.0`
4. **AC4:** If `entity_id` does not exist, returns `ENTITY_NOT_FOUND` error
5. **AC5:** If `entity_id` refers to an entity that is NOT a polyline (e.g., a LINE, ARC, CIRCLE, TEXT, INSERT), returns `INVALID_PARAMS` error with message indicating the actual entity type
6. **AC6:** If the polyline has fewer than 2 vertices (degenerate case), returns `INVALID_PARAMS` error
7. **AC7:** Works on both `EzdxfBackend` and `COMBackend`
8. **AC8:** Takes a snapshot BEFORE closing the polyline; snapshot enables rollback if the AI determines the gap was too large and wants to revert

## Tasks / Subtasks

- [ ] Task 1: Implement `EntityService.close_polyline` in `service.py` (AC: 1, 2, 3, 5, 6, 7)
  - [ ] 1.1: Replace `close_polyline` stub: first call `self._backend.entity_exists(entity_id)` — raise `EntityNotFoundError` if False
  - [ ] 1.2: Call `self._backend.get_entity_type(entity_id)` to retrieve the DXF type string; map to `EntityType` using `_entity_type_from_dxftype`; raise `InvalidEntityTypeError(entity_id, actual_type)` if not `EntityType.POLYLINE`
  - [ ] 1.3: Call `self._backend.get_polyline_vertices(entity_id) -> list[tuple[float, float]]`; raise `InvalidEntityTypeError` if fewer than 2 vertices
  - [ ] 1.4: Compute `closure_gap: float` = Euclidean distance between `vertices[0]` and `vertices[-1]`: `math.sqrt((x0-xn)**2 + (y0-yn)**2)`
  - [ ] 1.5: Check `was_already_closed`: call `self._backend.is_polyline_closed(entity_id) -> bool`; if True and `closure_gap < 0.001`, set `was_already_closed=True` and skip mutation (early return without modifying the drawing)
  - [ ] 1.6: Call `self._backend.close_polyline(entity_id)` — sets the closed flag and if `closure_gap > 0`, adds/adjusts the final segment to connect last vertex to first vertex
  - [ ] 1.7: Return a `ClosePolylineResult` dataclass with `entity_id`, `closed=True`, `closure_gap`, `was_already_closed`
  - [ ] 1.8: Define `ClosePolylineResult` as a Pydantic model (or dataclass) in `schemas.py`: `entity_id: str`, `closed: bool`, `closure_gap: float`, `was_already_closed: bool`
  - [ ] 1.9: Define `InvalidEntityTypeError(Exception)` in `service.py` with fields `entity_id: str` and `actual_type: str`

- [ ] Task 2: Implement `entity_close_polyline` MCP tool handler in `tools.py` following the 6-step pattern (AC: 1–8)
  - [ ] 2.1: Add async `entity_close_polyline(ctx: Context, entity_id: str) -> dict`
  - [ ] 2.2: Step 1 — Session: `session = ctx.get_state("drawing_session")`; `SESSION_NOT_STARTED` if None
  - [ ] 2.3: Step 2 — Validate `entity_id` is a non-empty string; return `INVALID_PARAMS` if empty
  - [ ] 2.4: Step 3 — NO layer existence check (entity_id-based operation, layer validated implicitly)
  - [ ] 2.5: Step 4 — Snapshot: `snapshot_id = await session.snapshot.take()` BEFORE any backend mutation
  - [ ] 2.6: Step 5 — Call `EntityService(session).close_polyline(entity_id)`; catch `EntityNotFoundError` → `ENTITY_NOT_FOUND` response; catch `InvalidEntityTypeError` → `INVALID_PARAMS` response with message `"Entity '<id>' is of type '<type>', not POLYLINE"`
  - [ ] 2.7: Step 6 — Event log: `{"tool": "entity_close_polyline", "entity_id": "...", "closure_gap": <float>, "was_already_closed": <bool>, "snapshot_id": "..."}`; return response
  - [ ] 2.8: Handle the idempotent case: if `was_already_closed=True`, include in response and do NOT take a new snapshot (check already-closed state BEFORE the snapshot step, or accept that a harmless snapshot was taken)
  - [ ] 2.9: Add docstring to tool explaining: "Closure gap is returned for AI decision-making. If gap > 1.0 (drawing unit), the AI should consider whether the polyline requires retracing. Use cad_undo or session rollback to revert if needed."

- [ ] Task 3: Extend `CADBackend` Protocol with polyline-specific methods (AC: 7)
  - [ ] 3.1: Add `get_entity_type(entity_id: str) -> str` to Protocol — returns DXF type string (e.g., `"LWPOLYLINE"`)
  - [ ] 3.2: Add `get_polyline_vertices(entity_id: str) -> list[tuple[float, float]]` to Protocol — returns ordered vertex list
  - [ ] 3.3: Add `is_polyline_closed(entity_id: str) -> bool` to Protocol
  - [ ] 3.4: Add `close_polyline(entity_id: str) -> None` to Protocol — sets the closed flag; if vertices[0] != vertices[-1], appends/adjusts to ensure geometric closure
  - [ ] 3.5: Implement `EzdxfBackend.get_entity_type`: `entity = self._doc.entitydb.get(entity_id); return entity.dxftype() if entity else None`
  - [ ] 3.6: Implement `EzdxfBackend.get_polyline_vertices`: get `LWPOLYLINE` entity; return `[(pt[0], pt[1]) for pt in entity.get_points()]`
  - [ ] 3.7: Implement `EzdxfBackend.is_polyline_closed`: `return bool(entity.closed)` for LWPOLYLINE
  - [ ] 3.8: Implement `EzdxfBackend.close_polyline`: set `entity.closed = True` on the LWPOLYLINE; ezdxf's closed flag handles the geometric closure automatically (the LWPOLYLINE closed flag connects last to first without duplicating a vertex)
  - [ ] 3.9: Add `COMBackend` stubs for `get_entity_type`, `get_polyline_vertices`, `is_polyline_closed`, `close_polyline` raising `NotImplementedError("COM backend polyline close: Story 5-7")`

- [ ] Task 4: Register `entity_close_polyline` in `entities/__init__.py` (AC: 1)
  - [ ] 4.1: Update `register(mcp)` to call `_register_close_polyline_tool(mcp)` from `tools.py`
  - [ ] 4.2: Verify `entity_close_polyline` appears correctly in MCP tool registry
  - [ ] 4.3: Confirm all previously registered entity tools remain registered and functional

- [ ] Task 5: Write comprehensive unit tests (AC: 1–8)
  - [ ] 5.1: Create `tests/unit/modules/entities/test_close_polyline_tool.py`
  - [ ] 5.2: Extend `MockCADBackend` with `get_entity_type`, `get_polyline_vertices`, `is_polyline_closed`, `close_polyline`; store polyline state in `_entities` dict
  - [ ] 5.3: Test `entity_close_polyline` happy path: 4-vertex open polyline with 2.5-unit gap → success, `closed=True`, `closure_gap=2.5`, `was_already_closed=False`
  - [ ] 5.4: Test `entity_close_polyline` on already-closed polyline → success, `was_already_closed=True`, `closure_gap=0.0`, no backend `close_polyline()` call made
  - [ ] 5.5: Test `entity_close_polyline` with `entity_id` that doesn't exist → `ENTITY_NOT_FOUND` error
  - [ ] 5.6: Test `entity_close_polyline` with `entity_id` of a LINE entity → `INVALID_PARAMS` error with message containing `"LINE"` and `"POLYLINE"`
  - [ ] 5.7: Test `entity_close_polyline` with `entity_id` of a CIRCLE entity → `INVALID_PARAMS` error
  - [ ] 5.8: Test `entity_close_polyline` on a 1-vertex degenerate polyline → `INVALID_PARAMS` error (fewer than 2 vertices)
  - [ ] 5.9: Test `entity_close_polyline` on a perfectly closed polyline (vertices[0] == vertices[-1]) → success, `closure_gap` close to 0.0 (floating point), `was_already_closed` based on closed flag
  - [ ] 5.10: Test snapshot is taken BEFORE mutation: assert `session.snapshot.take()` called once before `close_polyline()` on backend
  - [ ] 5.11: Test `closure_gap` computation accuracy: vertices `[(0,0), (3,4)]` → gap = `5.0` (3-4-5 triangle)
  - [ ] 5.12: Test event log entry contains `closure_gap` and `was_already_closed` fields

- [ ] Task 6: Integration with closure gap threshold documentation (AC: 2)
  - [ ] 6.1: Add a module-level constant to `service.py`: `CLOSURE_GAP_WARNING_THRESHOLD = 1.0` — document: "Gaps exceeding this value (in drawing units) indicate a significant geometry problem rather than a minor drafting error"
  - [ ] 6.2: Include `closure_gap_warning: bool` in the response `data` dict, set to `True` if `closure_gap > CLOSURE_GAP_WARNING_THRESHOLD`; this helps the AI decide whether to accept the closure or investigate the polyline
  - [ ] 6.3: Add test asserting `closure_gap_warning=True` for gap of 5.0 and `closure_gap_warning=False` for gap of 0.5

## Dev Notes

### Critical Architecture Constraints

1. **6-step handler pattern with modified Step 3:** For `entity_close_polyline`, Step 3 does NOT check layer existence (no layer parameter). Instead, Step 3 is where entity type validation occurs — but this can only happen via a backend call, which means the sequence is: session → validate entity_id string → snapshot → service call (which validates entity type and existence). The snapshot before service is mandatory even though validation may occur inside the service; this is acceptable because if the entity doesn't exist or isn't a polyline, no mutation occurs after the snapshot.
2. **Snapshot even for already-closed polylines:** The simplest correct implementation takes the snapshot regardless of whether the polyline is already closed. The `was_already_closed=True` response tells the AI no mutation occurred. A minor optimization (skip snapshot if already closed) can be implemented by checking `is_polyline_closed` before the snapshot step, but this adds complexity. The simpler approach (always snapshot, check inside service) is preferred.
3. **ezdxf LWPOLYLINE closed flag:** Setting `entity.closed = True` on a `LWPOLYLINE` is sufficient — ezdxf automatically renders the polyline as closed by connecting the last vertex to the first in DXF output. There is no need to manually append a duplicate vertex.
4. **PreDCR closure requirement:** This tool directly supports the PreDCR scrutiny requirement that plot boundaries, building footprints, and all room polygons must be geometrically closed polygons. The `closure_gap` field is the diagnostic metric. Story 6-1 (Closure Verification Engine) will use `entity_query` + `is_polyline_closed` to detect unclosed polylines and suggest this tool as the fix.
5. **EntityService is the only caller of backend polyline methods** — no direct backend calls from `tools.py`.

### Module/Component Notes

**Tool parameter definition:**

`entity_close_polyline`:
- `entity_id: str` — entity handle of the polyline to close (must be a POLYLINE/LWPOLYLINE entity)

**Response schema:**
```python
# Success — previously open polyline
{
    "success": True,
    "data": {
        "entity_id": "1F3A",
        "closed": True,
        "closure_gap": 2.547,           # Euclidean distance before closing
        "closure_gap_warning": False,    # True if gap > 1.0 drawing unit
        "was_already_closed": False
    }
}

# Success — already closed polyline
{
    "success": True,
    "data": {
        "entity_id": "1F3A",
        "closed": True,
        "closure_gap": 0.0,
        "closure_gap_warning": False,
        "was_already_closed": True
    }
}

# ENTITY_NOT_FOUND error
{
    "success": False,
    "error": {
        "code": "ENTITY_NOT_FOUND",
        "message": "Entity '1F3A' not found in current drawing",
        "recoverable": True,
        "suggested_action": "Use entity_query to find valid polyline entity IDs"
    }
}

# INVALID_PARAMS — wrong entity type
{
    "success": False,
    "error": {
        "code": "INVALID_PARAMS",
        "message": "Entity '2B7C' is of type 'LINE', not POLYLINE",
        "recoverable": True,
        "suggested_action": "Use entity_query with entity_type='POLYLINE' to find polylines"
    }
}
```

**Closure gap computation:**
```python
import math

def _compute_closure_gap(vertices: list[tuple[float, float]]) -> float:
    if len(vertices) < 2:
        return 0.0
    x0, y0 = vertices[0]
    xn, yn = vertices[-1]
    return math.sqrt((xn - x0) ** 2 + (yn - y0) ** 2)
```

**ClosePolylineResult schema to add to `schemas.py`:**
```python
class ClosePolylineResult(BaseModel):
    entity_id: str
    closed: bool = True
    closure_gap: float
    closure_gap_warning: bool
    was_already_closed: bool
```

**EzdxfBackend.close_polyline:**
```python
def close_polyline(self, entity_id: str) -> None:
    entity = self._doc.entitydb.get(entity_id)
    if entity is None:
        raise EntityNotFoundError(entity_id)
    if entity.dxftype() not in ("LWPOLYLINE", "POLYLINE"):
        raise ValueError(f"Entity {entity_id} is not a polyline")
    entity.closed = True  # ezdxf handles DXF output closure automatically
```

### Project Structure Notes

Files modified by this story:
```
src/lcs_cad_mcp/
├── backends/
│   ├── base.py              # get_entity_type, get_polyline_vertices, is_polyline_closed, close_polyline to Protocol
│   ├── ezdxf_backend.py     # implement all 4 polyline-specific methods
│   └── com_backend.py       # stubs for all 4 methods
└── modules/entities/
    ├── __init__.py           # register() includes close_polyline tool
    ├── schemas.py            # ClosePolylineResult model added
    ├── service.py            # close_polyline implemented; InvalidEntityTypeError defined; CLOSURE_GAP_WARNING_THRESHOLD constant
    └── tools.py              # entity_close_polyline handler

tests/unit/modules/entities/
└── test_close_polyline_tool.py  # new
```

### Dependencies

- **Story 5-5 (entity_move, entity_copy, entity_delete, entity_change_layer):** The `entity_exists()` backend method and `EntityNotFoundError` pattern are established in Story 5-5 and reused here. Story 5-5 must be complete before 5-7 begins.
- **Story 5-1 (Entity Data Models):** `EntityType`, `EntityService` skeleton, `schemas.py` (adding `ClosePolylineResult`)
- **Story 6-1 (Closure Verification, depends on THIS story):** The closure verification engine (Epic 6) will call `entity_close_polyline` as the suggested corrective action for open polylines detected by `verify_closure()`.
- **EzdxfBackend:** LWPOLYLINE entity `closed` attribute, `get_points()` method for vertex extraction

### References

- FR11 (polyline closure): [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Functional Requirements"]
- PreDCR closure requirements: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "PreDCR Module"]
- 6-step tool handler: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- Snapshot / rollback: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Snapshot / Rollback"]
- ErrorCode constants: [Source: `src/lcs_cad_mcp/errors.py` — `ENTITY_NOT_FOUND`, `INVALID_PARAMS`, `CLOSURE_FAILED`]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 5, Story 5-7]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/backends/base.py`
- `src/lcs_cad_mcp/backends/ezdxf_backend.py`
- `src/lcs_cad_mcp/backends/com_backend.py`
- `src/lcs_cad_mcp/modules/entities/__init__.py`
- `src/lcs_cad_mcp/modules/entities/schemas.py`
- `src/lcs_cad_mcp/modules/entities/service.py`
- `src/lcs_cad_mcp/modules/entities/tools.py`
- `tests/unit/modules/entities/test_close_polyline_tool.py`
