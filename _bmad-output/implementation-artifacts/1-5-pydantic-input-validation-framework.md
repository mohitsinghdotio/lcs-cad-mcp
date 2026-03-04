# Story 1.5: Pydantic Input Validation Framework

Status: ready-for-dev

## Story

As a **developer**,
I want **all MCP tool inputs validated by Pydantic v2 schemas before execution**,
so that **malformed parameters return structured validation errors, not unhandled exceptions (NFR17)**.

## Acceptance Criteria

1. **AC1:** Every tool that accepts parameters defines a Pydantic v2 `BaseModel` as its input schema in the corresponding `modules/{name}/schemas.py`
2. **AC2:** Missing required parameters return a structured validation error: `{ "success": false, "data": null, "error": { "code": "VALIDATION_ERROR", "message": "<field> is required", "recoverable": true, "suggested_action": "..." } }`
3. **AC3:** Type coercion errors (e.g. string passed where int expected) return the same `VALIDATION_ERROR` envelope with a human-readable message
4. **AC4:** Validation errors always set `success: false`, `error.code: "VALIDATION_ERROR"`, and `recoverable: true` — they never trigger rollback
5. **AC5:** Tool parameter schemas are visible in MCP `tools/list` — FastMCP reflects the Pydantic model as JSON Schema in the tool descriptor

## Tasks / Subtasks

- [ ] Task 1: Establish Pydantic v2 schema conventions and base patterns (AC: 1, 5)
  - [ ] 1.1: Create `src/lcs_cad_mcp/modules/cad/schemas.py` with at least one real input model: `CadOpenDrawingInput(BaseModel)` with `path: str` and `read_only: bool = False`
  - [ ] 1.2: Add Pydantic `Field(...)` annotations with `description=` strings on all fields — this populates `tools/list` schema (AC5)
  - [ ] 1.3: Add a `model_config = ConfigDict(str_strip_whitespace=True, frozen=True)` to each schema model
  - [ ] 1.4: Add `CadPingInput(BaseModel)` with no fields as the schema for the `cad_ping` stub tool (demonstrates zero-arg schema pattern)
  - [ ] 1.5: Confirm that FastMCP reflects `CadOpenDrawingInput` fields in the `tools/list` JSON Schema output for the `cad_open_drawing` tool stub

- [ ] Task 2: Implement validation error handling and the `VALIDATION_ERROR` envelope (AC: 2, 3, 4)
  - [ ] 2.1: Create `src/lcs_cad_mcp/modules/cad/tools.py` with a `cad_open_drawing` async tool handler stub that accepts `CadOpenDrawingInput` as its parameter model
  - [ ] 2.2: Wrap the FastMCP tool registration so that `pydantic.ValidationError` is caught and converted to `MCPError(code=ErrorCode.VALIDATION_ERROR, message=..., recoverable=True).to_response()`
  - [ ] 2.3: Format the `message` field from Pydantic's `ValidationError.errors()` list as a human-readable string: `"field '<name>': <msg>"` — NOT a raw JSON dump
  - [ ] 2.4: Set `suggested_action` to `"Check parameter types and required fields per tools/list schema"` for all validation errors
  - [ ] 2.5: Write a unit test in `tests/unit/modules/cad/test_tools.py` that calls `cad_open_drawing` with a missing `path` and asserts the response matches the AC2 envelope exactly

