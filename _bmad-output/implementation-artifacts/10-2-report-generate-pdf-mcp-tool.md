# Story 10.2: `report_generate_pdf` MCP Tool

Status: ready-for-dev

## Story

As an **AI client**,
I want **to generate a PDF compliance report from a completed scrutiny session**,
so that **the architect has a print-ready, self-contained document for review and authority sign-off (FR27)**.

## Acceptance Criteria

1. **AC1:** `report_generate_pdf(output_path: str | None = None)` MCP tool registered under the `reports` module, callable without arguments (auto-generates path under `ARCHIVE_PATH`).
2. **AC2:** PDF contains a cover page with: project name, report date (ISO 8601), overall compliance status (COMPLIANT / NON_COMPLIANT), config version, and config hash.
3. **AC3:** PDF contains an executive summary section: total rules checked, number passed, number failed, overall status statement.
4. **AC4:** PDF contains a rule results table with columns: Rule Name, Computed Value, Permissible Value, Unit, Status — with each row colored green (PASS) or red (FAIL).
5. **AC5:** PDF contains an area summary table with columns: Area Name, Computed Value, Unit.
6. **AC6:** PDF contains a remediation hints section listing all failed rules with their hint text and suggested action — section is omitted (or replaced with "No objections" statement) when all rules pass.
7. **AC7:** Overall status is visually prominent: COMPLIANT header in green, NON_COMPLIANT header in red, using ReportLab color constants.
8. **AC8:** PDF is fully self-contained and interpretable without access to the live system (FR30) — no external links or resources.
9. **AC9:** PDF generation completes within 30 seconds for reports with up to 100 rules (NFR5).
10. **AC10:** Tool returns `{"success": True, "data": {"file_path": "<absolute_path>", "overall_status": "...", "page_count": N}}` on success; `MCPError` on failure.

## Tasks / Subtasks

- [ ] Task 1: Implement `ReportService.generate_pdf()` in `service.py` using ReportLab (AC: 2, 3, 4, 5, 6, 7, 8)
  - [ ] 1.1: Add `generate_pdf(self, report: ComplianceReport, output_path: str) -> str` method to `ReportService`; use `reportlab.platypus.SimpleDocTemplate` for multi-page layout with `reportlab.platypus` flowables (Paragraph, Table, Spacer, PageBreak)
  - [ ] 1.2: Implement cover page: `Paragraph(project_name, title_style)`, date, config version, config hash; add overall status block using `colors.green` for COMPLIANT and `colors.red` for NON_COMPLIANT via a colored `Table` cell or `Paragraph` with custom `ParagraphStyle`
  - [ ] 1.3: Implement executive summary: "Rules Checked: N | Passed: N | Failed: N"; use `ParagraphStyle` with `fontName="Helvetica-Bold"` for the summary line
  - [ ] 1.4: Implement rule results table: header row `["Rule Name", "Computed", "Permissible", "Unit", "Status"]`; data rows from `report.rule_results`; apply `TableStyle` with `BACKGROUND` green (`colors.lightgreen`) for PASS rows and red (`colors.salmon`) for FAIL rows
  - [ ] 1.5: Implement area summary table: header `["Area Name", "Value", "Unit"]`; data rows from `report.area_table` using `display_value` (4dp); apply alternating row shading for readability
  - [ ] 1.6: Implement remediation section: if `report.remediation_hints` is non-empty, add a section header "Remediation Required" and a bulleted list of hint text + suggested_action for each; if empty, add "NO OBJECTIONS — All rules satisfied" paragraph
  - [ ] 1.7: Build and save the PDF to `output_path` via `doc.build(story)`; return the resolved absolute path string

