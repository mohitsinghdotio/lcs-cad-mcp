# Story 11.4: `workflow_get_audit_trail` MCP Tool

Status: ready-for-dev

## Story

As an **AI client**,
I want **to retrieve the complete audit trail of all tool invocations for a session or scrutiny run**,
so that **every tool call, its parameters, and its outcome are traceable for compliance audit and dispute resolution (FR34)**.

## Acceptance Criteria

1. **AC1:** `workflow_get_audit_trail(session_id: str | None = None, run_id: str | None = None)` MCP tool registered under the `workflow` module; supports filtering by session ID, by run ID, or returns all events when both are `None`.
2. **AC2:** Every MCP tool call in the system is automatically logged to the `tool_events` table: `tool_name`, `called_at` (ISO 8601), `params_summary` (JSON-serialized params dict, truncated to 1000 chars), `outcome` ("success"/"error"), `error_code` (nullable, present only on error).
3. **AC3:** `repository.save_tool_event(db_session, event_data: dict) -> None` persists a `ToolEvent` row; `event_data` includes `session_id`, `tool_name`, `called_at`, `params_summary`, `outcome`, `error_code`.
4. **AC4:** `repository.get_tool_events(db_session, session_id: str | None = None) -> list[dict]` returns `ToolEvent` rows as plain dicts, ordered by `called_at` ascending (chronological order).
5. **AC5:** `AuditEntry` Pydantic model with fields: `event_id: str`, `session_id: str`, `tool_name: str`, `called_at: str`, `params_summary: str`, `outcome: Literal["success", "error"]`, `error_code: str | None`.
6. **AC6:** Audit log entries are immutable once written — no update or delete operations on `tool_events` table; repository exposes no `update_tool_event()` or `delete_tool_event()` functions.
7. **AC7:** Returns `{"success": True, "data": {"events": [AuditEntry...], "total_count": N}}` on success; returns empty list (not error) when no events match the filter.
8. **AC8:** The automatic tool event logging is implemented as a FastMCP middleware or a shared `log_tool_event()` helper called at the end of every tool handler's Step 5 (event log step); it must NOT require each tool to manually call the DB — the middleware handles persistence transparently.
9. **AC9:** Unit tests: verify `save_tool_event()` inserts a row; verify `get_tool_events()` returns events ordered chronologically; verify `params_summary` is truncated to 1000 chars; verify immutability (no update/delete functions exist); verify filtering by `session_id`.

## Tasks / Subtasks

- [ ] Task 1: Implement `repository.save_tool_event()` in `archive/repository.py` (AC: 3, 6)
  - [ ] 1.1: Replace the stub `save_tool_event()` from Story 11-1 with the full implementation; signature: `save_tool_event(db_session: Session, event_data: dict) -> None`
  - [ ] 1.2: Create `ToolEvent` ORM instance: `ToolEvent(id=str(uuid.uuid4()), session_id=event_data.get("session_id", ""), tool_name=event_data["tool_name"], called_at=event_data.get("called_at", datetime.utcnow().isoformat() + "Z"), params_summary=event_data.get("params_summary", "")[:1000], outcome=event_data.get("outcome", "success"), error_code=event_data.get("error_code"))`
  - [ ] 1.3: Call `db_session.add(event)` and `db_session.flush()`; commit handled by context manager
  - [ ] 1.4: Note: `params_summary` is truncated to 1000 chars at write time using `[:1000]`; log a debug warning if truncation occurs

- [ ] Task 2: Implement `repository.get_tool_events()` in `archive/repository.py` (AC: 4)
  - [ ] 2.1: Replace the stub `get_tool_events()` with full implementation; signature: `get_tool_events(db_session: Session, session_id: str | None = None) -> list[dict]`
  - [ ] 2.2: Base query: `db_session.query(ToolEvent).order_by(ToolEvent.called_at.asc())`
  - [ ] 2.3: Apply `session_id` filter if provided: `.filter(ToolEvent.session_id == session_id)`
  - [ ] 2.4: Return plain dicts (not ORM objects): `[{"event_id": e.id, "session_id": e.session_id, "tool_name": e.tool_name, "called_at": e.called_at, "params_summary": e.params_summary, "outcome": e.outcome, "error_code": e.error_code} for e in query.all()]`

