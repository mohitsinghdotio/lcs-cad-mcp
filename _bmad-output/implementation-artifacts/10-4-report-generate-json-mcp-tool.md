# Story 10.4: `report_generate_json` MCP Tool

Status: ready-for-dev

## Story

As an **AI client**,
I want **to generate a structured JSON compliance report from a completed scrutiny session**,
so that **scrutiny results can be consumed programmatically by downstream systems and stored as a machine-readable archive artifact (FR29)**.

## Acceptance Criteria

1. **AC1:** `report_generate_json(output_path: str | None = None)` MCP tool registered under the `reports` module, callable without arguments (auto-generates path under `ARCHIVE_PATH`).
2. **AC2:** JSON output is the direct serialization of the `ComplianceReport` Pydantic model — all fields included: `project_name`, `date`, `config_version`, `config_hash`, `rule_set_name`, `area_table`, `rule_results`, `overall_status`, `remediation_hints`, `metadata`.
3. **AC3:** JSON schema is stable — field names do not change between runs for the same config version; no dynamic or runtime-generated field names.
4. **AC4:** JSON is pretty-printed with 2-space indentation (`indent=2` in `json.dumps()`).
5. **AC5:** JSON includes all computed values at full float precision in `computed_value` fields; `display_value` strings (4dp) also present in `area_table` entries per `AreaEntry` model.
6. **AC6:** JSON generation completes within 30 seconds (NFR5) — in practice should be near-instant for any realistic report size.
7. **AC7:** Tool returns `{"success": True, "data": {"file_path": "<absolute_path>", "overall_status": "...", "rule_count": N}}` on success; `MCPError` on failure.
8. **AC8:** `report_get_remediation_suggestions(rule_id: str)` MCP tool returns per-rule remediation hint text from the current session's compliance report; returns `{"found": False}` if rule not in report.

## Tasks / Subtasks

- [ ] Task 1: Implement `ReportService.generate_json()` in `service.py` using stdlib `json` (AC: 2, 3, 4, 5)
  - [ ] 1.1: Add `generate_json(self, report: ComplianceReport, output_path: str) -> str` method to `ReportService`
  - [ ] 1.2: Serialize the report: `report_dict = report.model_dump(mode="json")`; this uses Pydantic v2's `model_dump(mode="json")` which converts all types to JSON-serializable primitives (floats stay as floats, strings as strings)
  - [ ] 1.3: Write to file: `json_str = json.dumps(report_dict, indent=2, ensure_ascii=False)`; write to `output_path` with `encoding="utf-8"`
  - [ ] 1.4: Return resolved absolute path string; verify file is readable JSON by calling `json.loads(json_str)` as a sanity check before returning

- [ ] Task 2: Implement `report_generate_json` MCP tool handler in `tools.py` (AC: 1, 6, 7)
  - [ ] 2.1: Define `@mcp.tool()` decorated async function `report_generate_json(ctx: Context, output_path: str | None = None) -> dict`
  - [ ] 2.2: Step 1 — retrieve session: `session = ctx.get_state("session")`; if missing return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 2.3: Step 2 — validate `output_path` if provided: ensure parent exists and suffix is `.json`; if `None`, auto-generate using `ARCHIVE_PATH / f"{session.project_name}_{timestamp}.json"`
  - [ ] 2.4: Step 3 — retrieve cached `ComplianceReport`: `report = ctx.get_state("compliance_report")`; if not present, call `ReportService(session).assemble_report_data(session.scrutiny_report)` and cache via `ctx.set_state("compliance_report", report)`
  - [ ] 2.5: Step 4 — call `ReportService(session).generate_json(report, output_path)`; capture returned path
  - [ ] 2.6: Step 5 — log event: `session.event_log.append({"tool": "report_generate_json", "output_path": str(output_path), "rule_count": len(report.rule_results)})`
  - [ ] 2.7: Step 6 — return `{"success": True, "data": {"file_path": str(output_path), "overall_status": report.overall_status, "rule_count": len(report.rule_results)}}`

- [ ] Task 3: Implement `report_get_remediation_suggestions` MCP tool handler in `tools.py` (AC: 8)
  - [ ] 3.1: Define `@mcp.tool()` decorated async function `report_get_remediation_suggestions(ctx: Context, rule_id: str) -> dict`
  - [ ] 3.2: Step 1 — retrieve session: `session = ctx.get_state("session")`; if missing return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 3.3: Step 2 — validate `rule_id`: non-empty string; return `MCPError(INVALID_PARAMS)` if blank
  - [ ] 3.4: Step 3 — retrieve cached `ComplianceReport` from `ctx.get_state("compliance_report")`; if not present return `MCPError` with message "No compliance report in session — run scrutiny and generate a report first"
  - [ ] 3.5: Step 4 — search `report.remediation_hints` for entry with `hint.rule_id == rule_id`; if found return `hint.model_dump()`; if not found return `{"found": False, "rule_id": rule_id, "note": "Rule not in remediation list (may be a PASS rule)"}`
  - [ ] 3.6: Step 5 — log: `session.event_log.append({"tool": "report_get_remediation_suggestions", "rule_id": rule_id, "found": found})`
  - [ ] 3.7: Step 6 — return `{"success": True, "data": result_dict}`

