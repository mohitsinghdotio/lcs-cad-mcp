# Story 5.3: `entity_draw_arc` and `entity_draw_circle` MCP Tools

Status: ready-for-dev

## Story

As an **AI client**,
I want **to draw arcs and circles on specified CAD layers**,
so that **rounded architectural features, reference circles, and curved building elements can be created programmatically**.

## Acceptance Criteria

1. **AC1:** `entity_draw_arc(center: tuple[float, float], radius: float, start_angle: float, end_angle: float, layer: str)` MCP tool draws an arc and returns `{"success": true, "data": {"entity_id": "<handle>", "entity_type": "ARC", "layer": "<layer>"}}`
2. **AC2:** `entity_draw_circle(center: tuple[float, float], radius: float, layer: str)` MCP tool draws a full circle and returns `{"success": true, "data": {"entity_id": "<handle>", "entity_type": "CIRCLE", "layer": "<layer>"}}`
3. **AC3:** Both tools validate layer existence before drawing; non-existent layer returns `LAYER_NOT_FOUND` error without modifying the drawing
4. **AC4:** Both tools validate `radius > 0`; zero or negative radius returns `INVALID_PARAMS` error
5. **AC5:** `entity_draw_arc` validates angle values — `start_angle` and `end_angle` must be in `[0, 360)` degrees; angles are normalized if outside range (wrap modulo 360)
6. **AC6:** Both tools execute against both `EzdxfBackend` and `COMBackend` — same tool/service code, backend handles DXF-specifics
7. **AC7:** Both tools complete within 2 seconds (NFR1)
8. **AC8:** Both tools take a snapshot BEFORE mutating the drawing

## Tasks / Subtasks

- [ ] Task 1: Implement `EntityService.draw_arc` and `EntityService.draw_circle` in `service.py` (AC: 1, 2, 5, 6)
  - [ ] 1.1: Replace `draw_arc` stub: call `self._backend.add_arc(layer=layer, center=center, radius=radius, start_angle=start_angle, end_angle=end_angle)` — returns entity handle string
  - [ ] 1.2: Replace `draw_circle` stub: call `self._backend.add_circle(layer=layer, center=center, radius=radius)` — returns entity handle string
  - [ ] 1.3: Add angle normalization helper `_normalize_angle(angle: float) -> float` that wraps any angle into `[0, 360)` using `angle % 360`
  - [ ] 1.4: Apply `_normalize_angle` to both `start_angle` and `end_angle` before passing to backend
  - [ ] 1.5: Populate and return `ArcEntityRecord` / `CircleEntityRecord` with `entity_id`, `entity_type`, `layer`, and computed `bounding_box`
  - [ ] 1.6: Add `_compute_arc_bbox(center, radius, start_angle, end_angle) -> BoundingBox` helper — computes tight bounding box accounting for which quadrant extrema the arc passes through
  - [ ] 1.7: Add `_compute_circle_bbox(center, radius) -> BoundingBox` helper: `BoundingBox(min_x=cx-r, min_y=cy-r, max_x=cx+r, max_y=cy+r)`

- [ ] Task 2: Implement MCP tool handlers in `tools.py` following the 6-step pattern (AC: 1, 2, 3, 4, 5, 8)
  - [ ] 2.1: Add `@mcp.tool()` async function `entity_draw_arc(ctx: Context, center: tuple[float, float], radius: float, start_angle: float, end_angle: float, layer: str) -> dict`
  - [ ] 2.2: Add `@mcp.tool()` async function `entity_draw_circle(ctx: Context, center: tuple[float, float], radius: float, layer: str) -> dict`
  - [ ] 2.3: Step 1 — Session: `session = ctx.get_state("drawing_session")`; return `SESSION_NOT_STARTED` error if None
  - [ ] 2.4: Step 2 — Validate `radius > 0` for both tools; return `INVALID_PARAMS` MCPError if not
  - [ ] 2.5: Step 3 — Validate layer existence: `session.backend.layer_exists(layer)`; return `LAYER_NOT_FOUND` if False
  - [ ] 2.6: Step 4 — Snapshot: `snapshot_id = await session.snapshot.take()`
  - [ ] 2.7: Step 5 — Delegate to `EntityService(session).draw_arc(...)` or `draw_circle(...)`
  - [ ] 2.8: Step 6 — Event log entry + return structured response with `entity_id`, `entity_type`, `layer`, `bounding_box`

