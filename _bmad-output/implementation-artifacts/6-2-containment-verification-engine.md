# Story 6.2: Containment Verification Engine

Status: ready-for-dev

## Story

As a **developer**,
I want **a containment verification engine that checks parent/child spatial relationships using Shapely**,
so that **entities on child layers are confirmed to lie within their parent boundaries before scrutiny (FR14)**.

## Acceptance Criteria

1. **AC1:** `VerificationService.check_containment()` checks all entity/layer hierarchy relationships defined in the PreDCR layer registry — for each child entity, verifies it lies spatially within its designated parent boundary polygon using Shapely.
2. **AC2:** Returns `list[VerificationFailure]` where each failure carries `entity_id` (child handle), `failure_type="CONTAINMENT"`, `layer` (child layer name), `description` (which parent boundary was violated and by how much), and `suggested_correction` (actionable instruction).
3. **AC3:** Uses `shapely.geometry.Polygon.contains()` and/or `shapely.geometry.Polygon.within()` for containment checks — direct coordinate math is NOT acceptable for polygon containment.
4. **AC4:** Handles multi-polygon parent boundaries: if the parent layer has multiple closed polylines, the child must be within at least one of them (union semantics).
5. **AC5:** Zero false positives on correctly contained entities (NFR14) — a child entity fully within its parent boundary returns no failure.
6. **AC6:** The `verify_containment` MCP tool wraps `check_containment()`, follows the 6-step handler pattern (session → validate → NO snapshot → service call → event_log → return), and returns `passed: bool` and `failures: list`.

## Tasks / Subtasks

- [ ] Task 1: Extend `schemas.py` with containment result types (AC: 2)
  - [ ] 1.1: Add `ContainmentCheckResult` Pydantic model with fields: `passed: bool`, `failures: list[VerificationFailure]`, `checked_pair_count: int`
  - [ ] 1.2: Confirm `VerificationFailure` from Story 6-1 `schemas.py` supports `failure_type="CONTAINMENT"` — no new model needed for the failure itself, only the result wrapper
  - [ ] 1.3: Export `ContainmentCheckResult` from `schemas.py`

- [ ] Task 2: Implement geometry extraction helper in `service.py` (AC: 3, 4)
  - [ ] 2.1: Implement private method `_entity_to_polygon(entity) -> shapely.geometry.Polygon | None`: extract entity vertices list, construct `shapely.geometry.Polygon(vertices)`; return `None` if entity has fewer than 3 vertices or is not closed
  - [ ] 2.2: Implement private method `_get_parent_polygons(parent_layer_name: str) -> list[shapely.geometry.Polygon]`: call `EntityService.list_entities(layer=parent_layer_name, entity_type="POLYLINE")`, convert each to a Shapely polygon via `_entity_to_polygon`, filter `None` values
  - [ ] 2.3: If a parent layer has multiple polygons, compute `shapely.ops.unary_union(polygons)` to produce a single union geometry for containment testing (covers AC4 multi-polygon requirement)
  - [ ] 2.4: Add import guard: `from shapely.geometry import Polygon` and `from shapely.ops import unary_union` — raise `ImportError` with clear message if shapely is not installed

- [ ] Task 3: Implement `VerificationService.check_containment()` in `service.py` (AC: 1, 2, 3, 4, 5)
  - [ ] 3.1: Retrieve the PreDCR layer hierarchy from `LayerService` — specifically the parent-child layer relationships defined in `layer_registry.py`; store as `list[tuple[child_layer, parent_layer]]`
  - [ ] 3.2: For each `(child_layer, parent_layer)` pair: fetch all child entities on `child_layer`, fetch parent polygons for `parent_layer` using `_get_parent_polygons()`
  - [ ] 3.3: If parent layer has no polygons (parent boundary not drawn), record a `VerificationFailure` with `description="Parent boundary not found on layer {parent_layer}"` — this is a containment failure by definition
  - [ ] 3.4: For each child entity: convert to Shapely polygon via `_entity_to_polygon()`; if child is a polygon, test `parent_union.contains(child_polygon)`; if child is a point or line, test `parent_union.contains(child_geometry)`
  - [ ] 3.5: If `not parent_union.contains(child_geometry)`, append `VerificationFailure(entity_id=child.handle, failure_type="CONTAINMENT", layer=child_layer, description=f"Entity on '{child_layer}' lies outside parent boundary on '{parent_layer}'", suggested_correction=f"Move or resize entity {child.handle} to lie within {parent_layer} boundary")` to failures
  - [ ] 3.6: Return complete `failures` list

