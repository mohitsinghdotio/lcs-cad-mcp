# Story 11.3: `workflow_get_archive` MCP Tool — Archive Retrieval

Status: ready-for-dev

## Story

As an **AI client**,
I want **to retrieve previously archived scrutiny runs by filtering on project name, date, or config version**,
so that **architects can access historic compliance results for re-submission, dispute resolution, or audit (FR33)**.

## Acceptance Criteria

1. **AC1:** `workflow_get_archive(project_name: str | None = None, date: str | None = None, config_version: str | None = None)` MCP tool is registered under the `workflow` module and callable with any combination of filter parameters (all optional).
2. **AC2:** When called with no filters, returns all archived scrutiny runs (most recent first, ordered by `run_date` descending).
3. **AC3:** When filters are provided, returns only matching runs: `project_name` is case-insensitive substring match; `date` is prefix match on ISO 8601 date string (e.g., `"2026-03"` matches all March 2026 runs); `config_version` is exact match.
4. **AC4:** Each result is an `ArchiveSummary` Pydantic model with fields: `run_id: str`, `run_date: str`, `project_name: str`, `config_version: str`, `config_hash: str`, `overall_status: str`, `report_paths: dict[str, str]` (format → file_path), `rule_count: int`.
5. **AC5:** Returns `{"success": True, "data": {"runs": [ArchiveSummary...], "total_count": N}}` on success; returns empty list (not an error) when no runs match the filters.
6. **AC6:** Returns `MCPError` with code `RUN_NOT_FOUND` only when a specific `run_id` lookup returns zero results (not for empty filter results).
7. **AC7:** `repository.get_scrutiny_runs()` implements the filter logic using SQLAlchemy query filters; joins `ReportRecord` to populate `report_paths`.
8. **AC8:** Unit tests cover: unfiltered retrieval (all runs returned), project_name filter (case-insensitive, substring), date prefix filter, config_version exact match, empty result (no matching runs), `report_paths` dict populated correctly from joined `ReportRecord` rows.

## Tasks / Subtasks

- [ ] Task 1: Define `ArchiveSummary` Pydantic schema in `modules/workflow/schemas.py` (AC: 4)
  - [ ] 1.1: Create `ArchiveSummary` model with fields: `run_id: str`, `run_date: str`, `project_name: str`, `config_version: str`, `config_hash: str`, `overall_status: Literal["COMPLIANT", "NON_COMPLIANT"]`, `report_paths: dict[str, str]`, `rule_count: int`
  - [ ] 1.2: Use `model_config = ConfigDict(frozen=True)` for immutability
  - [ ] 1.3: Add `ArchiveListResult` model: `runs: list[ArchiveSummary]`, `total_count: int` — used as the response payload
  - [ ] 1.4: Export `ArchiveSummary`, `ArchiveListResult` from `schemas.py`

- [ ] Task 2: Implement `repository.get_scrutiny_runs()` in `archive/repository.py` (AC: 2, 3, 7)
  - [ ] 2.1: Replace the stub from Story 11-1 with the full implementation; signature: `get_scrutiny_runs(db_session: Session, project_name: str | None = None, run_date_prefix: str | None = None, config_version: str | None = None) -> list[dict]`
  - [ ] 2.2: Base query: `db_session.query(ScrutinyRun).order_by(ScrutinyRun.run_date.desc())`
  - [ ] 2.3: Apply `project_name` filter: if provided, use `ScrutinyRun.project_name.ilike(f"%{project_name}%")` (SQLite case-insensitive LIKE)
  - [ ] 2.4: Apply `run_date_prefix` filter: use `ScrutinyRun.run_date.startswith(run_date_prefix)` — relies on ISO 8601 lexicographic ordering; SQLite `LIKE` also works: `ScrutinyRun.run_date.like(f"{run_date_prefix}%")`
  - [ ] 2.5: Apply `config_version` filter: if provided, use `ScrutinyRun.config_version == config_version` (exact match)
  - [ ] 2.6: For each matching `ScrutinyRun`, query `ReportRecord` rows: `report_records = db_session.query(ReportRecord).filter(ReportRecord.run_id == run.id).all()`; build `report_paths = {r.format: r.file_path for r in report_records}`
  - [ ] 2.7: Query `RuleResultRecord` count: `rule_count = db_session.query(RuleResultRecord).filter(RuleResultRecord.run_id == run.id).count()`
  - [ ] 2.8: Build and return list of dicts (not ORM objects — avoids detached instance issues after session close): `[{"run_id": run.id, "run_date": run.run_date, ..., "report_paths": report_paths, "rule_count": rule_count}]`