- [ ] Task 3: Extend `CADBackend` Protocol and implement in backends (AC: 6)
  - [ ] 3.1: Add `add_arc(layer: str, center: tuple[float, float], radius: float, start_angle: float, end_angle: float) -> str` to `CADBackend` Protocol in `backends/base.py`
  - [ ] 3.2: Add `add_circle(layer: str, center: tuple[float, float], radius: float) -> str` to `CADBackend` Protocol
  - [ ] 3.3: Implement `EzdxfBackend.add_arc`: `msp.add_arc(radius=radius, center=center, start_angle=start_angle, end_angle=end_angle, dxfattribs={"layer": layer})`; return entity handle
  - [ ] 3.4: Implement `EzdxfBackend.add_circle`: `msp.add_circle(center=center, radius=radius, dxfattribs={"layer": layer})`; return entity handle
  - [ ] 3.5: Add `COMBackend.add_arc` and `COMBackend.add_circle` stubs raising `NotImplementedError("COM backend arc/circle: Story 5-3")`

- [ ] Task 4: Register new tools in `entities/__init__.py` (AC: 1, 2)
  - [ ] 4.1: Update `register(mcp)` to also invoke `_register_arc_circle_tools(mcp)` defined in `tools.py`
  - [ ] 4.2: Confirm tool names `entity_draw_arc` and `entity_draw_circle` appear correctly in MCP registry
  - [ ] 4.3: Ensure previously registered draw tools from Story 5-2 are not broken by this change

- [ ] Task 5: Write unit tests (AC: 1, 2, 3, 4, 5, 7, 8)
  - [ ] 5.1: Create `tests/unit/modules/entities/test_arc_circle_tools.py`
  - [ ] 5.2: Test `entity_draw_arc` happy path: valid center, radius, angles, layer → returns `entity_id` and `ARC` entity_type
  - [ ] 5.3: Test `entity_draw_arc` with `radius=0` → `INVALID_PARAMS` error
  - [ ] 5.4: Test `entity_draw_arc` with `radius=-5.0` → `INVALID_PARAMS` error
  - [ ] 5.5: Test `entity_draw_arc` with out-of-range angles (e.g., `start_angle=400, end_angle=-30`) → normalizes to `40.0` and `330.0` without error
  - [ ] 5.6: Test `entity_draw_circle` happy path: returns `entity_id` and `CIRCLE` entity_type
  - [ ] 5.7: Test `entity_draw_circle` with `radius=0` → `INVALID_PARAMS` error
  - [ ] 5.8: Test both tools with non-existent layer → `LAYER_NOT_FOUND`, no snapshot taken, no backend call made
  - [ ] 5.9: Test `BoundingBox` for circle: `center=(10,10)`, `radius=5` → `BoundingBox(min_x=5, min_y=5, max_x=15, max_y=15)`
  - [ ] 5.10: Test snapshot is taken exactly once for each successful call
  - [ ] 5.11: Test `_compute_arc_bbox` for a quarter-circle arc (0° to 90°, center at origin, radius 10) → bbox covers `[0,10] x [0,10]`

- [ ] Task 6: Arc bounding box edge-case validation (AC: 1)
  - [ ] 6.1: Document the arc bounding box algorithm in a docstring on `_compute_arc_bbox`: the extrema of a circular arc occur either at angle multiples of 90° (0°, 90°, 180°, 270°) that fall within the arc's angular span, or at the start/end angles themselves
  - [ ] 6.2: Implement the arc bbox to iterate over `[0, 90, 180, 270]` degree extrema and include each if its angle falls within the arc span (handling wrap-around correctly)
  - [ ] 6.3: Add parametrized unit tests for arc bbox across all four quadrant combinations

## Dev Notes

### Critical Architecture Constraints

