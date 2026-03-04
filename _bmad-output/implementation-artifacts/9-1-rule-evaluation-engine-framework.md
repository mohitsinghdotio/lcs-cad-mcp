# Story 9.1: Rule Evaluation Engine Framework

Status: ready-for-dev

## Story

As a **developer**, I want a rule evaluation framework that runs each DCR rule as a pluggable check function, so that new rule types can be added without modifying the engine core.

## Acceptance Criteria

1. **AC1:** `DCRRuleEvaluator` in `src/lcs_cad_mcp/rule_engine/evaluator.py` accepts `computed_areas: dict` and `loaded_config: DCRConfig` and returns `list[RuleResult]`; rules are evaluated in config declaration order.
2. **AC2:** Each rule type is implemented as a class implementing a `RuleChecker` protocol with a `check(computed_areas: dict, config: DCRConfig) -> RuleResult` method; the evaluator dispatches by `rule_type` string.
3. **AC3:** `RuleResult` Pydantic model in `rule_engine/models.py` contains: `rule_id: str`, `rule_name: str`, `rule_type: str`, `status: Literal["pass", "fail"]`, `computed_value: float`, `permissible_value: float`, `deviation: float`, `unit: str`, `suggested_action: str`.
4. **AC4:** `ScrutinyReport` Pydantic model in `rule_engine/models.py` contains: `run_id: str`, `timestamp: datetime`, `config_hash: str`, `rule_results: list[RuleResult]`, `overall_pass: bool`; `overall_pass` is `True` only when all `RuleResult.status == "pass"`.
5. **AC5:** `DCRRuleEvaluator` uses a registry dict `_RULE_CHECKERS: dict[str, type[RuleChecker]]`; registering a new rule type requires only adding an entry to this dict — no changes to the evaluator core logic.
6. **AC6:** `DCRRule` Pydantic model in `rule_engine/models.py` contains: `rule_id: str`, `rule_name: str`, `rule_type: str`, `threshold: float`, `unit: str`, `comparison: Literal["lte", "gte", "eq"]`.
7. **AC7:** Unit tests in `tests/unit/rule_engine/test_evaluator.py` verify: (a) evaluation runs rules in config declaration order, (b) a passing rule returns `status="pass"`, (c) a failing rule returns `status="fail"` with non-zero deviation, (d) unknown `rule_type` raises `ValueError` with the offending `rule_id`.
8. **AC8:** Hypothesis property-based test confirms that identical `computed_areas` + identical `DCRConfig` always produce identical `list[RuleResult]` (NFR13 reproducibility).

## Tasks / Subtasks

- [ ] Task 1: Define Pydantic data models in `src/lcs_cad_mcp/rule_engine/models.py` (AC: 3, 4, 6)
  - [ ] 1.1: Implement `DCRRule` model with fields: `rule_id`, `rule_name`, `rule_type`, `threshold`, `unit`, `comparison: Literal["lte", "gte", "eq"]`; add `model_config = ConfigDict(frozen=True)` for immutability
  - [ ] 1.2: Implement `RuleResult` model with all fields from AC3; add `model_config = ConfigDict(frozen=True)`; `deviation` must be signed (positive = over limit, negative = under limit)
  - [ ] 1.3: Implement `ScrutinyReport` model with all fields from AC4; `overall_pass` computed as `all(r.status == "pass" for r in rule_results)` using `@model_validator(mode="after")`
  - [ ] 1.4: Export all three models from `rule_engine/__init__.py`

- [ ] Task 2: Define `RuleChecker` protocol in `src/lcs_cad_mcp/rule_engine/evaluator.py` (AC: 2, 5)
  - [ ] 2.1: Define `class RuleChecker(Protocol)` with method `check(self, rule: DCRRule, computed_areas: dict, config: DCRConfig) -> RuleResult`
  - [ ] 2.2: Create module-level `_RULE_CHECKERS: dict[str, type[RuleChecker]] = {}` registry dict
  - [ ] 2.3: Create `register_checker(rule_type: str, checker_cls: type[RuleChecker]) -> None` helper function that inserts into `_RULE_CHECKERS`

- [ ] Task 3: Implement `DCRRuleEvaluator.evaluate()` in `src/lcs_cad_mcp/rule_engine/evaluator.py` (AC: 1, 5, 6)
  - [ ] 3.1: Implement `class DCRRuleEvaluator` with method `evaluate(computed_areas: dict, loaded_config: DCRConfig) -> list[RuleResult]`
  - [ ] 3.2: Inside `evaluate()`, iterate over `loaded_config.rules` in list order (preserving declaration order); for each rule, look up `_RULE_CHECKERS[rule.rule_type]` — raise `ValueError(f"Unknown rule_type '{rule.rule_type}' in rule '{rule.rule_id}'")` if not found
  - [ ] 3.3: Instantiate checker and call `checker.check(rule, computed_areas, loaded_config)`; collect `RuleResult` into results list; return list in same order as config rules

- [ ] Task 4: Implement a `NullRuleChecker` stub for testing and a `compare_value()` utility (AC: 2, 3)
  - [ ] 4.1: Implement `def compare_value(computed: float, threshold: float, comparison: str) -> bool` supporting `"lte"`, `"gte"`, `"eq"` (eq uses `abs(computed - threshold) < 1e-9`); raise `ValueError` for unsupported comparison
  - [ ] 4.2: Implement `NullRuleChecker` that always returns `status="pass"` with `deviation=0.0` and `suggested_action=""`; register it with `register_checker("null", NullRuleChecker)` for testing purposes
  - [ ] 4.3: Export `compare_value` and `register_checker` from `rule_engine/__init__.py`

