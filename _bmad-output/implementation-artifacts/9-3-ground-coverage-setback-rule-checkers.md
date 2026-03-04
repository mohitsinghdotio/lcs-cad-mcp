# Story 9.3: Ground Coverage and Setback Rule Checkers

Status: ready-for-dev

## Story

As a **developer**, I want ground coverage and setback rule checkers, so that these critical DCR rules are evaluated accurately in the scrutiny pass using geometry-aware calculations.

## Acceptance Criteria

1. **AC1:** `GroundCoverageChecker` in `src/lcs_cad_mcp/rule_engine/checkers/ground_coverage_checker.py` implements `RuleChecker`; registered via `register_checker("ground_coverage", GroundCoverageChecker)`; reads `computed_areas["ground_coverage"]` and compares against `rule.threshold` using `compare_value()`; `rule.comparison` for ground coverage is always `"lte"`.
2. **AC2:** `SetbackChecker` in `src/lcs_cad_mcp/rule_engine/checkers/setback_checker.py` implements `RuleChecker`; registered via `register_checker("setback", SetbackChecker)`; reads building footprint geometry and plot boundary geometry from `computed_areas` and measures minimum distances per side (front/side_left/side_right/rear) using Shapely `distance()`.
3. **AC3:** `SetbackChecker.check()` evaluates each setback side independently; if any side fails, the overall `RuleResult.status` is `"fail"`; `suggested_action` names the failing sides explicitly (e.g., `"Front setback: 2.1m computed vs 3.0m required. Side-left setback: 1.8m computed vs 2.5m required."`).
4. **AC4:** Both checkers return `RuleResult` with `status`, `computed_value`, `permissible_value`, `deviation`, `unit` (unit for ground coverage is `"ratio"`, for setback is `"m"`), and `suggested_action` with actionable remediation text (FR31).
5. **AC5:** `SetbackChecker` uses `shapely.geometry.Polygon.distance()` for setback measurement; it does NOT implement its own distance formula.
6. **AC6:** Both checkers are imported in `rule_engine/checkers/__init__.py` to auto-register at startup.
7. **AC7:** Unit tests in `tests/unit/rule_engine/test_ground_coverage_checker.py` and `tests/unit/rule_engine/test_setback_checker.py` cover: pass at boundary, fail with deviation, and (for setback) multi-side failure with correct side names in `suggested_action`.
8. **AC8:** Hypothesis test for `GroundCoverageChecker` confirms that for any `computed_coverage > threshold`, `result.deviation > 0` and `result.status == "fail"`.

## Tasks / Subtasks

- [ ] Task 1: Implement `GroundCoverageChecker` in `src/lcs_cad_mcp/rule_engine/checkers/ground_coverage_checker.py` (AC: 1, 4, 6)
  - [ ] 1.1: Implement `class GroundCoverageChecker` with `check(self, rule: DCRRule, computed_areas: dict, config: DCRConfig) -> RuleResult`
  - [ ] 1.2: Extract `computed_coverage = computed_areas["ground_coverage"]` (float, 0.0–1.0 ratio); let `KeyError` propagate
  - [ ] 1.3: Call `passed = compare_value(computed_coverage, rule.threshold, rule.comparison)` from `rule_engine.evaluator`
  - [ ] 1.4: Compute `deviation = round(computed_coverage - rule.threshold, 10)` (positive = over limit)
  - [ ] 1.5: Build and return `RuleResult`; if failing, `suggested_action` = `"Reduce ground floor footprint by {reduction_pct:.1f}% to meet coverage limit of {rule.threshold*100:.1f}%"` where `reduction_pct = (deviation / rule.threshold) * 100`
  - [ ] 1.6: Register at bottom of module: `register_checker("ground_coverage", GroundCoverageChecker)`

