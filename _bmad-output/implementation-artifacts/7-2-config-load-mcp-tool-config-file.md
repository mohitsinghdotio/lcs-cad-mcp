# Story 7.2: `config_load` MCP Tool — Config File Loader

Status: ready-for-dev

## Story

As an **AI client**,
I want **to load a DCR rule config file from a custom file path**,
so that **any authority's rules can be activated without code changes and the scrutiny engine always operates against a validated, versioned config** (FR19, FR42).

## Acceptance Criteria

1. **AC1:** `config_load(config_path: str)` MCP tool loads and parses a YAML or JSON DCR rule config file from the given path; if `config_path` is omitted, falls back to `DCR_CONFIG_PATH` env var.
2. **AC2:** `DCR_CONFIG_PATH` env var sets the default config path (FR42); if neither `config_path` nor the env var is set, returns a structured error `CONFIG_PATH_NOT_SET`.
3. **AC3:** Config is validated against the `DCRConfig` Pydantic schema on load (FR20); validation errors surface as field-level structured errors — not raw exceptions.
4. **AC4:** Schema validation errors are returned as `{"success": false, "error": {"code": "CONFIG_INVALID", "fields": [...], "message": "..."}}` with per-field detail.
5. **AC5:** Config files are opened in read-only mode — the loader never writes to the config file (NFR23).
6. **AC6:** Successful load returns: `{"success": true, "data": {"version": "...", "authority": "...", "rule_count": N, "zone_count": N, "config_hash": "<sha256>"}}`
7. **AC7:** Loaded `DCRConfig` object and its SHA-256 content hash are stored in session state (`ctx.set_state`) for use by downstream tools (evaluator, reporter).
8. **AC8:** Tool handler follows the 6-step pattern: (1) get session, (2) validate inputs, (3) no snapshot needed (read-only op), (4) `service.load_config()`, (5) event_log entry, (6) return response.

## Tasks / Subtasks

- [ ] Task 1: Implement `rule_engine/loader.py` — YAML/JSON file parser (AC: 1, 5)
  - [ ] 1.1: Create `load_raw(path: Path) -> dict` function that reads the file in read-only mode (`open(path, "r")`) and parses YAML (via `yaml.safe_load`) or JSON (via `json.load`) based on file extension (`.yaml`, `.yml`, `.json`)
  - [ ] 1.2: Raise `FileNotFoundError` with clear message if path does not exist; raise `ValueError` with message if file extension is unsupported
  - [ ] 1.3: Preserve dict insertion order — `yaml.safe_load` and `json.load` both use Python `dict` which preserves order (3.7+); add inline comment confirming this (NFR13)
  - [ ] 1.4: Return raw `dict` — do not instantiate Pydantic models in the loader (separation of concerns; validator does that)

- [ ] Task 2: Implement `rule_engine/validator.py` — Pydantic schema validation + hash (AC: 3, 4, 7)
  - [ ] 2.1: Create `validate(raw: dict) -> DCRConfig` function that calls `DCRConfig.model_validate(raw)` and re-raises `pydantic.ValidationError` as a structured list of `{field, message}` dicts
  - [ ] 2.2: Create `compute_hash(path: Path) -> str` function that reads the file as bytes and returns `hashlib.sha256(content).hexdigest()`
  - [ ] 2.3: Create `validate_and_hash(path: Path) -> tuple[DCRConfig, str]` convenience function combining loader + validator + hash in one call
  - [ ] 2.4: Ensure `ValidationError` from Pydantic is caught and converted to `ConfigValidationError` (a local exception class with `errors: list[dict]` attribute) — never let raw Pydantic errors leak to MCP response

- [ ] Task 3: Implement `modules/config/service.py` — `ConfigService` (AC: 1, 6, 7)
  - [ ] 3.1: Create `ConfigService` class with `load_config(path: str | Path) -> dict` method
  - [ ] 3.2: Delegate to `rule_engine.validator.validate_and_hash(path)` to get `(dcr_config, content_hash)`
  - [ ] 3.3: Return a summary dict: `{"version": ..., "authority": ..., "rule_count": ..., "zone_count": ..., "config_hash": ...}` — do NOT store state in the service (stateless service, state lives in session)
  - [ ] 3.4: Add `get_active_config(ctx) -> DCRConfig | None` class method that retrieves the stored `DCRConfig` from session state key `"active_dcr_config"`

