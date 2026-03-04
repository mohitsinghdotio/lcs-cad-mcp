# Story 8.3: `area_compute_builtup` and `area_compute_carpet` MCP Tools

Status: ready-for-dev

## Story

As an **AI client**,
I want **to compute built-up area and carpet area for all floors in the loaded drawing**,
so that **these values are available as inputs to FSI calculation and DCR rule checking** (FR22).

## Acceptance Criteria

1. **AC1:** `area_compute_builtup()` MCP tool sums the Shapely polygon areas of all floor plate entities across all floor layers (layers matching pattern `FLOOR_PLATE_*` or equivalent PreDCR convention), returning both per-floor breakdown and total.
2. **AC2:** `area_compute_carpet()` MCP tool computes carpet area as `built-up area × wall_thickness_factor`; `wall_thickness_factor` is configurable with a default of `0.85` (representing 85% of built-up after deducting walls and ducts per PreDCR definition).
3. **AC3:** Both tools return a per-floor breakdown list and a total: `{"floors": [{"floor": "GF", "area_sqm": ..., "area_sqm_str": "..."}, ...], "total_sqm": ..., "total_sqm_str": "..."}`.
4. **AC4:** Area accuracy to ±0.01 sqm per floor plate and in the total (NFR11).
5. **AC5:** Both tools store their results in session state: `"buildup_area_sqm"` (float) and `"carpet_area_sqm"` (float) for downstream FSI/coverage tools.
6. **AC6:** Returns `FLOOR_PLATES_NOT_FOUND` error if no floor plate layers/entities are found in the drawing.
7. **AC7:** Both tool handlers follow the 6-step pattern: (1) session, (2) validate inputs (`wall_thickness_factor` range 0.0–1.0), (3) no snapshot, (4) `AreaService` method, (5) event_log, (6) return response.

## Tasks / Subtasks

- [ ] Task 1: Implement floor layer discovery in `AreaService` (AC: 1, 6)
  - [ ] 1.1: Add `_get_floor_plate_layers(self, session) -> list[str]` method that calls `session.backend.list_layers()` and returns all layers whose names match the PreDCR floor plate naming convention (e.g., prefix `FLOOR_PLATE_` or layers from PreDCR layer registry)
  - [ ] 1.2: Check `modules/predcr/layer_registry.py` for the authoritative floor plate layer naming pattern; use that pattern (do NOT hardcode a guess — check and reference the actual constant)
  - [ ] 1.3: If no matching layers found, raise `AreaComputationError(code="FLOOR_PLATES_NOT_FOUND", message="No floor plate layers found in drawing. Expected layers matching FLOOR_PLATE_* pattern.")`
  - [ ] 1.4: Return layers sorted by floor order (ground floor first, then upper floors) — use natural sort on the numeric suffix if present (e.g., `FLOOR_PLATE_GF`, `FLOOR_PLATE_1`, `FLOOR_PLATE_2`, ...)

- [ ] Task 2: Implement `AreaService.compute_buildup_area` method (AC: 1, 3, 4)
  - [ ] 2.1: Method signature: `def compute_buildup_area(self, session) -> dict` returning `{"floors": list[dict], "total_sqm": float}`
  - [ ] 2.2: Call `_get_floor_plate_layers(session)` to get the list of floor layers
  - [ ] 2.3: For each layer, call `session.backend.get_entities_on_layer(layer_name)` to get floor plate entities
  - [ ] 2.4: For each entity in each layer, call `self._entities_to_polygon(entity["vertices"])` and sum the areas via `total_layer_area = sum(polygon.area for polygon in polygons)` — all via Shapely (NFR11)
  - [ ] 2.5: Build per-floor dict: `{"floor": layer_name, "area_sqm": layer_area, "area_sqm_str": format_area(layer_area)}`
  - [ ] 2.6: Compute `total_sqm = sum(f["area_sqm"] for f in floors)` — do NOT re-sum from strings; sum from floats
  - [ ] 2.7: Return `{"floors": floors, "total_sqm": total_sqm, "total_sqm_str": format_area(total_sqm)}`

- [ ] Task 3: Implement `AreaService.compute_carpet_area` method (AC: 2, 3, 4)
  - [ ] 3.1: Method signature: `def compute_carpet_area(self, session, wall_thickness_factor: float = 0.85) -> dict`
  - [ ] 3.2: Validate `0.0 < wall_thickness_factor <= 1.0`; raise `AreaComputationError(code="INVALID_WALL_FACTOR", message="wall_thickness_factor must be between 0.0 and 1.0 (exclusive/inclusive)")` if out of range
  - [ ] 3.3: Call `self.compute_buildup_area(session)` to get the buildup result
  - [ ] 3.4: Compute carpet area per floor: `carpet_floor_area = floor["area_sqm"] * wall_thickness_factor`
  - [ ] 3.5: Compute total: `total_carpet = total_buildup * wall_thickness_factor`
  - [ ] 3.6: Return same structure as buildup but with carpet-adjusted values, plus `"wall_thickness_factor": wall_thickness_factor` in the response for traceability