- [ ] Task 2: Implement geometry geometry key contract for setback checker (AC: 2, 5)
  - [ ] 2.1: Define expected `computed_areas` geometry keys: `"building_footprint_polygon"` (Shapely `Polygon`) and `"plot_boundary_polygon"` (Shapely `Polygon`); document these in a module-level comment in `setback_checker.py`
  - [ ] 2.2: Define per-side boundary lines: derive `front_line`, `side_left_line`, `side_right_line`, `rear_line` by splitting `plot_boundary_polygon` edges; use the convention from the DCR config side labeling (front = side facing road, as annotated in the drawing)
  - [ ] 2.3: For each side: compute `distance = building_footprint_polygon.distance(side_line)` using Shapely; compare against `rule.threshold` (or per-side threshold from `computed_areas["setback_requirements"]` if provided)

- [ ] Task 3: Implement `SetbackChecker` class (AC: 2, 3, 4, 5)
  - [ ] 3.1: Implement `class SetbackChecker` with `check(self, rule: DCRRule, computed_areas: dict, config: DCRConfig) -> RuleResult`
  - [ ] 3.2: Extract `building_footprint = computed_areas["building_footprint_polygon"]` and `plot_boundary = computed_areas["plot_boundary_polygon"]`; raise `KeyError` with informative message if either missing
  - [ ] 3.3: Compute per-side setback distances using `shapely.distance()`; collect results as `dict[str, float]` keyed by side name (`"front"`, `"side_left"`, `"side_right"`, `"rear"`)
  - [ ] 3.4: Compare each side distance against `rule.threshold`; collect failing sides with their computed and required values
  - [ ] 3.5: If any side fails, `status="fail"`; `computed_value = min(side_distances.values())` (worst case); `deviation = rule.threshold - computed_value` (positive = under minimum required); format `suggested_action` listing each failing side
  - [ ] 3.6: If all sides pass, `status="pass"`, `computed_value = min(side_distances.values())`, `deviation = 0.0`, `suggested_action = ""`
  - [ ] 3.7: Register at module bottom: `register_checker("setback", SetbackChecker)`

- [ ] Task 4: Update `rule_engine/checkers/__init__.py` to auto-register both new checkers (AC: 6)
  - [ ] 4.1: Add to `checkers/__init__.py`: `from lcs_cad_mcp.rule_engine.checkers import ground_coverage_checker as _gc_checker  # noqa: F401`
  - [ ] 4.2: Add to `checkers/__init__.py`: `from lcs_cad_mcp.rule_engine.checkers import setback_checker as _sb_checker  # noqa: F401`

- [ ] Task 5: Write unit tests for `GroundCoverageChecker` (AC: 7, 8)
  - [ ] 5.1: Write `test_ground_coverage_pass_at_boundary`: `computed_coverage=0.40`, `threshold=0.40`, assert `status=="pass"`, `deviation==0.0`
  - [ ] 5.2: Write `test_ground_coverage_fail`: `computed_coverage=0.55`, `threshold=0.40`, assert `status=="fail"`, `deviation==pytest.approx(0.15)`, `"coverage limit"` in `suggested_action`
  - [ ] 5.3: Write `@given` hypothesis `test_ground_coverage_fail_always_positive_deviation`: for any `computed > threshold`, assert `deviation > 0`

- [ ] Task 6: Write unit tests for `SetbackChecker` (AC: 7)
  - [ ] 6.1: Create minimal Shapely polygon fixtures: `plot_polygon` (10m x 10m square), `building_polygon` (6m x 6m square centered inside plot, giving 2m setback on all sides)
  - [ ] 6.2: Write `test_setback_all_pass`: all sides have 2m setback, `rule.threshold=2.0`, assert `status=="pass"`
  - [ ] 6.3: Write `test_setback_front_fail`: push building 0.5m toward front boundary (1.5m front setback), `threshold=2.0`, assert `status=="fail"`, `"front"` in `suggested_action`, `"side"` NOT in `suggested_action`
  - [ ] 6.4: Write `test_setback_multi_side_fail`: two sides failing, assert both side names appear in `suggested_action`
  - [ ] 6.5: Write `test_missing_geometry_keys_raise`: pass `computed_areas={}`, assert `KeyError` raised with informative message

