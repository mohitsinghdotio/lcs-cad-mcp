# Story 3.4: PreDCR Layer Naming Validation

Status: ready-for-dev

## Story

As a **developer**,
I want **a validation engine that checks layer names against PreDCR naming conventions**,
so that **layers created by the system are guaranteed to match authority requirements and violations are caught before submission (NFR14)**.

## Acceptance Criteria

1. **AC1:** `LayerValidator.validate(name: str, building_type: str) -> ValidationResult` returns a `ValidationResult` with `valid: bool` and `violations: list[str]`; used internally by other services and exposed via `layer_validate_naming()` in Story 6.
2. **AC2:** PreDCR layer naming rules are defined as a configurable data structure (YAML file or Python dataclass catalog), NOT as hard-coded regex strings scattered in code. The rule set is loaded once and reused across validations.
3. **AC3:** Validation catches at minimum: wrong prefix (prefix does not match any expected authority/entity pattern), wrong separator character (must use `-` not `_` or `.` between components), and unsupported entity type suffix (suffix not in the allowed entity type list for the given building type).
4. **AC4:** Zero false positives — all known-correct PreDCR layer names (test fixtures) return `valid=True, violations=[]`.
5. **AC5:** `layer_create` (from Story 3-2) calls `LayerValidator.validate(name, building_type)` when a `building_type` parameter is provided; if `valid=False`, the create operation is aborted and the `MCPError` message includes the violations list. If no `building_type` is passed, naming validation is skipped (backwards-compatible).
6. **AC6:** `LayerValidator` is implemented as a standalone class (no MCP tool in this story — the MCP-exposed tool `layer_validate_naming` is created in Story 6/verification module); its `validate()` method is synchronous (not async) since it is a pure computation with no I/O.
7. **AC7:** Unit tests in `tests/unit/modules/layers/test_layer_validator.py` verify: correct names pass, wrong prefix fails, wrong separator fails, invalid suffix fails, empty name fails, and `ValidationResult` structure is correct.

## Tasks / Subtasks

- [ ] Task 1: Define `ValidationResult` Pydantic model in `schemas.py` (AC: 1)
  - [ ] 1.1: Add `ValidationResult(BaseModel)` to `src/lcs_cad_mcp/modules/layers/schemas.py`:
    ```python
    class ValidationResult(BaseModel):
        valid: bool
        violations: list[str] = []
        layer_name: str = ""
        building_type: str = ""
    ```
  - [ ] 1.2: Add `to_dict() -> dict` helper method for clean serialization

- [ ] Task 2: Define PreDCR naming rule data structure (AC: 2)
  - [ ] 2.1: Create `src/lcs_cad_mcp/modules/layers/predcr_naming_rules.yaml` with the PreDCR layer naming specification:
    - [ ] 2.1.1: Define `separator`: `-` (the mandatory component separator)
    - [ ] 2.1.2: Define `valid_prefixes`: list of allowed authority/discipline prefixes (e.g., `["PLOT", "WALL", "COLUMN", "BEAM", "SLAB", "STAIR", "DOOR", "WINDOW", "RAMP", "LIFT"]`)
    - [ ] 2.1.3: Define `valid_entity_suffixes`: dict mapping building_type to list of allowed suffixes (e.g., `{"residential": ["BDY", "HDR", "FTR"], "commercial": [...]}`)
    - [ ] 2.1.4: Define `max_length`: 31 (AutoCAD layer name character limit)
    - [ ] 2.1.5: Define `forbidden_characters`: list of chars not allowed in layer names (e.g., `["<", ">", "/", "\\", '"', ":", ";", "?", "*", "|", "=", "'"]`)
  - [ ] 2.2: Create `src/lcs_cad_mcp/modules/layers/naming_rule_loader.py` with `NamingRuleLoader`:
    - [ ] 2.2.1: `NamingRuleLoader.load(path: Path | None = None) -> NamingRules` — reads the YAML file (defaults to the bundled `predcr_naming_rules.yaml`)
    - [ ] 2.2.2: `NamingRules` is a Pydantic model or dataclass holding `separator`, `valid_prefixes`, `valid_entity_suffixes`, `max_length`, `forbidden_characters`
    - [ ] 2.2.3: Use `importlib.resources` or `Path(__file__).parent / "predcr_naming_rules.yaml"` to locate the bundled YAML file
    - [ ] 2.2.4: Cache the loaded rules as a module-level singleton (load once per process, not per validation call)