- [ ] Task 3: Propagate the validation pattern to all 10 module `schemas.py` files (AC: 1)
  - [ ] 3.1: Create stub `schemas.py` files for all 10 modules (`cad`, `predcr`, `layers`, `entities`, `verification`, `config`, `area`, `autodcr`, `reports`, `workflow`) — each with at minimum one example input model relevant to the module's domain
  - [ ] 3.2: `predcr/schemas.py`: define `PredcrRunCheckInput(BaseModel)` with `drawing_path: str`, `authority_code: str`
  - [ ] 3.3: `layers/schemas.py`: define `LayerCreateInput(BaseModel)` with `name: str`, `color: int = 7`, `linetype: str = "CONTINUOUS"`
  - [ ] 3.4: `entities/schemas.py`: define `EntityQueryInput(BaseModel)` with `layer: str | None = None`, `entity_type: str | None = None`
  - [ ] 3.5: `verification/schemas.py`: define `VerifyClosureInput(BaseModel)` with `layer: str`, `tolerance: float = 0.001`
  - [ ] 3.6: `config/schemas.py`: define `ConfigLoadInput(BaseModel)` with `config_path: str`
  - [ ] 3.7: `area/schemas.py`: define `AreaCalculateInput(BaseModel)` with `layer: str`, `unit: Literal["sqm", "sqft"] = "sqm"`
  - [ ] 3.8: `autodcr/schemas.py`: define `AutodcrRunInput(BaseModel)` with `drawing_path: str`, `authority_code: str`, `output_path: str | None = None`
  - [ ] 3.9: `reports/schemas.py`: define `ReportGenerateInput(BaseModel)` with `report_type: Literal["pdf", "docx"]`, `output_path: str`
  - [ ] 3.10: `workflow/schemas.py`: define `WorkflowRunInput(BaseModel)` with `workflow_name: str`, `params: dict = Field(default_factory=dict)`

- [ ] Task 4: Implement a shared `validate_input` utility for consistent error formatting (AC: 2, 3, 4)
  - [ ] 4.1: Add a `validate_input(model_cls: type[BaseModel], raw: dict) -> tuple[BaseModel | None, dict | None]` function in `errors.py` (or a new `src/lcs_cad_mcp/utils.py`)
  - [ ] 4.2: The function attempts `model_cls(**raw)` and returns `(instance, None)` on success
  - [ ] 4.3: On `pydantic.ValidationError`, it returns `(None, MCPError(code=ErrorCode.VALIDATION_ERROR, ...).to_response())`
  - [ ] 4.4: The error message is built from `exc.errors()` list: concatenate all error messages as `"; ".join(f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}" for e in exc.errors())`
  - [ ] 4.5: Write unit tests for `validate_input` covering: valid input (returns model instance), missing field (returns error envelope), wrong type (returns error envelope)

- [ ] Task 5: Register the `cad_open_drawing` stub tool in `modules/cad/__init__.py` using the schema (AC: 1, 5)
  - [ ] 5.1: Import `CadOpenDrawingInput` from `modules/cad/schemas.py` inside `modules/cad/__init__.py`'s `register()` function
  - [ ] 5.2: Register `cad_open_drawing` as an `@mcp.tool()` handler that accepts `CadOpenDrawingInput` and returns `success_response({"path": inp.path, "read_only": inp.read_only, "status": "stub — not yet implemented"})` (placeholder)
  - [ ] 5.3: Confirm `tools/list` JSON Schema output for `cad_open_drawing` shows `path` (required) and `read_only` (optional, default false) fields
  - [ ] 5.4: Write a unit test asserting the `cad_open_drawing` schema has `path` as required and `read_only` as optional with default `False`

- [ ] Task 6: Write comprehensive validation tests (AC: 2, 3, 4, 5)
  - [ ] 6.1: Create `tests/unit/modules/cad/test_schemas.py` with tests for `CadOpenDrawingInput`: valid input, missing required field, wrong type for `read_only`, whitespace stripping on `path`
  - [ ] 6.2: Create `tests/unit/modules/layers/test_schemas.py` with tests for `LayerCreateInput`: valid input, color out-of-range (if validator added), linetype as enum (if constrained)
  - [ ] 6.3: Add a `hypothesis`-based property test in `tests/unit/test_validation_framework.py` using `st.text()` for path fields — assert server never raises an unhandled exception regardless of input
  - [ ] 6.4: Add a parametrized test covering all 10 `schemas.py` files asserting each exports at least one `BaseModel` subclass
  - [ ] 6.5: Run `pytest tests/unit/ -v` and confirm all tests pass

## Dev Notes