- [ ] Task 2: Implement `report_generate_pdf` MCP tool handler in `tools.py` (AC: 1, 9, 10)
  - [ ] 2.1: Define `@mcp.tool()` decorated async function `report_generate_pdf(ctx: Context, output_path: str | None = None) -> dict`
  - [ ] 2.2: Step 1 — retrieve session: `session = ctx.get_state("session")`; if missing return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 2.3: Step 2 — validate `output_path` if provided: ensure parent directory exists and has `.pdf` suffix; if `output_path` is `None`, auto-generate: `ARCHIVE_PATH / f"{session.project_name}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.pdf"`
  - [ ] 2.4: Step 3 — retrieve current `ComplianceReport` from session state: `report = ctx.get_state("compliance_report")`; if not assembled yet, call `ReportService(session).assemble_report_data(session.scrutiny_report)` and cache it via `ctx.set_state("compliance_report", report)`
  - [ ] 2.5: Step 4 — call `ReportService(session).generate_pdf(report, output_path)`; capture returned path; track elapsed time
  - [ ] 2.6: Step 5 — log event: `session.event_log.append({"tool": "report_generate_pdf", "output_path": output_path, "overall_status": report.overall_status})`
  - [ ] 2.7: Step 6 — return `{"success": True, "data": {"file_path": str(output_path), "overall_status": report.overall_status, "page_count": N}}`

- [ ] Task 3: Resolve output path and ARCHIVE_PATH integration (AC: 1, 8)
  - [ ] 3.1: Import `Settings` from `lcs_cad_mcp.settings` and access `Settings().archive_path` for auto-generated paths
  - [ ] 3.2: Ensure `ARCHIVE_PATH` directory exists before writing; call `output_path.parent.mkdir(parents=True, exist_ok=True)`
  - [ ] 3.3: Confirm generated PDF paths follow pattern: `{ARCHIVE_PATH}/{project_name}_{timestamp}.pdf`

- [ ] Task 4: Add `report_generate_pdf` registration to `tools.py` `register()` function (AC: 1)
  - [ ] 4.1: Ensure `register(mcp: FastMCP) -> None` in `tools.py` binds `report_generate_pdf` to the `mcp` instance
  - [ ] 4.2: Confirm `report_generate_pdf` appears in server tool list by running `mcp dev` or checking tool registration log at startup

- [ ] Task 5: Write unit and integration tests (AC: 9, 10)
  - [ ] 5.1: Create `tests/unit/modules/reports/test_generate_pdf.py`
  - [ ] 5.2: Test `generate_pdf()` with mock `ComplianceReport` (2 pass + 1 fail rule, 2 area entries): assert returned path exists, file size > 0, file ends with `.pdf`
  - [ ] 5.3: Test COMPLIANT report: assert no remediation section present; test NON_COMPLIANT report: assert remediation section present
  - [ ] 5.4: Test auto-path generation: when `output_path=None`, assert returned path is under `ARCHIVE_PATH` and follows naming pattern
  - [ ] 5.5: Test performance: time `generate_pdf()` with 100 mock rules; assert elapsed < 30 seconds (NFR5)
  - [ ] 5.6: Test error case: if session not started, `report_generate_pdf` tool returns `success: False` with `SESSION_NOT_STARTED` error code

- [ ] Task 6: Verify ReportLab page layout and visual correctness (AC: 2, 3, 4, 5, 7)
  - [ ] 6.1: Manually generate a sample PDF using a mock report and visually verify cover page, tables, color coding, and remediation section render correctly
  - [ ] 6.2: Verify PASS rows are green-background and FAIL rows are red-background in the rule results table
  - [ ] 6.3: Verify COMPLIANT/NON_COMPLIANT header text color is correct (green/red) and visually prominent
  - [ ] 6.4: Verify area table uses `display_value` (4dp) and not raw `computed_value` float

## Dev Notes

### Critical Architecture Constraints

