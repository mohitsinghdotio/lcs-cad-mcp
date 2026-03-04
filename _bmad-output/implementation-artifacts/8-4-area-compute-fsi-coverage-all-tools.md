# Story 8.4: `area_compute_fsi`, `area_compute_coverage`, and `area_compute_all` MCP Tools

Status: ready-for-dev

## Story

As an **AI client**,
I want **to compute FSI, ground coverage, and a complete area report in a single call**,
so that **the scrutiny engine has all required area metrics as a cohesive, reproducible data set** (FR22, NFR13).

## Acceptance Criteria

1. **AC1:** `area_compute_fsi()` = total built-up area / plot area; accurate to 3 decimal places (NFR12); returns `PLOT_AREA_NOT_COMPUTED` error if plot area has not been computed in this session.
2. **AC2:** `area_compute_coverage()` = ground floor footprint area / plot area; accurate to 3 decimal places (NFR12); returns `GROUND_FLOOR_NOT_FOUND` error if no ground floor entity exists.
3. **AC3:** `area_compute_all()` runs all area computations in dependency order (plot → built-up → carpet → FSI → coverage) and returns a structured `AreaReport` with all values.
4. **AC4:** `area_compute_all()` completes within 10 seconds for a typical multi-floor drawing (NFR4).
5. **AC5:** All area computations are reproducible — same drawing + same config always yields identical results; `area_compute_all()` stores a composite hash in session state (NFR13).
6. **AC6:** `AreaReport` returned by `area_compute_all()` includes: `plot_area_sqm`, `buildup_area_sqm`, `carpet_area_sqm`, `fsi`, `ground_coverage`, `floor_breakdown`, `wall_thickness_factor`, `computed_at` (ISO timestamp), `drawing_hash` (from session).
7. **AC7:** FSI and coverage values are formatted to exactly 3 decimal places in the response string fields (NFR12); underlying floats retain full precision.
8. **AC8:** All three tools follow the 6-step pattern: (1) session, (2) validate, (3) no snapshot, (4) service method, (5) event_log, (6) return.

## Tasks / Subtasks

- [ ] Task 1: Implement `AreaService.compute_fsi` method in `modules/area/service.py` (AC: 1, 7)
  - [ ] 1.1: Method signature: `def compute_fsi(self, buildup_area_sqm: float, plot_area_sqm: float) -> float`
  - [ ] 1.2: Guard divide-by-zero: if `plot_area_sqm <= 0.0`, raise `AreaComputationError(code="INVALID_PLOT_AREA", message="Plot area must be > 0 to compute FSI")`
  - [ ] 1.3: Return `buildup_area_sqm / plot_area_sqm` as raw float (full precision); formatting to 3dp happens at response boundary only
  - [ ] 1.4: Add inline comment: `# FSI = total_buildup / plot_area — NFR12: accurate to 3dp`

- [ ] Task 2: Implement `AreaService.compute_coverage` method in `modules/area/service.py` (AC: 2, 7)
  - [ ] 2.1: Method signature: `def compute_coverage(self, ground_floor_area_sqm: float, plot_area_sqm: float) -> float`
  - [ ] 2.2: Guard divide-by-zero: if `plot_area_sqm <= 0.0`, raise `AreaComputationError(code="INVALID_PLOT_AREA", ...)`
  - [ ] 2.3: Return `ground_floor_area_sqm / plot_area_sqm` as raw float
  - [ ] 2.4: Add inline comment: `# Coverage = ground_floor_area / plot_area — NFR12: accurate to 3dp`

- [ ] Task 3: Implement `AreaService.compute_all` method in `modules/area/service.py` (AC: 3, 5, 6)
  - [ ] 3.1: Method signature: `def compute_all(self, session, wall_thickness_factor: float = 0.85) -> dict`
  - [ ] 3.2: Call `self.compute_plot_area(session)` → `plot_area_sqm: float`
  - [ ] 3.3: Call `self.compute_buildup_area(session)` → `buildup_result: dict` (with floors breakdown and `total_sqm`)
  - [ ] 3.4: Derive `ground_floor_area_sqm` from `buildup_result["floors"][0]["area_sqm"]` — the ground floor is the first floor in the sorted list; if `floors` is empty, raise `GROUND_FLOOR_NOT_FOUND`
  - [ ] 3.5: Call `self.compute_carpet_area(session, wall_thickness_factor)` → `carpet_result: dict`
  - [ ] 3.6: Call `self.compute_fsi(buildup_result["total_sqm"], plot_area_sqm)` → `fsi: float`
  - [ ] 3.7: Call `self.compute_coverage(ground_floor_area_sqm, plot_area_sqm)` → `coverage: float`
  - [ ] 3.8: Build and return complete area report dict (matches `AreaReport` schema in AC6)

