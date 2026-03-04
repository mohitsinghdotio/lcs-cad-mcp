# Story 9.2: FSI Rule Checker

Status: ready-for-dev

## Story

As a **developer**, I want an FSI rule checker that compares computed FSI against the permissible FSI for the zone, so that FSI violations are detected and reported with computed vs. permissible values and actionable remediation suggestions.

## Acceptance Criteria

1. **AC1:** `FSIRuleChecker` class in `src/lcs_cad_mcp/rule_engine/checkers/fsi_checker.py` implements the `RuleChecker` protocol; it is registered via `register_checker("fsi", FSIRuleChecker)` so it is active at import time.
2. **AC2:** `FSIRuleChecker.check(rule, computed_areas, config)` reads `computed_areas["fsi"]` (float, sourced from `AreaService.compute_all()`) and compares it against `rule.threshold` using `compare_value(computed, threshold, rule.comparison)`; passes if `computed_fsi <= rule.threshold`.
3. **AC3:** Returns `RuleResult` with `status="pass"` when FSI is within limit; comparison is exact to 3 decimal places — values within `0.001` of threshold are considered passing (NFR12).
4. **AC4:** Returns `RuleResult` with `status="fail"`, `deviation = computed_fsi - rule.threshold` (positive float), and `suggested_action` in the format: `"Reduce built-up area by {sqm_to_remove:.2f} sqm to meet FSI limit of {rule.threshold}"` where `sqm_to_remove = deviation * plot_area` (FR31).
5. **AC5:** `plot_area` used in the remediation calculation is read from `computed_areas["plot_area"]`; if `"plot_area"` key is absent, `suggested_action` falls back to: `"Reduce built-up area to bring FSI to {rule.threshold} (plot area unavailable for sqm estimate)"`.
6. **AC6:** Unit tests in `tests/unit/rule_engine/test_fsi_checker.py` verify: (a) pass case at FSI = threshold (boundary condition), (b) pass case at FSI < threshold, (c) fail case with correct deviation and sqm calculation, (d) missing `"fsi"` key in `computed_areas` raises `KeyError` with message including `"fsi"`.
7. **AC7:** Hypothesis property-based test confirms that for any `computed_fsi > threshold`, `result.deviation > 0` and `result.status == "fail"`.

## Tasks / Subtasks

- [ ] Task 1: Create `checkers/` subdirectory under `rule_engine/` (AC: 1)
  - [ ] 1.1: Create `src/lcs_cad_mcp/rule_engine/checkers/__init__.py`; this file imports all checkers so that a single `import lcs_cad_mcp.rule_engine.checkers` registers them all via side-effect
  - [ ] 1.2: Create `src/lcs_cad_mcp/rule_engine/checkers/fsi_checker.py` with module docstring: `"""FSI rule checker — registers itself via register_checker('fsi', FSIRuleChecker) on import."""`

- [ ] Task 2: Implement `FSIRuleChecker` class (AC: 2, 3, 4, 5)
  - [ ] 2.1: Implement `class FSIRuleChecker` with `check(self, rule: DCRRule, computed_areas: dict, config: DCRConfig) -> RuleResult`
  - [ ] 2.2: Extract `computed_fsi = computed_areas["fsi"]`; let `KeyError` propagate naturally (caller sees informative Python traceback)
  - [ ] 2.3: Call `passed = compare_value(computed_fsi, rule.threshold, rule.comparison)` from `rule_engine.evaluator`
  - [ ] 2.4: Compute `deviation = round(computed_fsi - rule.threshold, 10)` (signed; positive = over limit)
  - [ ] 2.5: If `passed`, build `RuleResult` with `status="pass"`, `deviation=deviation`, `suggested_action=""`
  - [ ] 2.6: If not `passed`, compute `sqm_to_remove` using `computed_areas.get("plot_area")`; build failure `RuleResult` with formatted `suggested_action` per AC4/AC5
  - [ ] 2.7: Return immutable `RuleResult` (Pydantic frozen model); populate all fields including `rule_id`, `rule_name`, `rule_type`, `computed_value`, `permissible_value`, `unit`

- [ ] Task 3: Register `FSIRuleChecker` at module import time (AC: 1)
  - [ ] 3.1: At the bottom of `fsi_checker.py`, call `register_checker("fsi", FSIRuleChecker)` — this must execute as a module-level side effect when the file is imported
  - [ ] 3.2: In `checkers/__init__.py`, add `from lcs_cad_mcp.rule_engine.checkers import fsi_checker as _fsi_checker  # noqa: F401` to trigger registration

