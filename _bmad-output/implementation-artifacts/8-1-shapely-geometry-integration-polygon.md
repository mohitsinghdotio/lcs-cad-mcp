# Story 8.1: Shapely Geometry Integration and Polygon Extraction

Status: ready-for-dev

## Story

As a **developer**,
I want **a geometry layer that extracts closed polylines from the CAD drawing as Shapely polygons**,
so that **all area computations use accurate, floating-point-safe polygon operations rather than raw manual math** (NFR11, NFR12).

## Acceptance Criteria

1. **AC1:** `AreaService._entities_to_polygon(entities: list[dict]) -> shapely.Polygon` converts a list of polyline vertex dicts (each with `x: float`, `y: float`) to a valid `shapely.geometry.Polygon`.
2. **AC2:** Returns a structured error `POLYGON_NOT_CLOSED` if the vertex sequence does not form a closed polygon (first vertex != last vertex within tolerance).
3. **AC3:** `AreaService` extracts polygons from entities supplied by either the ezdxf or COM backend (backend-agnostic: input is a list of vertex dicts, not a backend-specific object).
4. **AC4:** Unit tests in `tests/unit/modules/area/test_geometry.py` verify area accuracy to ±0.01 sqm against known test polygons (NFR11): a 10×10 square (area=100.0), a 3-4-5 right triangle (area=6.0), and a regular hexagon with known exact area.
5. **AC5:** Self-intersecting polygons are detected and returned as a `POLYGON_SELF_INTERSECTING` error (Shapely `is_valid` check).
6. **AC6:** `AreaService` is initialized as a stateless service in `modules/area/service.py`; polygon helper is a private method (`_entities_to_polygon`), not a public MCP tool.
7. **AC7:** `modules/area/__init__.py` exports a `register(mcp)` function; this story registers no MCP tools — only the service infrastructure is built here.

## Tasks / Subtasks

- [ ] Task 1: Implement `AreaService` class skeleton in `modules/area/service.py` (AC: 3, 6)
  - [ ] 1.1: Create `class AreaService` with no `__init__` arguments (stateless); add docstring: `"""Area computation service. Uses Shapely for ALL polygon operations — never raw math."""`
  - [ ] 1.2: Add class-level constant `CLOSURE_TOLERANCE: float = 1e-6` for vertex matching
  - [ ] 1.3: Import `from shapely.geometry import Polygon` and `from shapely.validation import make_valid` at module level; add comment: `# shapely: all polygon operations go through Shapely — never raw math (NFR11)`

- [ ] Task 2: Implement `_entities_to_polygon` private method (AC: 1, 2, 5)
  - [ ] 2.1: Method signature: `def _entities_to_polygon(self, entities: list[dict]) -> Polygon` where each dict has at minimum `"x": float, "y": float` keys
  - [ ] 2.2: Extract vertex tuples: `coords = [(e["x"], e["y"]) for e in entities]`
  - [ ] 2.3: Check closure: if `len(coords) < 3`, raise `AreaComputationError(code="POLYGON_TOO_FEW_VERTICES", message="Polygon requires at least 3 vertices")`
  - [ ] 2.4: Check closure tolerance: compute distance between first and last vertex; if `> self.CLOSURE_TOLERANCE` and first != last, raise `AreaComputationError(code="POLYGON_NOT_CLOSED", message="Polyline is not closed — first and last vertex do not match within tolerance")`
  - [ ] 2.5: Remove duplicate closing vertex if present (Shapely does not require explicit closure in constructor): `if coords[0] == coords[-1]: coords = coords[:-1]`
  - [ ] 2.6: Construct `polygon = Polygon(coords)`
  - [ ] 2.7: Check validity: `if not polygon.is_valid`, raise `AreaComputationError(code="POLYGON_SELF_INTERSECTING", message=f"Polygon is self-intersecting or invalid: {shapely.validation.explain_validity(polygon)}")`
  - [ ] 2.8: Return the valid `Polygon` object

- [ ] Task 3: Create `AreaComputationError` exception class in `modules/area/service.py` (AC: 2, 5)
  - [ ] 3.1: Define `class AreaComputationError(Exception)` with `__init__(self, code: str, message: str)` and store both as attributes
  - [ ] 3.2: This exception is used internally within `AreaService`; tool handlers in `tools.py` catch it and convert to structured MCP error responses
  - [ ] 3.3: Add `ErrorCode` entries in `errors.py`: `POLYGON_NOT_CLOSED`, `POLYGON_SELF_INTERSECTING`, `POLYGON_TOO_FEW_VERTICES`, `PLOT_BOUNDARY_NOT_FOUND`