- [ ] Task 4: Implement `area_compute_fsi` tool handler in `modules/area/tools.py` (AC: 1, 7, 8)
  - [ ] 4.1: Tool signature: `async def area_compute_fsi(ctx: Context) -> dict`
  - [ ] 4.2: Step 1: get session; return `SESSION_NOT_STARTED` if missing
  - [ ] 4.3: Step 2: retrieve `plot_area_sqm = ctx.get_state("plot_area_sqm")`; if `None`, return `PLOT_AREA_NOT_COMPUTED` error with `suggested_action: "Call area_compute_plot() first"`; retrieve `buildup_area_sqm = ctx.get_state("buildup_area_sqm")`; if `None`, return `BUILDUP_AREA_NOT_COMPUTED` error
  - [ ] 4.4: Step 3: skip snapshot
  - [ ] 4.5: Step 4: call `AreaService().compute_fsi(buildup_area_sqm, plot_area_sqm)`; catch `AreaComputationError`
  - [ ] 4.6: Step 5: event log `{"event": "area_fsi_computed", "fsi": fsi_float}`
  - [ ] 4.7: Step 6: store `ctx.set_state("fsi", fsi_float)`; return `{"success": true, "data": {"fsi": fsi_float, "fsi_str": format_ratio(fsi_float), "buildup_area_sqm": buildup_area_sqm, "plot_area_sqm": plot_area_sqm}}`

- [ ] Task 5: Implement `area_compute_coverage` tool handler in `modules/area/tools.py` (AC: 2, 7, 8)
  - [ ] 5.1: Tool signature: `async def area_compute_coverage(ctx: Context) -> dict`
  - [ ] 5.2: Step 2: retrieve `plot_area_sqm` and `buildup_area_sqm` from session; also retrieve `floors` breakdown — if `buildup_area_sqm` is `None`, return `BUILDUP_AREA_NOT_COMPUTED`; extract ground floor from session or re-compute
  - [ ] 5.3: Design decision: either store `ground_floor_area_sqm` in session during `area_compute_builtup` (preferred — avoids re-querying backend), or re-call `AreaService().compute_buildup_area(session)["floors"][0]`; document the chosen approach in code comment
  - [ ] 5.4: Step 4: call `AreaService().compute_coverage(ground_floor_area_sqm, plot_area_sqm)`
  - [ ] 5.5: Step 5: event log `{"event": "area_coverage_computed", "coverage": coverage_float}`
  - [ ] 5.6: Step 6: store `ctx.set_state("ground_coverage", coverage_float)`; return `{"success": true, "data": {"ground_coverage": coverage_float, "ground_coverage_str": format_ratio(coverage_float), "ground_floor_area_sqm": ground_floor_area_sqm, "plot_area_sqm": plot_area_sqm}}`

- [ ] Task 6: Implement `area_compute_all` tool handler in `modules/area/tools.py` (AC: 3, 4, 5, 6, 8)
  - [ ] 6.1: Tool signature: `async def area_compute_all(ctx: Context, wall_thickness_factor: float = 0.85) -> dict`
  - [ ] 6.2: Step 1: get session; return `SESSION_NOT_STARTED` if missing
  - [ ] 6.3: Step 2: validate `0.0 < wall_thickness_factor <= 1.0`
  - [ ] 6.4: Step 3: skip snapshot
  - [ ] 6.5: Step 4: call `AreaService().compute_all(session, wall_thickness_factor)`; catch all `AreaComputationError` variants with correct codes
  - [ ] 6.6: Step 5: event log with all computed values summary
  - [ ] 6.7: Step 6: store ALL values in session (`plot_area_sqm`, `buildup_area_sqm`, `carpet_area_sqm`, `fsi`, `ground_coverage`, `ground_floor_area_sqm`); add `computed_at` (ISO 8601 UTC timestamp); return complete `AreaReport`

- [ ] Task 7: Add `format_ratio` helper and `AreaReport` schema (AC: 6, 7)
  - [ ] 7.1: Add `format_ratio(value: float) -> str` to `modules/area/service.py`: returns `f"{value:.3f}"` (3dp for FSI/coverage, NFR12)
  - [ ] 7.2: Create `AreaReport(BaseModel)` in `modules/area/schemas.py`: fields per AC6 — `plot_area_sqm: float`, `buildup_area_sqm: float`, `carpet_area_sqm: float`, `fsi: float`, `ground_coverage: float`, `floor_breakdown: list[FloorAreaBreakdown]`, `wall_thickness_factor: float`, `computed_at: str`, `drawing_hash: str | None = None`
  - [ ] 7.3: Add string-formatted versions as additional fields or computed properties: `fsi_str: str`, `ground_coverage_str: str`, `plot_area_sqm_str: str`, etc.