## Dev Notes

### Critical Architecture Constraints

1. **Shapely dependency**: `SetbackChecker` uses Shapely, which is a declared dependency in `pyproject.toml` from Story 1-1. No additional dependencies needed. Import as `from shapely.geometry import Polygon, LineString`.
2. **Geometry key contract**: The keys `"building_footprint_polygon"` and `"plot_boundary_polygon"` must match what `AreaService.compute_all()` (Epic 8) returns. Confirm with the Epic 8 implementation before coding.
3. **Per-side setback thresholds**: The `rule.threshold` field is a single float (the most restrictive / default minimum setback). If the DCR config supports per-side thresholds (e.g., front=3.0m, side=2.5m, rear=2.5m), these must be embedded in the rule as additional metadata or via separate rules with distinct `rule_id` values. For this story, implement single-threshold mode; per-side configuration is a future enhancement.
4. **NFR12 precision**: Setback distances in meters, compared at 3 decimal places (`abs(computed - threshold) < 1e-3` is passing).
5. **No MCP layer imports**: Both checkers are pure domain logic — no FastMCP or `tools.py` imports.

### Module/Component Notes

- `GroundCoverageChecker`: `computed_areas["ground_coverage"]` is a ratio (e.g., 0.40 for 40%); the `rule.threshold` is also a ratio; `unit = "ratio"` in `RuleResult`
- `SetbackChecker`: distances in meters; `unit = "m"` in `RuleResult`
- Plot boundary side labeling convention: front = polygon edge closest to road annotation (requires `computed_areas["road_facing_edge_index"]` or similar from AreaService); if not available, use the longest edge as front
- `suggested_action` for setback must explicitly name failing sides — this is used by AI clients to issue targeted remediation instructions

### Project Structure Notes

```
src/lcs_cad_mcp/
└── rule_engine/
    └── checkers/
        ├── __init__.py              # updated: imports all 3 checker modules
        ├── fsi_checker.py           # from story 9-2
        ├── ground_coverage_checker.py   # NEW
        └── setback_checker.py           # NEW

tests/
└── unit/
    └── rule_engine/
        ├── test_fsi_checker.py               # from story 9-2
        ├── test_ground_coverage_checker.py   # NEW
        └── test_setback_checker.py           # NEW
```

### Dependencies

- Story 9-1: `RuleChecker` protocol, `register_checker()`, `compare_value()`, `DCRRule`, `RuleResult`
- Story 9-2: `checkers/` directory and `__init__.py` pattern (created in story 9-2)
- Epic 7 (Story 7-2): `DCRConfig` with ground_coverage and setback rule definitions
- Epic 8 (Story 8-4): `AreaService.compute_all()` returning `"ground_coverage"`, `"building_footprint_polygon"`, `"plot_boundary_polygon"` keys

### References

- Story 9-1: `_bmad-output/implementation-artifacts/9-1-rule-evaluation-engine-framework.md`
- Story 9-2: `_bmad-output/implementation-artifacts/9-2-fsi-rule-checker.md`
- FR22 (ground coverage): `_bmad-output/planning-artifacts/epics-and-stories.md`
- FR31 (remediation suggestions): `_bmad-output/planning-artifacts/epics-and-stories.md`
- Epic 9 stories: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 9, Story 9-3

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/rule_engine/checkers/ground_coverage_checker.py`
- `src/lcs_cad_mcp/rule_engine/checkers/setback_checker.py`
- `src/lcs_cad_mcp/rule_engine/checkers/__init__.py` (updated)
- `tests/unit/rule_engine/test_ground_coverage_checker.py`
- `tests/unit/rule_engine/test_setback_checker.py`