- [ ] Task 4: Implement `verify_containment` MCP tool handler in `tools.py` (AC: 6)
  - [ ] 4.1: Define `@mcp.tool()` decorated async function `verify_containment(ctx: Context) -> dict`
  - [ ] 4.2: Step 1 — retrieve session: `session = ctx.get_state("drawing_session")`; if missing, return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 4.3: Step 2 — validate: confirm active session has an open drawing; no additional params to validate for this tool
  - [ ] 4.4: Step 3 — NO snapshot (read-only tool)
  - [ ] 4.5: Step 4 — call `VerificationService(session).check_containment()`; collect `failures`
  - [ ] 4.6: Step 5 — append to event log: `{"tool": "verify_containment", "failure_count": len(failures)}`
  - [ ] 4.7: Step 6 — return `{"success": True, "data": {"passed": len(failures) == 0, "failures": [f.model_dump() for f in failures]}}`

- [ ] Task 5: Register `verify_containment` tool and update `__init__.py` (AC: 6)
  - [ ] 5.1: Add `verify_containment` to the `register(mcp)` call chain in `tools.py`
  - [ ] 5.2: Confirm `modules/verification/__init__.py` `register()` function picks up both `verify_closure` and `verify_containment`

- [ ] Task 6: Write unit tests for containment verification (AC: 5, 6)
  - [ ] 6.1: Create `tests/unit/modules/verification/test_containment.py`
  - [ ] 6.2: Build `MockCADBackend` fixture with: a plot boundary polygon (outer), a building footprint polygon fully inside plot (pass case), a building footprint polygon partially outside plot (fail case), a multi-polygon parent layer (two non-overlapping zones)
  - [ ] 6.3: Test `check_containment()` passes for fully-contained child, fails for out-of-bounds child
  - [ ] 6.4: Test multi-polygon parent: child within one of the parent polygons passes (union semantics)
  - [ ] 6.5: Test missing parent boundary: `check_containment()` returns a failure describing the missing parent
  - [ ] 6.6: Write Hypothesis property-based test: generate random child polygon that is a strict subset of a parent polygon → `check_containment()` always returns zero failures (NFR14 property)

