# Story 7.1: DCR Rule Config Schema and Pydantic Models

Status: ready-for-dev

## Story

As a **developer**,
I want **a documented, Pydantic-validated schema for DCR rule config files**,
so that **engineers can write authority rule configs without ambiguity and rule files are validated at parse time** (FR19, NFR20).

## Acceptance Criteria

1. **AC1:** Schema covers all required rule dimensions: FSI limits by zone, ground coverage percentage, setback distances (front/side/rear), parking ratio per building type, and height restrictions — each as a typed Pydantic field with validation constraints.
2. **AC2:** Schema is fully defined as Pydantic v2 models in `src/lcs_cad_mcp/rule_engine/models.py` — using `model_validator`, `field_validator`, and `Annotated` types where appropriate.
3. **AC3:** Schema is documented as a YAML template with inline comments at `dcr_configs/schema.yaml`.
4. **AC4:** Schema documentation published in `docs/dcr-config-schema.md` covering all fields, types, required vs. optional, and example values.
5. **AC5:** A sample config for a generic residential authority is included at `dcr_configs/sample-residential.yaml` with real-world plausible values.
6. **AC6:** `DCRRule`, `DCRConfig`, and `RuleResult` models are importable from `src/lcs_cad_mcp/rule_engine/models.py`.
7. **AC7:** Unit tests in `tests/unit/rule_engine/test_models.py` validate that invalid configs raise `ValidationError` and valid configs parse cleanly.

## Tasks / Subtasks

- [ ] Task 1: Define `DCRRule` Pydantic model in `rule_engine/models.py` (AC: 1, 2, 6)
  - [ ] 1.1: Add fields: `rule_id: str`, `name: str`, `description: str`, `rule_type: RuleType` (enum), `threshold: float`, `unit: str`, `zone_applicability: list[str]`, `tolerance: float = 0.0`
  - [ ] 1.2: Create `RuleType` enum with values: `FSI`, `GROUND_COVERAGE`, `SETBACK_FRONT`, `SETBACK_SIDE`, `SETBACK_REAR`, `PARKING_RATIO`, `HEIGHT_RESTRICTION`, `OPEN_SPACE`
  - [ ] 1.3: Add Pydantic v2 `field_validator` on `threshold` to reject negative values; add `model_validator` ensuring `zone_applicability` is non-empty list
  - [ ] 1.4: Add `Config` inner class with `frozen=True` to enforce immutability during scrutiny (NFR23)

- [ ] Task 2: Define `DCRConfig` Pydantic model in `rule_engine/models.py` (AC: 1, 2, 6)
  - [ ] 2.1: Add fields: `version: str`, `authority: str`, `effective_date: str`, `rules: list[DCRRule]`, `metadata: dict[str, str] = {}`
  - [ ] 2.2: Add `model_validator` ensuring `rules` list is non-empty and all `rule_id` values are unique across the list
  - [ ] 2.3: Add computed property `rule_count: int` returning `len(self.rules)` and `zone_set: set[str]` returning all distinct zones across all rules
  - [ ] 2.4: Add `Config` inner class with `frozen=True` — once loaded, the config object is immutable

- [ ] Task 3: Define `RuleResult` Pydantic model in `rule_engine/models.py` (AC: 2, 6)
  - [ ] 3.1: Add fields: `rule_id: str`, `rule_name: str`, `passed: bool`, `computed_value: float`, `permissible_value: float`, `deviation: float`, `suggested_action: str = ""`
  - [ ] 3.2: Add computed property `deviation_percent: float` = `abs(computed_value - permissible_value) / permissible_value * 100` (guard divide-by-zero)
  - [ ] 3.3: Add `status: Literal["pass", "fail", "deviation"]` derived field: `"pass"` if `passed`, `"deviation"` if `abs(deviation) <= tolerance`, else `"fail"`

- [ ] Task 4: Create `dcr_configs/schema.yaml` YAML template with inline comments (AC: 3)
  - [ ] 4.1: Document every field with `# required` / `# optional` comment and its data type
  - [ ] 4.2: Include one example rule block for each `RuleType` enum value
  - [ ] 4.3: Add top-level comments explaining zone codes, unit conventions (sqm, m, ratio), and versioning policy

- [ ] Task 5: Create `dcr_configs/sample-residential.yaml` with realistic values (AC: 5)
  - [ ] 5.1: Define at least 6 rules covering: FSI (residential zone R1), ground coverage (R1), front setback, side setback, rear setback, parking ratio (residential)
  - [ ] 5.2: Use real-world-plausible values (e.g., FSI=1.0, coverage=40%, front setback=4.5m)
  - [ ] 5.3: Include `version: "1.0.0"`, `authority: "Sample Residential Authority"`, `effective_date`

- [ ] Task 6: Write unit tests in `tests/unit/rule_engine/test_models.py` (AC: 7)
  - [ ] 6.1: Test `DCRRule` with valid data parses without error
  - [ ] 6.2: Test `DCRRule` with `threshold < 0` raises `ValidationError`
  - [ ] 6.3: Test `DCRConfig` with empty `rules` list raises `ValidationError`
  - [ ] 6.4: Test `DCRConfig` with duplicate `rule_id` values raises `ValidationError`
  - [ ] 6.5: Test `RuleResult.deviation_percent` calculation for known inputs