- [ ] Task 4: Create `modules/area/schemas.py` — input/output Pydantic models (AC: 1)
  - [ ] 4.1: Create `VertexInput(BaseModel)`: `x: float`, `y: float`
  - [ ] 4.2: Create `AreaResult(BaseModel)`: `area_sqm: float`, `area_sqm_4dp: str` (area formatted to 4 decimal places as string)
  - [ ] 4.3: Create helper function `format_area(value: float) -> str` returning `f"{value:.4f}"` — used consistently in all area responses (NFR result format: 4dp)

- [ ] Task 5: Create `modules/area/__init__.py` — module registration stub (AC: 7)
  - [ ] 5.1: Define `register(mcp: FastMCP) -> None` function — currently empty (no tools yet); add comment: `# Tools registered in Stories 8-2, 8-3, 8-4`
  - [ ] 5.2: Import `AreaService` and re-export for convenience

- [ ] Task 6: Write unit tests in `tests/unit/modules/area/test_geometry.py` (AC: 4, 2, 5)
  - [ ] 6.1: Test `_entities_to_polygon` with a 10m × 10m square: vertices `[(0,0),(10,0),(10,10),(0,10),(0,0)]`; assert `polygon.area == pytest.approx(100.0, abs=0.01)` (NFR11)
  - [ ] 6.2: Test with a 3-4-5 right triangle: vertices `[(0,0),(4,0),(0,3),(0,0)]`; assert `polygon.area == pytest.approx(6.0, abs=0.01)` (NFR11)
  - [ ] 6.3: Test with a regular hexagon with known area (compute analytically): use `side=5`, `expected_area = 3*sqrt(3)/2 * 25 ≈ 64.952`; assert within 0.01
  - [ ] 6.4: Test `POLYGON_NOT_CLOSED` error: provide open polyline (first != last vertex, gap > tolerance); assert `AreaComputationError` raised with `code == "POLYGON_NOT_CLOSED"`
  - [ ] 6.5: Test `POLYGON_TOO_FEW_VERTICES`: provide only 2 vertices; assert error raised
  - [ ] 6.6: Test self-intersecting polygon (bowtie shape: `[(0,0),(1,1),(1,0),(0,1),(0,0)]`); assert `POLYGON_SELF_INTERSECTING` error

- [ ] Task 7: Verify Shapely and scipy are properly installed and importable (AC: 3)
  - [ ] 7.1: Add a smoke test in `tests/unit/modules/area/test_geometry.py`: `import shapely; assert shapely.__version__` passes — ensures dependency is available
  - [ ] 7.2: Confirm `shapely` and `scipy` are in `pyproject.toml` dependencies (should be from Story 1-1); if missing, add via `uv add shapely scipy`
  - [ ] 7.3: Add `from shapely.validation import explain_validity` import to `service.py` and confirm no import errors

## Dev Notes

### Critical Architecture Constraints

1. **Shapely for ALL polygon operations — never raw math** — this is a hard architectural rule. Do NOT compute polygon areas with the shoelace formula, do NOT compute intersections manually. Every geometric operation must go through `shapely.geometry.Polygon`. Add comment `# shapely: all polygon operations go through Shapely — never raw math (NFR11)` on every Shapely import.
2. **`AreaService` is stateless** — it has no `__init__` parameters and holds no instance variables. All inputs come in via method arguments. State (computed areas) lives in the tool handler or session, not in the service.
3. **Input is backend-agnostic vertex dicts** — `_entities_to_polygon` receives `list[dict]` with `"x"` and `"y"` keys. It does NOT accept ezdxf entity objects or COM `AcadPolyline` references. The entity query tools (Epic 5) return vertex dicts; those are the inputs here. This decouples area computation from the CAD backend (NFR requirement).
4. **Area precision: 4 decimal places in results, full float precision in computation** — `polygon.area` returns a Python `float` (full 64-bit precision). Format to 4dp only at the response boundary using `format_area()`. Never truncate mid-computation.
5. **Closure detection uses Euclidean distance, not exact equality** — floating-point vertex coordinates from DXF files may have tiny rounding differences. Use `math.sqrt((x1-x2)**2 + (y1-y2)**2) < CLOSURE_TOLERANCE` where `CLOSURE_TOLERANCE = 1e-6` (meters). This matches the closure verification engine from Epic 6.
6. **`POLYGON_NOT_CLOSED` vs closure verification (Story 6-1)** — Story 6-1 checks closure at the entity level in the CAD drawing. Story 8-1 checks closure at the geometry level when converting to Shapely. Both checks are needed: 6-1 is a pre-flight check on the drawing structure; 8-1 is a safety net during computation.

### Module/Component Notes

