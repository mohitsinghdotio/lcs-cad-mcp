# Story 10.1: Report Data Model and Assembly

Status: ready-for-dev

## Story

As a **developer**,
I want **a structured report data model that assembles all scrutiny results into a single report payload**,
so that **all three report formats (PDF, DOCX, JSON) share a single source of truth and are consistent across formats (FR30)**.

## Acceptance Criteria

1. **AC1:** `ComplianceReport` Pydantic model defined in `src/lcs_cad_mcp/modules/reports/schemas.py` with fields: `project_name: str`, `date: str` (ISO 8601), `config_version: str`, `config_hash: str`, `rule_set_name: str`, `area_table: list[AreaEntry]`, `rule_results: list[RuleResultEntry]`, `overall_status: Literal["COMPLIANT", "NON_COMPLIANT"]`, `remediation_hints: list[RemediationHint]`, `metadata: ReportMetadata`.
2. **AC2:** `AreaEntry` Pydantic model with fields: `area_name: str`, `computed_value: float` (full precision), `unit: str`, `display_value: str` (rounded to 4 decimal places for display).
3. **AC3:** `RuleResultEntry` Pydantic model with fields: `rule_id: str`, `rule_name: str`, `status: Literal["PASS", "FAIL"]`, `computed_value: float | None`, `permissible_value: float | None`, `unit: str`, `description: str`.
4. **AC4:** `RemediationHint` Pydantic model with fields: `rule_id: str`, `rule_name: str`, `hint: str`, `suggested_action: str`.
5. **AC5:** `ReportService.assemble_report_data(session, scrutiny_report: ScrutinyReport) -> ComplianceReport` assembles the complete report payload from the active session and the scrutiny output — includes project name from session, date as ISO 8601 string, config hash, all rule results, all area entries, overall_status derived from rule results, and remediation hints for all FAIL rules.
6. **AC6:** `overall_status` is `"COMPLIANT"` if and only if all `RuleResultEntry.status == "PASS"`; any single FAIL yields `"NON_COMPLIANT"`.
7. **AC7:** Unit tests cover: all fields populated from mock `ScrutinyReport`, overall_status derivation (all pass, one fail, all fail), area display_value rounded to 4 decimal places, empty rule set yields COMPLIANT.

## Tasks / Subtasks

- [ ] Task 1: Define all Pydantic schemas in `schemas.py` (AC: 1, 2, 3, 4)
  - [ ] 1.1: Create `AreaEntry` model with `area_name`, `computed_value: float`, `unit: str`, `display_value: str`; implement `model_validator(mode="before")` or `@computed_field` to auto-populate `display_value = f"{computed_value:.4f}"` when not supplied
  - [ ] 1.2: Create `RuleResultEntry` model with `rule_id`, `rule_name`, `status: Literal["PASS","FAIL"]`, `computed_value: float | None`, `permissible_value: float | None`, `unit: str`, `description: str`; mark optional numeric fields with `None` default
  - [ ] 1.3: Create `RemediationHint` model with `rule_id`, `rule_name`, `hint: str`, `suggested_action: str`
  - [ ] 1.4: Create `ReportMetadata` model with `generator_version: str`, `generated_at: str` (ISO 8601), `drawing_path: str`, `config_path: str`
  - [ ] 1.5: Create `ComplianceReport` top-level model with all fields per AC1; use `model_config = ConfigDict(frozen=True)` for immutability
  - [ ] 1.6: Export all models from `schemas.py` and expose via `modules/reports/__init__.py`

- [ ] Task 2: Implement `ReportService.assemble_report_data()` in `service.py` (AC: 5, 6)
  - [ ] 2.1: Create `ReportService` class with `__init__(self, session)` — stores session reference; does NOT instantiate other services eagerly (accepts scrutiny_report as argument to avoid circular dependencies)
  - [ ] 2.2: Implement `assemble_report_data(self, scrutiny_report: ScrutinyReport) -> ComplianceReport`: extract `project_name` from `session.project_name` (or session metadata); extract `date` as `datetime.utcnow().isoformat() + "Z"` (ISO 8601)
  - [ ] 2.3: Extract `config_version` and `config_hash` from `scrutiny_report.config_snapshot` (or session config); map all `scrutiny_report.rule_results` to `list[RuleResultEntry]` with correct field mapping
  - [ ] 2.4: Extract area data from `session` (or `scrutiny_report.area_results`) and convert to `list[AreaEntry]`; ensure `computed_value` stored at full float precision, `display_value` rounded to 4dp
  - [ ] 2.5: Derive `overall_status`: `"COMPLIANT"` if all `RuleResultEntry.status == "PASS"` else `"NON_COMPLIANT"`
  - [ ] 2.6: Build `remediation_hints`: for every `RuleResultEntry` with `status == "FAIL"`, look up remediation text from rule config and construct `RemediationHint`; if no remediation text available, use `hint = f"Rule {rule_id} failed: computed={computed_value}, permissible={permissible_value}"`
  - [ ] 2.7: Construct and return `ComplianceReport(...)` with all assembled fields; raise `ValueError` with descriptive message if required fields are missing from inputs