- [ ] Task 7: Publish schema documentation to `docs/dcr-config-schema.md` (AC: 4)
  - [ ] 7.1: Document all `DCRConfig` top-level fields with type, required/optional, and description
  - [ ] 7.2: Document all `DCRRule` fields with type, constraints, and example values
  - [ ] 7.3: Include a full annotated YAML example block

## Dev Notes

### Critical Architecture Constraints

1. **Pydantic v2 only** — use `model_validator(mode="after")` and `field_validator` decorators, NOT v1 `@validator`. All models use `model_config = ConfigDict(frozen=True)` to enforce read-only rule objects during scrutiny (NFR23).
2. **`RuleType` must be a `str` enum** (`class RuleType(str, Enum)`) so that YAML/JSON string values deserialize directly without custom validators.
3. **Insertion order preservation** — `rules: list[DCRRule]` preserves the order from the YAML/JSON file (Python `list` + `dict` 3.7+ guarantee). The evaluator will process rules in this order, ensuring determinism (NFR13).
4. **`frozen=True` on all config models** — once a `DCRConfig` or `DCRRule` is instantiated, no field mutation is permitted. This is the primary NFR23 enforcement mechanism.
5. **No circular imports** — `rule_engine/models.py` must import only from `pydantic` and Python stdlib. It must not import from `modules/`, `backends/`, or `session/`.

### Module/Component Notes

**File: `src/lcs_cad_mcp/rule_engine/models.py`**

```python
from enum import Enum
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RuleType(str, Enum):
    FSI = "FSI"
    GROUND_COVERAGE = "GROUND_COVERAGE"
    SETBACK_FRONT = "SETBACK_FRONT"
    SETBACK_SIDE = "SETBACK_SIDE"
    SETBACK_REAR = "SETBACK_REAR"
    PARKING_RATIO = "PARKING_RATIO"
    HEIGHT_RESTRICTION = "HEIGHT_RESTRICTION"
    OPEN_SPACE = "OPEN_SPACE"


class DCRRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    name: str
    description: str
    rule_type: RuleType
    threshold: Annotated[float, Field(ge=0.0)]
    unit: str
    zone_applicability: Annotated[list[str], Field(min_length=1)]
    tolerance: float = 0.0

    @field_validator("threshold")
    @classmethod
    def threshold_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("threshold must be >= 0")
        return v


class DCRConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    authority: str
    effective_date: str
    rules: Annotated[list[DCRRule], Field(min_length=1)]
    metadata: dict[str, str] = {}

    @model_validator(mode="after")
    def check_unique_rule_ids(self) -> "DCRConfig":
        ids = [r.rule_id for r in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("All rule_id values must be unique within a DCRConfig")
        return self

    @property
    def rule_count(self) -> int:
        return len(self.rules)

    @property
    def zone_set(self) -> set[str]:
        zones: set[str] = set()
        for rule in self.rules:
            zones.update(rule.zone_applicability)
        return zones


class RuleResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    rule_name: str
    passed: bool
    computed_value: float
    permissible_value: float
    deviation: float
    suggested_action: str = ""

    @property
    def deviation_percent(self) -> float:
        if self.permissible_value == 0.0:
            return 0.0
        return abs(self.computed_value - self.permissible_value) / self.permissible_value * 100
```

**Key design note on `status` field:** The `status` derived field described in AC7-3.3 should be implemented as a `@property` rather than a stored Pydantic field to keep `frozen=True` compatible and avoid complex `model_validator` chains. The evaluator (`rule_engine/evaluator.py`) consumes `RuleResult.passed` directly.

### Project Structure Notes

Files to create or modify in this story:

```
src/lcs_cad_mcp/rule_engine/
├── models.py          # PRIMARY DELIVERABLE — all Pydantic models
├── __init__.py        # Export: DCRRule, DCRConfig, RuleResult, RuleType
├── loader.py          # Stub only — implemented in Story 7-2
├── validator.py       # Stub only — implemented in Story 7-2
└── evaluator.py       # Stub only — implemented in Story 9-1

dcr_configs/
├── schema.yaml        # New: annotated YAML template
└── sample-residential.yaml  # New: example authority config

docs/
└── dcr-config-schema.md     # New or update stub

tests/unit/rule_engine/
├── __init__.py        # Create if not exists
└── test_models.py     # New: unit tests for models
```

**Important:** `rule_engine/` lives at `src/lcs_cad_mcp/rule_engine/` — NOT inside `modules/`. It is shared infrastructure used by both `modules/config/` and `modules/autodcr/`.

### Dependencies

- **Story 1-5** (Pydantic input validation framework) — must be complete; this story depends on Pydantic v2 being installed and `pyproject.toml` correct.
- No other story dependencies. This story can proceed as soon as Story 1-5 is done.

### References

- Architecture doc rule engine models: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Rule Engine"]
- DCR rule dimensions: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 7, Story 7-1, AC1]
- Pydantic v2 frozen models: [Source: Pydantic v2 docs — `ConfigDict(frozen=True)`]
- NFR23 (config immutability): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- NFR13 (determinism / insertion order): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]

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
- `src/lcs_cad_mcp/rule_engine/__init__.py`
- `dcr_configs/schema.yaml`
- `dcr_configs/sample-residential.yaml`
- `docs/dcr-config-schema.md`
- `tests/unit/rule_engine/__init__.py`
- `tests/unit/rule_engine/test_models.py`