**`AreaService._entities_to_polygon` full implementation reference:**

```python
import math
from shapely.geometry import Polygon
from shapely.validation import explain_validity  # shapely: all polygon ops through Shapely (NFR11)


CLOSURE_TOLERANCE: float = 1e-6  # meters


class AreaComputationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class AreaService:
    """Area computation service. Uses Shapely for ALL polygon operations — never raw math."""

    CLOSURE_TOLERANCE: float = CLOSURE_TOLERANCE

    def _entities_to_polygon(self, entities: list[dict]) -> Polygon:
        """Convert a list of vertex dicts ({x, y}) to a validated Shapely Polygon.

        Raises AreaComputationError if:
        - fewer than 3 vertices
        - polyline is not closed within CLOSURE_TOLERANCE
        - resulting polygon is self-intersecting or invalid
        """
        coords = [(float(e["x"]), float(e["y"])) for e in entities]

        if len(coords) < 3:
            raise AreaComputationError(
                code="POLYGON_TOO_FEW_VERTICES",
                message=f"Polygon requires at least 3 vertices, got {len(coords)}"
            )

        # Check closure: first vertex must equal last vertex within tolerance
        dx = coords[0][0] - coords[-1][0]
        dy = coords[0][1] - coords[-1][1]
        gap = math.sqrt(dx * dx + dy * dy)
        if gap > self.CLOSURE_TOLERANCE:
            raise AreaComputationError(
                code="POLYGON_NOT_CLOSED",
                message=f"Polyline is not closed — gap between first and last vertex: {gap:.6f}m"
            )

        # Remove duplicate closing vertex (Shapely polygon does not require it)
        if coords[0] == coords[-1]:
            coords = coords[:-1]

        # Construct Shapely polygon — ALL area ops go through Shapely (NFR11)
        polygon = Polygon(coords)

        # Validate polygon — detect self-intersections and degenerate geometry
        if not polygon.is_valid:
            reason = explain_validity(polygon)
            raise AreaComputationError(
                code="POLYGON_SELF_INTERSECTING",
                message=f"Polygon is invalid: {reason}"
            )

        return polygon
```

**`format_area` helper:**

```python
def format_area(value: float) -> str:
    """Format area to 4 decimal places for MCP response output."""
    return f"{value:.4f}"
```

### Project Structure Notes

Files to create or modify in this story:

```
src/lcs_cad_mcp/
├── errors.py                              # Update: add POLYGON_NOT_CLOSED, POLYGON_SELF_INTERSECTING,
│                                          #         POLYGON_TOO_FEW_VERTICES, PLOT_BOUNDARY_NOT_FOUND
└── modules/area/
    ├── __init__.py                        # Implement: register(mcp) stub
    ├── service.py                         # Implement: AreaService, AreaComputationError, format_area
    └── schemas.py                         # Implement: VertexInput, AreaResult

tests/unit/modules/area/
├── __init__.py                            # Create if not exists
└── test_geometry.py                       # New: polygon extraction and area accuracy tests
```

**Note:** `modules/area/tools.py` is NOT modified in this story. Tools are added in Stories 8-2, 8-3, 8-4. This story delivers only the service layer foundation.

### Dependencies

- **Story 6-1** (closure verification engine) — the architecture doc notes that Story 8-1 depends on Story 6-1 because closure verification ensures polygons are valid before area computation. However, the technical dependency is only that `PLOT_BOUNDARY_NOT_FOUND` and related patterns are established. The Shapely integration itself has no runtime dependency on the verification engine code.
- **Story 5-1** (entity data model) — entity query results from Story 5-6 (`entity_query`) provide the vertex dicts that `_entities_to_polygon` consumes. The dict format `{"x": float, "y": float}` must match what entity tools return.
- **Story 2-1** (backend abstraction) — `AreaService` is backend-agnostic by design. It receives pre-extracted vertex data, not backend objects. No direct dependency on backend code.
- `shapely` and `scipy` must be in `pyproject.toml` (established in Story 1-1).

### References

- Architecture area computation section: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Area Computation Engine"]
- NFR11 (area accuracy ±0.01 sqm): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- NFR12 (FSI/coverage 3dp accuracy): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- Shapely docs — Polygon: [https://shapely.readthedocs.io/en/stable/manual.html#polygons]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 8, Story 8-1]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/area/__init__.py`
- `src/lcs_cad_mcp/modules/area/service.py`
- `src/lcs_cad_mcp/modules/area/schemas.py`
- `src/lcs_cad_mcp/errors.py` (updated)
- `tests/unit/modules/area/__init__.py`
- `tests/unit/modules/area/test_geometry.py`
