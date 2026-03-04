# Story 11.2: Scrutiny Run Archival

Status: ready-for-dev

## Story

As a **developer**,
I want **all scrutiny run artifacts archived automatically in SQLite after a completed scrutiny + report generation cycle**,
so that **every run is persistently stored, auditable, and re-retrievable for re-submission or dispute resolution (FR32, NFR9)**.

## Acceptance Criteria

1. **AC1:** `repository.save_scrutiny_run(db_session, session, scrutiny_report, report_paths)` persists: a `ScrutinyRun` row, all `RuleResultRecord` rows for every rule result, a `ConfigVersionRecord` row with full config JSON snapshot, and a `ReportRecord` row for each generated report file path — all in a single ACID transaction.
2. **AC2:** Archival is all-or-nothing (ACID): if any insert fails (e.g., FK violation, disk error), the entire transaction is rolled back and no partial data is persisted (NFR9).
3. **AC3:** Returns `run_id` (UUID string) on success; raises a typed exception `ArchivalError` (with `error_code`, `message`) on failure — never returns `None` silently.
4. **AC4:** `ScrutinyRun.run_date` is stored as ISO 8601 string at the moment of archival (not the scrutiny execution time — the archival timestamp is the authoritative record).
5. **AC5:** `ConfigVersionRecord.config_snapshot_json` stores the full DCR config as a JSON string; `config_hash` is the SHA-256 hex digest of this JSON string, computed at archival time and consistent with the `config_hash` in `ComplianceReport`.
6. **AC6:** `ReportRecord` rows are created for each entry in `report_paths` dict (`{"pdf": "/path/to/report.pdf", "docx": "...", "json": "..."}`) — missing formats are skipped (not all three formats are mandatory).
7. **AC7:** `WorkflowService.archive_run(session, scrutiny_report, report_paths)` method wraps `repository.save_scrutiny_run()` with the ACID context manager from `archive.engine.get_db_session()`; logs the `run_id` to the session event log on success.
8. **AC8:** Unit tests: verify all rows inserted in a single transaction; verify rollback on simulated insert failure (mock raises exception mid-transaction); verify `run_id` is a valid UUID string; verify `config_hash` matches SHA-256 of stored JSON.

## Tasks / Subtasks

- [ ] Task 1: Implement `repository.save_scrutiny_run()` in `archive/repository.py` (AC: 1, 2, 3, 4, 5, 6)
  - [ ] 1.1: Replace the stub `save_scrutiny_run()` from Story 11-1 with the full implementation; signature: `save_scrutiny_run(db_session: Session, drawing_session, scrutiny_report, report_paths: dict[str, str]) -> str`
  - [ ] 1.2: Generate `run_id = str(uuid.uuid4())`; create `ScrutinyRun` ORM instance with all required fields; set `run_date = datetime.utcnow().isoformat() + "Z"` (ISO 8601 archival timestamp)
  - [ ] 1.3: Create `ConfigVersionRecord` ORM instance: serialize config to JSON using `json.dumps(scrutiny_report.config_snapshot, indent=2, ensure_ascii=False)`; compute `config_hash = "sha256:" + hashlib.sha256(config_json.encode()).hexdigest()`
  - [ ] 1.4: Create one `RuleResultRecord` per entry in `scrutiny_report.rule_results`; store `computed_value` and `permissible_value` at full float precision (never round)
  - [ ] 1.5: Create one `ReportRecord` per format in `report_paths` dict; skip if value is `None` or empty string; set `generated_at = datetime.utcnow().isoformat() + "Z"`
  - [ ] 1.6: Use `db_session.add_all([run, config_record, *rule_records, *report_records])` then `db_session.flush()` (commit handled by the calling context manager); return `run_id`
  - [ ] 1.7: If any exception is raised inside the function, let it propagate — the `get_db_session()` context manager handles rollback

- [ ] Task 2: Define `ArchivalError` exception class (AC: 3)
  - [ ] 2.1: Add `ArchivalError` to `src/lcs_cad_mcp/errors.py`: `class ArchivalError(Exception): def __init__(self, error_code: str, message: str): self.error_code = error_code; self.message = message`
  - [ ] 2.2: Add `ErrorCode.ARCHIVAL_FAILED = "ARCHIVAL_FAILED"` to `ErrorCode` in `errors.py`
  - [ ] 2.3: In `WorkflowService.archive_run()`, catch any exception from `save_scrutiny_run()` and re-raise as `ArchivalError(ErrorCode.ARCHIVAL_FAILED, str(e))`

- [ ] Task 3: Implement `WorkflowService.archive_run()` in `modules/workflow/service.py` (AC: 7)
  - [ ] 3.1: Create `WorkflowService` class in `modules/workflow/service.py` with `__init__(self, session)` — stores session reference
  - [ ] 3.2: Implement `archive_run(self, scrutiny_report, report_paths: dict[str, str]) -> str`:
    - Use `get_db_session()` context manager from `archive.engine`
    - Inside context: call `save_scrutiny_run(db_session, self._session, scrutiny_report, report_paths)`
    - Capture `run_id`; log to session event log: `self._session.event_log.append({"tool": "workflow_archive_run", "run_id": run_id, "status": "success"})`
    - Return `run_id`
  - [ ] 3.3: If `ArchivalError` raised: log `{"tool": "workflow_archive_run", "status": "error", "error_code": e.error_code}`; re-raise the `ArchivalError` for the MCP tool handler to convert to `MCPError.to_response()`