1. **6-step handler pattern** (same as Story 5-2): session → validate → layer-check → snapshot → service → event_log+return. No exceptions to this ordering.
2. **Angle convention:** DXF arc angles are in degrees, measured counter-clockwise from the positive X axis. This story passes angles directly to ezdxf without conversion — the AI client is expected to provide angles in degrees CCW from X-axis. Document this in the tool docstring.
3. **Snapshot before mutation** — identical requirement to Story 5-2. The snapshot `take()` call must precede any `session.backend` method call.
4. **EntityService is the sole mediator** — `tools.py` never calls `session.backend.add_arc()` directly.

### Module/Component Notes

**Tool parameter definitions for MCP clients:**

`entity_draw_arc`:
- `center: tuple[float, float]` — `(x, y)` center point of the arc's parent circle
- `radius: float` — must be > 0; in drawing units
- `start_angle: float` — start angle in degrees, CCW from positive X axis; normalized to `[0, 360)`
- `end_angle: float` — end angle in degrees, CCW from positive X axis; normalized to `[0, 360)`
- `layer: str` — target layer name (must exist)

`entity_draw_circle`:
- `center: tuple[float, float]` — `(x, y)` center point
- `radius: float` — must be > 0; in drawing units
- `layer: str` — target layer name (must exist)

**Response schema:**
```python
# entity_draw_arc success response
{
    "success": True,
    "data": {
        "entity_id": "2B7C",
        "entity_type": "ARC",
        "layer": "SETBACK-LINE",
        "center": [10.0, 20.0],
        "radius": 5.0,
        "start_angle": 45.0,
        "end_angle": 135.0,
        "bounding_box": {"min_x": 6.46, "min_y": 20.0, "max_x": 13.54, "max_y": 25.0}
    }
}

# entity_draw_circle success response
{
    "success": True,
    "data": {
        "entity_id": "3C8D",
        "entity_type": "CIRCLE",
        "layer": "BLDG-FOOTPRINT",
        "center": [50.0, 50.0],
        "radius": 10.0,
        "bounding_box": {"min_x": 40.0, "min_y": 40.0, "max_x": 60.0, "max_y": 60.0}
    }
}
```

**Arc bounding box algorithm sketch:**
```python
def _compute_arc_bbox(center, radius, start_angle, end_angle) -> BoundingBox:
    import math
    cx, cy = center
    # Start with the two endpoint extrema
    xs = [cx + radius * math.cos(math.radians(start_angle)),
          cx + radius * math.cos(math.radians(end_angle))]
    ys = [cy + radius * math.sin(math.radians(start_angle)),
          cy + radius * math.sin(math.radians(end_angle))]
    # Check cardinal extrema (0, 90, 180, 270 degrees)
    for cardinal in [0.0, 90.0, 180.0, 270.0]:
        if _angle_in_arc_span(cardinal, start_angle, end_angle):
            xs.append(cx + radius * math.cos(math.radians(cardinal)))
            ys.append(cy + radius * math.sin(math.radians(cardinal)))
    return BoundingBox(min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys))
```

### Project Structure Notes

Files modified by this story:
```
src/lcs_cad_mcp/
├── backends/
│   ├── base.py              # add_arc, add_circle to Protocol
│   ├── ezdxf_backend.py     # implement add_arc, add_circle
│   └── com_backend.py       # stub add_arc, add_circle
└── modules/entities/
    ├── __init__.py           # register() includes arc/circle tools
    ├── service.py            # draw_arc, draw_circle implemented
    └── tools.py              # entity_draw_arc, entity_draw_circle handlers

tests/unit/modules/entities/
└── test_arc_circle_tools.py  # new
```

### Dependencies

- **Story 5-2 (draw_polyline / draw_line):** The `CADBackend` Protocol extension pattern, `layer_exists()`, session snapshot integration, and 6-step tool handler structure are all established in Story 5-2. This story follows the same pattern.
- **Story 5-1 (Entity Data Models):** `ArcEntityRecord`, `CircleEntityRecord`, `BoundingBox`, `EntityService` skeleton
- **EzdxfBackend (Story 2-x):** Must expose `msp` (model space) with ezdxf's `add_arc` and `add_circle` methods

### References

- Entity tool naming: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "MCP Tool Naming Conventions"]
- 6-step tool handler: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- CADBackend Protocol extension: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Backend Abstraction"]
- Snapshot / rollback: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Snapshot / Rollback"]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 5, Story 5-3]

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
- `tests/unit/modules/entities/test_arc_circle_tools.py`