- [ ] Task 3: Implement `LayerValidator` class (AC: 1, 3, 4, 6)
  - [ ] 3.1: Create `src/lcs_cad_mcp/modules/layers/validator.py` with `LayerValidator` class:
    - [ ] 3.1.1: `__init__(self, rules: NamingRules | None = None)` — if `rules` is None, load via `NamingRuleLoader.load()`
    - [ ] 3.1.2: `validate(self, name: str, building_type: str) -> ValidationResult` — main entry point; synchronous, pure computation
    - [ ] 3.1.3: Internal `_check_empty(name) -> str | None` — returns violation string if name is empty or whitespace
    - [ ] 3.1.4: Internal `_check_length(name) -> str | None` — checks `len(name) <= self.rules.max_length`
    - [ ] 3.1.5: Internal `_check_forbidden_chars(name) -> str | None` — checks no forbidden chars present
    - [ ] 3.1.6: Internal `_check_separator(name) -> str | None` — verifies that components are joined by `self.rules.separator` (e.g., `-`); fails if underscore or dot used as separator where dash expected
    - [ ] 3.1.7: Internal `_check_prefix(name) -> str | None` — splits on `self.rules.separator`, checks `parts[0].upper()` is in `{p.upper() for p in self.rules.valid_prefixes}`
    - [ ] 3.1.8: Internal `_check_suffix(name, building_type) -> str | None` — checks last component is in `self.rules.valid_entity_suffixes.get(building_type.lower(), [])`
    - [ ] 3.1.9: `validate()` runs all checks, collects non-None violation strings, returns `ValidationResult(valid=len(violations)==0, violations=violations, layer_name=name, building_type=building_type)`

- [ ] Task 4: Wire `LayerValidator` into `LayerService.create_layer()` (AC: 5)
  - [ ] 4.1: Modify `LayerService.create_layer()` signature to accept optional `building_type: str | None = None`
  - [ ] 4.2: After the `registry.contains(name)` check and before the backend call, add:
    ```python
    if building_type is not None:
        from lcs_cad_mcp.modules.layers.validator import LayerValidator
        result = LayerValidator().validate(name, building_type)
        if not result.valid:
            raise MCPError(
                code=ErrorCode.LAYER_NAME_INVALID,
                message=f"Layer name '{name}' violates PreDCR naming conventions.",
                recoverable=True,
                suggested_action=f"Violations: {'; '.join(result.violations)}",
            )
    ```
  - [ ] 4.3: Add `LAYER_NAME_INVALID = "LAYER_NAME_INVALID"` to `ErrorCode` in `errors.py`
  - [ ] 4.4: Update `layer_create` tool handler in `tools.py` to accept and pass through `building_type: str | None = None`

- [ ] Task 5: Export `LayerValidator` and `ValidationResult` from the `layers` package (AC: 6)
  - [ ] 5.1: Update `src/lcs_cad_mcp/modules/layers/__init__.py` to import and re-export `LayerValidator` and `ValidationResult` so other modules (e.g., Epic 6 verification module) can import from `lcs_cad_mcp.modules.layers`
  - [ ] 5.2: Do NOT register `LayerValidator` as an MCP tool in this story — it will be wrapped in an MCP tool in the verification/Epic 6 module

- [ ] Task 6: Write unit tests (AC: 7)
  - [ ] 6.1: Create `tests/unit/modules/layers/test_layer_validator.py`
  - [ ] 6.2: Define fixture `VALID_PREDCR_NAMES` — a list of 5+ layer names that are known-correct PreDCR names (matching prefix, separator, and suffix):
    ```python
    VALID_PREDCR_NAMES = [
        "PLOT-BOUNDARY-BDY",
        "WALL-OUTER-HDR",
        "DOOR-MAIN-FTR",
        "WINDOW-FRONT-BDY",
        "STAIR-MAIN-HDR",
    ]
    ```
  - [ ] 6.3: Test `validate()` on each valid name — verify `valid=True, violations=[]`
  - [ ] 6.4: Test wrong prefix — `"INVALID_PREFIX-OUTER-BDY"` — verify `valid=False`, violations include prefix error message
  - [ ] 6.5: Test wrong separator — `"WALL_OUTER_BDY"` (underscore instead of dash) — verify `valid=False`, violations include separator error
  - [ ] 6.6: Test invalid suffix — `"WALL-OUTER-WRONGSUFFIX"` — verify `valid=False`, violations include suffix error
  - [ ] 6.7: Test empty name — `""` — verify `valid=False`, violations include empty name error
  - [ ] 6.8: Test name exceeding max length (32+ chars) — verify `valid=False`, length violation included
  - [ ] 6.9: Test name with forbidden character — `"WALL>OUTER-BDY"` — verify `valid=False`, forbidden char violation
  - [ ] 6.10: Test `ValidationResult` structure — verify `valid`, `violations`, `layer_name`, `building_type` fields present
  - [ ] 6.11: Test that `LayerValidator` can be instantiated with a custom `NamingRules` object (dependency injection for testability — no YAML file I/O in unit tests)
  - [ ] 6.12: Test that `LayerService.create_layer()` with `building_type="residential"` and an invalid name raises `MCPError` with `LAYER_NAME_INVALID` code

