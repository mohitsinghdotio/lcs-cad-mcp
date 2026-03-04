# Story 9.4: Parking Ratio and Height Restriction Rule Checkers

Status: ready-for-dev

## Story

As a **developer**, I want parking ratio and height restriction rule checkers, so that all common DCR rule types are covered in the MVP scrutiny engine with actionable remediation guidance.

## Acceptance Criteria

1. **AC1:** `ParkingChecker` in `src/lcs_cad_mcp/rule_engine/checkers/parking_checker.py` implements `RuleChecker`; registered via `register_checker("parking_ratio", ParkingChecker)`; reads `computed_areas["parking_count"]` (int) and `computed_areas["dwelling_unit_count"]` (int or float); computes `parking_ratio = parking_count / dwelling_unit_count`; compares against `rule.threshold` using `compare_value()` with `rule.comparison = "gte"` (minimum ratio).
2. **AC2:** `HeightChecker` in `src/lcs_cad_mcp/rule_engine/checkers/height_checker.py` implements `RuleChecker`; registered via `register_checker("height_restriction", HeightChecker)`; reads `computed_areas["building_height"]` (float, meters) from entity metadata queried via `EntityService`; compares against `rule.threshold` with `rule.comparison = "lte"` (maximum height).
3. **AC3:** `ParkingChecker` returns `RuleResult` with `status="fail"` when `parking_ratio < rule.threshold`; `deviation = parking_ratio - rule.threshold` (negative = deficit); `suggested_action` = `"Add {shortfall} parking spaces to meet minimum ratio of {rule.threshold} per dwelling unit"` where `shortfall = ceil(abs(deviation) * dwelling_unit_count)`.
4. **AC4:** `HeightChecker` returns `RuleResult` with `status="fail"` when `building_height > rule.threshold`; `deviation = building_height - rule.threshold` (positive = over limit); `suggested_action` = `"Reduce building height by {deviation:.2f}m to meet maximum height restriction of {rule.threshold}m"`.
5. **AC5:** Both checkers handle missing keys in `computed_areas` by raising `KeyError` with a message that includes the missing key name and the checker name.
6. **AC6:** `ParkingChecker` handles `dwelling_unit_count == 0` by raising `ValueError("dwelling_unit_count must be > 0 for parking ratio calculation")` — a zero-dwelling building is a config error, not a rule pass.
7. **AC7:** Both checkers are imported in `rule_engine/checkers/__init__.py` for auto-registration.
8. **AC8:** Unit tests cover: pass at boundary, fail with correct deviation, missing keys, and (for parking) zero-dwelling-unit edge case.

## Tasks / Subtasks

- [ ] Task 1: Implement `ParkingChecker` in `src/lcs_cad_mcp/rule_engine/checkers/parking_checker.py` (AC: 1, 3, 5, 6)
  - [ ] 1.1: Implement `class ParkingChecker` with `check(self, rule: DCRRule, computed_areas: dict, config: DCRConfig) -> RuleResult`
  - [ ] 1.2: Extract `parking_count = computed_areas["parking_count"]` and `dwelling_unit_count = computed_areas["dwelling_unit_count"]`; raise `KeyError(f"ParkingChecker requires '{key}' in computed_areas")` for missing keys
  - [ ] 1.3: Guard: `if dwelling_unit_count == 0: raise ValueError("dwelling_unit_count must be > 0 for parking ratio calculation")`
  - [ ] 1.4: Compute `parking_ratio = parking_count / dwelling_unit_count`; call `passed = compare_value(parking_ratio, rule.threshold, rule.comparison)` — `rule.comparison` must be `"gte"` for parking (minimum)
  - [ ] 1.5: Compute `deviation = round(parking_ratio - rule.threshold, 10)` (negative means deficit)
  - [ ] 1.6: If failing: `shortfall = math.ceil(abs(deviation) * dwelling_unit_count)`; build `suggested_action` per AC3
  - [ ] 1.7: Return `RuleResult` with `unit="spaces_per_dwelling"`, `computed_value=parking_ratio`, `permissible_value=rule.threshold`
  - [ ] 1.8: Register at module bottom: `register_checker("parking_ratio", ParkingChecker)`

