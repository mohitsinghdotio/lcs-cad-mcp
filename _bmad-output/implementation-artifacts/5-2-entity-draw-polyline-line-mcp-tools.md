# Story 5.2: `entity_draw_polyline` and `entity_draw_line` MCP Tools

Status: ready-for-dev

## Story

As an **AI client**,
I want **to draw polylines and lines on specified CAD layers**,
so that **plot boundaries, building footprints, setback lines, and structural geometry can be created programmatically via MCP**.

## Acceptance Criteria

1. **AC1:** `entity_draw_polyline(vertices: list[tuple[float, float]], layer: str, closed: bool = False)` MCP tool draws a polyline on the specified layer and returns `{"success": true, "data": {"entity_id": "<handle>"}}` — entity_id is the ezdxf DXF handle string or COM UUID
2. **AC2:** `entity_draw_line(start: tuple[float, float], end: tuple[float, float], layer: str)` MCP tool draws a single line segment and returns `{"success": true, "data": {"entity_id": "<handle>"}}`
3. **AC3:** Both tools validate that the target layer exists before drawing; if layer does not exist they return `{"success": false, "error": {"code": "LAYER_NOT_FOUND", ...}}` without modifying the drawing
4. **AC4:** When `closed=True`, the polyline produced is geometrically closed — the backend sets the polyline's closed flag AND the first and last vertex are verified to be equal (or the backend closes them); tool returns closure confirmation in response properties
5. **AC5:** Both tools execute against both `EzdxfBackend` and `COMBackend` without modification to tool or service code — backend abstraction handles the difference
6. **AC6:** Both tools complete within 2 seconds on drawings with up to 10,000 entities (NFR1)
7. **AC7:** Both tools take a snapshot via the session snapshot mechanism BEFORE mutating the drawing, enabling rollback if a subsequent error occurs

## Tasks / Subtasks

- [ ] Task 1: Implement `EntityService.draw_polyline` and `EntityService.draw_line` in `service.py` (AC: 1, 2, 4, 5)
  - [ ] 1.1: Replace `draw_polyline` stub with real implementation: call `self._backend.add_polyline(layer=layer, vertices=vertices, closed=closed)` — returns entity handle string
  - [ ] 1.2: Replace `draw_line` stub with real implementation: call `self._backend.add_line(layer=layer, start=start, end=end)` — returns entity handle string
  - [ ] 1.3: For `draw_polyline` with `closed=True`: after drawing, verify closure by asserting `vertices[0] == vertices[-1]` OR set the polyline's closed flag via backend; log closure gap if vertices differ by epsilon (< 0.001)
  - [ ] 1.4: Both methods must return `EntityRecord` (from `schemas.py`) populated with `entity_id`, `entity_type`, `layer`, and computed `bounding_box`
  - [ ] 1.5: Add private helper `_compute_polyline_bbox(vertices) -> BoundingBox` and `_compute_line_bbox(start, end) -> BoundingBox`

- [ ] Task 2: Implement MCP tool handlers in `tools.py` following the 6-step pattern (AC: 1, 2, 3, 7)
  - [ ] 2.1: Add `@mcp.tool()` async function `entity_draw_polyline(ctx: Context, vertices: list[tuple[float, float]], layer: str, closed: bool = False) -> dict`
  - [ ] 2.2: Add `@mcp.tool()` async function `entity_draw_line(ctx: Context, start: tuple[float, float], end: tuple[float, float], layer: str) -> dict`
  - [ ] 2.3: Step 1 — Session retrieval: `session = ctx.get_state("drawing_session")`; raise `TOOL_CALLED_WITHOUT_SESSION` MCPError if None
  - [ ] 2.4: Step 2 — Input validation: for `entity_draw_polyline` check `len(vertices) >= 2`, raise `INVALID_PARAMS` MCPError if not; for `entity_draw_line` check `start != end`, raise `INVALID_PARAMS` if identical
  - [ ] 2.5: Step 3 — Layer existence check: call `session.backend.layer_exists(layer)`; return `LAYER_NOT_FOUND` MCPError if False
  - [ ] 2.6: Step 4 — Snapshot: `snapshot_id = await session.snapshot.take()` BEFORE any mutation
  - [ ] 2.7: Step 5 — EntityService call: `result = EntityService(session).draw_polyline(...)` or `draw_line(...)`
  - [ ] 2.8: Step 6 — Event log + return: `session.event_log.append(...)`, return `{"success": True, "data": {"entity_id": result.entity_id, "layer": result.layer, "bounding_box": result.bounding_box.model_dump() if result.bounding_box else None}}`

