# Story 7.3: `config_validate` and `config_get_version` MCP Tools

Status: ready-for-dev

## Story

As an **AI client**,
I want **to validate a config file without loading it and retrieve version metadata of the active config**,
so that **config errors are caught before a scrutiny run begins and the active rule set is always auditable** (FR20, FR26).

## Acceptance Criteria

1. **AC1:** `config_validate(config_path: str)` validates a YAML/JSON config file against the `DCRConfig` Pydantic schema without storing the config into session state — a pure dry-run.
2. **AC2:** `config_validate` returns `{"valid": bool, "errors": list[{"field": str, "message": str}]}` — empty `errors` list when `valid: true`.
3. **AC3:** `config_get_version()` returns the version string, authority name, and SHA-256 checksum of the currently loaded (active) config.
4. **AC4:** `config_get_version()` returns a `CONFIG_NOT_LOADED` error (not an exception) if no config has been loaded in the current session.
5. **AC5:** Config version string and hash from `config_get_version()` are recorded in every scrutiny run result (FR26) — the tool provides the data; the scrutiny engine (Epic 9) records it.
6. **AC6:** `config_list_rules()` MCP tool returns all rule IDs and names in the currently loaded config as an ordered list (preserving YAML insertion order).
7. **AC7:** All three tool handlers follow the 6-step pattern: (1) session, (2) validate inputs, (3) no snapshot (read-only), (4) service method, (5) event_log, (6) return response.

## Tasks / Subtasks