- [ ] Task 4: Add both tools to `register()` in `tools.py` (AC: 1, 8)
  - [ ] 4.1: Ensure `register(mcp: FastMCP) -> None` in `tools.py` binds both `report_generate_json` and `report_get_remediation_suggestions` to the `mcp` instance (note: `report_get_remediation_suggestions` may already be partially stubbed from Story 10-1 — promote the full implementation here)
  - [ ] 4.2: Confirm both tools appear in server tool list at startup

- [ ] Task 5: Write unit tests (AC: 6, 7, 8)
  - [ ] 5.1: Create `tests/unit/modules/reports/test_generate_json.py`
  - [ ] 5.2: Test `generate_json()` with mock `ComplianceReport`: load the written file with `json.loads()`, assert all top-level keys present (`project_name`, `date`, `config_version`, `config_hash`, `rule_set_name`, `area_table`, `rule_results`, `overall_status`, `remediation_hints`, `metadata`)
  - [ ] 5.3: Test JSON field stability: call `generate_json()` twice with identical input; assert both output files have identical key sets (field names must not change)
  - [ ] 5.4: Test pretty-print format: read file content as string; assert `"  "` (2-space indent) pattern present and `"\n"` line breaks present
  - [ ] 5.5: Test full float precision: assert `area_table[0]["computed_value"]` in parsed JSON is a float with more than 4 significant digits (not truncated to display_value precision)
  - [ ] 5.6: Test `report_get_remediation_suggestions` tool: with cached FAIL report, call with valid `rule_id`; assert `hint`, `suggested_action` fields present in response
  - [ ] 5.7: Test `report_get_remediation_suggestions` with `rule_id` of a PASS rule: assert `{"found": False}` returned
  - [ ] 5.8: Test performance: time `generate_json()` with 100 mock rules; assert elapsed < 1 second (well within NFR5 30s limit)

- [ ] Task 6: Validate JSON schema stability across runs (AC: 3)
  - [ ] 6.1: Generate two JSON reports from the same `ComplianceReport` in a test; assert `set(report1.keys()) == set(report2.keys())` at all nesting levels
  - [ ] 6.2: Confirm no Python-specific types leak into JSON (no `datetime` objects, no `Path` objects, no `Decimal` objects) — `model_dump(mode="json")` should handle all conversions
  - [ ] 6.3: Validate against a manually written JSON schema (`jsonschema` not required — structural assertion in tests is sufficient)

## Dev Notes

### Critical Architecture Constraints

1. **Use stdlib `json` only — no external JSON libraries.** `json.dumps()` with `indent=2` and `ensure_ascii=False` is the required serialization. Do NOT use `orjson`, `ujson`, or any third-party JSON library.
2. **Use `model_dump(mode="json")` for Pydantic v2 serialization.** This correctly converts Pydantic models to JSON-serializable dicts, including nested models and `Literal` types. Do NOT use `.dict()` (Pydantic v1 API) or `model_dump()` without `mode="json"` (may leave non-serializable types).
3. **JSON schema must be stable.** Field names come exclusively from Pydantic model field definitions in `schemas.py`. Dynamic key generation (e.g., `{rule_id: value}` dicts) is prohibited — use `list[RuleResultEntry]` structure, not dicts keyed by rule_id.
4. **Full float precision in `computed_value`.** JSON floats retain Python float precision. `display_value` (4dp string) is also present per the `AreaEntry` model. Both are intentional — the JSON serves both human readers (display_value) and downstream systems (computed_value).
5. **`ComplianceReport` caching is mandatory.** All three format generators must share the same `ComplianceReport` instance from `ctx.get_state("compliance_report")`.
6. **`report_get_remediation_suggestions` is a lookup-only tool.** It does NOT re-assemble the report. It reads from the already-cached `ComplianceReport.remediation_hints` list. If no report is cached, it returns an error (not a silent empty result).

### Module/Component Notes

**`generate_json()` implementation:**

```python
import json
from pathlib import Path
from lcs_cad_mcp.modules.reports.schemas import ComplianceReport


def generate_json(self, report: ComplianceReport, output_path: str | Path) -> str:
    report_dict = report.model_dump(mode="json")
    json_str = json.dumps(report_dict, indent=2, ensure_ascii=False)
    # Sanity check: verify round-trip
    json.loads(json_str)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_str, encoding="utf-8")
    return str(path.resolve())
```