- [ ] Task 7: Verify Shapely version compatibility and error handling (AC: 3)
  - [ ] 7.1: Confirm `shapely>=2.0` is used (Shapely 2.x API differs from 1.x — `shapely.geometry.Polygon` constructor is identical but `ops` module location changed); add inline comment in imports noting the version
  - [ ] 7.2: Handle degenerate geometries: if `_entity_to_polygon()` returns `None` for a child entity, skip containment check for that entity and log a warning in event_log (do NOT treat it as a containment failure — that's a closure failure caught by Story 6-1)
  - [ ] 7.3: Add try/except around Shapely operations to catch `TopologicalError` — return a `VerificationFailure` with `description="Geometry error during containment check: {error}"` rather than crashing

## Dev Notes

### Critical Architecture Constraints

1. **READ-ONLY tool — no snapshot.** `verify_containment` never mutates drawing state. The 6-step handler pattern Step 3 (snapshot) is skipped entirely.
2. **VerificationService calls EntityService and LayerService DIRECTLY** — never call MCP tools (`entity_list_entities`, `layer_get_hierarchy`) from within the service. Instantiate `EntityService(session)` and `LayerService(session)` as plain Python objects.
3. **Shapely is the required geometry library** — do not reimplement polygon containment with coordinate math. The `contains()` predicate handles all edge cases including holes, degeneracy, and floating-point precision.
4. **Parent-child layer hierarchy is defined in `layer_registry.py`** (Epic 3) — `VerificationService` must read this registry to know which layers are children of which parents. Do NOT hardcode layer names.

### Module/Component Notes

**Layer hierarchy lookup pattern:**

```python
# In VerificationService.check_containment()
from lcs_cad_mcp.modules.predcr.layer_registry import LAYER_REGISTRY

# LAYER_REGISTRY is expected to have a structure like:
# {layer_name: LayerDefinition(parent_layer=str | None, ...)}
hierarchy_pairs = [
    (layer_name, defn.parent_layer)
    for layer_name, defn in LAYER_REGISTRY.items()
    if defn.parent_layer is not None
]
```

**Shapely containment check pattern:**

```python
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union

def _get_parent_union(self, parent_layer: str):
    parent_entities = self._entity_svc.list_entities(layer=parent_layer, entity_type="POLYLINE")
    polygons = [self._entity_to_polygon(e) for e in parent_entities]
    polygons = [p for p in polygons if p is not None]
    if not polygons:
        return None
    return unary_union(polygons)

def check_containment(self) -> list[VerificationFailure]:
    failures = []
    for child_layer, parent_layer in self._get_hierarchy_pairs():
        parent_union = self._get_parent_union(parent_layer)
        if parent_union is None:
            failures.append(VerificationFailure(
                entity_id="N/A",
                failure_type="CONTAINMENT",
                layer=child_layer,
                description=f"Parent boundary not found on layer '{parent_layer}'",
                suggested_correction=f"Draw a closed polyline on layer '{parent_layer}' to define the boundary",
            ))
            continue
        child_entities = self._entity_svc.list_entities(layer=child_layer)
        for entity in child_entities:
            child_geom = self._entity_to_polygon(entity)
            if child_geom is None:
                continue  # not a polygon — skip (closure check handles this)
            if not parent_union.contains(child_geom):
                failures.append(VerificationFailure(
                    entity_id=entity.handle,
                    failure_type="CONTAINMENT",
                    layer=child_layer,
                    description=f"Entity on '{child_layer}' extends outside '{parent_layer}' boundary",
                    suggested_correction=f"Resize or relocate entity {entity.handle} to fit within {parent_layer}",
                ))
    return failures
```

**ContainmentCheckResult schema:**

```python
class ContainmentCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    failures: list[VerificationFailure]
    checked_pair_count: int        # number of parent-child layer pairs evaluated
```

### Project Structure Notes

Files modified or created for this story:

```
src/lcs_cad_mcp/modules/verification/
├── __init__.py       # updated: register() includes verify_containment
├── schemas.py        # updated: add ContainmentCheckResult
├── service.py        # updated: add check_containment(), _entity_to_polygon(), _get_parent_union()
└── tools.py          # updated: add verify_containment handler

tests/unit/modules/verification/
├── __init__.py       # already exists from Story 6-1
└── test_containment.py   # NEW
```

### Dependencies

- **Story 6-1** (Closure Verification — `VerificationFailure` model must already exist in `schemas.py`; `VerificationService` class must already exist in `service.py`)
- **Story 5-6** (Entity listing — `EntityService.list_entities(layer=..., entity_type=...)` must support layer-filtered queries)
- **Story 3-4** (Layer naming and hierarchy — `LayerService` and `layer_registry.py` must define parent-child layer relationships)
- **Story 4-1** (PreDCR layer catalog — `layer_registry.py` must be populated with actual PreDCR layer definitions including `parent_layer` field)
- **Story 8-1** (Shapely geometry integration) — NOTE: Story 8-1 has a declared dependency on Story 6-1, but Story 6-2 needs Shapely independently. Shapely is already declared in `pyproject.toml` (Story 1-1). This story should use Shapely directly without waiting for Story 8-1's `GeometryEngine` abstraction.
- **Story 2-1** (CAD Backend — `DrawingSession` accessible via `ctx.get_state()`)

### References

- FR14: Containment check requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 6, Story 6-2]
- NFR14: Zero false positives — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 6 NFR coverage]
- Shapely containment docs: `polygon.contains(other)` returns True if no point of `other` is on the exterior of polygon — [Shapely 2.x documentation]
- Layer hierarchy design — [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Layer Registry"]
- 6-step tool handler pattern — [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]

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
- `tests/unit/modules/verification/test_containment.py`