### Critical Architecture Constraints

1. **Pydantic models live in `schemas.py` only — never in `tools.py` or `service.py`.** The module layer contract is: `schemas.py` owns all Pydantic models, `tools.py` owns thin FastMCP handler wrappers, `service.py` owns business logic. This separation is enforced by the architecture and must not be violated.
2. **FastMCP 3.x natively accepts Pydantic v2 `BaseModel` subclasses as tool parameter types.** Use this directly: `async def my_tool(inp: MyInput) -> dict:` — do NOT manually call `model_validate()` in the tool handler body if FastMCP handles it. Confirm how FastMCP 3.x surfaces validation errors before deciding whether to add a manual `try/except ValidationError` wrapper or rely on the global handler from Story 1-4.
3. **`model_config = ConfigDict(frozen=True)` on all schema models** — tool input schemas must be immutable. This prevents accidental mutation inside `service.py` and makes schemas hashable for caching.
4. **`str_strip_whitespace=True` on all schema models** — all string fields automatically strip leading/trailing whitespace. This prevents common AI-client errors where the LLM adds a trailing space to a file path.
5. **All `Field(...)` annotations MUST include `description=`** — this populates the JSON Schema description in `tools/list`, which is the primary documentation surface for AI clients.
6. **`recoverable: true` is mandatory for all `VALIDATION_ERROR` responses.** Validation errors never trigger rollback. This is a hard contract — do not set `recoverable=False` on validation errors under any circumstance.
7. **FORBIDDEN:** `dict` as a raw tool parameter type (always use a Pydantic model), `Any` as a field type, skipping `Field(description=...)`, returning raw `pydantic.ValidationError` objects to the client.

### Module / Component Notes

**Pattern for every `schemas.py` file:**

```python
"""Pydantic v2 input/output schemas for the <name> module."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class SomeToolInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    required_field: str = Field(..., description="Human-readable description of what this field is.")
    optional_field: int = Field(7, description="Default value description.")
```

**Pattern for `tools.py` handler referencing schema:**

```python
"""Thin MCP tool handlers for the <name> module. Business logic lives in service.py."""
from fastmcp import Context
from lcs_cad_mcp.errors import MCPError, ErrorCode, success_response
from lcs_cad_mcp.modules.cad.schemas import CadOpenDrawingInput


async def cad_open_drawing(ctx: Context, inp: CadOpenDrawingInput) -> dict:
    """Step 1: Check session."""
    session = ctx.get_state("session")
    if session is None:
        return MCPError(
            code=ErrorCode.SESSION_NOT_STARTED,
            message="No active drawing session. Call cad_start_session first.",
            recoverable=True,
            suggested_action="Call cad_start_session to open a drawing.",
        ).to_response()
    # Steps 2-6 implemented in Epic 2 stories
    return success_response({"status": "stub"})
```

**`validate_input` utility in `errors.py` (or `utils.py`):**

```python
from pydantic import BaseModel, ValidationError


def validate_input(model_cls: type[BaseModel], raw: dict) -> tuple[BaseModel | None, dict | None]:
    """Parse and validate raw dict against a Pydantic model.

    Returns (instance, None) on success, (None, error_response_dict) on failure.
    """
    try:
        return model_cls(**raw), None
    except ValidationError as exc:
        msg = "; ".join(
            f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        return None, MCPError(
            code=ErrorCode.VALIDATION_ERROR,
            message=msg,
            recoverable=True,
            suggested_action="Check parameter types and required fields per tools/list schema.",
        ).to_response()
```

**`CadOpenDrawingInput` full definition (`modules/cad/schemas.py`):**

```python
"""Pydantic v2 input/output schemas for the cad module."""
from pydantic import BaseModel, Field, ConfigDict


class CadOpenDrawingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    path: str = Field(..., description="Absolute or relative path to the DXF/DWG file to open.")
    read_only: bool = Field(False, description="If true, open the drawing in read-only mode. No save operations are permitted.")


class CadPingInput(BaseModel):
    """Zero-argument schema for the cad_ping health check tool."""
    model_config = ConfigDict(frozen=True)
```

