# Story 9.5: `autodcr_run_scrutiny` MCP Tool — Full Scrutiny Pass

Status: ready-for-dev

## Story

As an **AI client**, I want to run a full DCR scrutiny pass in a single tool call, so that the AI can produce a complete compliance result without making multiple rule-specific calls.

## Acceptance Criteria

1. **AC1:** `autodcr_run_scrutiny` MCP tool is registered in `src/lcs_cad_mcp/modules/autodcr/tools.py`; it calls `AutoDCRService.run_scrutiny()` which orchestrates the full pipeline: (a) verify config is loaded via `ConfigService.get_loaded_config()`, (b) compute all areas via `AreaService.compute_all()`, (c) evaluate all rules via `DCRRuleEvaluator().evaluate(computed_areas, loaded_config)`, (d) build `ScrutinyReport`, (e) archive via `repository.save_scrutiny_run()`, (f) return serialized `ScrutinyReport`.
2. **AC2:** `ScrutinyReport` returned by the tool includes: `run_id` (UUID string), `timestamp` (ISO8601), `config_hash` (SHA-256 hex digest of the loaded config file content), `rule_results: list[RuleResult]`, `overall_pass: bool`; also includes `area_table: dict` (the raw `computed_areas` dict) and `config_version_used: str` (from `DCRConfig.version`).
3. **AC3:** Full scrutiny pass (area computation + rule evaluation) completes within 30 seconds for drawings up to 50 layers and 10,000 entities (NFR3).
4. **AC4:** Results are fully reproducible: identical drawing file + identical config file always produce identical `rule_results` list and `overall_pass` value (NFR13); the `config_hash` stored in `ScrutinyReport` enables post-hoc verification that the same config was used.
5. **AC5:** `config_version_used` field in `ScrutinyReport` records the version string from the loaded `DCRConfig` (FR26).
6. **AC6:** `autodcr_run_scrutiny` works on both `ezdxf` and `com` backends — the tool delegates to `AreaService` which is backend-agnostic via the `CADBackend` abstraction.
7. **AC7:** If no config is loaded when `autodcr_run_scrutiny` is called, the tool returns `MCPError(code="CONFIG_NOT_LOADED", message="No DCR config loaded. Call config_load first.", recoverable=True)`.
8. **AC8:** If no drawing session is active, the tool returns `MCPError(code="SESSION_NOT_STARTED", message="No drawing session active. Call cad_open or cad_create first.", recoverable=True)`.
9. **AC9:** Integration test in `tests/integration/test_autodcr_scrutiny.py` with a mock drawing and mock config runs the full pipeline and verifies: (a) `ScrutinyReport` is returned, (b) `overall_pass` reflects the actual rule results, (c) archival is called with the report.

## Tasks / Subtasks

- [ ] Task 1: Implement `AutoDCRService.run_scrutiny()` in `src/lcs_cad_mcp/modules/autodcr/service.py` (AC: 1, 2, 4, 5)
  - [ ] 1.1: Import `ConfigService` from `modules.config.service`, `AreaService` from `modules.area.service`, `DCRRuleEvaluator` from `rule_engine.evaluator`, `save_scrutiny_run` from `archive.repository`, and `lcs_cad_mcp.rule_engine.checkers` (side-effect import to register all checkers)
  - [ ] 1.2: Implement `async def run_scrutiny(self, session_ctx: DrawingSessionContext, dry_run: bool = False) -> ScrutinyReport`
  - [ ] 1.3: Step 1 — load config: `loaded_config = ConfigService.get_loaded_config(session_ctx)`; if `None`, raise `MCPError(code="CONFIG_NOT_LOADED", ...)`
  - [ ] 1.4: Step 2 — compute config hash: `config_hash = hashlib.sha256(loaded_config.raw_yaml_bytes).hexdigest()` where `raw_yaml_bytes` is stored on the `DCRConfig` object when loaded (Epic 7)
  - [ ] 1.5: Step 3 — compute areas: `computed_areas = await AreaService(session_ctx).compute_all()`
  - [ ] 1.6: Step 4 — evaluate rules: `rule_results = DCRRuleEvaluator().evaluate(computed_areas, loaded_config)`; evaluation is synchronous (pure computation)
  - [ ] 1.7: Step 5 — build `ScrutinyReport`: generate `run_id = str(uuid.uuid4())`, `timestamp = datetime.utcnow()`, set all fields from AC2
  - [ ] 1.8: Step 6 — archive (if not dry_run): `if not dry_run: save_scrutiny_run(report, session_ctx)`; if `dry_run=True`, skip archival entirely
  - [ ] 1.9: Return `ScrutinyReport`