## Dev Notes

### Critical Architecture Constraints

1. **`LayerValidator` is synchronous, not async** — it performs no I/O; it is a pure computation over an in-memory rule set. Do NOT add `async def validate(...)`. Tool handlers that call it do not need `await`.
2. **YAML rules file, not hard-coded** — the naming rules must be in `predcr_naming_rules.yaml`. Hard-coding regex patterns or prefix lists in Python source violates AC2 and the architecture's config-driven extensibility requirement.
3. **`LayerValidator` is NOT an MCP tool in this story** — do NOT call `mcp.tool()` on it, do NOT add it to `register(mcp)`. It is a utility class. The MCP-exposed tool (`layer_validate_naming`) is a Story 6 responsibility.
4. **No `ezdxf` import** — `LayerValidator` and `NamingRuleLoader` have zero CAD dependencies. They operate on plain strings and YAML data only.
5. **Dependency injection for rules** — `LayerValidator(rules=custom_rules)` must work for unit tests. The constructor should accept an optional `NamingRules` argument to avoid file I/O in tests.
6. **Rule loading is cached** — `NamingRuleLoader` loads the YAML file once at module import (or first call) and caches it. Do NOT re-read the file on every `validate()` invocation.
7. **`building_type` is case-insensitive** — normalize to lowercase before lookup in `valid_entity_suffixes`. `"Residential"` and `"residential"` must both work.
8. **Backwards-compatible `layer_create`** — adding `building_type` to `create_layer()` must be optional (default `None`). Existing callers that do not pass `building_type` must continue to work without naming validation.

### Module/Component Notes

**`predcr_naming_rules.yaml` schema (annotated):**
```yaml
# PreDCR layer naming convention rules
# Source: Legacy AutoDCR_PreDCR specification
# Extend valid_entity_suffixes for new building types without code changes.

separator: "-"
max_length: 31
forbidden_characters:
  - "<"
  - ">"
  - "/"
  - "\\"
  - "\""
  - ":"
  - ";"
  - "?"
  - "*"
  - "|"
  - "="
  - "'"

valid_prefixes:
  - PLOT
  - WALL
  - COLUMN
  - BEAM
  - SLAB
  - STAIR
  - DOOR
  - WINDOW
  - RAMP
  - LIFT
  - TOILET
  - KITCHEN
  - BALCONY
  - PARKING
  - SETBACK

valid_entity_suffixes:
  residential:
    - BDY     # Boundary
    - HDR     # Header / outline
    - FTR     # Footer / base
    - INF     # Infill
    - TXT     # Text/annotation
    - DIM     # Dimension
  commercial:
    - BDY
    - HDR
    - FTR
    - INF
    - TXT
    - DIM
    - COR     # Core (commercial-specific)
  industrial:
    - BDY
    - HDR
    - FTR
    - INF
    - TXT
    - DIM
    - MEC     # Mechanical (industrial-specific)
```

**`NamingRules` Pydantic model and loader:**
```python
# naming_rule_loader.py
from pathlib import Path
from functools import lru_cache
import yaml
from pydantic import BaseModel


class NamingRules(BaseModel):
    separator: str
    max_length: int
    forbidden_characters: list[str]
    valid_prefixes: list[str]
    valid_entity_suffixes: dict[str, list[str]]


@lru_cache(maxsize=1)
def _load_default_rules() -> NamingRules:
    rules_path = Path(__file__).parent / "predcr_naming_rules.yaml"
    with open(rules_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return NamingRules(**data)


class NamingRuleLoader:
    @staticmethod
    def load(path: Path | None = None) -> NamingRules:
        if path is None:
            return _load_default_rules()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return NamingRules(**data)
```