### Project Structure Notes

Files created or modified in this story:

```
src/lcs_cad_mcp/
├── errors.py                           # MODIFY: add validate_input() utility (or utils.py)
└── modules/
    ├── cad/
    │   ├── __init__.py                 # MODIFY: register cad_open_drawing with schema
    │   ├── tools.py                    # IMPLEMENT: cad_open_drawing stub handler
    │   └── schemas.py                  # IMPLEMENT: CadOpenDrawingInput, CadPingInput
    ├── predcr/
    │   └── schemas.py                  # IMPLEMENT: PredcrRunCheckInput
    ├── layers/
    │   └── schemas.py                  # IMPLEMENT: LayerCreateInput
    ├── entities/
    │   └── schemas.py                  # IMPLEMENT: EntityQueryInput
    ├── verification/
    │   └── schemas.py                  # IMPLEMENT: VerifyClosureInput
    ├── config/
    │   └── schemas.py                  # IMPLEMENT: ConfigLoadInput
    ├── area/
    │   └── schemas.py                  # IMPLEMENT: AreaCalculateInput
    ├── autodcr/
    │   └── schemas.py                  # IMPLEMENT: AutodcrRunInput
    ├── reports/
    │   └── schemas.py                  # IMPLEMENT: ReportGenerateInput
    └── workflow/
        └── schemas.py                  # IMPLEMENT: WorkflowRunInput

tests/unit/
├── test_validation_framework.py        # CREATE: hypothesis-based property tests
├── modules/
│   ├── __init__.py                     # CREATE (if not already exists)
│   └── cad/
│       ├── __init__.py                 # CREATE (if not already exists)
│       ├── test_schemas.py             # CREATE
│       └── test_tools.py              # CREATE
└── modules/layers/
    └── test_schemas.py                 # CREATE
```

The `tests/unit/modules/` subdirectory mirrors `src/lcs_cad_mcp/modules/` exactly. Each module gets its own test subdirectory created in this story (even if initially sparse), ready for Epic-specific tests later.

### Dependencies

- **Story 1-1** must be complete: `pyproject.toml` with `pydantic>=2.0`, all stub files present.
- **Story 1-2** must be complete: `mcp` FastMCP instance, `cad_ping` tool, all 10 `register()` stubs.
- **Story 1-4** must be complete: `MCPError`, `ErrorCode.VALIDATION_ERROR`, `success_response()` implemented and tested — this story builds directly on those.

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern (6-Step)"]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Module Layer Contract (schemas.py / tools.py / service.py)"]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Naming Patterns"]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Enforcement Guidelines"]
- [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 1, Story 1-5]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

- `src/lcs_cad_mcp/errors.py`
- `src/lcs_cad_mcp/modules/cad/__init__.py`
- `src/lcs_cad_mcp/modules/cad/tools.py`
- `src/lcs_cad_mcp/modules/cad/schemas.py`
- `src/lcs_cad_mcp/modules/predcr/schemas.py`
- `src/lcs_cad_mcp/modules/layers/schemas.py`
- `src/lcs_cad_mcp/modules/entities/schemas.py`
- `src/lcs_cad_mcp/modules/verification/schemas.py`
- `src/lcs_cad_mcp/modules/config/schemas.py`
- `src/lcs_cad_mcp/modules/area/schemas.py`
- `src/lcs_cad_mcp/modules/autodcr/schemas.py`
- `src/lcs_cad_mcp/modules/reports/schemas.py`
- `src/lcs_cad_mcp/modules/workflow/schemas.py`
- `tests/unit/test_validation_framework.py`
- `tests/unit/modules/__init__.py`
- `tests/unit/modules/cad/__init__.py`
- `tests/unit/modules/cad/test_schemas.py`
- `tests/unit/modules/cad/test_tools.py`
- `tests/unit/modules/layers/test_schemas.py`