- [ ] Task 2: Implement `HeightChecker` in `src/lcs_cad_mcp/rule_engine/checkers/height_checker.py` (AC: 2, 4, 5)
  - [ ] 2.1: Implement `class HeightChecker` with `check(self, rule: DCRRule, computed_areas: dict, config: DCRConfig) -> RuleResult`
  - [ ] 2.2: Extract `building_height = computed_areas["building_height"]`; raise `KeyError(f"HeightChecker requires 'building_height' in computed_areas")` if missing
  - [ ] 2.3: Call `passed = compare_value(building_height, rule.threshold, rule.comparison)` — `rule.comparison` must be `"lte"` for height restriction (maximum)
  - [ ] 2.4: Compute `deviation = round(building_height - rule.threshold, 10)` (positive = over limit)
  - [ ] 2.5: If failing, build `suggested_action` per AC4 with `deviation` in meters to 2 decimal places
  - [ ] 2.6: Return `RuleResult` with `unit="m"`, `computed_value=building_height`, `permissible_value=rule.threshold`
  - [ ] 2.7: Register at module bottom: `register_checker("height_restriction", HeightChecker)`

- [ ] Task 3: Note on `computed_areas["building_height"]` sourcing (AC: 2)
  - [ ] 3.1: Document in `height_checker.py` module docstring: `building_height` is sourced from `AreaService.compute_all()` which in turn reads it from the entity attribute `"HEIGHT"` on entities in the `BUILDING` layer (or from the Z-coordinate extent of the tallest building entity); this is an Epic 8 / Entity Management concern — `HeightChecker` only reads the pre-computed float value
  - [ ] 3.2: Document in `parking_checker.py` module docstring: `parking_count` is sourced from `AreaService.compute_all()` which counts entities on the `PARKING` layer; `dwelling_unit_count` comes from drawing annotation entity with attribute `"DWELLING_UNITS"` on the `NOTES` layer (or from `config.building_metadata.dwelling_units` if present)

- [ ] Task 4: Update `rule_engine/checkers/__init__.py` for auto-registration (AC: 7)
  - [ ] 4.1: Add `from lcs_cad_mcp.rule_engine.checkers import parking_checker as _pk_checker  # noqa: F401`
  - [ ] 4.2: Add `from lcs_cad_mcp.rule_engine.checkers import height_checker as _ht_checker  # noqa: F401`
  - [ ] 4.3: Verify all 5 checker registrations are present: `fsi`, `ground_coverage`, `setback`, `parking_ratio`, `height_restriction`

- [ ] Task 5: Write unit tests for `ParkingChecker` in `tests/unit/rule_engine/test_parking_checker.py` (AC: 8)
  - [ ] 5.1: Write `test_parking_pass`: `parking_count=20`, `dwelling_unit_count=10`, `threshold=2.0`, assert `status=="pass"`, `computed_value==pytest.approx(2.0)`
  - [ ] 5.2: Write `test_parking_fail`: `parking_count=15`, `dwelling_unit_count=10`, `threshold=2.0`, assert `status=="fail"`, `deviation==pytest.approx(-0.5)`, `"5 parking spaces"` in `suggested_action`
  - [ ] 5.3: Write `test_parking_zero_dwelling_raises`: `dwelling_unit_count=0`, assert `ValueError` with `"dwelling_unit_count"` in message
  - [ ] 5.4: Write `test_parking_missing_key_raises`: `computed_areas={}`, assert `KeyError` with checker name in message
  - [ ] 5.5: Write `test_parking_shortfall_rounds_up`: `parking_ratio=1.9`, `threshold=2.0`, `dwelling_units=5`, assert `shortfall=1` (ceil of 0.5)

- [ ] Task 6: Write unit tests for `HeightChecker` in `tests/unit/rule_engine/test_height_checker.py` (AC: 8)
  - [ ] 6.1: Write `test_height_pass_at_boundary`: `building_height=15.0`, `threshold=15.0`, assert `status=="pass"`, `deviation==0.0`
  - [ ] 6.2: Write `test_height_fail`: `building_height=17.5`, `threshold=15.0`, assert `status=="fail"`, `deviation==pytest.approx(2.5)`, `"2.50m"` in `suggested_action`
  - [ ] 6.3: Write `test_height_missing_key_raises`: `computed_areas={}`, assert `KeyError` with `"building_height"` in message

## Dev Notes

### Critical Architecture Constraints