- [ ] Task 3: Define `AuditEntry` Pydantic schema in `modules/workflow/schemas.py` (AC: 5)
  - [ ] 3.1: Add `AuditEntry` model to `schemas.py`: all fields per AC5; use `model_config = ConfigDict(frozen=True)`
  - [ ] 3.2: Add `AuditTrailResult` model: `events: list[AuditEntry]`, `total_count: int`
  - [ ] 3.3: Export `AuditEntry`, `AuditTrailResult` from `schemas.py`

- [ ] Task 4: Implement `WorkflowService.get_audit_trail()` in `service.py` (AC: 1, 4, 7)
  - [ ] 4.1: Add `get_audit_trail(self, session_id: str | None = None, run_id: str | None = None) -> AuditTrailResult` method to `WorkflowService`
  - [ ] 4.2: Use `get_db_session()` context manager; call `get_tool_events(db_session, session_id=session_id)` inside; note: `run_id` filter is a future enhancement — for now, log a warning if `run_id` provided and return all session events
  - [ ] 4.3: Convert each raw dict to `AuditEntry(**event_dict)` using Pydantic validation
  - [ ] 4.4: Return `AuditTrailResult(events=entries, total_count=len(entries))`

- [ ] Task 5: Implement `workflow_get_audit_trail` MCP tool handler in `tools.py` (AC: 1, 7)
  - [ ] 5.1: Define `@mcp.tool()` decorated async function `workflow_get_audit_trail(ctx: Context, session_id: str | None = None, run_id: str | None = None) -> dict`
  - [ ] 5.2: Step 1 — session is optional for audit retrieval; if `session_id` is `None` and active session exists, default to `session_id = ctx.get_state("session").id`
  - [ ] 5.3: Step 2 — no validation needed; both params are optional strings
  - [ ] 5.4: Step 3 — call `WorkflowService(session).get_audit_trail(session_id=session_id, run_id=run_id)`; capture `result`
  - [ ] 5.5: Step 4 — log event (to session event log only, NOT to DB — avoids infinite recursion): if session exists, `session.event_log.append({"tool": "workflow_get_audit_trail", "session_id": session_id, "result_count": result.total_count})`
  - [ ] 5.6: Step 5 — return `{"success": True, "data": {"events": [e.model_dump() for e in result.events], "total_count": result.total_count}}`

- [ ] Task 6: Implement automatic tool event logging middleware (AC: 2, 8)
  - [ ] 6.1: Create `src/lcs_cad_mcp/archive/event_logger.py` with `log_tool_event(session_id: str | None, tool_name: str, params: dict, outcome: str, error_code: str | None = None) -> None` function
  - [ ] 6.2: Inside `log_tool_event()`: serialize `params` with `json.dumps(params, default=str)[:1000]`; call `save_tool_event()` inside a new `get_db_session()` context: `with get_db_session() as db: save_tool_event(db, {"session_id": session_id, "tool_name": tool_name, "called_at": datetime.utcnow().isoformat() + "Z", "params_summary": params_summary, "outcome": outcome, "error_code": error_code})`
  - [ ] 6.3: Wrap `log_tool_event()` in a try/except that silently logs to Python `logging` if DB write fails — audit logging failures must NEVER cause the tool call itself to fail (graceful degradation)
  - [ ] 6.4: Call `log_tool_event()` at the end of Step 5 in key tool handlers (at minimum: `autodcr_run_scrutiny`, `report_generate_pdf`, `report_generate_docx`, `report_generate_json`, `workflow_archive_run`); document that all new tools added post-Epic-11 must also call `log_tool_event()` in their Step 5
  - [ ] 6.5: Add `log_tool_event` to `archive/__init__.py` exports