**`LayerValidator` implementation:**
```python
# validator.py
from lcs_cad_mcp.modules.layers.naming_rule_loader import NamingRuleLoader, NamingRules
from lcs_cad_mcp.modules.layers.schemas import ValidationResult


class LayerValidator:
    def __init__(self, rules: NamingRules | None = None) -> None:
        self.rules = rules if rules is not None else NamingRuleLoader.load()

    def validate(self, name: str, building_type: str) -> ValidationResult:
        violations: list[str] = []
        for check in [
            self._check_empty,
            self._check_length,
            self._check_forbidden_chars,
            self._check_separator,
            self._check_prefix,
        ]:
            v = check(name)
            if v:
                violations.append(v)
        # Only check suffix if basic structure passed
        if not violations:
            v = self._check_suffix(name, building_type)
            if v:
                violations.append(v)
        return ValidationResult(
            valid=len(violations) == 0,
            violations=violations,
            layer_name=name,
            building_type=building_type,
        )

    def _check_empty(self, name: str) -> str | None:
        if not name or not name.strip():
            return "Layer name cannot be empty."
        return None

    def _check_length(self, name: str) -> str | None:
        if len(name) > self.rules.max_length:
            return f"Layer name exceeds {self.rules.max_length} character limit (got {len(name)})."
        return None

    def _check_forbidden_chars(self, name: str) -> str | None:
        found = [c for c in self.rules.forbidden_characters if c in name]
        if found:
            return f"Layer name contains forbidden character(s): {found}"
        return None

    def _check_separator(self, name: str) -> str | None:
        sep = self.rules.separator
        # Must contain at least one separator
        if sep not in name:
            return (
                f"Layer name must use '{sep}' as separator between components "
                f"(e.g., WALL{sep}OUTER{sep}BDY). Got: '{name}'."
            )
        return None

    def _check_prefix(self, name: str) -> str | None:
        sep = self.rules.separator
        parts = name.split(sep)
        prefix = parts[0].upper()
        valid = {p.upper() for p in self.rules.valid_prefixes}
        if prefix not in valid:
            return (
                f"Prefix '{parts[0]}' is not a valid PreDCR layer prefix. "
                f"Valid prefixes: {sorted(self.rules.valid_prefixes)}."
            )
        return None

    def _check_suffix(self, name: str, building_type: str) -> str | None:
        sep = self.rules.separator
        parts = name.split(sep)
        suffix = parts[-1].upper()
        allowed = {
            s.upper()
            for s in self.rules.valid_entity_suffixes.get(building_type.lower(), [])
        }
        if not allowed:
            return (
                f"Unknown building_type '{building_type}'. "
                f"Cannot validate suffix against unknown building type."
            )
        if suffix not in allowed:
            return (
                f"Suffix '{parts[-1]}' is not valid for building type '{building_type}'. "
                f"Valid suffixes: {sorted(allowed)}."
            )
        return None
```

**Integration into `LayerService.create_layer()`:**
```python
def create_layer(
    self,
    name: str,
    color: int = 7,
    linetype: str = "CONTINUOUS",
    lineweight: float = 0.25,
    building_type: str | None = None,   # NEW — optional, backwards-compatible
) -> LayerRecord:
    self.ensure_synced()
    if self.registry.contains(name):
        raise MCPError(code=ErrorCode.LAYER_ALREADY_EXISTS, ...)

    # PreDCR naming validation (only when building_type is provided)
    if building_type is not None:
        from lcs_cad_mcp.modules.layers.validator import LayerValidator
        result = LayerValidator().validate(name, building_type)
        if not result.valid:
            raise MCPError(
                code=ErrorCode.LAYER_NAME_INVALID,
                message=f"Layer name '{name}' violates PreDCR naming conventions.",
                recoverable=True,
                suggested_action=f"Violations: {'; '.join(result.violations)}",
            )

    self.session.backend.create_layer(name=name, color=color, linetype=linetype, lineweight=lineweight)
    record = LayerRecord(name=name, color=color, linetype=linetype, lineweight=lineweight)
    self.registry.add(record)
    return record
```