- [ ] Task 4: Implement `workflow_archive_run` MCP tool handler in `modules/workflow/tools.py` (AC: 3, 7)
  - [ ] 4.1: Define `@mcp.tool()` decorated async function `workflow_archive_run(ctx: Context, report_paths: dict[str, str] | None = None) -> dict`
  - [ ] 4.2: Step 1 — retrieve session: `session = ctx.get_state("session")`; if missing return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 4.3: Step 2 — retrieve cached `scrutiny_report = ctx.get_state("scrutiny_report")`; if missing return `MCPError(INVALID_PARAMS, "No scrutiny report in session — run autodcr_run_scrutiny first").to_response()`
  - [ ] 4.4: Step 3 — if `report_paths` is `None`, attempt to retrieve from session state: `report_paths = ctx.get_state("report_paths") or {}`
  - [ ] 4.5: Step 4 — call `WorkflowService(session).archive_run(scrutiny_report, report_paths)`; capture `run_id`
  - [ ] 4.6: Step 5 — log event: `session.event_log.append({"tool": "workflow_archive_run", "run_id": run_id})`
  - [ ] 4.7: Step 6 — return `{"success": True, "data": {"run_id": run_id, "archived_at": datetime.utcnow().isoformat() + "Z"}}`
  - [ ] 4.8: Handle `ArchivalError`: return `MCPError(ErrorCode.ARCHIVAL_FAILED, str(e.message), recoverable=False).to_response()`

- [ ] Task 5: Wire `workflow` module registration (AC: 7)
  - [ ] 5.1: Create `modules/workflow/__init__.py` with `register(mcp: FastMCP) -> None` that calls `tools.register(mcp)`
  - [ ] 5.2: In `tools.py`, implement `register(mcp: FastMCP) -> None` that binds `workflow_archive_run` to the `mcp` instance
  - [ ] 5.3: Confirm `modules/workflow` is included in `server.py` module registration loop

- [ ] Task 6: Write unit and integration tests (AC: 8)
  - [ ] 6.1: Create `tests/unit/archive/test_repository.py`
  - [ ] 6.2: Use `tmp_archive_engine` fixture (in-memory SQLite from Story 11-1 test) to test `save_scrutiny_run()` in isolation
  - [ ] 6.3: Test happy path: call `save_scrutiny_run()` with mock `ScrutinyReport` (3 rules, 2 report paths); assert 1 `ScrutinyRun`, 3 `RuleResultRecord`, 1 `ConfigVersionRecord`, 2 `ReportRecord` rows in DB; assert returned `run_id` is valid UUID
  - [ ] 6.4: Test rollback: mock `db_session.flush()` to raise `SQLAlchemyError` after inserting `ScrutinyRun` but before `RuleResultRecord`; assert no rows remain in any table after exception
  - [ ] 6.5: Test `config_hash` correctness: assert stored `config_hash` equals `"sha256:" + sha256(config_snapshot_json.encode()).hexdigest()`
  - [ ] 6.6: Test `run_date` is ISO 8601 string (not a datetime object): assert `re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z", run.run_date)`
  - [ ] 6.7: Test missing report format: call with `report_paths={"pdf": "/path/to/report.pdf"}` (no docx/json); assert only 1 `ReportRecord` created

## Dev Notes

### Critical Architecture Constraints

1. **ACID is enforced at the `get_db_session()` context manager level.** `save_scrutiny_run()` must NOT call `db_session.commit()` itself — it only calls `db_session.flush()` to validate constraints within the transaction. The commit happens in the context manager on clean exit. This is the NFR9 ACID guarantee.
2. **All date fields stored as ISO 8601 strings.** `run_date`, `recorded_at`, `generated_at` are all `datetime.utcnow().isoformat() + "Z"` at the moment of the function call. Never store Python `datetime` objects or Unix timestamps.
3. **`computed_value` and `permissible_value` stored at full float precision.** SQLAlchemy `Float` maps to SQLite `REAL` (8-byte IEEE 754 double). Never round at DB write time.
4. **`config_snapshot_json` stores the FULL config.** This is the complete DCR rule configuration at the time of the run — not a summary. This makes every run independently verifiable without needing the original config file.
5. **`config_hash` is always `"sha256:" + hexdigest`.** Include the `"sha256:"` prefix to be explicit about the hash algorithm. This matches the format in `ComplianceReport.config_hash`.
6. **`WorkflowService.archive_run()` does NOT call `workflow_archive_run` as an MCP tool.** It calls `repository.save_scrutiny_run()` directly as plain Python — no MCP tool chaining, no network overhead.

### Module/Component Notes

**`repository.save_scrutiny_run()` full implementation skeleton:**

