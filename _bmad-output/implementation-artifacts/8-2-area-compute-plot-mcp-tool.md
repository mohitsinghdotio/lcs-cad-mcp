# Story 8.2: `area_compute_plot` MCP Tool

Status: ready-for-dev

## Story

As an **AI client**,
I want **to compute the plot boundary area from the loaded drawing**,
so that **the base area for all FSI and ground coverage calculations is established with verified Shapely precision** (FR22).

## Acceptance Criteria

1. **AC1:** `area_compute_plot()` MCP tool identifies the plot boundary entity by querying for entities on the `PLOT_BOUNDARY` layer and computes its polygon area via Shapely.
2. **AC2:** Returns area in square meters accurate to 4 decimal places (NFR11), with the raw float also available: `{"area_sqm": 1234.5678, "area_sqm_str": "1234.5678"}`.
3. **AC3:** Returns structured error `PLOT_BOUNDARY_NOT_FOUND` if no entity exists on the `PLOT_BOUNDARY` layer.
4. **AC4:** Returns structured error `POLYGON_NOT_CLOSED` if the plot boundary polyline is not closed.
5. **AC5:** Computation completes within 10 seconds (NFR4).
6. **AC6:** Computed plot area is stored in session state under `"plot_area_sqm"` for use by FSI and coverage tools downstream.
7. **AC7:** Tool handler follows the 6-step pattern: (1) session, (2) validate (no input params needed), (3) no snapshot, (4) `AreaService.compute_plot_area(session)`, (5) event_log, (6) return response.

## Tasks / Subtasks

- [ ] Task 1: Implement `AreaService.compute_plot_area` method in `modules/area/service.py` (AC: 1, 2, 3, 4)
  - [ ] 1.1: Method signature: `def compute_plot_area(self, session: DrawingSession) -> float` where `DrawingSession` provides access to the CAD backend
  - [ ] 1.2: Query entities on the `PLOT_BOUNDARY` layer using `session.backend.get_entities_on_layer("PLOT_BOUNDARY")` — returns `list[dict]` where each dict includes at minimum `"handle"`, `"type"`, and `"vertices": list[{x, y}]`
  - [ ] 1.3: If the result list is empty, raise `AreaComputationError(code="PLOT_BOUNDARY_NOT_FOUND", message="No entity found on PLOT_BOUNDARY layer")`
  - [ ] 1.4: Use the first entity's `"vertices"` list (plot boundary is a single closed polyline): `vertices = entities[0]["vertices"]`
  - [ ] 1.5: Call `self._entities_to_polygon(vertices)` to get a `shapely.Polygon`; let `AreaComputationError` propagate (e.g., `POLYGON_NOT_CLOSED`, `POLYGON_SELF_INTERSECTING`)
  - [ ] 1.6: Return `polygon.area` as a Python `float` (full 64-bit precision; formatting is done at the response boundary)

- [ ] Task 2: Implement `area_compute_plot` tool handler in `modules/area/tools.py` (AC: 1, 2, 3, 4, 6, 7)
  - [ ] 2.1: Tool signature: `async def area_compute_plot(ctx: Context) -> dict`
  - [ ] 2.2: Step 1 — retrieve session from `ctx.get_state("session")`; if `None`, return `SESSION_NOT_STARTED` error
  - [ ] 2.3: Step 2 — no input parameters to validate; add comment `# Step 2: no input params for area_compute_plot`
  - [ ] 2.4: Step 3 — no snapshot required (read-only computation); add comment `# Step 3: skipped — read-only computation`
  - [ ] 2.5: Step 4 — call `AreaService().compute_plot_area(session)`; catch `AreaComputationError` and return structured error: `{"success": false, "error": {"code": e.code, "message": e.message}}`
  - [ ] 2.6: Step 5 — write event log: `{"event": "area_plot_computed", "area_sqm": area_float}`
  - [ ] 2.7: Step 6 — store result in session: `ctx.set_state("plot_area_sqm", area_float)`; return `{"success": true, "data": {"area_sqm": area_float, "area_sqm_str": format_area(area_float), "layer": "PLOT_BOUNDARY"}}`