- [ ] Task 7: Add `workflow_get_audit_trail` to `register()` in `tools.py` and write tests (AC: 1, 9)
  - [ ] 7.1: Add `workflow_get_audit_trail` to `register(mcp)` in `tools.py`
  - [ ] 7.2: Create `tests/unit/archive/test_audit_trail.py`
  - [ ] 7.3: Test `save_tool_event()`: insert event; assert 1 row in `tool_events`; assert `called_at` is ISO 8601 string; assert `params_summary` is ≤ 1000 chars
  - [ ] 7.4: Test `params_summary` truncation: pass params that serialize to 2000 chars; assert stored `params_summary` is exactly 1000 chars
  - [ ] 7.5: Test `get_tool_events()` chronological order: insert 3 events with different `called_at`; assert returned list is ascending by `called_at`
  - [ ] 7.6: Test `session_id` filter: insert events for 2 sessions; `get_tool_events(db, session_id="session-1")` returns only session-1 events
  - [ ] 7.7: Test immutability: confirm no `update_tool_event` or `delete_tool_event` function exists in `repository.py` (import inspection)
  - [ ] 7.8: Test `log_tool_event()` graceful degradation: mock `get_db_session()` to raise an exception; assert `log_tool_event()` does NOT re-raise (silent failure with logging only)

## Dev Notes

### Critical Architecture Constraints

1. **Audit log entries are write-once, immutable.** No `UPDATE` or `DELETE` operations on `tool_events`. Repository exposes only `save_tool_event()` and `get_tool_events()`. This is a legal requirement — modifying audit trails destroys their evidential value.
2. **`log_tool_event()` must NEVER fail silently in a way that blocks the tool response.** If the DB write fails, catch the exception, log to Python `logging.warning()`, and return normally. The audit trail is important but secondary to the tool's primary response.
3. **`workflow_get_audit_trail` must NOT write its own invocation to the `tool_events` DB table.** This would create an infinite loop (every audit query would be logged, which would show up in the next audit query). Only log to the in-memory `session.event_log` list.
4. **`params_summary` is truncated to 1000 chars.** Large parameter payloads (e.g., full drawing paths, config blobs) must be truncated before DB insert. Use `[:1000]` after JSON serialization. Use `json.dumps(params, default=str)` to handle non-JSON-serializable params (e.g., `Path` objects).
5. **`called_at` is always the DB write time (ISO 8601 UTC).** Do NOT use the session event_log timestamp — generate a fresh `datetime.utcnow().isoformat() + "Z"` at the moment of `log_tool_event()` call.
6. **SQLAlchemy detached instances**: `get_tool_events()` must return plain dicts before the `get_db_session()` context manager closes.

### Module/Component Notes

**`event_logger.py` — `log_tool_event()` function:**

```python
import json
import logging
from datetime import datetime
from lcs_cad_mcp.archive.engine import get_db_session
from lcs_cad_mcp.archive.repository import save_tool_event

logger = logging.getLogger(__name__)


def log_tool_event(
    session_id: str | None,
    tool_name: str,
    params: dict,
    outcome: str,
    error_code: str | None = None,
) -> None:
    try:
        params_summary = json.dumps(params, default=str)[:1000]
        with get_db_session() as db_session:
            save_tool_event(db_session, {
                "session_id": session_id or "",
                "tool_name": tool_name,
                "called_at": datetime.utcnow().isoformat() + "Z",
                "params_summary": params_summary,
                "outcome": outcome,
                "error_code": error_code,
            })
    except Exception as exc:
        logger.warning("Audit log write failed for tool %s: %s", tool_name, exc)
        # Intentionally suppress — audit failure must never block tool response
```

**Using `log_tool_event()` in a tool handler (Step 5 pattern):**