```python
import uuid
import hashlib
import json
from datetime import datetime
from sqlalchemy.orm import Session
from lcs_cad_mcp.archive.models import (
    ScrutinyRun, RuleResultRecord, ConfigVersionRecord, ReportRecord
)


def save_scrutiny_run(
    db_session: Session,
    drawing_session,
    scrutiny_report,
    report_paths: dict[str, str],
) -> str:
    run_id = str(uuid.uuid4())
    run_date = datetime.utcnow().isoformat() + "Z"

    # Config snapshot
    config_dict = getattr(scrutiny_report, "config_snapshot", {}) or {}
    config_json = json.dumps(config_dict, indent=2, ensure_ascii=False)
    config_hash = "sha256:" + hashlib.sha256(config_json.encode()).hexdigest()

    scrutiny_run = ScrutinyRun(
        id=run_id,
        session_id=getattr(drawing_session, "id", str(uuid.uuid4())),
        run_date=run_date,
        config_version=getattr(scrutiny_report, "config_version", ""),
        config_hash=config_hash,
        rule_set_name=getattr(scrutiny_report, "rule_set_name", ""),
        overall_status="COMPLIANT" if scrutiny_report.overall_pass else "NON_COMPLIANT",
        drawing_path=getattr(drawing_session, "drawing_path", ""),
    )

    config_record = ConfigVersionRecord(
        id=str(uuid.uuid4()),
        run_id=run_id,
        version=getattr(scrutiny_report, "config_version", ""),
        config_hash=config_hash,
        config_snapshot_json=config_json,
        recorded_at=run_date,
    )

    rule_records = [
        RuleResultRecord(
            id=str(uuid.uuid4()),
            run_id=run_id,
            rule_id=r.rule_id,
            rule_name=r.rule_name,
            status="PASS" if r.passed else "FAIL",
            computed_value=r.computed_value,
            permissible_value=r.permissible_value,
            unit=getattr(r, "unit", ""),
            description=getattr(r, "description", ""),
        )
        for r in (scrutiny_report.rule_results or [])
    ]

    report_records = [
        ReportRecord(
            id=str(uuid.uuid4()),
            run_id=run_id,
            format=fmt,
            file_path=path,
            generated_at=datetime.utcnow().isoformat() + "Z",
        )
        for fmt, path in report_paths.items()
        if path
    ]

    db_session.add_all([scrutiny_run, config_record, *rule_records, *report_records])
    db_session.flush()  # validate constraints; commit handled by get_db_session() context manager
    return run_id
```

**`ArchivalError` definition to add to `errors.py`:**

```python
class ArchivalError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
```

### Project Structure Notes

Files to create or modify for this story:

```
src/lcs_cad_mcp/archive/
└── repository.py         # MODIFY: implement save_scrutiny_run()

src/lcs_cad_mcp/
└── errors.py             # MODIFY: add ArchivalError, ErrorCode.ARCHIVAL_FAILED

src/lcs_cad_mcp/modules/workflow/
├── __init__.py            # CREATE: register(mcp) → tools.register(mcp)
├── service.py             # CREATE: WorkflowService with archive_run()
├── schemas.py             # CREATE: ArchiveSummary schema (used in 11-3)
└── tools.py               # CREATE: workflow_archive_run MCP tool handler

tests/unit/archive/
└── test_repository.py     # NEW
```

### Dependencies

- **Story 11-1** (SQLite engine, ORM models, `get_db_session()` context manager must exist)
- **Story 10-4** (`report_generate_json` — JSON report path available before archival)
- **Story 10-2 / 10-3** (PDF/DOCX report paths available in session state)
- **Story 9-5** (`ScrutinyReport` from autodcr — must expose `rule_results`, `config_snapshot`, `overall_pass`)
- **Story 2-1** (DrawingSession with `id`, `drawing_path`, `config_path`, `project_name` attributes)
- **Story 1-2** (FastMCP server — `mcp` instance + `ctx.set_state()`/`ctx.get_state()`)

### References

- FR32: Archival requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 11, Story 11-2]
- NFR9: ACID transactions — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 11 NFR coverage]
- `save_scrutiny_run` + ACID pattern — [Source: Architecture mandatory context — EPIC 11 SPECIFIC CONTEXT, 11-2]
- ISO 8601 date storage — [Source: Architecture mandatory context — DATES section]
- Full float precision storage — [Source: Architecture mandatory context — AREAS section]
- `get_db_session()` context manager — [Source: Architecture mandatory context — EPIC 11, Story 11-1]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/archive/repository.py` (modified — `save_scrutiny_run()` fully implemented)
- `src/lcs_cad_mcp/errors.py` (modified — `ArchivalError`, `ErrorCode.ARCHIVAL_FAILED` added)
- `src/lcs_cad_mcp/modules/workflow/__init__.py`
- `src/lcs_cad_mcp/modules/workflow/service.py`
- `src/lcs_cad_mcp/modules/workflow/schemas.py`
- `src/lcs_cad_mcp/modules/workflow/tools.py`
- `tests/unit/archive/test_repository.py`