- [ ] Task 3: Implement `report_get_remediation_suggestions` MCP tool in `tools.py` (AC: 4)
  - [ ] 3.1: Define `@mcp.tool()` decorated async function `report_get_remediation_suggestions(ctx: Context, rule_id: str) -> dict`
  - [ ] 3.2: Step 1 — retrieve session: `session = ctx.get_state("session")`; if missing return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 3.3: Step 2 — validate: ensure `rule_id` is non-empty string; return `MCPError(INVALID_PARAMS)` if blank
  - [ ] 3.4: Step 4 — look up rule in session config; return `RemediationHint.model_dump()` for the matched rule; return `{"success": True, "data": {"found": False, "rule_id": rule_id}}` if rule not in config
  - [ ] 3.5: Step 5 — log event: `session.event_log.append({"tool": "report_get_remediation_suggestions", "rule_id": rule_id})`
  - [ ] 3.6: Step 6 — return `{"success": True, "data": hint.model_dump()}`

- [ ] Task 4: Register tools in `__init__.py` and wire `register(mcp)` (AC: 5)
  - [ ] 4.1: In `modules/reports/__init__.py`, implement `register(mcp: FastMCP) -> None` that calls `tools.register(mcp)`
  - [ ] 4.2: In `tools.py`, implement `register(mcp: FastMCP) -> None` that binds all report tool handlers to the passed `mcp` instance
  - [ ] 4.3: Confirm that `modules/reports` is included in `server.py` module registration loop

- [ ] Task 5: Write unit tests for data model assembly (AC: 7)
  - [ ] 5.1: Create `tests/unit/modules/reports/__init__.py` and `test_report_data_model.py`
  - [ ] 5.2: Build `MockScrutinyReport` fixture with: 3 rules (2 pass, 1 fail), 3 area entries, config snapshot with version and hash
  - [ ] 5.3: Test `assemble_report_data()`: assert all `RuleResultEntry` fields populated, `overall_status == "NON_COMPLIANT"`, one `RemediationHint` present, all `AreaEntry.display_value` rounded to 4dp
  - [ ] 5.4: Test all-pass scenario: `overall_status == "COMPLIANT"`, `remediation_hints == []`
  - [ ] 5.5: Test all-fail scenario: `overall_status == "NON_COMPLIANT"`, `len(remediation_hints) == len(rule_results)`
  - [ ] 5.6: Test `AreaEntry` display_value precision: `computed_value=123.456789` yields `display_value="123.4568"` (rounded, not truncated)
  - [ ] 5.7: Test empty rule set (zero rules): `overall_status == "COMPLIANT"`, `rule_results == []`, `remediation_hints == []`

- [ ] Task 6: Validate ScrutinyReport interface contract with Epic 9 (AC: 5)
  - [ ] 6.1: Confirm `ScrutinyReport` from `modules/autodcr/schemas.py` exposes: `rule_results`, `config_snapshot`, `overall_pass`; document field names in Dev Notes for Story 10-2/10-3/10-4 to reference
  - [ ] 6.2: If field names differ from expected, add a private `_map_rule_result(raw) -> RuleResultEntry` adapter in `ReportService` — do NOT modify `autodcr` schemas
  - [ ] 6.3: Run `pytest tests/unit/modules/reports/` and confirm zero failures

## Dev Notes

### Critical Architecture Constraints

1. **Pydantic v2 is mandatory.** Use `model_config = ConfigDict(frozen=True)`, `model_dump()` (NOT `.dict()`), `model_validate()` (NOT `.from_orm()`). FastMCP 3.x requires Pydantic v2 serialization throughout.
2. **`ComplianceReport` is the single source of truth for all three format generators.** Stories 10-2, 10-3, and 10-4 each call `ReportService.assemble_report_data()` and receive the same `ComplianceReport` object — field names must not change without coordinating across all three tools.
3. **Area precision rule:** `computed_value: float` is stored at full Python float precision in `AreaEntry`; `display_value: str` is ALWAYS rounded to exactly 4 decimal places. Reports display `display_value`; archival (Story 11-2) stores `computed_value`. Never truncate — use Python `round()` or `f"{value:.4f}"`.
4. **Date fields are always ISO 8601 strings.** Never use Unix timestamps. `datetime.utcnow().isoformat() + "Z"` is the correct format.
5. **`ReportService` does NOT call other MCP tools internally.** All data comes from the `session` object and the `scrutiny_report` argument passed as plain Python. This prevents circular MCP calls and network overhead.

### Module/Component Notes

**`schemas.py` — Key model definitions:**

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, computed_field


class AreaEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    area_name: str
    computed_value: float          # full precision — for archival
    unit: str
    display_value: str = ""        # auto-populated: f"{computed_value:.4f}"

    def model_post_init(self, __context) -> None:
        # Pydantic v2: use object.__setattr__ for frozen models
        if not self.display_value:
            object.__setattr__(self, "display_value", f"{self.computed_value:.4f}")


class RuleResultEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    rule_name: str
    status: Literal["PASS", "FAIL"]
    computed_value: float | None = None
    permissible_value: float | None = None
    unit: str = ""
    description: str = ""


class RemediationHint(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    rule_name: str
    hint: str
    suggested_action: str


class ReportMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    generator_version: str
    generated_at: str              # ISO 8601
    drawing_path: str
    config_path: str


class ComplianceReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_name: str
    date: str                      # ISO 8601
    config_version: str
    config_hash: str
    rule_set_name: str
    area_table: list[AreaEntry]
    rule_results: list[RuleResultEntry]
    overall_status: Literal["COMPLIANT", "NON_COMPLIANT"]
    remediation_hints: list[RemediationHint]
    metadata: ReportMetadata
```

**`service.py` — ReportService assembly skeleton:**

```python
from datetime import datetime
from lcs_cad_mcp.modules.reports.schemas import (
    ComplianceReport, AreaEntry, RuleResultEntry, RemediationHint, ReportMetadata
)


class ReportService:
    def __init__(self, session) -> None:
        self._session = session

    def assemble_report_data(self, scrutiny_report) -> ComplianceReport:
        rule_results = [
            RuleResultEntry(
                rule_id=r.rule_id,
                rule_name=r.rule_name,
                status="PASS" if r.passed else "FAIL",
                computed_value=r.computed_value,
                permissible_value=r.permissible_value,
                unit=r.unit,
                description=r.description,
            )
            for r in scrutiny_report.rule_results
        ]
        overall_status = (
            "COMPLIANT" if all(r.status == "PASS" for r in rule_results)
            else "NON_COMPLIANT"
        )
        remediation_hints = [
            RemediationHint(
                rule_id=r.rule_id,
                rule_name=r.rule_name,
                hint=f"Rule {r.rule_id} failed: computed={r.computed_value}, permissible={r.permissible_value}",
                suggested_action=f"Adjust {r.rule_name} to meet permissible value {r.permissible_value} {r.unit}",
            )
            for r in rule_results if r.status == "FAIL"
        ]
        area_table = [
            AreaEntry(area_name=a.name, computed_value=a.value, unit=a.unit)
            for a in (getattr(scrutiny_report, "area_results", []) or [])
        ]
        return ComplianceReport(
            project_name=getattr(self._session, "project_name", "Unknown Project"),
            date=datetime.utcnow().isoformat() + "Z",
            config_version=getattr(scrutiny_report, "config_version", ""),
            config_hash=getattr(scrutiny_report, "config_hash", ""),
            rule_set_name=getattr(scrutiny_report, "rule_set_name", ""),
            area_table=area_table,
            rule_results=rule_results,
            overall_status=overall_status,
            remediation_hints=remediation_hints,
            metadata=ReportMetadata(
                generator_version="1.0.0",
                generated_at=datetime.utcnow().isoformat() + "Z",
                drawing_path=getattr(self._session, "drawing_path", ""),
                config_path=getattr(self._session, "config_path", ""),
            ),
        )
```

### Project Structure Notes

Files to create or modify for this story:

```
src/lcs_cad_mcp/modules/reports/
├── __init__.py        # register(mcp) → tools.register(mcp)
├── schemas.py         # ComplianceReport, AreaEntry, RuleResultEntry, RemediationHint, ReportMetadata
├── service.py         # ReportService with assemble_report_data()
└── tools.py           # report_get_remediation_suggestions MCP tool

tests/unit/modules/reports/
├── __init__.py
└── test_report_data_model.py
```

### Dependencies

- **Story 9-5** (`autodcr_run_scrutiny` — `ScrutinyReport` output schema must be stable before this story's `assemble_report_data()` can map fields correctly)
- **Story 2-1** (DrawingSession with `project_name`, `drawing_path`, `config_path` attributes)
- **Story 7-x** (DCR Config — `config_version`, `config_hash`, `rule_set_name` come from the loaded config snapshot)
- **Story 1-2** (FastMCP server — `mcp` instance available for tool registration)
- Python stdlib `datetime` module — no additional dependency required

### References

- FR30: Report must include all computed values — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 10, Story 10-1]
- ComplianceReport model design — [Source: Architecture mandatory context — EPIC 10 SPECIFIC CONTEXT, Story 10-1]
- Area precision rule (4dp display, full float storage) — [Source: Architecture mandatory context — AREAS section]
- ISO 8601 date rule — [Source: Architecture mandatory context — DATES section]
- Pydantic v2 frozen model pattern — [Source: `_bmad-output/implementation-artifacts/6-1-closure-verification-engine.md` — Dev Notes]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/reports/__init__.py`
- `src/lcs_cad_mcp/modules/reports/schemas.py`
- `src/lcs_cad_mcp/modules/reports/service.py`
- `src/lcs_cad_mcp/modules/reports/tools.py`
- `tests/unit/modules/reports/__init__.py`
- `tests/unit/modules/reports/test_report_data_model.py`