**Test fixture with dependency injection (no YAML I/O):**
```python
# test_layer_validator.py
import pytest
from lcs_cad_mcp.modules.layers.naming_rule_loader import NamingRules
from lcs_cad_mcp.modules.layers.validator import LayerValidator


@pytest.fixture
def rules() -> NamingRules:
    return NamingRules(
        separator="-",
        max_length=31,
        forbidden_characters=["<", ">", "/"],
        valid_prefixes=["PLOT", "WALL", "DOOR", "WINDOW", "STAIR"],
        valid_entity_suffixes={
            "residential": ["BDY", "HDR", "FTR"],
            "commercial": ["BDY", "HDR", "COR"],
        },
    )


@pytest.fixture
def validator(rules: NamingRules) -> LayerValidator:
    return LayerValidator(rules=rules)


VALID_PREDCR_NAMES = [
    ("PLOT-BOUNDARY-BDY", "residential"),
    ("WALL-OUTER-HDR", "residential"),
    ("DOOR-MAIN-FTR", "residential"),
    ("WINDOW-FRONT-BDY", "residential"),
    ("STAIR-MAIN-HDR", "residential"),
]


@pytest.mark.parametrize("name,building_type", VALID_PREDCR_NAMES)
def test_valid_names_pass(validator, name, building_type):
    result = validator.validate(name, building_type)
    assert result.valid is True
    assert result.violations == []
```

### Project Structure Notes

Files created or modified by this story:

```
src/lcs_cad_mcp/modules/layers/
├── __init__.py                   # MODIFY — export LayerValidator, ValidationResult
├── schemas.py                    # MODIFY — add ValidationResult model
├── service.py                    # MODIFY — add building_type param to create_layer()
├── tools.py                      # MODIFY — add building_type param to layer_create handler
├── validator.py                  # NEW — LayerValidator class
├── naming_rule_loader.py         # NEW — NamingRules Pydantic model + NamingRuleLoader
└── predcr_naming_rules.yaml      # NEW — PreDCR naming rule specification

src/lcs_cad_mcp/errors.py         # MODIFY — add LAYER_NAME_INVALID error code

tests/unit/modules/layers/
└── test_layer_validator.py       # NEW — LayerValidator unit tests
```

### YAML Dependency

`pyyaml` (package: `PyYAML`) is required for loading the YAML rules file. Verify it is listed in `pyproject.toml` dependencies. If not, add it:
```toml
"pyyaml>=6.0",
```
And run `uv add pyyaml` to install.

### PreDCR Naming Convention Research Note

The `valid_prefixes` and `valid_entity_suffixes` in `predcr_naming_rules.yaml` are **initial stubs** based on the general PreDCR specification pattern. Before finalizing this story:
1. Consult the legacy `AutoDCR_PreDCR` specification documents for the authoritative layer name list.
2. Update `predcr_naming_rules.yaml` with the exact prefix and suffix values from the spec.
3. Add a comment in the YAML file: `# Source: AutoDCR_PreDCR specification document, version <X>`

The YAML-driven design (AC2) means this can be updated without code changes — only the YAML file needs editing.

### Dependencies

- **Story 3-1** (`LayerRecord`, `LayerRegistry`, `LayerService` skeleton in `layers/`) — `validator.py` is added to the same `layers/` module package; `ValidationResult` is added to `schemas.py` from 3-1.
- **Story 3-2** (`LayerService.create_layer()`) — this story modifies that method to accept `building_type` and call `LayerValidator`.
- **Story 1-1** (project scaffold) — `pyyaml` must be available; add to `pyproject.toml` if not present.
- **Epic 6** (verification module) — will import `LayerValidator` from `lcs_cad_mcp.modules.layers` and wrap it in an MCP-exposed tool. This story provides the importable utility; Epic 6 provides the MCP surface.

### References

- PreDCR naming requirement (NFR14): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- Configurable rule storage principle: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 3-4, AC2 Technical Notes]
- `layer_validate_naming` as future MCP tool: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 3-4, AC1]
- Integration with `layer_create`: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 3-4, AC5]
- `predcr/layer_registry.py` as related naming source: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Complete Project Directory Structure", predcr/ module]
- Story definition: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 3, Story 3-4]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/errors.py`
- `src/lcs_cad_mcp/modules/layers/__init__.py`
- `src/lcs_cad_mcp/modules/layers/schemas.py`
- `src/lcs_cad_mcp/modules/layers/service.py`
- `src/lcs_cad_mcp/modules/layers/tools.py`
- `src/lcs_cad_mcp/modules/layers/validator.py`
- `src/lcs_cad_mcp/modules/layers/naming_rule_loader.py`
- `src/lcs_cad_mcp/modules/layers/predcr_naming_rules.yaml`
- `tests/unit/modules/layers/test_layer_validator.py`