- [ ] Task 3: Register tools in `__init__.py` (AC: 1, 2)
  - [ ] 3.1: Update `register(mcp)` in `entities/__init__.py` to import and call `_register_draw_tools(mcp)` from `tools.py`
  - [ ] 3.2: Define `_register_draw_tools(mcp)` in `tools.py` that calls `mcp.tool()(entity_draw_polyline)` and `mcp.tool()(entity_draw_line)` — or use decorator syntax if `mcp` is available at import time via closure
  - [ ] 3.3: Confirm both tool names appear as `entity_draw_polyline` and `entity_draw_line` in the MCP tool registry (no prefix mangling)

- [ ] Task 4: Extend `CADBackend` protocol for entity drawing methods (AC: 5)
  - [ ] 4.1: Add `add_polyline(layer: str, vertices: list[tuple[float, float]], closed: bool) -> str` to the `CADBackend` Protocol in `backends/base.py`
  - [ ] 4.2: Add `add_line(layer: str, start: tuple[float, float], end: tuple[float, float]) -> str` to `CADBackend` Protocol
  - [ ] 4.3: Add `layer_exists(layer: str) -> bool` to `CADBackend` Protocol (if not already present from Epic 3)
  - [ ] 4.4: Implement both methods in `EzdxfBackend`: use `msp.add_lwpolyline(points=vertices, close=closed, dxfattribs={"layer": layer})` and `msp.add_line(start=start, end=end, dxfattribs={"layer": layer})`; return entity `.dxf.handle`
  - [ ] 4.5: Add stub implementations in `COMBackend` that raise `NotImplementedError("COM backend entity drawing: Story 5-2")` — COM implementation deferred, stub prevents import errors

- [ ] Task 5: Write unit tests with `MockCADBackend` (AC: 1, 2, 3, 4, 7)
  - [ ] 5.1: Create `tests/unit/modules/entities/test_draw_tools.py`
  - [ ] 5.2: Build `MockCADBackend` fixture (or extend existing from `conftest.py`) that records `add_polyline` / `add_line` calls and returns deterministic fake handles (`"MOCK_HANDLE_001"` etc.)
  - [ ] 5.3: Test `entity_draw_polyline` happy path: 4 vertices, `closed=False` → returns `entity_id`, correct `layer`
  - [ ] 5.4: Test `entity_draw_polyline` with `closed=True`: verify response includes closure confirmation
  - [ ] 5.5: Test `entity_draw_polyline` with only 1 vertex → `INVALID_PARAMS` error response
  - [ ] 5.6: Test both tools with non-existent layer → `LAYER_NOT_FOUND` error, no snapshot taken, no backend mutation
  - [ ] 5.7: Test `entity_draw_line` happy path: distinct start/end → returns `entity_id`
  - [ ] 5.8: Test `entity_draw_line` with identical start/end → `INVALID_PARAMS` error
  - [ ] 5.9: Test snapshot is taken before service call: mock snapshot and assert `take()` called exactly once per successful draw operation

- [ ] Task 6: Performance sanity check (AC: 6)
  - [ ] 6.1: Add a timing test in `tests/unit/modules/entities/test_draw_tools.py` using `time.perf_counter()` that calls `entity_draw_polyline` 100 times via `MockCADBackend` and asserts average < 20ms per call (ensures no O(n) overhead in Python layer)
  - [ ] 6.2: Document in test comment: "Full 2s NFR1 compliance measured against real ezdxf backend in integration tests"

## Dev Notes

### Critical Architecture Constraints