- [ ] Task 2: Define `ScrutinyReport` extended schema in `src/lcs_cad_mcp/modules/autodcr/schemas.py` (AC: 2, 5)
  - [ ] 2.1: Import base `ScrutinyReport` from `rule_engine.models`; define `AutoDCRScrutinyResponse` Pydantic model that wraps the report for MCP tool output: `success: bool`, `data: ScrutinyReport | None`, `error: dict | None`
  - [ ] 2.2: Extend `ScrutinyReport` (in `rule_engine/models.py`) to include `area_table: dict[str, float | int]` and `config_version_used: str` fields — add these fields with defaults to avoid breaking existing tests
  - [ ] 2.3: Add `config_hash: str` field to `ScrutinyReport` if not already present from Story 9-1

- [ ] Task 3: Implement `autodcr_run_scrutiny` MCP tool in `src/lcs_cad_mcp/modules/autodcr/tools.py` (AC: 1, 7, 8)
  - [ ] 3.1: Decorate with `@mcp.tool()` and name `"autodcr_run_scrutiny"`; parameters: none (uses session context from `ctx.get_state()`)
  - [ ] 3.2: Retrieve session context: `session_ctx = ctx.get_state("drawing_session")`; if `None`, return `MCPError(code="SESSION_NOT_STARTED", ...)`.to_response()`
  - [ ] 3.3: Instantiate `service = AutoDCRService()` and call `report = await service.run_scrutiny(session_ctx, dry_run=False)`
  - [ ] 3.4: Catch `MCPError` from service and return it via `.to_response()`
  - [ ] 3.5: On success, return `{"success": True, "data": report.model_dump(), "error": None}`

- [ ] Task 4: Implement `archive/repository.py` `save_scrutiny_run()` function (AC: 1)
  - [ ] 4.1: In `src/lcs_cad_mcp/archive/repository.py`, implement `def save_scrutiny_run(report: ScrutinyReport, session_ctx: DrawingSessionContext) -> None`
  - [ ] 4.2: Serialize `report` to JSON using `report.model_dump_json()`; write to `ARCHIVE_PATH/runs/{report.run_id}.json`
  - [ ] 4.3: If `ARCHIVE_PATH` directory does not exist, create it (use `Path.mkdir(parents=True, exist_ok=True)`)
  - [ ] 4.4: Wrap file write in a try/except; on failure, log warning but do NOT raise — archival failure must not abort the scrutiny result returned to the AI client

- [ ] Task 5: Register `autodcr` module tools in `__main__.py` (AC: 1)
  - [ ] 5.1: In `src/lcs_cad_mcp/__main__.py`, ensure `from lcs_cad_mcp.modules.autodcr import tools as autodcr_tools` is imported so all `autodcr_*` tools are registered with the FastMCP instance
  - [ ] 5.2: Ensure `import lcs_cad_mcp.rule_engine.checkers` appears in `AutoDCRService.__init__` or at module load time so all 5 checkers are registered before any scrutiny call

- [ ] Task 6: Write integration test in `tests/integration/test_autodcr_scrutiny.py` (AC: 9)
  - [ ] 6.1: Use `MockCADBackend` (from `conftest.py`) with a pre-built mock drawing that has known FSI, coverage, setbacks, parking, and height values
  - [ ] 6.2: Load a mock `DCRConfig` with one passing rule and one failing rule
  - [ ] 6.3: Call `AutoDCRService().run_scrutiny(mock_session_ctx, dry_run=True)` (dry_run to skip file archival in test)
  - [ ] 6.4: Assert `report.overall_pass == False` (due to the failing rule)
  - [ ] 6.5: Assert `len(report.rule_results) == 2`, one `status=="pass"` and one `status=="fail"`
  - [ ] 6.6: Assert `report.config_hash` is a non-empty 64-character hex string (SHA-256)
  - [ ] 6.7: Assert reproducibility: call `run_scrutiny()` again with the same inputs; assert the two reports have identical `rule_results` (by comparing `model_dump()` output)

- [ ] Task 7: Verify 30-second performance requirement (AC: 3)
  - [ ] 7.1: Add `@pytest.mark.timeout(30)` to the integration test (requires `pytest-timeout` in dev dependencies)
  - [ ] 7.2: Add `pytest-timeout` to `pyproject.toml` dev dependencies if not already present

## Dev Notes

### Critical Architecture Constraints

1. **Direct Python calls — no MCP-via-MCP**: `AutoDCRService.run_scrutiny()` calls `AreaService.compute_all()` and `DCRRuleEvaluator().evaluate()` as direct Python method calls. It does NOT use the MCP tool layer to call area computation tools. This is a hard architectural requirement.
2. **`dry_run` flag controls ONLY archival**: Dry-run mode skips `save_scrutiny_run()` but runs the full pipeline identically. The returned `ScrutinyReport` must be identical whether `dry_run=True` or `dry_run=False` (AC4 — NFR13 reproducibility).
3. **Checker registration at startup**: `import lcs_cad_mcp.rule_engine.checkers` must happen before the first `DCRRuleEvaluator().evaluate()` call. Place this import in `AutoDCRService.__init__` or at the top of `service.py` so it executes at module import time.
4. **`config_hash` must be stored with run**: The SHA-256 of the config file bytes is the audit trail linking each `ScrutinyReport` to the exact config used. This is required for the archival audit trail (NFR audit).
5. **`uuid.uuid4()` for `run_id`**: Use `import uuid; run_id = str(uuid.uuid4())`. Do NOT use timestamps as IDs — UUIDs are guaranteed unique even under concurrent runs.
6. **Archival failure must not block result**: If `save_scrutiny_run()` fails (e.g., disk full, permissions), the tool logs a warning but still returns the `ScrutinyReport` to the client. The AI receives the result regardless. This is the correct resilience posture.

### Module/Component Notes

- `AutoDCRService` lives at `src/lcs_cad_mcp/modules/autodcr/service.py`
- `autodcr_run_scrutiny` MCP tool lives at `src/lcs_cad_mcp/modules/autodcr/tools.py`
- `save_scrutiny_run()` lives at `src/lcs_cad_mcp/archive/repository.py`
- Session context is retrieved from FastMCP connection state via `ctx.get_state("drawing_session")` — this is the FastMCP 3.x session architecture
- `DCRRuleEvaluator` is stateless — instantiate per call with `DCRRuleEvaluator().evaluate()`
- `AreaService` is async (`compute_all()` is `async def`) because it may call the CAD backend; `AutoDCRService.run_scrutiny()` must therefore be `async def` and called with `await`

### MCP Tool API Reference

```
Tool name: autodcr_run_scrutiny
Parameters: none (uses session state)
Returns on success:
{
  "success": true,
  "data": {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-03-04T10:30:00Z",
    "config_hash": "a3f1c2d4...",
    "config_version_used": "MCGM-2024-v3",
    "overall_pass": false,
    "area_table": {"fsi": 2.3, "ground_coverage": 0.42, ...},
    "rule_results": [
      {
        "rule_id": "fsi-limit",
        "rule_name": "FSI Limit",
        "rule_type": "fsi",
        "status": "fail",
        "computed_value": 2.3,
        "permissible_value": 2.0,
        "deviation": 0.3,
        "unit": "ratio",
        "suggested_action": "Reduce built-up area by 300.00 sqm..."
      }
    ]
  },
  "error": null
}
```

### Project Structure Notes

```
src/lcs_cad_mcp/
├── modules/
│   └── autodcr/
│       ├── __init__.py
│       ├── tools.py          # autodcr_run_scrutiny MCP tool
│       ├── service.py        # AutoDCRService.run_scrutiny()
│       └── schemas.py        # AutoDCRScrutinyResponse
└── archive/
    └── repository.py         # save_scrutiny_run()