- [ ] Task 4: Implement `area_compute_builtup` tool handler in `modules/area/tools.py` (AC: 1, 3, 5, 7)
  - [ ] 4.1: Tool signature: `async def area_compute_builtup(ctx: Context) -> dict`
  - [ ] 4.2: Steps 1–3: get session, no input params to validate, skip snapshot
  - [ ] 4.3: Step 4: call `AreaService().compute_buildup_area(session)`; catch `AreaComputationError` → structured error
  - [ ] 4.4: Step 5: event log `{"event": "area_buildup_computed", "total_sqm": total, "floor_count": len(floors)}`
  - [ ] 4.5: Step 6: `ctx.set_state("buildup_area_sqm", result["total_sqm"])`; return success response with full `result` dict

- [ ] Task 5: Implement `area_compute_carpet` tool handler in `modules/area/tools.py` (AC: 2, 3, 5, 7)
  - [ ] 5.1: Tool signature: `async def area_compute_carpet(ctx: Context, wall_thickness_factor: float = 0.85) -> dict`
  - [ ] 5.2: Step 2: validate `0.0 < wall_thickness_factor <= 1.0`; return `INVALID_PARAMS` error if out of range
  - [ ] 5.3: Steps 1, 3: get session, skip snapshot
  - [ ] 5.4: Step 4: call `AreaService().compute_carpet_area(session, wall_thickness_factor)`; catch `AreaComputationError` → structured error
  - [ ] 5.5: Step 5: event log `{"event": "area_carpet_computed", "total_sqm": total, "wall_thickness_factor": wall_thickness_factor}`
  - [ ] 5.6: Step 6: `ctx.set_state("carpet_area_sqm", result["total_sqm"])`; return success response

- [ ] Task 6: Register tools and update schemas (AC: 1, 2, 7)
  - [ ] 6.1: Add `FLOOR_PLATES_NOT_FOUND` and `INVALID_WALL_FACTOR` to `ErrorCode` in `errors.py`
  - [ ] 6.2: Register both tools in `modules/area/__init__.py`: `area_compute_builtup` and `area_compute_carpet`
  - [ ] 6.3: Add `FloorAreaBreakdown(BaseModel)`: `floor: str`, `area_sqm: float`, `area_sqm_str: str` to `schemas.py`
  - [ ] 6.4: Add `BuiltupAreaResult(BaseModel)`: `floors: list[FloorAreaBreakdown]`, `total_sqm: float`, `total_sqm_str: str` to `schemas.py`
  - [ ] 6.5: Add `CarpetAreaResult(BaseModel)`: extends `BuiltupAreaResult` with `wall_thickness_factor: float` to `schemas.py`

- [ ] Task 7: Write unit tests (AC: 1, 2, 3, 4, 6)
  - [ ] 7.1: `tests/unit/modules/area/test_area_compute_builtup.py` — mock 3-floor building (GF 200sqm, 1F 180sqm, 2F 180sqm); assert total = 560.0 ±0.01; assert `floors` list has 3 entries in floor order
  - [ ] 7.2: Test `FLOOR_PLATES_NOT_FOUND`: mock `list_layers()` returns no matching layers; assert error response
  - [ ] 7.3: Test session storage: after `area_compute_builtup`, `ctx.get_state("buildup_area_sqm")` == 560.0
  - [ ] 7.4: `tests/unit/modules/area/test_area_compute_carpet.py` — with 560.0 buildup and factor 0.85, assert carpet total = 476.0 ±0.01
  - [ ] 7.5: Test `wall_thickness_factor = 0.0` returns `INVALID_PARAMS` (or `INVALID_WALL_FACTOR`); factor > 1.0 also returns error
  - [ ] 7.6: Test `area_sqm_str` format: assert `format_area(560.0) == "560.0000"` (exactly 4dp)

## Dev Notes

### Critical Architecture Constraints

1. **Shapely for ALL area computation — no exceptions** — `compute_buildup_area` sums `polygon.area` values from Shapely polygons. It does NOT sum vertex-based manual calculations. Each floor plate entity becomes a Shapely polygon via `_entities_to_polygon`; its `.area` is used. Comment: `# shapely polygon.area — NFR11 compliance`.
2. **Floor ordering** — per-floor breakdown must be in a consistent, deterministic order. Use natural sort on layer names to ensure `GF` → `1` → `2` → ... order. This is required for NFR13 (same drawing = identical results). If layer names don't have a numeric suffix, sort alphabetically and document the sort order in a comment.
3. **`wall_thickness_factor` default is 0.85** — this is the PreDCR default (85% of built-up after deducting walls/ducts). It is a configurable parameter, NOT derived from the DCR config file (DCR config covers FSI/setbacks, not wall thickness factor). It is passed directly by the AI client.
4. **Sum of floats, not strings** — always sum `float` values. Never parse formatted strings back to floats. The `total_sqm` must be `sum(f["area_sqm"] for f in floors)`, not `sum(float(f["area_sqm_str"]) for f in floors)`.
5. **Session state key names are a contract** — `"buildup_area_sqm"` and `"carpet_area_sqm"` are consumed by `area_compute_fsi` and `area_compute_all` in Story 8-4. Do NOT rename these keys without updating Story 8-4.
6. **Multiple entities per floor layer** — a floor plate layer may have multiple closed polylines (e.g., split floor plate, courtyard excluded). Sum all polygon areas on the layer: `total_layer_area = sum(self._entities_to_polygon(e["vertices"]).area for e in entities_on_layer)`.

