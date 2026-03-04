# Story 10.3: `report_generate_docx` MCP Tool

Status: ready-for-dev

## Story

As an **AI client**,
I want **to generate a DOCX objection list from a completed scrutiny session**,
so that **non-compliant rules are documented in an editable Word format suitable for formal authority submission (FR28)**.

## Acceptance Criteria

1. **AC1:** `report_generate_docx(output_path: str | None = None)` MCP tool registered under the `reports` module, callable without arguments (auto-generates path under `ARCHIVE_PATH`).
2. **AC2:** DOCX contains a header section with: project name, report date (ISO 8601), config version, config hash, overall compliance status.
3. **AC3:** DOCX contains an executive summary paragraph stating overall compliance result and counts of passed/failed rules.
4. **AC4:** DOCX contains an objection list table with columns: Rule Name, Computed Value, Permissible Value, Unit, Violation Description — populated only for FAIL rules.
5. **AC5:** When all rules pass (COMPLIANT drawing), the DOCX objection table is replaced with a bold "NO OBJECTIONS — All rules satisfied" statement.
6. **AC6:** DOCX contains an area summary table with columns: Area Name, Value (4dp), Unit — including all computed areas from the scrutiny session.
7. **AC7:** All `ComplianceReport` metadata fields are included in the document (FR30).
8. **AC8:** DOCX generation completes within 30 seconds for reports with up to 100 rules (NFR5).
9. **AC9:** Tool returns `{"success": True, "data": {"file_path": "<absolute_path>", "overall_status": "...", "objection_count": N}}` on success; `MCPError` on failure.

## Tasks / Subtasks

- [ ] Task 1: Implement `ReportService.generate_docx()` in `service.py` using python-docx (AC: 2, 3, 4, 5, 6, 7)
  - [ ] 1.1: Add `generate_docx(self, report: ComplianceReport, output_path: str) -> str` method to `ReportService`; instantiate `docx.Document()` as the base document
  - [ ] 1.2: Implement header section: add document title using `doc.add_heading(report.project_name, level=0)`; add metadata paragraph with date, config version, config hash, overall_status as a formatted block paragraph; use `run.bold = True` for overall_status label
  - [ ] 1.3: Implement executive summary: `doc.add_heading("Executive Summary", level=1)`; add paragraph: `f"Total Rules: {len(report.rule_results)} | Passed: {passed_count} | Failed: {failed_count}"`; add compliance statement paragraph in bold
  - [ ] 1.4: Implement objection list: `doc.add_heading("Objection List", level=1)`; if `report.remediation_hints` is non-empty, add a `doc.add_table(rows=1, cols=5)` with header row `["Rule Name", "Computed", "Permissible", "Unit", "Violation Description"]` and one data row per FAIL rule; apply `table.style = "Table Grid"` for borders
  - [ ] 1.5: Handle COMPLIANT case: if `report.remediation_hints == []`, add `doc.add_paragraph("NO OBJECTIONS — All rules satisfied.")` with the run set to `bold=True`; skip adding any table
  - [ ] 1.6: Implement area summary section: `doc.add_heading("Area Summary", level=1)`; add `doc.add_table(rows=1, cols=3)` with header `["Area Name", "Value", "Unit"]`; data rows from `report.area_table` using `entry.display_value` (4dp)
  - [ ] 1.7: Save document: `doc.save(output_path)`; return resolved absolute path string

- [ ] Task 2: Implement `report_generate_docx` MCP tool handler in `tools.py` (AC: 1, 8, 9)
  - [ ] 2.1: Define `@mcp.tool()` decorated async function `report_generate_docx(ctx: Context, output_path: str | None = None) -> dict`
  - [ ] 2.2: Step 1 — retrieve session: `session = ctx.get_state("session")`; if missing return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 2.3: Step 2 — validate `output_path` if provided: ensure parent directory exists and suffix is `.docx`; if `None`, auto-generate using `ARCHIVE_PATH / f"{session.project_name}_{timestamp}.docx"`
  - [ ] 2.4: Step 3 — retrieve cached `ComplianceReport`: `report = ctx.get_state("compliance_report")`; if not present, call `ReportService(session).assemble_report_data(session.scrutiny_report)` and cache via `ctx.set_state("compliance_report", report)`
  - [ ] 2.5: Step 4 — call `ReportService(session).generate_docx(report, output_path)`; capture returned path
  - [ ] 2.6: Step 5 — log event: `session.event_log.append({"tool": "report_generate_docx", "output_path": str(output_path), "objection_count": len(report.remediation_hints)})`
  - [ ] 2.7: Step 6 — return `{"success": True, "data": {"file_path": str(output_path), "overall_status": report.overall_status, "objection_count": len(report.remediation_hints)}}`

- [ ] Task 3: Resolve output path and ARCHIVE_PATH integration (AC: 1)
  - [ ] 3.1: Reuse the `_resolve_output_path(output_path, session, suffix=".docx")` helper introduced in Story 10-2 (or define it in a shared `reports/_utils.py` if not already shared)
  - [ ] 3.2: Confirm `ARCHIVE_PATH` directory is created if it does not exist before saving

- [ ] Task 4: Add `report_generate_docx` to `register()` in `tools.py` (AC: 1)
  - [ ] 4.1: Ensure `register(mcp: FastMCP) -> None` in `tools.py` binds `report_generate_docx` alongside existing report tools
  - [ ] 4.2: Confirm tool appears in server tool list at startup