**`report_get_remediation_suggestions` tool handler:**

```python
@mcp.tool()
async def report_get_remediation_suggestions(ctx: Context, rule_id: str) -> dict:
    # Step 1: Session
    session = ctx.get_state("session")
    if session is None:
        return MCPError(ErrorCode.SESSION_NOT_STARTED, "No active session").to_response()
    # Step 2: Validate
    if not rule_id or not rule_id.strip():
        return MCPError(ErrorCode.INVALID_PARAMS, "rule_id must be a non-empty string").to_response()
    # Step 3: Get cached report
    report = ctx.get_state("compliance_report")
    if report is None:
        return MCPError(
            ErrorCode.INVALID_PARAMS,
            "No compliance report in session — run scrutiny and generate a report first",
        ).to_response()
    # Step 4: Look up hint
    found = next((h for h in report.remediation_hints if h.rule_id == rule_id), None)
    result = found.model_dump() if found else {"found": False, "rule_id": rule_id}
    # Step 5: Log
    session.event_log.append({
        "tool": "report_get_remediation_suggestions",
        "rule_id": rule_id,
        "found": found is not None,
    })
    # Step 6: Return
    return {"success": True, "data": result}
```

**Expected JSON output structure (abbreviated):**

```json
{
  "project_name": "Residential Block A",
  "date": "2026-03-04T10:30:00Z",
  "config_version": "2.1.0",
  "config_hash": "sha256:abcdef...",
  "rule_set_name": "Maharashtra DCR 2034",
  "overall_status": "NON_COMPLIANT",
  "rule_results": [
    {
      "rule_id": "FAR_001",
      "rule_name": "Floor Area Ratio",
      "status": "FAIL",
      "computed_value": 2.75,
      "permissible_value": 2.5,
      "unit": "ratio",
      "description": "FAR exceeds permissible limit"
    }
  ],
  "area_table": [
    {
      "area_name": "Plot Area",
      "computed_value": 1234.56789012345,
      "unit": "sqm",
      "display_value": "1234.5679"
    }
  ],
  "remediation_hints": [
    {
      "rule_id": "FAR_001",
      "rule_name": "Floor Area Ratio",
      "hint": "Rule FAR_001 failed: computed=2.75, permissible=2.5",
      "suggested_action": "Reduce built-up area to achieve FAR <= 2.5"
    }
  ],
  "metadata": {
    "generator_version": "1.0.0",
    "generated_at": "2026-03-04T10:30:01Z",
    "drawing_path": "/path/to/drawing.dxf",
    "config_path": "/path/to/dcr_rules.yaml"
  }
}
```

### Project Structure Notes

Files to create or modify for this story:

```
src/lcs_cad_mcp/modules/reports/
├── __init__.py        # (unchanged)
├── schemas.py         # (unchanged)
├── service.py         # ADD generate_json() method to ReportService
└── tools.py           # ADD report_generate_json + finalize report_get_remediation_suggestions

tests/unit/modules/reports/
├── __init__.py        # (unchanged)
└── test_generate_json.py   # NEW
```

### Dependencies

- **Story 10-1** (`ComplianceReport` model + `ReportService.assemble_report_data()`; `RemediationHint` model for `report_get_remediation_suggestions`)
- **Story 10-2 / 10-3** (`_resolve_output_path()` helper reused; `compliance_report` caching pattern established)
- **Story 9-5** (`ScrutinyReport` for fallback assembly)
- **Story 2-1** (DrawingSession accessible via `ctx.get_state("session")`)
- **Story 1-2** (FastMCP server — `mcp` instance + `ctx.set_state()`/`ctx.get_state()`)
- Python stdlib `json` — no additional dependency required

### References

- FR29: JSON report requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 10, Story 10-4]
- FR30: All computed values included — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 10, Story 10-4]
- NFR5: 30-second generation limit — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 10 NFR coverage]
- `report_get_remediation_suggestions` tool — [Source: Architecture mandatory context — EPIC 10 SPECIFIC CONTEXT, 10-4]
- `model_dump(mode="json")` Pydantic v2 pattern — [Source: Architecture mandatory context — Pydantic v2]
- JSON 2-space indentation requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 10-4, AC5]
- Area full-precision + display_value duality — [Source: Architecture mandatory context — AREAS section]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/reports/service.py` (modified — `generate_json()` added)
- `src/lcs_cad_mcp/modules/reports/tools.py` (modified — `report_generate_json` + `report_get_remediation_suggestions` finalized)
- `tests/unit/modules/reports/test_generate_json.py`