1. **`parking_ratio` comparison direction**: Parking ratio uses `comparison="gte"` (minimum — must have AT LEAST the required ratio). This is the OPPOSITE direction from FSI and ground coverage (`"lte"`). The `compare_value()` utility handles all three directions; ensure the `rule.comparison` field in the DCR config YAML is set correctly when testing.
2. **`math.ceil` import**: `ParkingChecker` requires `import math` for `math.ceil(shortfall)`. This is stdlib — no new dependency.
3. **Entity querying for parking count**: `computed_areas["parking_count"]` is an int produced by `AreaService.compute_all()` by counting entities on the `PARKING` layer. The `ParkingChecker` itself does NOT query entities directly — it only reads the pre-computed value. This is the correct separation of concerns.
4. **Building height sourcing**: `computed_areas["building_height"]` is a float (meters) produced by `AreaService.compute_all()`. Height may be stored as an entity attribute (`HEIGHT` attribute on a BUILDING entity) or derived from 3D coordinates. The checker does not care — it reads the float.
5. **`dwelling_unit_count` fallback chain**: Primary source is `computed_areas["dwelling_unit_count"]` (from drawing annotation). If not found in `computed_areas`, `ParkingChecker` may check `config.building_metadata.dwelling_units` as fallback — document this in the module docstring. Raise `KeyError` only if both sources are absent.

### Module/Component Notes

- `ParkingChecker` — `unit = "spaces_per_dwelling"` in `RuleResult`; `rule.comparison = "gte"`
- `HeightChecker` — `unit = "m"` in `RuleResult`; `rule.comparison = "lte"`
- Shortfall calculation: `shortfall = math.ceil(abs(deviation) * dwelling_unit_count)` — this gives the integer number of additional parking spaces needed (always round up, since you cannot add a fractional parking space)
- These two checkers complete the core DCR rule set for MVP; the `_RULE_CHECKERS` registry after this story has 5 entries: `fsi`, `ground_coverage`, `setback`, `parking_ratio`, `height_restriction`

### Project Structure Notes

```
src/lcs_cad_mcp/
└── rule_engine/
    └── checkers/
        ├── __init__.py              # updated: imports all 5 checker modules
        ├── fsi_checker.py           # story 9-2
        ├── ground_coverage_checker.py  # story 9-3
        ├── setback_checker.py          # story 9-3
        ├── parking_checker.py          # NEW
        └── height_checker.py           # NEW

tests/
└── unit/
    └── rule_engine/
        ├── test_fsi_checker.py           # story 9-2
        ├── test_ground_coverage_checker.py  # story 9-3
        ├── test_setback_checker.py          # story 9-3
        ├── test_parking_checker.py          # NEW
        └── test_height_checker.py           # NEW
```

### Dependencies

- Story 9-1: `RuleChecker` protocol, `register_checker()`, `compare_value()`, `DCRRule`, `RuleResult`
- Story 9-2: `checkers/` directory and `__init__.py` side-effect pattern
- Story 9-3: no direct code dependency, but same `checkers/__init__.py` file is updated
- Epic 7 (Story 7-2): `DCRConfig` with parking and height rule definitions
- Epic 8 (Story 8-4): `AreaService.compute_all()` returning `"parking_count"`, `"dwelling_unit_count"`, `"building_height"` keys
- Entity Management (Epic 5): `EntityService` is used by `AreaService` to count PARKING entities — but `ParkingChecker` and `HeightChecker` do NOT import `EntityService` directly

### References

- Story 9-1: `_bmad-output/implementation-artifacts/9-1-rule-evaluation-engine-framework.md`
- Story 9-2: `_bmad-output/implementation-artifacts/9-2-fsi-rule-checker.md`
- FR24 (iterative correction), FR25 (dry-run): apply in stories 9-5 and 9-6
- FR31 (remediation suggestions): `_bmad-output/planning-artifacts/epics-and-stories.md`
- Epic 9 stories: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 9, Story 9-4

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/rule_engine/checkers/parking_checker.py`
- `src/lcs_cad_mcp/rule_engine/checkers/height_checker.py`
- `src/lcs_cad_mcp/rule_engine/checkers/__init__.py` (updated — all 5 checkers)
- `tests/unit/rule_engine/test_parking_checker.py`
- `tests/unit/rule_engine/test_height_checker.py`