- [ ] Task 5: Write unit tests (AC: 8, 9)
  - [ ] 5.1: Create `tests/unit/modules/reports/test_generate_docx.py`
  - [ ] 5.2: Test `generate_docx()` with NON_COMPLIANT mock report (2 FAIL rules, 2 area entries): assert file exists, `objection_count == 2`, area table rows present
  - [ ] 5.3: Test COMPLIANT report: assert "NO OBJECTIONS" text appears in document paragraphs; assert no objection table exists
  - [ ] 5.4: Test metadata completeness: open generated DOCX with `python-docx`, assert project name, date, config version, config hash appear in document text
  - [ ] 5.5: Test area display_value: assert area table cells contain 4dp-rounded strings, not raw float repr
  - [ ] 5.6: Test performance: time `generate_docx()` with 100 mock FAIL rules; assert elapsed < 30 seconds (NFR5)
  - [ ] 5.7: Test tool error path: when `report_generate_docx` called without active session, assert `success: False` and `SESSION_NOT_STARTED` error code

- [ ] Task 6: Validate DOCX structure with python-docx (AC: 4, 5, 6, 7)
  - [ ] 6.1: After generating a sample DOCX, read it back with `docx.Document(path)` and assert: correct number of tables (2 for NON_COMPLIANT: objections + areas; 1 for COMPLIANT: areas only), correct header row values, correct cell content
  - [ ] 6.2: Verify objection table column order matches spec: `["Rule Name", "Computed", "Permissible", "Unit", "Violation Description"]`
  - [ ] 6.3: Verify "Table Grid" style is applied (borders visible) by checking `table.style.name == "Table Grid"`

## Dev Notes

### Critical Architecture Constraints

1. **python-docx only — no other DOCX libraries.** Do NOT use `openpyxl`, `xlsxwriter`, or any Word library not in `pyproject.toml`.
2. **Objection list contains FAIL rules ONLY.** PASS rules do NOT appear in the DOCX objection table. This is by design — the DOCX is a formal objection document for authority submission, not a full compliance report. (The PDF in Story 10-2 contains all rules.)
3. **`ComplianceReport` caching is mandatory.** `ctx.get_state("compliance_report")` must be checked before calling `assemble_report_data()`. All three format tools must operate on identical data. Re-assembling on each call risks timestamp drift and data inconsistency between formats.
4. **Area display uses `display_value` (4dp rounded string).** Never use raw `computed_value: float` in document cells.
5. **DOCX is an editable document.** Formatting must be functional (table borders, bold headers) but should not be overly styled. The architect will edit this document before submission.
6. **Tool does NOT call `assemble_report_data()` if `ComplianceReport` already cached.** Check `ctx.get_state("compliance_report")` first.

### Module/Component Notes

**python-docx import pattern:**

```python
import docx
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
```

**Objection table construction pattern:**

```python
def _add_objection_table(doc: Document, report: ComplianceReport) -> None:
    if not report.remediation_hints:
        p = doc.add_paragraph("NO OBJECTIONS — All rules satisfied.")
        p.runs[0].bold = True
        return

    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, title in enumerate(["Rule Name", "Computed", "Permissible", "Unit", "Violation"]):
        hdr[i].text = title
        hdr[i].paragraphs[0].runs[0].bold = True

    failed = [r for r in report.rule_results if r.status == "FAIL"]
    for rule in failed:
        row = table.add_row().cells
        row[0].text = rule.rule_name
        row[1].text = str(rule.computed_value) if rule.computed_value is not None else "N/A"
        row[2].text = str(rule.permissible_value) if rule.permissible_value is not None else "N/A"
        row[3].text = rule.unit
        row[4].text = rule.description
```

**DOCX section order:**
1. Document title (Heading 0) — project name
2. Metadata paragraph — date, config version, config hash, overall status
3. Executive Summary (Heading 1) — counts + compliance statement
4. Objection List (Heading 1) — table or "NO OBJECTIONS"
5. Area Summary (Heading 1) — area table

### Project Structure Notes

Files to create or modify for this story:

```
src/lcs_cad_mcp/modules/reports/
├── __init__.py        # (unchanged)
├── schemas.py         # (unchanged)
├── service.py         # ADD generate_docx() method to ReportService
└── tools.py           # ADD report_generate_docx MCP tool handler

tests/unit/modules/reports/
├── __init__.py        # (unchanged)
└── test_generate_docx.py   # NEW
```

Optionally create:
```
src/lcs_cad_mcp/modules/reports/
└── _utils.py          # Shared _resolve_output_path() helper (if not already in service.py)
```

### Dependencies

- **Story 10-1** (`ComplianceReport` model + `ReportService.assemble_report_data()`)
- **Story 10-2** (`_resolve_output_path()` helper — reuse or extract to `_utils.py`)
- **Story 9-5** (`ScrutinyReport` for fallback assembly)
- **Story 2-1** (DrawingSession accessible via `ctx.get_state("session")`)
- **Story 1-2** (FastMCP server — `mcp` instance + `ctx.set_state()`/`ctx.get_state()`)
- `python-docx` — declared in `pyproject.toml` from Story 1-1

### References

- FR28: DOCX objection list requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 10, Story 10-3]
- FR30: Self-contained, all metadata fields included — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 10, Story 10-3]
- NFR5: 30-second generation limit — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 10 NFR coverage]
- python-docx pattern — [Source: Architecture mandatory context — EPIC 10 SPECIFIC CONTEXT, 10-3]
- Area 4dp display rule — [Source: Architecture mandatory context — AREAS section]
- ComplianceReport caching pattern — [Source: Architecture mandatory context — EPIC 10 SPECIFIC CONTEXT]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/reports/service.py` (modified — `generate_docx()` added)
- `src/lcs_cad_mcp/modules/reports/tools.py` (modified — `report_generate_docx` added)
- `src/lcs_cad_mcp/modules/reports/_utils.py` (optional — shared path resolution helper)
- `tests/unit/modules/reports/test_generate_docx.py`