- [ ] Task 4: Implement `modules/config/tools.py` — `config_load` MCP tool handler (AC: 1, 2, 4, 6, 8)
  - [ ] 4.1: Register `config_load` tool with FastMCP using `@mcp.tool(name="config_load")` in `modules/config/__init__.py`
  - [ ] 4.2: Tool signature: `async def config_load(ctx: Context, config_path: str = "") -> dict`
  - [ ] 4.3: Step 1 — get session from `ctx.get_state("session")`; if no session, return `ErrorCode.SESSION_NOT_STARTED`
  - [ ] 4.4: Step 2 — resolve path: use `config_path` if provided, else `settings.dcr_config_path`, else return `CONFIG_PATH_NOT_SET` error
  - [ ] 4.5: Step 3 — no snapshot (read-only operation)
  - [ ] 4.6: Step 4 — call `ConfigService().load_config(resolved_path)`; catch `FileNotFoundError` → `CONFIG_NOT_FOUND` error; catch `ConfigValidationError` → `CONFIG_INVALID` error with field-level details
  - [ ] 4.7: Step 5 — write event log entry: `{"event": "config_loaded", "path": str(resolved_path), "hash": config_hash, "rule_count": N}`
  - [ ] 4.8: Step 6 — store `DCRConfig` object in session via `ctx.set_state("active_dcr_config", dcr_config)` and `ctx.set_state("active_config_hash", config_hash)`; return success response

- [ ] Task 5: Update `modules/config/schemas.py` — input/output Pydantic models (AC: 3, 6)
  - [ ] 5.1: Create `ConfigLoadInput(BaseModel)`: `config_path: str = ""`
  - [ ] 5.2: Create `ConfigLoadResult(BaseModel)`: `version: str`, `authority: str`, `rule_count: int`, `zone_count: int`, `config_hash: str`
  - [ ] 5.3: Create `ConfigValidationFieldError(BaseModel)`: `field: str`, `message: str`
  - [ ] 5.4: Create `ConfigLoadError(BaseModel)`: `code: str`, `message: str`, `fields: list[ConfigValidationFieldError] = []`

- [ ] Task 6: Add `ErrorCode` constants for config errors in `errors.py` (AC: 2, 4)
  - [ ] 6.1: Add `CONFIG_PATH_NOT_SET = "CONFIG_PATH_NOT_SET"` to `ErrorCode` class
  - [ ] 6.2: Add `CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"` to `ErrorCode` class
  - [ ] 6.3: Verify `CONFIG_INVALID = "CONFIG_INVALID"` already exists from Story 1-4 stub; add if missing

- [ ] Task 7: Write unit tests for loader, validator, and tool (AC: 1, 3, 4)
  - [ ] 7.1: `tests/unit/rule_engine/test_loader.py` — test YAML load, JSON load, file-not-found error, unsupported extension error
  - [ ] 7.2: `tests/unit/rule_engine/test_validator.py` — test valid config parses to `DCRConfig`, test invalid config raises `ConfigValidationError` with correct `errors` list, test `compute_hash` returns 64-char hex string
  - [ ] 7.3: `tests/unit/modules/config/test_config_tool.py` — mock `ConfigService`, test success response shape, test `CONFIG_PATH_NOT_SET` path, test `CONFIG_INVALID` response includes field errors

## Dev Notes

### Critical Architecture Constraints

1. **6-step tool handler pattern** — every MCP tool handler in this project follows exactly: (1) session, (2) validate, (3) snapshot if write, (4) service.method(), (5) event_log, (6) return. Step 3 is skipped for read-only operations like `config_load`.
2. **Stateless `ConfigService`** — the service never holds instance state. `DCRConfig` is stored in the FastMCP session via `ctx.set_state()` / `ctx.get_state()`. This is the connection-scoped session model from FastMCP 3.x (not per-request, not global).
3. **YAML insertion order must be preserved** — `yaml.safe_load` returns a plain Python `dict` which preserves insertion order in Python 3.7+. Do NOT use `yaml.load` with custom Loaders that sort keys. Add a comment in `loader.py`: `# PyYAML safe_load preserves insertion order (Python dict 3.7+) — required for NFR13 determinism`.
4. **SHA-256 hash of file content** — always hash the raw file bytes (`path.read_bytes()`), not the parsed dict. This ensures the hash is stable across YAML/JSON serialization differences and captures any whitespace/comment changes.
5. **Read-only file access** — use `open(path, "r")` or `path.read_text()`. Never use write modes. Add `# read-only: NFR23` comment at each file open call.
6. **MCP tool prefix** — all tools in `modules/config/` use the `config_` prefix. Tool name is `config_load` (not `load_config`).