```python
# Step 5: Event log (both in-memory + DB audit)
session.event_log.append({"tool": "autodcr_run_scrutiny", "status": "success"})
log_tool_event(
    session_id=getattr(session, "id", None),
    tool_name="autodcr_run_scrutiny",
    params={"config_path": config_path},
    outcome="success",
)
```

**`AuditEntry` and `AuditTrailResult` schemas:**

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict


class AuditEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    session_id: str
    tool_name: str
    called_at: str                             # ISO 8601
    params_summary: str
    outcome: Literal["success", "error"]
    error_code: str | None = None


class AuditTrailResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    events: list[AuditEntry]
    total_count: int
```

### Project Structure Notes

Files to create or modify for this story:

```
src/lcs_cad_mcp/archive/
├── repository.py          # MODIFY: implement save_tool_event() + get_tool_events()
├── event_logger.py        # CREATE: log_tool_event() helper
└── __init__.py            # MODIFY: export log_tool_event

src/lcs_cad_mcp/modules/workflow/
├── schemas.py             # MODIFY: add AuditEntry, AuditTrailResult
├── service.py             # MODIFY: add get_audit_trail() method
└── tools.py               # MODIFY: add workflow_get_audit_trail handler

# Tool handlers to update for log_tool_event() integration (Step 5):
src/lcs_cad_mcp/modules/autodcr/tools.py      # MODIFY: add log_tool_event() call
src/lcs_cad_mcp/modules/reports/tools.py      # MODIFY: add log_tool_event() calls
src/lcs_cad_mcp/modules/workflow/tools.py     # MODIFY: add log_tool_event() calls (except audit trail tool itself)

tests/unit/archive/
└── test_audit_trail.py    # NEW
```

### Dependencies

- **Story 11-1** (`ToolEvent` ORM model, `get_db_session()`, `save_tool_event()` stub)
- **Story 11-2** (`WorkflowService` class scaffolded, `modules/workflow/` package exists)
- **Story 11-3** (`ArchiveSummary`, `ArchiveListResult` already in `schemas.py` — add `AuditEntry` alongside)
- **Story 9-5** (autodcr tools — `log_tool_event()` integration point)
- **Story 10-2 / 10-3 / 10-4** (reports tools — `log_tool_event()` integration points)
- **Story 1-2** (FastMCP server — `mcp` instance for tool registration)

### References

- FR34: Audit trail requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 11, Story 11-4]
- `workflow_get_audit_trail` tool name and filter params — [Source: Architecture mandatory context — EPIC 11 SPECIFIC CONTEXT, 11-4]
- `ToolEvent` schema (tool_name, timestamp, params_summary, outcome) — [Source: Architecture mandatory context — EPIC 11 SPECIFIC CONTEXT, 11-4]
- Immutable audit log requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 11-4, AC3]
- ISO 8601 `called_at` format — [Source: Architecture mandatory context — DATES section]
- Graceful degradation for logging failures — [Source: Architecture mandatory context — NFR pattern]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/archive/repository.py` (modified — `save_tool_event()`, `get_tool_events()` implemented)
- `src/lcs_cad_mcp/archive/event_logger.py`
- `src/lcs_cad_mcp/archive/__init__.py` (modified — `log_tool_event` exported)
- `src/lcs_cad_mcp/modules/workflow/schemas.py` (modified — `AuditEntry`, `AuditTrailResult` added)
- `src/lcs_cad_mcp/modules/workflow/service.py` (modified — `get_audit_trail()` added)
- `src/lcs_cad_mcp/modules/workflow/tools.py` (modified — `workflow_get_audit_trail` added)
- `src/lcs_cad_mcp/modules/autodcr/tools.py` (modified — `log_tool_event()` calls added)
- `src/lcs_cad_mcp/modules/reports/tools.py` (modified — `log_tool_event()` calls added)
- `tests/unit/archive/test_audit_trail.py`