- [ ] Task 1: Implement `config_validate` tool handler in `modules/config/tools.py` (AC: 1, 2, 7)
  - [ ] 1.1: Tool signature: `async def config_validate(ctx: Context, config_path: str) -> dict`
  - [ ] 1.2: Step 1 — get session; no session required for validate (it's a pure file check — skip session gate or make it optional based on architecture decision; document choice in code comment)
  - [ ] 1.3: Step 2 — validate that `config_path` is a non-empty string; return `INVALID_PARAMS` if empty
  - [ ] 1.4: Step 4 — call `ConfigService().validate_only(config_path)`; catch `FileNotFoundError` → return `{"valid": false, "errors": [{"field": "config_path", "message": "File not found: ..."}]}`
  - [ ] 1.5: Step 5 — write event log entry: `{"event": "config_validated", "path": config_path, "valid": bool}`
  - [ ] 1.6: Step 6 — return `{"valid": true, "errors": []}` on success, or `{"valid": false, "errors": [...]}` on validation failure

- [ ] Task 2: Implement `config_get_version` tool handler in `modules/config/tools.py` (AC: 3, 4, 5, 7)
  - [ ] 2.1: Tool signature: `async def config_get_version(ctx: Context) -> dict`
  - [ ] 2.2: Step 1 — get session; return `SESSION_NOT_STARTED` if no session
  - [ ] 2.3: Step 2/4 — call `ConfigService.get_active_config(ctx)` to retrieve `DCRConfig` from session state; if `None`, return `CONFIG_NOT_LOADED` error
  - [ ] 2.4: Step 4 — retrieve `active_config_hash` from `ctx.get_state("active_config_hash")`
  - [ ] 2.5: Step 5 — event log: `{"event": "config_version_queried", "version": ..., "hash": ...}`
  - [ ] 2.6: Step 6 — return `{"version": ..., "authority": ..., "rule_count": N, "zone_count": N, "config_hash": "...", "effective_date": "..."}`

- [ ] Task 3: Implement `config_list_rules` tool handler in `modules/config/tools.py` (AC: 6, 7)
  - [ ] 3.1: Tool signature: `async def config_list_rules(ctx: Context) -> dict`
  - [ ] 3.2: Step 1 — get session; return `SESSION_NOT_STARTED` if no session
  - [ ] 3.3: Step 4 — retrieve active `DCRConfig`; if `None`, return `CONFIG_NOT_LOADED` error
  - [ ] 3.4: Step 4 — build ordered list from `[{"rule_id": r.rule_id, "name": r.name, "rule_type": r.rule_type, "zones": r.zone_applicability} for r in dcr_config.rules]` — preserves insertion order from loaded YAML (NFR13)
  - [ ] 3.5: Step 5 — event log: `{"event": "config_rules_listed", "rule_count": N}`
  - [ ] 3.6: Step 6 — return `{"rules": [...], "rule_count": N, "config_version": "..."}`

- [ ] Task 4: Add `validate_only` method to `ConfigService` in `modules/config/service.py` (AC: 1, 2)
  - [ ] 4.1: `validate_only(path: str | Path) -> dict` method that calls `rule_engine.loader.load_raw()` + `rule_engine.validator.validate()` but does NOT call `compute_hash()` and does NOT store anything in session
  - [ ] 4.2: On `ConfigValidationError`, return `{"valid": False, "errors": error.errors}` — structured, not raised
  - [ ] 4.3: On `FileNotFoundError`, re-raise (let the tool handler catch it)
  - [ ] 4.4: On success, return `{"valid": True, "errors": []}` — the tool handler returns this directly

- [ ] Task 5: Add `ErrorCode` constant and register tools in `__init__.py` (AC: 4, 6)
  - [ ] 5.1: Add `CONFIG_NOT_LOADED = "CONFIG_NOT_LOADED"` to `ErrorCode` in `errors.py`
  - [ ] 5.2: Register `config_validate`, `config_get_version`, and `config_list_rules` in `modules/config/__init__.py` using `@mcp.tool()` decorator pattern
  - [ ] 5.3: Ensure all three tool names use `config_` prefix: `config_validate`, `config_get_version`, `config_list_rules`

- [ ] Task 6: Add output schemas in `modules/config/schemas.py` (AC: 2, 3, 6)
  - [ ] 6.1: Create `ConfigValidateResult(BaseModel)`: `valid: bool`, `errors: list[ConfigValidationFieldError]`
  - [ ] 6.2: Create `ConfigVersionResult(BaseModel)`: `version: str`, `authority: str`, `rule_count: int`, `zone_count: int`, `config_hash: str`, `effective_date: str`
  - [ ] 6.3: Create `RuleSummary(BaseModel)`: `rule_id: str`, `name: str`, `rule_type: str`, `zones: list[str]`
  - [ ] 6.4: Create `ConfigListRulesResult(BaseModel)`: `rules: list[RuleSummary]`, `rule_count: int`, `config_version: str`

- [ ] Task 7: Write unit and integration tests (AC: 1, 2, 3, 4, 6)
  - [ ] 7.1: `tests/unit/modules/config/test_config_validate_tool.py` — test valid file returns `{"valid": true, "errors": []}`, invalid file returns `{"valid": false, "errors": [...]}`, missing file returns file-not-found error, empty path returns `INVALID_PARAMS`
  - [ ] 7.2: `tests/unit/modules/config/test_config_get_version_tool.py` — test with active config in session returns correct version + hash, test with no loaded config returns `CONFIG_NOT_LOADED`
  - [ ] 7.3: `tests/unit/modules/config/test_config_list_rules_tool.py` — test rule ordering matches YAML order (NFR13), test with no loaded config returns `CONFIG_NOT_LOADED`

## Dev Notes

### Critical Architecture Constraints

1. **`config_validate` must NOT modify session state** — it is a pure dry-run. No `ctx.set_state()` calls. The loaded `DCRConfig` object is constructed, validated, then discarded. Add inline comment `# dry-run: no session state mutation`.
2. **Insertion order is a correctness requirement (NFR13)** — `config_list_rules` must return rules in the same order as they appear in the YAML/JSON file. Use `[r for r in dcr_config.rules]` — do NOT sort, group, or reorder. The `DCRConfig.rules` field is a `list[DCRRule]`, preserving order by design.
3. **`config_get_version` is the audit anchor (FR26)** — the version string + hash returned by this tool are what the AutoDCR scrutiny engine records in every `ScrutinyRun` archive record. The hash proves which exact config was active during a run.
4. **6-step pattern strictly** — even for read-only tools. Steps 3 (snapshot) is explicitly skipped but must be noted with a comment: `# Step 3: skipped — read-only operation, no snapshot required`.
5. **Tool registration pattern** — all three tools must be registered in `modules/config/__init__.py` via the `register(mcp)` function pattern. The `__init__.py` must export a `register` function that takes the FastMCP `mcp` instance and decorates all handlers.
6. **Error returns, not exceptions** — tool handlers must NEVER raise exceptions to the MCP layer. All errors are caught internally and returned as structured dicts with `{"success": false, "error": {...}}` shape.

### Module/Component Notes

**`modules/config/__init__.py` registration pattern:**

```python
from fastmcp import FastMCP
from .tools import config_load, config_validate, config_get_version, config_list_rules


def register(mcp: FastMCP) -> None:
    """Register all config module tools with the FastMCP server."""
    mcp.tool(name="config_load")(config_load)
    mcp.tool(name="config_validate")(config_validate)
    mcp.tool(name="config_get_version")(config_get_version)
    mcp.tool(name="config_list_rules")(config_list_rules)
```

**`config_validate` tool response contract:**

```python
# Success:
{"valid": True, "errors": []}

# Validation failure:
{"valid": False, "errors": [
    {"field": "rules[0].threshold", "message": "Value must be >= 0"},
    {"field": "rules[1].zone_applicability", "message": "List must have at least 1 item"}
]}

# File not found:
{"valid": False, "errors": [
    {"field": "config_path", "message": "Config file not found: /path/to/file.yaml"}
]}
```

**`config_get_version` tool response contract:**

```python
# Success:
{
    "success": True,
    "data": {
        "version": "1.2.0",
        "authority": "MCGM Mumbai",
        "rule_count": 12,
        "zone_count": 4,
        "config_hash": "a3f4b2c1d9e8...",  # 64-char SHA-256 hex
        "effective_date": "2026-01-01"
    }
}

# No config loaded:
{
    "success": False,
    "error": {"code": "CONFIG_NOT_LOADED", "message": "No DCR config is loaded. Call config_load() first."}
}
```

**`config_list_rules` tool response contract:**

```python
{
    "success": True,
    "data": {
        "rules": [
            {"rule_id": "FSI-R1", "name": "FSI Residential Zone 1", "rule_type": "FSI", "zones": ["R1"]},
            {"rule_id": "GC-R1", "name": "Ground Coverage R1", "rule_type": "GROUND_COVERAGE", "zones": ["R1", "R2"]}
            # ... in YAML insertion order
        ],
        "rule_count": 12,
        "config_version": "1.2.0"
    }
}
```

### Project Structure Notes

Files to create or modify in this story:

```
src/lcs_cad_mcp/
├── errors.py                          # Update: add CONFIG_NOT_LOADED
└── modules/config/
    ├── __init__.py                    # Update: register config_validate, config_get_version, config_list_rules
    ├── tools.py                       # Update: add config_validate, config_get_version, config_list_rules handlers
    ├── service.py                     # Update: add validate_only() method
    └── schemas.py                     # Update: add ConfigValidateResult, ConfigVersionResult, RuleSummary, ConfigListRulesResult

tests/unit/modules/config/
├── test_config_validate_tool.py       # New
├── test_config_get_version_tool.py    # New
└── test_config_list_rules_tool.py     # New
```

**Note:** `modules/config/service.py` `ConfigService` must remain stateless. All state retrieved/stored through `ctx` (FastMCP session). The `validate_only` method does not accept a `ctx` argument.

### Dependencies

- **Story 7-2** — `ConfigService`, `rule_engine/loader.py`, `rule_engine/validator.py`, and `config_load` tool must be complete. The `ConfigValidationError` class, `validate_and_hash()` function, and `active_dcr_config` / `active_config_hash` session state keys are all established in Story 7-2.
- **Story 1-4** — `ErrorCode` constants and `MCPError` must be established.
- **Story 1-2** — FastMCP server + session architecture (`ctx.get_state` / `ctx.set_state`) must be in place.

### References

- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 7, Story 7-3]
- FR26 (config version tracking): [Source: `_bmad-output/planning-artifacts/architecture.md` — FR section]
- NFR13 (determinism / ordering): [Source: `_bmad-output/planning-artifacts/architecture.md` — NFR section]
- 6-step tool pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- MCP tool naming (`config_` prefix): [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Naming Patterns"]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/config/__init__.py` (updated)
- `src/lcs_cad_mcp/modules/config/tools.py` (updated)
- `src/lcs_cad_mcp/modules/config/service.py` (updated)
- `src/lcs_cad_mcp/modules/config/schemas.py` (updated)
- `src/lcs_cad_mcp/errors.py` (updated)
- `tests/unit/modules/config/test_config_validate_tool.py`
- `tests/unit/modules/config/test_config_get_version_tool.py`
- `tests/unit/modules/config/test_config_list_rules_tool.py`