- [ ] Task 8: Register tools, add error codes, and write tests (AC: 1, 2, 3, 4, 5)
  - [ ] 8.1: Add to `ErrorCode` in `errors.py`: `PLOT_AREA_NOT_COMPUTED`, `BUILDUP_AREA_NOT_COMPUTED`, `GROUND_FLOOR_NOT_FOUND`, `INVALID_PLOT_AREA`
  - [ ] 8.2: Register `area_compute_fsi`, `area_compute_coverage`, `area_compute_all` in `modules/area/__init__.py`
  - [ ] 8.3: `tests/unit/modules/area/test_area_compute_fsi.py` — test FSI = 560/1000 = 0.560 (3dp: `"0.560"`); test `PLOT_AREA_NOT_COMPUTED` when session missing `plot_area_sqm`; test divide-by-zero protection (plot_area = 0.0)
  - [ ] 8.4: `tests/unit/modules/area/test_area_compute_coverage.py` — test coverage = 200/1000 = 0.200; test `BUILDUP_AREA_NOT_COMPUTED` error path
  - [ ] 8.5: `tests/unit/modules/area/test_area_compute_all.py` — integration-style test with mock backend returning known polygon data; assert all 5 area values are correct; assert `computed_at` is a valid ISO timestamp; assert `area_compute_all` completes < 10s (NFR4)
  - [ ] 8.6: Test NFR13 reproducibility: call `area_compute_all` twice on same mock session; assert both calls return identical `fsi`, `ground_coverage`, and area values

## Dev Notes

### Critical Architecture Constraints

1. **`area_compute_all` calls individual service methods in dependency order** — it does NOT call the individual MCP tools (`area_compute_plot`, `area_compute_builtup`, etc.). It calls `AreaService` methods directly, bypassing the tool handlers. This keeps tool handlers thin and service methods reusable. The session state is updated by the `area_compute_all` tool handler after all computations succeed.
2. **NFR13 — reproducibility requires no randomness** — all computations are pure functions of the drawing data and `wall_thickness_factor`. No random sampling, no approximate algorithms. The same set of Shapely polygon operations on the same vertex data always yields the same float value. Do NOT use `time.time()` or `random` anywhere in computation paths.
3. **NFR12 — 3dp accuracy for FSI and coverage** — format to 3dp at the response boundary only. Intermediate computations use full float precision. `format_ratio` is a display function, not a rounding function for computation.
4. **NFR4 — 10 second limit for `area_compute_all`** — this means for a typical 10-floor building with moderately complex floor plates, all Shapely operations must complete in < 10s. Shapely is very fast for typical building polygons (< 100 vertices per polygon). If performance is an issue, consider batching polygon construction.
5. **Ground floor identification** — the "ground floor" for coverage purposes is the first entry in the `buildup_result["floors"]` list (after natural sort). The naming convention (e.g., `FLOOR_PLATE_GF`) determines which layer this is. Document this assumption in code comments and in the `AreaReport` response.
6. **`drawing_hash` in `AreaReport`** — retrieve from `ctx.get_state("drawing_hash")` if the session tracks a hash of the current drawing state. If not available yet (established in later story), set to `None` with a TODO comment. This field is for audit/archival purposes (NFR13 traceability).

### Module/Component Notes

**`AreaReport` complete schema:**

```python
from datetime import datetime, timezone
from pydantic import BaseModel, computed_field


class AreaReport(BaseModel):
    # Raw float values for downstream arithmetic
    plot_area_sqm: float
    buildup_area_sqm: float
    carpet_area_sqm: float
    fsi: float
    ground_coverage: float
    ground_floor_area_sqm: float

    # Configuration inputs
    wall_thickness_factor: float

    # Per-floor breakdown (preserves insertion order — NFR13)
    floor_breakdown: list[FloorAreaBreakdown]

    # Audit / traceability fields (FR26, NFR13)
    computed_at: str          # ISO 8601 UTC, e.g. "2026-03-04T12:00:00Z"
    drawing_hash: str | None  # from session state, None if not yet tracked

    # Formatted display strings (4dp for areas, 3dp for ratios — NFR11, NFR12)
    @computed_field
    @property
    def plot_area_sqm_str(self) -> str:
        return f"{self.plot_area_sqm:.4f}"

    @computed_field
    @property
    def buildup_area_sqm_str(self) -> str:
        return f"{self.buildup_area_sqm:.4f}"

    @computed_field
    @property
    def carpet_area_sqm_str(self) -> str:
        return f"{self.carpet_area_sqm:.4f}"

    @computed_field
    @property
    def fsi_str(self) -> str:
        return f"{self.fsi:.3f}"  # NFR12: 3dp for ratios

    @computed_field
    @property
    def ground_coverage_str(self) -> str:
        return f"{self.ground_coverage:.3f}"  # NFR12: 3dp for ratios
```

**`area_compute_fsi` and `area_compute_coverage` — session state dependency:**