- [ ] Task 3: Implement `WorkflowService.get_archive()` method in `modules/workflow/service.py` (AC: 4, 5)
  - [ ] 3.1: Add `get_archive(self, project_name: str | None = None, date: str | None = None, config_version: str | None = None) -> ArchiveListResult` method to `WorkflowService`
  - [ ] 3.2: Use `get_db_session()` context manager; call `get_scrutiny_runs(db_session, project_name, date, config_version)` inside
  - [ ] 3.3: Convert each raw dict to `ArchiveSummary(**run_dict)` using Pydantic model validation
  - [ ] 3.4: Return `ArchiveListResult(runs=summaries, total_count=len(summaries))`

- [ ] Task 4: Implement `workflow_get_archive` MCP tool handler in `modules/workflow/tools.py` (AC: 1, 5, 6)
  - [ ] 4.1: Define `@mcp.tool()` decorated async function `workflow_get_archive(ctx: Context, project_name: str | None = None, date: str | None = None, config_version: str | None = None) -> dict`
  - [ ] 4.2: Step 1 — session is NOT required for archive retrieval (archive is global, not session-scoped); skip session check; log warning if no session for audit purposes but do not block
  - [ ] 4.3: Step 2 — validate `date` format if provided: accept any string (flexible prefix match); do NOT enforce strict ISO 8601 format here — let repository handle partial matches
  - [ ] 4.4: Step 3 — call `WorkflowService(session).get_archive(project_name, date, config_version)` where `session = ctx.get_state("session")` (may be `None`); pass `None` session — `WorkflowService` must handle `None` session gracefully for read-only operations
  - [ ] 4.5: Step 4 — if `result.total_count == 0` and any filter was provided, return success with empty list (not an error): `{"success": True, "data": {"runs": [], "total_count": 0}}`
  - [ ] 4.6: Step 5 — log event if session exists: `session.event_log.append({"tool": "workflow_get_archive", "filter": {"project_name": project_name, "date": date}, "result_count": result.total_count})`
  - [ ] 4.7: Step 6 — return `{"success": True, "data": {"runs": [r.model_dump() for r in result.runs], "total_count": result.total_count}}`

- [ ] Task 5: Add `workflow_get_archive` to `register()` in `tools.py` (AC: 1)
  - [ ] 5.1: Ensure `register(mcp: FastMCP) -> None` in `tools.py` binds `workflow_get_archive` alongside `workflow_archive_run` from Story 11-2
  - [ ] 5.2: Confirm both tools appear in server tool list at startup

- [ ] Task 6: Write unit tests (AC: 8)
  - [ ] 6.1: Create `tests/unit/archive/test_get_runs.py`
  - [ ] 6.2: Use `tmp_archive_engine` in-memory fixture; seed 3 `ScrutinyRun` rows with varying project names, dates, config versions, and report records
  - [ ] 6.3: Test unfiltered: `get_scrutiny_runs(db_session)` returns all 3 runs ordered by `run_date` descending
  - [ ] 6.4: Test `project_name` filter: case-insensitive substring match — `"block"` matches `"Residential Block A"` and `"Commercial Block B"` but not `"Warehouse"`
  - [ ] 6.5: Test `run_date_prefix` filter: `"2026-03"` matches March 2026 runs, does not match `"2026-02-"` runs
  - [ ] 6.6: Test `config_version` exact match: `"2.1.0"` does not match `"2.1.1"` or `"2.1"`
  - [ ] 6.7: Test combined filters: `project_name="Block"` + `config_version="2.1.0"` returns intersection only
  - [ ] 6.8: Test `report_paths` populated: seed 2 `ReportRecord` rows for one run; assert `result[0]["report_paths"] == {"pdf": "...", "docx": "..."}`
  - [ ] 6.9: Test empty result: filter that matches nothing returns `[]`, not an exception
  - [ ] 6.10: Test `rule_count`: seed 5 `RuleResultRecord` rows for one run; assert `result[0]["rule_count"] == 5`

## Dev Notes

### Critical Architecture Constraints

1. **`workflow_get_archive` does NOT require an active drawing session.** Archive retrieval is a global query operation — it reads from the SQLite DB regardless of whether a drawing is currently open. The tool handler must not return `SESSION_NOT_STARTED` error when called without a session.
2. **Return plain dicts from repository, not SQLAlchemy ORM objects.** After the `get_db_session()` context manager closes, ORM objects enter a "detached" state and accessing their attributes raises `DetachedInstanceError`. Convert to plain dicts inside the `with get_db_session()` block before returning.
3. **`date` parameter is a prefix match, not an exact ISO 8601 date.** `"2026-03"` should match all runs in March 2026. `"2026-03-04"` should match all runs on March 4. `"2026"` should match all 2026 runs. This is achieved by `run.run_date.like(f"{date}%")` in SQLAlchemy.
4. **Empty results are not errors.** If no runs match the filters, return `{"runs": [], "total_count": 0}` with `success: True`. Only use `RUN_NOT_FOUND` error for a future `workflow_get_run_by_id` tool (not this story).
5. **`WorkflowService` must support `None` session.** For read-only operations like `get_archive()`, the session may be `None` if the tool is called outside an active drawing session. The service's `__init__` should accept `session = None`.