1. **6-Step tool handler pattern is mandatory** (enforced across all entity write tools):
   - Step 1: Get session from `ctx.get_state("drawing_session")`
   - Step 2: Validate inputs (Python-level, before touching backend)
   - Step 3: Check layer existence via `session.backend.layer_exists(layer)`
   - Step 4: Take snapshot via `session.snapshot.take()`
   - Step 5: Call `EntityService(session).method(...)`
   - Step 6: Append to event log, return structured response

2. **Snapshot BEFORE mutation** — if any exception occurs after the snapshot but before the return, the caller (or a subsequent rollback tool call) can restore the drawing to the pre-mutation state. The snapshot must always precede the backend call.

3. **EntityService is the only caller of `session.backend` entity methods** — tool handlers in `tools.py` must NOT call `session.backend.add_polyline()` directly. They delegate to `EntityService`. This is the module boundary enforced by the architecture.

4. **No direct ezdxf imports in `entities/` module** — `EzdxfBackend` handles all ezdxf-specific API. The `EntityService` and `tools.py` are backend-agnostic.

### Module/Component Notes

**Tool parameter types exposed to MCP clients:**

`entity_draw_polyline`:
- `vertices: list[tuple[float, float]]` — list of (x, y) coordinate pairs; minimum 2 points
- `layer: str` — target layer name (must already exist)
- `closed: bool = False` — if True, polyline is closed (last vertex connects to first)

`entity_draw_line`:
- `start: tuple[float, float]` — (x, y) start point
- `end: tuple[float, float]` — (x, y) end point
- `layer: str` — target layer name (must already exist)

**Response schema (both tools):**
```python
{
    "success": True,
    "data": {
        "entity_id": "1F3A",          # DXF handle or UUID string
        "entity_type": "POLYLINE",    # or "LINE"
        "layer": "PLOT-BOUNDARY",
        "bounding_box": {
            "min_x": 0.0, "min_y": 0.0,
            "max_x": 100.0, "max_y": 50.0
        },
        "closed": True                 # only for polyline
    }
}
```

**`EzdxfBackend.add_polyline` implementation reference:**
```python
def add_polyline(self, layer: str, vertices: list[tuple[float, float]], closed: bool) -> str:
    msp = self._doc.modelspace()
    entity = msp.add_lwpolyline(
        points=vertices,
        close=closed,
        dxfattribs={"layer": layer}
    )
    return entity.dxf.handle
```

### Project Structure Notes

Files modified by this story:
```
src/lcs_cad_mcp/
├── backends/
│   ├── base.py              # add_polyline, add_line, layer_exists to Protocol
│   ├── ezdxf_backend.py     # implement add_polyline, add_line
│   └── com_backend.py       # stub add_polyline, add_line
└── modules/entities/
    ├── __init__.py           # register() now wires draw tools
    ├── service.py            # draw_polyline, draw_line implemented
    └── tools.py              # entity_draw_polyline, entity_draw_line handlers

tests/unit/modules/entities/
└── test_draw_tools.py        # new
```

### Dependencies

- **Story 5-1 (Entity Data Models):** `EntityRecord`, `PolylineEntityRecord`, `LineEntityRecord`, `BoundingBox`, `EntityService` skeleton must exist before this story begins
- **Story 2-4 (EzdxfBackend write operations):** The `EzdxfBackend` must support the `add_polyline`/`add_line` Protocol methods; if Story 2-4 did not add them, this story adds them to both Protocol and EzdxfBackend
- **Story 3-1 (Layer management):** `layer_exists()` on the backend — may already exist from Epic 3; if not, add it to Protocol and implement here
- **Session snapshot mechanism (Story 2-x):** `session.snapshot.take()` must be a working coroutine

### References

- Entity tool naming: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "MCP Tool Naming Conventions"]
- 6-step tool handler: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- CADBackend Protocol: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Backend Abstraction"]
- Snapshot before mutation: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Snapshot / Rollback"]
- NFR1 (2s per tool): [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Performance Requirements"]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 5, Story 5-2]

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
- `src/lcs_cad_mcp/modules/entities/service.py`
- `src/lcs_cad_mcp/modules/entities/tools.py`
- `tests/unit/modules/entities/test_draw_tools.py`