- [ ] Task 3: Register `area_compute_plot` tool in `modules/area/__init__.py` (AC: 1)
  - [ ] 3.1: Update `register(mcp: FastMCP)` to call `mcp.tool(name="area_compute_plot")(area_compute_plot)`
  - [ ] 3.2: Import `area_compute_plot` from `.tools` in `__init__.py`
  - [ ] 3.3: Add comment: `# area_ prefix for all area module tools — MCP naming convention`

- [ ] Task 4: Add/update output schemas in `modules/area/schemas.py` (AC: 2)
  - [ ] 4.1: Create `PlotAreaResult(BaseModel)`: `area_sqm: float`, `area_sqm_str: str`, `layer: str = "PLOT_BOUNDARY"`
  - [ ] 4.2: Ensure `format_area` utility function is accessible from `schemas.py` or keep it in `service.py` and import where needed

- [ ] Task 5: Verify `PLOT_BOUNDARY` layer constant is consistent (AC: 1, 3)
  - [ ] 5.1: Check if a `LayerNames` constants module exists (from Epic 3/4 — PreDCR layer registry); if yes, import `PLOT_BOUNDARY` constant from there instead of using a raw string
  - [ ] 5.2: If no such module exists yet, define `PLOT_BOUNDARY_LAYER = "PLOT_BOUNDARY"` as a module-level constant in `modules/area/service.py` with comment `# Must match PreDCR layer registry (Story 4-1)`
  - [ ] 5.3: Never hardcode layer name strings as bare literals inside logic — always reference the constant

- [ ] Task 6: Write unit and integration tests (AC: 1, 2, 3, 4, 5)
  - [ ] 6.1: `tests/unit/modules/area/test_area_compute_plot.py` — mock `session.backend.get_entities_on_layer("PLOT_BOUNDARY")` to return a 10×10 square; assert returned area = 100.0 (within 0.01)
  - [ ] 6.2: Test `PLOT_BOUNDARY_NOT_FOUND`: mock returns empty list; assert error response with correct code
  - [ ] 6.3: Test `POLYGON_NOT_CLOSED`: mock returns open polygon vertices; assert error propagated with `POLYGON_NOT_CLOSED` code
  - [ ] 6.4: Test session storage: after successful call, `ctx.get_state("plot_area_sqm")` returns the computed float
  - [ ] 6.5: Test response format: `area_sqm_str` is `"100.0000"` for a 100 sqm plot (4dp formatting)
  - [ ] 6.6: Test performance: use `time.perf_counter()` before/after call; assert duration < 10.0 seconds on a moderately complex polygon (NFR4)

## Dev Notes

### Critical Architecture Constraints

1. **Shapely for ALL polygon operations** — `compute_plot_area` must NOT compute area via the shoelace formula or any other manual method. The only area computation is `polygon.area` where `polygon` is a `shapely.geometry.Polygon`. Add comment: `# shapely polygon.area — NFR11 compliance`.
2. **Session state key `"plot_area_sqm"`** — this exact key name is consumed by downstream tools `area_compute_fsi` and `area_compute_coverage` in Story 8-4. Do not change the key name without updating those tools.
3. **Layer name consistency** — the string `"PLOT_BOUNDARY"` must match the layer name established in the PreDCR layer registry (Epic 4). If Epic 4 defines a different canonical name, that name takes precedence. Check `modules/predcr/layer_registry.py` for the authoritative value.
4. **Return raw float AND formatted string** — `area_sqm` is the raw `float` (for downstream arithmetic without re-parsing), `area_sqm_str` is the 4dp-formatted string (for display). Both are required in the response. Never return only the string.
5. **No snapshot for read-only tools** — `area_compute_plot` reads from the drawing but does not modify it. Step 3 (snapshot) is explicitly skipped. Add `# Step 3: skipped — read-only computation, no drawing mutation` comment.
6. **`AreaService` is instantiated per-call** — `AreaService()` is created fresh in the tool handler, not stored in session. It is a stateless computation class.

### Module/Component Notes

**`AreaService.compute_plot_area` full signature and contract:**