- [ ] Task 5: Write unit tests in `tests/unit/rule_engine/test_evaluator.py` (AC: 7, 8)
  - [ ] 5.1: Write `test_evaluation_order`: build a `DCRConfig` with 3 null rules in known order, call `evaluate()`, assert result list indices match config declaration order by `rule_id`
  - [ ] 5.2: Write `test_passing_rule`: configure a null rule, assert `result.status == "pass"` and `result.deviation == 0.0`
  - [ ] 5.3: Write `test_failing_rule`: register a test checker that always fails, assert `result.status == "fail"` and `result.deviation != 0.0`
  - [ ] 5.4: Write `test_unknown_rule_type_raises`: call `evaluate()` with a config containing `rule_type="nonexistent"`, assert `ValueError` is raised with the rule_id in the message
  - [ ] 5.5: Write `@given` hypothesis test `test_reproducibility`: generate random `computed_areas` dict and fixed config, assert two successive calls to `evaluate()` return identical `list[RuleResult]`

- [ ] Task 6: Create `tests/unit/rule_engine/__init__.py` and wire `conftest.py` fixtures (AC: 7)
  - [ ] 6.1: Create `tests/unit/rule_engine/__init__.py` (empty)
  - [ ] 6.2: Add `mock_dcr_config` fixture to `tests/conftest.py` that returns a minimal `DCRConfig` with one rule of `rule_type="null"`; this fixture will be reused by stories 9-2 through 9-6

## Dev Notes

### Critical Architecture Constraints

1. **Evaluation order is mandatory**: Rules MUST be evaluated in the order they appear in `loaded_config.rules`. Python `list` preserves insertion order (3.7+). Do NOT sort, group, or reorder rules during evaluation — this is an NFR13 reproducibility requirement.
2. **Registry pattern — no core changes**: The `_RULE_CHECKERS` dict is the only extension point. Stories 9-2, 9-3, and 9-4 will call `register_checker()` from their own modules; the evaluator core must not be modified.
3. **Frozen Pydantic models**: `RuleResult` and `DCRRule` use `ConfigDict(frozen=True)` so they are hashable and cannot be mutated after creation. This is essential for the reproducibility guarantee.
4. **`AutoDCRService` integration (Story 9-5)**: `AutoDCRService.run_scrutiny()` calls `DCRRuleEvaluator().evaluate(computed_areas, loaded_config)` — a direct Python method call, NOT an MCP tool call. The evaluator must be importable independently of MCP.
5. **`deviation` sign convention**: `deviation = computed_value - permissible_value`. Positive deviation = over limit (bad for FSI/coverage/height); negative deviation = under minimum (bad for parking/setback).

### Module/Component Notes

- `rule_engine/evaluator.py` location: `src/lcs_cad_mcp/rule_engine/evaluator.py` — at the package level, NOT inside `modules/`
- `rule_engine/models.py` location: `src/lcs_cad_mcp/rule_engine/models.py`
- `DCRConfig` is defined in Epic 7 (`src/lcs_cad_mcp/modules/config/schemas.py`); import it as `from lcs_cad_mcp.modules.config.schemas import DCRConfig`
- The evaluator must NOT import from any MCP tool layer (`tools.py` files) — it is pure domain logic
- `compare_value()` utility will be called by all rule checkers in stories 9-2 through 9-4; place it in `evaluator.py` and export from `rule_engine/__init__.py`

### Project Structure Notes

```
src/lcs_cad_mcp/
└── rule_engine/
    ├── __init__.py         # exports: DCRRule, RuleResult, ScrutinyReport, DCRRuleEvaluator, register_checker, compare_value
    ├── evaluator.py        # DCRRuleEvaluator, RuleChecker protocol, _RULE_CHECKERS registry, compare_value
    ├── models.py           # DCRRule, RuleResult, ScrutinyReport Pydantic models
    ├── loader.py           # stub from story 1-1 (not modified in this story)
    └── validator.py        # stub from story 1-1 (not modified in this story)

tests/
└── unit/
    └── rule_engine/
        ├── __init__.py
        └── test_evaluator.py
```

### Dependencies

- Epic 7 (Story 7-2): `DCRConfig` model with `rules: list[DCRRule]` field — must be implemented before this story
- Epic 8 (Story 8-4): `computed_areas: dict` structure from `AreaService.compute_all()` — keys must match what rule checkers expect (e.g., `"fsi"`, `"ground_coverage"`, `"building_height"`)
- Story 1-1: `rule_engine/` directory stub already exists

### References

- Architecture doc rule engine section: `_bmad-output/planning-artifacts/architecture.md` — Section "AutoDCR Module"
- NFR13 reproducibility: `_bmad-output/planning-artifacts/epics-and-stories.md` — NFR section
- Epic 9 stories: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 9, Story 9-1
- `DCRConfig` schema: Epic 7 stories in `_bmad-output/planning-artifacts/epics-and-stories.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/rule_engine/models.py`
- `src/lcs_cad_mcp/rule_engine/evaluator.py`
- `src/lcs_cad_mcp/rule_engine/__init__.py`
- `tests/unit/rule_engine/__init__.py`
- `tests/unit/rule_engine/test_evaluator.py`
- `tests/conftest.py` (updated with `mock_dcr_config` fixture)