- [ ] Task 4: Write unit tests in `tests/unit/rule_engine/test_fsi_checker.py` (AC: 6, 7)
  - [ ] 4.1: Write `test_fsi_pass_at_boundary`: `computed_areas = {"fsi": 2.000, "plot_area": 1000.0}`, `rule.threshold = 2.0`, assert `status == "pass"`, `deviation == 0.0`
  - [ ] 4.2: Write `test_fsi_pass_below_limit`: `computed_fsi = 1.5`, `threshold = 2.0`, assert `status == "pass"`
  - [ ] 4.3: Write `test_fsi_fail_with_sqm`: `computed_fsi = 2.5`, `threshold = 2.0`, `plot_area = 1000.0`, assert `status == "fail"`, `deviation == pytest.approx(0.5)`, `"500.00 sqm"` in `suggested_action`
  - [ ] 4.4: Write `test_fsi_fail_without_plot_area`: `computed_areas = {"fsi": 2.5}` (no `"plot_area"`), assert `status == "fail"` and `"plot area unavailable"` in `suggested_action`
  - [ ] 4.5: Write `test_missing_fsi_key_raises`: `computed_areas = {}`, assert `KeyError` raised
  - [ ] 4.6: Write `@given` hypothesis test `test_fsi_fail_always_positive_deviation`: for any `computed_fsi > threshold`, assert `result.deviation > 0` and `result.status == "fail"`

- [ ] Task 5: Verify 3-decimal-place precision behaviour (AC: 3, NFR12)
  - [ ] 5.1: Write `test_fsi_boundary_precision`: test that `computed_fsi = 2.0009` passes (within 0.001 of threshold 2.0) and `computed_fsi = 2.001` fails; implement the tolerance check inside `FSIRuleChecker` using `abs(computed - threshold) < 1e-3` before calling the standard `compare_value`
  - [ ] 5.2: Document the tolerance logic in a module-level comment in `fsi_checker.py`: `# NFR12: values within 0.001 of threshold are treated as passing to handle floating-point rounding in area computation`

## Dev Notes

### Critical Architecture Constraints

1. **Registration via import side-effect**: `FSIRuleChecker` must be registered when `rule_engine.checkers` is imported — NOT lazily. `AutoDCRService` will do `import lcs_cad_mcp.rule_engine.checkers` once at startup to register all checkers. If a checker module is not imported, its `rule_type` will not be recognized.
2. **`computed_areas["fsi"]` key contract**: The key `"fsi"` is the agreed-upon contract between `AreaService.compute_all()` (Epic 8) and the rule engine. If Epic 8 uses a different key name, this checker breaks. Verify the key name against Story 8-4 implementation before coding.
3. **NFR12 precision**: 3 decimal places for FSI comparison. FSI is a ratio (dimensionless), so comparison is numeric. The `rule.comparison` field for FSI rules will always be `"lte"` (FSI limit is an upper bound).
4. **No MCP imports**: `fsi_checker.py` must NOT import anything from `modules/autodcr/tools.py` or FastMCP. It is pure domain logic called by `DCRRuleEvaluator`.
5. **`suggested_action` is a string, not a structured object**: The remediation text is human-readable, consumed by AI clients and human architects. Future stories may parse it, so keep the format consistent: `"Reduce built-up area by {X:.2f} sqm to meet FSI limit of {Y}"`.

### Module/Component Notes

- `FSIRuleChecker` lives in `rule_engine/checkers/`, a new subdirectory under `rule_engine/`
- The `computed_areas` dict comes from `AreaService.compute_all()` (Epic 8, Story 8-4); expected keys include at minimum: `"fsi"`, `"plot_area"`, `"built_up_area"`, `"ground_coverage"`, `"building_height"`
- `DCRConfig` from Epic 7 provides `rules: list[DCRRule]`; the FSI rule entry will have `rule_type="fsi"`, `threshold=<float>`, `unit="ratio"`, `comparison="lte"`
- `plot_area` is expected in `computed_areas`; it is computed by `AreaService` from the PLOT layer polygon area

### Project Structure Notes

```
src/lcs_cad_mcp/
└── rule_engine/
    ├── checkers/
    │   ├── __init__.py         # imports all checker modules for side-effect registration
    │   └── fsi_checker.py      # FSIRuleChecker + register_checker("fsi", ...)

tests/
└── unit/
    └── rule_engine/
        ├── __init__.py         # already created in story 9-1
        ├── test_evaluator.py   # already created in story 9-1
        └── test_fsi_checker.py # NEW in this story
```

### Dependencies

- Story 9-1: `DCRRuleEvaluator`, `RuleChecker` protocol, `register_checker()`, `compare_value()`, `DCRRule`, `RuleResult` — all must be implemented first
- Epic 7 (Story 7-2): `DCRConfig` with `rules: list[DCRRule]` and the FSI rule configuration schema
- Epic 8 (Story 8-4): `AreaService.compute_all()` return dict with `"fsi"` and `"plot_area"` keys

### References

- Story 9-1 (this story's direct dependency): `_bmad-output/implementation-artifacts/9-1-rule-evaluation-engine-framework.md`
- FR23 (FSI violation detection): `_bmad-output/planning-artifacts/epics-and-stories.md`
- FR31 (remediation suggestions): `_bmad-output/planning-artifacts/epics-and-stories.md`
- NFR12 (3 decimal precision): `_bmad-output/planning-artifacts/epics-and-stories.md`
- Epic 9 stories: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 9, Story 9-2

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/rule_engine/checkers/__init__.py`
- `src/lcs_cad_mcp/rule_engine/checkers/fsi_checker.py`
- `tests/unit/rule_engine/test_fsi_checker.py`