```python
def compute_plot_area(self, session) -> float:
    """Compute plot boundary area using Shapely polygon.

    Args:
        session: Active DrawingSession with backend access

    Returns:
        Plot area in square meters as float (full precision)

    Raises:
        AreaComputationError: PLOT_BOUNDARY_NOT_FOUND, POLYGON_NOT_CLOSED,
                              POLYGON_SELF_INTERSECTING, POLYGON_TOO_FEW_VERTICES
    """
    entities = session.backend.get_entities_on_layer(PLOT_BOUNDARY_LAYER)
    if not entities:
        raise AreaComputationError(
            code="PLOT_BOUNDARY_NOT_FOUND",
            message=f"No entity found on layer '{PLOT_BOUNDARY_LAYER}'. "
                    "Ensure plot boundary polyline is drawn on the correct layer."
        )
    vertices = entities[0].get("vertices", [])
    polygon = self._entities_to_polygon(vertices)  # shapely polygon.area — NFR11 compliance
    return polygon.area  # full float precision; format at response boundary
```

**Expected tool response shape:**

```python
# Success:
{
    "success": True,
    "data": {
        "area_sqm": 1234.5678,        # raw float for downstream arithmetic
        "area_sqm_str": "1234.5678",  # 4dp string for display (NFR11)
        "layer": "PLOT_BOUNDARY"
    }
}

# Error — no plot boundary:
{
    "success": False,
    "error": {
        "code": "PLOT_BOUNDARY_NOT_FOUND",
        "message": "No entity found on layer 'PLOT_BOUNDARY'. Ensure plot boundary polyline is drawn on the correct layer.",
        "recoverable": True,
        "suggested_action": "Draw a closed polyline on the PLOT_BOUNDARY layer and retry."
    }
}
```

**Backend method contract expected from `session.backend`:**

The `get_entities_on_layer(layer_name: str) -> list[dict]` method is expected to return dicts in this shape (established in Epic 5):

```python
{
    "handle": "1A2B",
    "type": "LWPOLYLINE",
    "layer": "PLOT_BOUNDARY",
    "vertices": [
        {"x": 0.0, "y": 0.0},
        {"x": 10.0, "y": 0.0},
        {"x": 10.0, "y": 10.0},
        {"x": 0.0, "y": 10.0},
        {"x": 0.0, "y": 0.0}   # closing vertex
    ]
}
```

### Project Structure Notes

Files to create or modify in this story:

```
src/lcs_cad_mcp/modules/area/
├── __init__.py                       # Update: register area_compute_plot
├── tools.py                          # Implement: area_compute_plot handler
├── service.py                        # Update: add compute_plot_area method, PLOT_BOUNDARY_LAYER constant
└── schemas.py                        # Update: add PlotAreaResult

tests/unit/modules/area/
└── test_area_compute_plot.py         # New
```

**No new files outside `modules/area/` are needed.** `errors.py` additions for this story were handled in Story 8-1 (`PLOT_BOUNDARY_NOT_FOUND` error code).

### Dependencies

- **Story 8-1** — `AreaService`, `_entities_to_polygon`, `AreaComputationError`, and `format_area` must be implemented. `POLYGON_NOT_CLOSED` and `POLYGON_SELF_INTERSECTING` error codes must exist.
- **Story 5-6** (`entity_query`) — provides the `get_entities_on_layer` backend method signature. The entity dict format (including `"vertices"` list) must match what `_entities_to_polygon` expects.
- **Story 2-1** (backend abstraction) — `session.backend.get_entities_on_layer()` is part of the `CADBackend` abstract interface; must be implemented in both ezdxf and COM backends.
- **Story 4-1** (PreDCR layer specification) — the canonical `PLOT_BOUNDARY` layer name is established there; check for consistency.

### References

- Architecture area computation: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Area Computation Engine"]
- NFR4 (10 second computation limit): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- NFR11 (area accuracy ±0.01 sqm): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- FR22 (area computation): [Source: `_bmad-output/planning-artifacts/architecture.md` — FR section]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 8, Story 8-2]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/area/__init__.py` (updated)
- `src/lcs_cad_mcp/modules/area/tools.py` (updated)
- `src/lcs_cad_mcp/modules/area/service.py` (updated)
- `src/lcs_cad_mcp/modules/area/schemas.py` (updated)
- `tests/unit/modules/area/test_area_compute_plot.py`