tests/
└── integration/
    └── test_autodcr_scrutiny.py  # NEW
```

### Dependencies

- Story 9-4: All 5 rule checkers registered and `DCRRuleEvaluator` functional
- Epic 7 (Story 7-2): `ConfigService.get_loaded_config()` and `DCRConfig` with `raw_yaml_bytes` and `version` fields
- Epic 8 (Story 8-4): `AreaService.compute_all()` returning complete `computed_areas` dict
- Story 1-1: `archive/repository.py` stub exists; `ARCHIVE_PATH` setting defined in `Settings`
- Epic 5 (Entity Management): used by `AreaService` for entity querying — no direct dependency from this story

### References

- FR21 (full scrutiny in single call): `_bmad-output/planning-artifacts/epics-and-stories.md`
- FR26 (config version in report): `_bmad-output/planning-artifacts/epics-and-stories.md`
- NFR3 (30-second performance): `_bmad-output/planning-artifacts/epics-and-stories.md`
- NFR13 (reproducibility): `_bmad-output/planning-artifacts/epics-and-stories.md`
- Epic 9 stories: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 9, Story 9-5
- FastMCP 3.x session state: architecture doc section "Session Architecture"

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/autodcr/service.py`
- `src/lcs_cad_mcp/modules/autodcr/tools.py`
- `src/lcs_cad_mcp/modules/autodcr/schemas.py`
- `src/lcs_cad_mcp/rule_engine/models.py` (updated: `area_table`, `config_version_used`, `config_hash` fields)
- `src/lcs_cad_mcp/archive/repository.py`
- `src/lcs_cad_mcp/__main__.py` (updated: autodcr tools import)
- `tests/integration/test_autodcr_scrutiny.py`