### Module/Component Notes

**`rule_engine/loader.py` skeleton:**

```python
import json
from pathlib import Path
import yaml  # PyYAML


def load_raw(path: Path) -> dict:
    """Load YAML or JSON config file as raw dict.

    # PyYAML safe_load preserves insertion order (Python dict 3.7+) — required for NFR13 determinism
    # read-only: NFR23
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    ext = path.suffix.lower()
    with open(path, "r") as f:  # read-only: NFR23
        if ext in (".yaml", ".yml"):
            return yaml.safe_load(f)
        elif ext == ".json":
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config file extension: {ext}. Use .yaml, .yml, or .json")
```

**`rule_engine/validator.py` skeleton:**

```python
import hashlib
from pathlib import Path
from pydantic import ValidationError as PydanticValidationError
from .loader import load_raw
from .models import DCRConfig


class ConfigValidationError(Exception):
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(f"Config validation failed with {len(errors)} error(s)")


def compute_hash(path: Path) -> str:
    """SHA-256 of raw file bytes — stable regardless of parse/serialization."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(raw: dict) -> DCRConfig:
    try:
        return DCRConfig.model_validate(raw)
    except PydanticValidationError as e:
        errors = [{"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
                  for err in e.errors()]
        raise ConfigValidationError(errors) from e


def validate_and_hash(path: Path) -> tuple[DCRConfig, str]:
    raw = load_raw(path)
    config = validate(raw)
    content_hash = compute_hash(path)
    return config, content_hash
```

**Session state keys for config:**

| Key | Type | Set by |
|-----|------|--------|
| `"active_dcr_config"` | `DCRConfig` | `config_load` tool |
| `"active_config_hash"` | `str` (SHA-256 hex) | `config_load` tool |

These keys are consumed by `autodcr_run_scrutiny` (Epic 9) and `report_generate_*` tools (Epic 10).

### Project Structure Notes

Files to create or modify in this story:

```
src/lcs_cad_mcp/
├── errors.py                            # Update: add CONFIG_PATH_NOT_SET, CONFIG_NOT_FOUND
├── rule_engine/
│   ├── loader.py                        # Implement: load_raw()
│   └── validator.py                     # Implement: validate(), compute_hash(), validate_and_hash()
└── modules/config/
    ├── __init__.py                      # Update: register config_load tool
    ├── tools.py                         # Implement: async config_load handler
    ├── service.py                       # Implement: ConfigService
    └── schemas.py                       # Implement: ConfigLoadInput, ConfigLoadResult, etc.

tests/unit/
├── rule_engine/
│   ├── test_loader.py                   # New
│   └── test_validator.py               # New
└── modules/config/
    ├── __init__.py                      # Create if not exists
    └── test_config_tool.py             # New
```

### Dependencies

- **Story 7-1** — `DCRConfig`, `DCRRule`, `RuleType` models must exist in `rule_engine/models.py` before this story begins.
- **Story 1-4** — `ErrorCode` and `MCPError` base infrastructure from `errors.py` must be in place.
- **Story 1-2** — FastMCP server instance and `ctx.set_state()` / `ctx.get_state()` session pattern must be established.
- `PyYAML` must be available — verify it is listed in `pyproject.toml` dependencies (add `"pyyaml"` if missing from Story 1-1 setup).

### References

- Architecture rule engine loader: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Rule Engine: loader.py"]
- 6-step tool handler pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- NFR23 (read-only config): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- NFR13 (determinism / insertion order): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- FastMCP 3.x session state: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Session Architecture"]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 7, Story 7-2]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/rule_engine/loader.py`
- `src/lcs_cad_mcp/rule_engine/validator.py`
- `src/lcs_cad_mcp/modules/config/__init__.py`
- `src/lcs_cad_mcp/modules/config/tools.py`
- `src/lcs_cad_mcp/modules/config/service.py`
- `src/lcs_cad_mcp/modules/config/schemas.py`
- `src/lcs_cad_mcp/errors.py` (updated)
- `tests/unit/rule_engine/test_loader.py`
- `tests/unit/rule_engine/test_validator.py`
- `tests/unit/modules/config/__init__.py`
- `tests/unit/modules/config/test_config_tool.py`