### Module/Component Notes

**`ArchiveSummary` schema:**

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict


class ArchiveSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    run_date: str                              # ISO 8601 string
    project_name: str
    config_version: str
    config_hash: str
    overall_status: Literal["COMPLIANT", "NON_COMPLIANT"]
    report_paths: dict[str, str]              # {"pdf": "/path/...", "docx": "/path/..."}
    rule_count: int


class ArchiveListResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    runs: list[ArchiveSummary]
    total_count: int
```

**`get_scrutiny_runs()` SQLAlchemy query with joins:**

```python
def get_scrutiny_runs(
    db_session: Session,
    project_name: str | None = None,
    run_date_prefix: str | None = None,
    config_version: str | None = None,
) -> list[dict]:
    query = db_session.query(ScrutinyRun).order_by(ScrutinyRun.run_date.desc())

    if project_name:
        query = query.filter(ScrutinyRun.project_name.ilike(f"%{project_name}%"))
    if run_date_prefix:
        query = query.filter(ScrutinyRun.run_date.like(f"{run_date_prefix}%"))
    if config_version:
        query = query.filter(ScrutinyRun.config_version == config_version)

    results = []
    for run in query.all():
        report_records = db_session.query(ReportRecord).filter(
            ReportRecord.run_id == run.id
        ).all()
        rule_count = db_session.query(RuleResultRecord).filter(
            RuleResultRecord.run_id == run.id
        ).count()
        results.append({
            "run_id": run.id,
            "run_date": run.run_date,
            "project_name": run.project_name,
            "config_version": run.config_version,
            "config_hash": run.config_hash,
            "overall_status": run.overall_status,
            "report_paths": {r.format: r.file_path for r in report_records},
            "rule_count": rule_count,
        })
    return results
```

**`WorkflowService` supporting `None` session:**

```python
class WorkflowService:
    def __init__(self, session=None) -> None:
        self._session = session  # may be None for read-only operations

    def get_archive(self, project_name=None, date=None, config_version=None) -> ArchiveListResult:
        with get_db_session() as db_session:
            raw = get_scrutiny_runs(db_session, project_name, date, config_version)
        runs = [ArchiveSummary(**r) for r in raw]
        return ArchiveListResult(runs=runs, total_count=len(runs))
```

### Project Structure Notes

Files to create or modify for this story:

```
src/lcs_cad_mcp/archive/
└── repository.py          # MODIFY: implement get_scrutiny_runs() fully

src/lcs_cad_mcp/modules/workflow/
├── schemas.py             # MODIFY: add ArchiveSummary, ArchiveListResult
├── service.py             # MODIFY: add get_archive() method to WorkflowService
└── tools.py               # MODIFY: add workflow_get_archive tool handler

tests/unit/archive/
└── test_get_runs.py       # NEW
```

### Dependencies

- **Story 11-2** (`ScrutinyRun`, `ReportRecord`, `RuleResultRecord` ORM models and `WorkflowService` class must exist)
- **Story 11-1** (SQLite engine, `get_db_session()`, ORM models — DB must be initialized)
- **Story 1-2** (FastMCP server — `mcp` instance for tool registration)
- No active session required — this tool is callable from any context

### References

- FR33: Archive retrieval — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 11, Story 11-3]
- `workflow_get_archive` tool name and signature — [Source: Architecture mandatory context — EPIC 11 SPECIFIC CONTEXT, 11-3]
- `ArchiveSummary` fields — [Source: Architecture mandatory context — EPIC 11 SPECIFIC CONTEXT, 11-3]
- ISO 8601 date prefix matching approach — [Source: Architecture mandatory context — DATES section]
- No-session-required for read-only tools — [Source: Architecture mandatory context — EPIC 11 SPECIFIC CONTEXT]
- SQLAlchemy detached instance avoidance — [Source: Architecture mandatory context — EPIC 11 SPECIFIC CONTEXT, 11-1 repository pattern]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/archive/repository.py` (modified — `get_scrutiny_runs()` fully implemented)
- `src/lcs_cad_mcp/modules/workflow/schemas.py` (modified — `ArchiveSummary`, `ArchiveListResult` added)
- `src/lcs_cad_mcp/modules/workflow/service.py` (modified — `get_archive()` added)
- `src/lcs_cad_mcp/modules/workflow/tools.py` (modified — `workflow_get_archive` added)
- `tests/unit/archive/test_get_runs.py`