These tools rely on previously computed values stored in session. The recommended flow is:

```
area_compute_plot()       → stores "plot_area_sqm"
area_compute_builtup()    → stores "buildup_area_sqm", "ground_floor_area_sqm"
area_compute_fsi()        → reads "plot_area_sqm", "buildup_area_sqm"
area_compute_coverage()   → reads "plot_area_sqm", "ground_floor_area_sqm"
```

OR the AI client calls:

```
area_compute_all()        → runs all in sequence, stores all keys
```

**Note on `ground_floor_area_sqm` session key** — update Story 8-3 (`area_compute_builtup` handler) to also store `ctx.set_state("ground_floor_area_sqm", floors[0]["area_sqm"])` if the floors list is non-empty. Add a TODO in Story 8-3 if it was not done there.

**`area_compute_all` response shape:**

```python
{
    "success": True,
    "data": {
        "plot_area_sqm": 1000.0,
        "plot_area_sqm_str": "1000.0000",
        "buildup_area_sqm": 560.0,
        "buildup_area_sqm_str": "560.0000",
        "carpet_area_sqm": 476.0,
        "carpet_area_sqm_str": "476.0000",
        "fsi": 0.56,
        "fsi_str": "0.560",
        "ground_coverage": 0.2,
        "ground_coverage_str": "0.200",
        "ground_floor_area_sqm": 200.0,
        "wall_thickness_factor": 0.85,
        "floor_breakdown": [
            {"floor": "FLOOR_PLATE_GF", "area_sqm": 200.0, "area_sqm_str": "200.0000"},
            {"floor": "FLOOR_PLATE_1",  "area_sqm": 180.0, "area_sqm_str": "180.0000"},
            {"floor": "FLOOR_PLATE_2",  "area_sqm": 180.0, "area_sqm_str": "180.0000"}
        ],
        "computed_at": "2026-03-04T12:00:00Z",
        "drawing_hash": null
    }
}
```

**Session state keys set by this story:**

| Key | Type | Set by |
|-----|------|--------|
| `"fsi"` | `float` | `area_compute_fsi`, `area_compute_all` |
| `"ground_coverage"` | `float` | `area_compute_coverage`, `area_compute_all` |
| `"ground_floor_area_sqm"` | `float` | `area_compute_all` (or `area_compute_builtup` update) |

These join `"plot_area_sqm"`, `"buildup_area_sqm"`, `"carpet_area_sqm"` (Stories 8-2, 8-3) to provide the complete area state consumed by the AutoDCR scrutiny engine (Epic 9).

### Project Structure Notes

Files to create or modify in this story:

```
src/lcs_cad_mcp/
├── errors.py                              # Update: PLOT_AREA_NOT_COMPUTED, BUILDUP_AREA_NOT_COMPUTED,
│                                          #         GROUND_FLOOR_NOT_FOUND, INVALID_PLOT_AREA
└── modules/area/
    ├── __init__.py                        # Update: register area_compute_fsi, area_compute_coverage, area_compute_all
    ├── tools.py                           # Update: add all 3 tool handlers
    ├── service.py                         # Update: add compute_fsi, compute_coverage, compute_all, format_ratio
    └── schemas.py                         # Update: add AreaReport

tests/unit/modules/area/
├── test_area_compute_fsi.py               # New
├── test_area_compute_coverage.py          # New
└── test_area_compute_all.py               # New
```

### Dependencies

- **Story 8-3** — `AreaService.compute_buildup_area`, `compute_carpet_area`, and all floor plate layer infrastructure must exist. Session state keys `"buildup_area_sqm"` and `"carpet_area_sqm"` must be set by the Story 8-3 tools.
- **Story 8-2** — `AreaService.compute_plot_area` and session state key `"plot_area_sqm"` must exist.
- **Story 8-1** — `AreaService`, `_entities_to_polygon`, `AreaComputationError` base infrastructure must exist.
- **Story 9-1** (AutoDCR scrutiny engine) — `area_compute_all` output (`AreaReport`) is the primary input to the rule evaluation engine. The schema defined here must be compatible with what Story 9-1 expects.

### References

- Architecture area computation engine: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Area Computation Engine"]
- NFR4 (10 second limit): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- NFR11 (area ±0.01 sqm): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- NFR12 (FSI/coverage 3dp): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- NFR13 (reproducibility — same drawing = identical results): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- FR22 (area computation): [Source: `_bmad-output/planning-artifacts/architecture.md` — FR section]
- FR26 (audit trail / config version in results): [Source: `_bmad-output/planning-artifacts/architecture.md` — FR section]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 8, Story 8-4]

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
- `tests/unit/modules/area/test_area_compute_fsi.py`
- `tests/unit/modules/area/test_area_compute_coverage.py`
- `tests/unit/modules/area/test_area_compute_all.py`