1. **ReportLab only — no external PDF libraries.** Use `reportlab.platypus` for all layout. Do NOT use `fpdf`, `weasyprint`, or any library not in `pyproject.toml`.
2. **PDF must be self-contained (FR30).** No external fonts, no embedded URLs, no references to file paths that require live system access. All content is rendered inline as ReportLab flowables.
3. **`ComplianceReport` is assembled once and cached in session state.** If `ctx.get_state("compliance_report")` is already set, use the cached value rather than re-assembling. This ensures all three format tools (PDF, DOCX, JSON) operate on identical data.
4. **`generate_pdf()` is a pure function on `ComplianceReport`.** It does NOT call `assemble_report_data()` internally. The MCP tool handler is responsible for assembling the report first, then passing it to `generate_pdf()`. This separation makes `generate_pdf()` independently testable.
5. **Never use Unix timestamps for file names or DB storage.** Use ISO 8601 format strings: `datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')` for file name timestamps.
6. **Area display uses `display_value` (4dp rounded string), never raw `computed_value` float.** This is the display precision rule from architecture.

### Module/Component Notes

**ReportLab import pattern:**

```python
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
```

**Color-coded table row style example:**

```python
def _build_rule_table_style(rule_results: list[RuleResultEntry]) -> TableStyle:
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),       # header row
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]
    for i, rule in enumerate(rule_results, start=1):
        bg = colors.lightgreen if rule.status == "PASS" else colors.salmon
        style_commands.append(("BACKGROUND", (0, i), (-1, i), bg))
    return TableStyle(style_commands)
```

**Overall status header color:**

```python
status_color = colors.green if report.overall_status == "COMPLIANT" else colors.red
status_style = ParagraphStyle(
    name="StatusStyle",
    parent=styles["Heading1"],
    textColor=status_color,
    fontSize=20,
)
story.append(Paragraph(report.overall_status, status_style))
```

**Auto-path generation pattern:**

```python
from lcs_cad_mcp.settings import Settings
from pathlib import Path
from datetime import datetime

def _resolve_output_path(output_path: str | None, session, suffix: str) -> Path:
    if output_path:
        p = Path(output_path)
    else:
        settings = Settings()
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        p = settings.archive_path / f"{session.project_name}_{ts}{suffix}"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
```

### Project Structure Notes

Files to create or modify for this story:

```
src/lcs_cad_mcp/modules/reports/
├── __init__.py        # (already exists from 10-1) — no changes needed
├── schemas.py         # (already exists from 10-1) — no changes needed
├── service.py         # ADD generate_pdf() method to ReportService
└── tools.py           # ADD report_generate_pdf MCP tool handler

tests/unit/modules/reports/
├── __init__.py        # (already exists from 10-1)
└── test_generate_pdf.py   # NEW
```

### Dependencies

- **Story 10-1** (`ComplianceReport` Pydantic model and `ReportService.assemble_report_data()` must exist)
- **Story 9-5** (`ScrutinyReport` from autodcr module — needed to populate `ComplianceReport`)
- **Story 2-1** (DrawingSession accessible via `ctx.get_state("session")`)
- **Story 1-2** (FastMCP server — `mcp` instance + `ctx.set_state()`/`ctx.get_state()`)
- `reportlab` — declared in `pyproject.toml` from Story 1-1
- `lcs_cad_mcp.settings.Settings` for `ARCHIVE_PATH` resolution

### References

- FR27: PDF report requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 10, Story 10-2]
- FR30: Self-contained report — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 10, Story 10-2]
- NFR5: 30-second generation limit — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 10 NFR coverage]
- ReportLab platypus pattern — [Source: Architecture mandatory context — EPIC 10 SPECIFIC CONTEXT, 10-2]
- Area 4dp display rule — [Source: Architecture mandatory context — AREAS section]
- ISO 8601 date rule — [Source: Architecture mandatory context — DATES section]
- `ctx.set_state()` / `ctx.get_state()` pattern — [Source: Architecture mandatory context — FastMCP 3.x session architecture]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/reports/service.py` (modified — `generate_pdf()` added)
- `src/lcs_cad_mcp/modules/reports/tools.py` (modified — `report_generate_pdf` added)
- `tests/unit/modules/reports/test_generate_pdf.py`