### Module/Component Notes

**Floor layer naming convention — MUST verify against PreDCR registry:**

The layer naming for floor plates is established in Epic 4 (Story 4-1: PreDCR Layer Specification Catalog). Before hardcoding any pattern, check `src/lcs_cad_mcp/modules/predcr/layer_registry.py` for the canonical names. Expected pattern is `FLOOR_PLATE_GF`, `FLOOR_PLATE_1`, `FLOOR_PLATE_2`, etc. but the exact convention is authoritative from the registry.

```python
# In service.py — check and use PreDCR registry constant
# from src/lcs_cad_mcp/modules/predcr/layer_registry import FLOOR_PLATE_LAYER_PREFIX
FLOOR_PLATE_LAYER_PREFIX = "FLOOR_PLATE_"  # fallback if registry not yet available — update when Story 4-1 is done
```

**`compute_buildup_area` multi-entity per layer example:**

```python
floor_polygons = []
for entity in entities_on_layer:
    try:
        polygon = self._entities_to_polygon(entity["vertices"])
        floor_polygons.append(polygon)
    except AreaComputationError as e:
        # Log but continue — one invalid entity doesn't block the whole floor
        # (design decision: partial floor plate computation is better than failure)
        # TODO: surface as a warning in the response
        pass
layer_area = sum(p.area for p in floor_polygons)  # shapely polygon.area — NFR11 compliance
```

**`area_compute_carpet` tool — parameter in tool signature:**

The `wall_thickness_factor` parameter appears in the MCP tool signature, making it AI-client-configurable without code changes. The AI client can call `area_compute_carpet(wall_thickness_factor=0.80)` for stricter deduction or use the default 0.85.

**Session state keys summary for this story:**

| Key | Type | Set by |
|-----|------|--------|
| `"buildup_area_sqm"` | `float` | `area_compute_builtup` |
| `"carpet_area_sqm"` | `float` | `area_compute_carpet` |

These join `"plot_area_sqm"` (from Story 8-2) to form the complete area state consumed by Story 8-4.

### Project Structure Notes

Files to create or modify in this story:

```
src/lcs_cad_mcp/
├── errors.py                              # Update: FLOOR_PLATES_NOT_FOUND, INVALID_WALL_FACTOR
└── modules/area/
    ├── __init__.py                        # Update: register area_compute_builtup, area_compute_carpet
    ├── tools.py                           # Update: add area_compute_builtup, area_compute_carpet handlers
    ├── service.py                         # Update: add _get_floor_plate_layers, compute_buildup_area,
    │                                      #         compute_carpet_area methods
    └── schemas.py                         # Update: add FloorAreaBreakdown, BuiltupAreaResult, CarpetAreaResult

tests/unit/modules/area/
├── test_area_compute_builtup.py           # New
└── test_area_compute_carpet.py            # New
```

### Dependencies

- **Story 8-2** — `AreaService.compute_plot_area`, `_entities_to_polygon`, `format_area`, and `AreaComputationError` must exist. The `area_compute_plot` session state pattern is the model for this story.
- **Story 4-1** (PreDCR layer specification) — floor plate layer naming convention is canonical here. Check `modules/predcr/layer_registry.py` before implementing `_get_floor_plate_layers`.
- **Story 5-6** (`entity_query`) — `session.backend.get_entities_on_layer(layer)` must return entities with `"vertices"` lists. Verify the dict schema matches Story 8-2's assumption.
- **Story 2-1** — `session.backend.list_layers() -> list[str]` backend method must exist on the `CADBackend` abstract interface.

### References

- Architecture area computation: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Area Computation Engine"]
- EPIC context (wall_thickness_factor 0.85 default): [Story prompt mandatory context — Epic 8, Story 8-3]
- NFR11 (area accuracy ±0.01 sqm): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- NFR13 (determinism — same drawing = same result): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- FR22 (area computation): [Source: `_bmad-output/planning-artifacts/architecture.md` — FR section]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 8, Story 8-3]

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
- `src/lcs_cad_mcp/errors.py` (updated)
- `tests/unit/modules/area/test_area_compute_builtup.py`
- `tests/unit/modules/area/test_area_compute_carpet.py`
