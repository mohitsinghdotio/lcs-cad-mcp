# Story 2.4: Drawing State Snapshot and Rollback

Status: ready-for-dev

## Story

As a **developer**,
I want **the CAD layer to snapshot drawing state before every write operation and automatically roll back on unrecoverable failure**,
so that **drawing files are never left in a partially written or corrupted state after a tool error** (FR35, NFR7, NFR8).

## Acceptance Criteria

1. **AC1:** `SnapshotManager.take() -> str` saves the current drawing state as an in-memory DXF string (for ezdxf) or temp file; returns an opaque checkpoint identifier (e.g. a UUID string); multiple sequential `take()` calls each produce a distinct checkpoint.
2. **AC2:** `SnapshotManager.restore(checkpoint_id: str) -> None` rolls the drawing back to the exact state captured at `take()` time; raises `MCPError(ErrorCode.SNAPSHOT_NOT_FOUND)` if the checkpoint ID does not exist.
3. **AC3:** After `restore()`, the drawing document in the session is byte-identical to the document state at snapshot time (verified by re-serialising to DXF string and comparing checksums in tests).
4. **AC4:** The 6-step tool handler pattern (as defined in the architecture) automatically calls `SnapshotManager.take()` at step 3 for every write-category tool and calls `SnapshotManager.restore(latest_checkpoint)` when a tool raises `MCPError` with `recoverable=False`.
5. **AC5:** After a successful rollback the server remains fully operational — subsequent tool calls succeed without restart (NFR15, NFR10).
6. **AC6:** `DrawingSession` in `session/context.py` holds a `SnapshotManager` instance alongside the `backend` reference; the `SnapshotManager` receives the backend reference at construction time so it can access `self._doc`.
7. **AC7:** Unit tests verify: take creates distinct checkpoints, restore returns document to snapshot state, restore with invalid ID raises MCPError, rollback-then-tool-call succeeds.

## Tasks / Subtasks

- [ ] Task 1: Implement `SnapshotManager` in `session/snapshot.py` (AC: 1, 2, 3, 6)
  - [ ] 1.1: Replace the stub `session/snapshot.py` with a full class: `class SnapshotManager:`
  - [ ] 1.2: Add instance variable `_backend: CADBackend` (receive via constructor); add `_snapshots: dict[str, str]` — maps checkpoint UUID to serialised DXF content string; add `_latest_checkpoint: str | None = None`
  - [ ] 1.3: Implement `take(self) -> str`: generate `checkpoint_id = str(uuid.uuid4())`; serialise the ezdxf document to a DXF string using `io.StringIO` and `backend._doc.write(stream)`; store in `self._snapshots[checkpoint_id]`; update `self._latest_checkpoint = checkpoint_id`; return `checkpoint_id`
  - [ ] 1.4: Implement `restore(self, checkpoint_id: str) -> None`: look up `checkpoint_id` in `self._snapshots`; if missing raise `MCPError(ErrorCode.SNAPSHOT_NOT_FOUND, message=f"Checkpoint '{checkpoint_id}' not found", recoverable=False)`; deserialise the DXF string back using `ezdxf.read(io.StringIO(snapshot_str))`; replace `backend._doc` with the restored document
  - [ ] 1.5: Implement `restore_latest(self) -> None`: convenience method that calls `restore(self._latest_checkpoint)` if `_latest_checkpoint` is not None; logs a WARNING if no snapshot has been taken yet
  - [ ] 1.6: Implement `clear(self, checkpoint_id: str | None = None) -> None`: if `checkpoint_id` given, remove just that checkpoint from `_snapshots`; if None, clear all snapshots (called after successful tool completion to avoid unbounded memory growth)
  - [ ] 1.7: Add `@property latest_checkpoint(self) -> str | None` returning `self._latest_checkpoint`

- [ ] Task 2: Implement `DrawingSession` in `session/context.py` (AC: 6)
  - [ ] 2.1: Replace the stub `session/context.py` with a full class: `class DrawingSession:`
  - [ ] 2.2: Constructor signature: `__init__(self, backend: CADBackend)` — store `self.backend = backend`
  - [ ] 2.3: Instantiate `SnapshotManager`: `self.snapshots = SnapshotManager(backend=self.backend)`
  - [ ] 2.4: Add `self.event_log: EventLog = EventLog()` (stub reference to `session/event_log.py` — placeholder for Story 1-4 / logging stories)
  - [ ] 2.5: Add `self.is_drawing_open: bool = False` flag; `open_drawing` / `new_drawing` set it to `True`, `close_drawing` sets it to `False`
  - [ ] 2.6: Add `def close_drawing(self) -> None`: calls `self.backend` to release document if supported; sets `self.is_drawing_open = False`; calls `self.snapshots.clear()` to free memory

- [ ] Task 3: Implement the 6-step write tool handler wrapper (AC: 4, 5)
  - [ ] 3.1: Create `session/tool_wrapper.py` with an `async def execute_write_tool(ctx, fn, *args, **kwargs)` coroutine; this function encapsulates the snapshot-rollback logic for all write-category tools
  - [ ] 3.2: Step 1 in wrapper: `session: DrawingSession = ctx.get_state("session")` — raise `MCPError(ErrorCode.SESSION_NOT_STARTED)` if None
  - [ ] 3.3: Step 3 in wrapper: `checkpoint_id = session.snapshots.take()` — called before every write operation
  - [ ] 3.4: Call `result = await fn(*args, **kwargs)` (the actual tool logic)
  - [ ] 3.5: On success: `session.snapshots.clear(checkpoint_id)` and return `result`
  - [ ] 3.6: On `MCPError` with `recoverable=False`: call `session.snapshots.restore(checkpoint_id)`; log the rollback; re-raise the error as a structured error response
  - [ ] 3.7: On `MCPError` with `recoverable=True`: do NOT rollback; re-raise as structured error response
  - [ ] 3.8: On unhandled exception: call `session.snapshots.restore_latest()`; wrap in `MCPError(ErrorCode.INVALID_PARAMS, recoverable=False)` and re-raise

- [ ] Task 4: Update `backends/__init__.py` and `session/__init__.py` exports (AC: 6)
  - [ ] 4.1: In `session/__init__.py`, export `DrawingSession` and `SnapshotManager`
  - [ ] 4.2: Update `tests/conftest.py`: update the `mock_session` fixture to use the real `DrawingSession(backend=mock_backend)` instead of a bare stub
  - [ ] 4.3: Confirm `DrawingSession` and `SnapshotManager` are importable: `from lcs_cad_mcp.session import DrawingSession, SnapshotManager`

- [ ] Task 5: Add `ErrorCode.SNAPSHOT_NOT_FOUND` to `errors.py` (AC: 2)
  - [ ] 5.1: Open `errors.py` and add `SNAPSHOT_NOT_FOUND = "SNAPSHOT_NOT_FOUND"` to the `ErrorCode` class
  - [ ] 5.2: Add `SESSION_DRAWING_NOT_OPEN = "SESSION_DRAWING_NOT_OPEN"` for use when tools requiring an open drawing are called with none open

- [ ] Task 6: Write unit tests in `tests/unit/session/test_snapshot.py` (AC: 7)
  - [ ] 6.1: Create `tests/unit/session/__init__.py` (empty) and `tests/unit/session/test_snapshot.py`
  - [ ] 6.2: Test `SnapshotManager.take()` returns a non-empty string UUID
  - [ ] 6.3: Test two consecutive `take()` calls return distinct checkpoint IDs
  - [ ] 6.4: Test `take()` then mutate drawing (add a LINE entity) then `restore(checkpoint_id)` — verify entity is gone after restore (entity_count back to 0)
  - [ ] 6.5: Test restored drawing is functionally identical to snapshot: serialise both to DXF string, compare MD5 checksums
  - [ ] 6.6: Test `restore("nonexistent-id")` raises `MCPError` with code `SNAPSHOT_NOT_FOUND`
  - [ ] 6.7: Test `restore_latest()` with no prior `take()` logs a WARNING and does not raise
  - [ ] 6.8: Test `clear(checkpoint_id)` removes that checkpoint but leaves others
  - [ ] 6.9: Test `clear()` with no argument removes all checkpoints
  - [ ] 6.10: Integration test: simulate a write tool failure — take snapshot, mutate drawing, raise `MCPError(recoverable=False)`, call restore; confirm drawing state restored and subsequent tool call succeeds

- [ ] Task 7: Verify memory behaviour and run full test suite (AC: 5)
  - [ ] 7.1: Measure snapshot memory overhead for a large DXF (100+ entities): confirm it is within acceptable range (< 10 MB per snapshot for typical architectural drawings per NFR8)
  - [ ] 7.2: Run `pytest tests/unit/session/ -v` — all tests pass
  - [ ] 7.3: Run `pytest tests/unit/ -v` — no regressions from Stories 2-1, 2-2, 2-3

## Dev Notes

### Critical Architecture Constraints

1. **Serialise to DXF string, not temp file (default strategy)** — `ezdxf` supports writing to `io.StringIO` via `doc.write(stream)`. This is faster and avoids filesystem I/O. For drawings larger than a configurable threshold (e.g. 50 MB serialised), fall back to a temp file using `tempfile.NamedTemporaryFile`. Implement the threshold check but default to in-memory.
2. **`SnapshotManager` accesses `backend._doc` directly** — This is an intentional controlled coupling between `SnapshotManager` and `EzdxfBackend`. The `SnapshotManager` is instantiated with an `EzdxfBackend` reference and accesses `backend._doc` to serialise/deserialise. For the COM backend (Story 2-5), the snapshot strategy is different (COM does not have an in-memory doc object); the `SnapshotManager` must detect which backend type it holds and dispatch accordingly.
3. **The `DrawingSession` is the unit of connection state** — It is created once per MCP client connection and stored via `ctx.set_state("session", session)`. It is NOT a singleton. Do not store it in a module-level variable.
4. **`execute_write_tool` wrapper is not FastMCP middleware** — It is a plain async function called explicitly from `tools.py`. Do not attempt to hook it into FastMCP's request pipeline. Each write tool in `tools.py` wraps its service call with `execute_write_tool`.
5. **FORBIDDEN:** Do not store snapshots in a database or external file system. In-memory only (with optional temp-file fallback for large drawings). Snapshots are ephemeral — they do not survive server restart.
6. **Memory growth guard** — After a successful tool call, `clear(checkpoint_id)` removes the snapshot. Only one pending snapshot per in-flight tool call should exist at any time. If a tool calls `take()` twice without clearing, that is a bug.

### Module/Component Notes

**`session/snapshot.py` key structure:**

```python
"""SnapshotManager: in-memory drawing state checkpoint/rollback for write-tool safety."""
from __future__ import annotations
import io
import uuid
import logging
import hashlib
from typing import TYPE_CHECKING

import ezdxf  # allowed in session/ for document round-trip via ezdxf.read()

from lcs_cad_mcp.errors import MCPError, ErrorCode

if TYPE_CHECKING:
    from lcs_cad_mcp.backends.base import CADBackend

logger = logging.getLogger(__name__)


class SnapshotManager:
    def __init__(self, backend: "CADBackend") -> None:
        self._backend = backend
        self._snapshots: dict[str, str] = {}
        self._latest_checkpoint: str | None = None

    def take(self) -> str:
        """Snapshot current drawing state. Returns checkpoint_id."""
        doc = self._backend._doc  # type: ignore[attr-defined]
        if doc is None:
            return ""  # no drawing open — no-op snapshot
        stream = io.StringIO()
        doc.write(stream)
        checkpoint_id = str(uuid.uuid4())
        self._snapshots[checkpoint_id] = stream.getvalue()
        self._latest_checkpoint = checkpoint_id
        logger.debug("Snapshot taken: %s (%d chars)", checkpoint_id,
                     len(self._snapshots[checkpoint_id]))
        return checkpoint_id

    def restore(self, checkpoint_id: str) -> None:
        """Restore drawing to snapshot state. Raises MCPError if checkpoint missing."""
        if checkpoint_id not in self._snapshots:
            raise MCPError(code=ErrorCode.SNAPSHOT_NOT_FOUND,
                           message=f"Checkpoint '{checkpoint_id}' not found",
                           recoverable=False)
        stream = io.StringIO(self._snapshots[checkpoint_id])
        self._backend._doc = ezdxf.read(stream)  # type: ignore[attr-defined]
        logger.info("Drawing rolled back to checkpoint %s", checkpoint_id)

    def restore_latest(self) -> None:
        if self._latest_checkpoint is None:
            logger.warning("restore_latest() called with no snapshots taken")
            return
        self.restore(self._latest_checkpoint)

    def clear(self, checkpoint_id: str | None = None) -> None:
        if checkpoint_id is not None:
            self._snapshots.pop(checkpoint_id, None)
        else:
            self._snapshots.clear()
            self._latest_checkpoint = None
```

**`session/context.py` structure:**

```python
"""DrawingSession: per-connection state container (backend + snapshots + event log)."""
from __future__ import annotations
from lcs_cad_mcp.backends.base import CADBackend
from lcs_cad_mcp.session.snapshot import SnapshotManager


class DrawingSession:
    def __init__(self, backend: CADBackend) -> None:
        self.backend = backend
        self.snapshots = SnapshotManager(backend=backend)
        self.is_drawing_open: bool = False

    def close_drawing(self) -> None:
        self.is_drawing_open = False
        self.snapshots.clear()
```

**`session/tool_wrapper.py` — 6-step write pattern:**

```python
"""execute_write_tool: snapshot-before, rollback-on-failure wrapper for write tools."""
from __future__ import annotations
import logging
from typing import Awaitable, Callable, TypeVar
from lcs_cad_mcp.errors import MCPError, ErrorCode

logger = logging.getLogger(__name__)
T = TypeVar("T")


async def execute_write_tool(ctx, fn: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
    """
    6-step write tool handler:
    1. Get session from ctx
    2. Validate session/drawing open (caller's responsibility)
    3. Take snapshot
    4. Call tool function
    5. Clear snapshot on success
    6. Restore on recoverable=False error
    """
    session = ctx.get_state("session")
    if session is None:
        raise MCPError(code=ErrorCode.SESSION_NOT_STARTED,
                       message="No active session. Call cad_open_drawing or cad_new_drawing first.",
                       recoverable=False)
    checkpoint_id = session.snapshots.take()
    try:
        result = await fn(*args, **kwargs)
        session.snapshots.clear(checkpoint_id)
        return result
    except MCPError as e:
        if not e.recoverable:
            logger.warning("Non-recoverable error — rolling back to checkpoint %s", checkpoint_id)
            session.snapshots.restore(checkpoint_id)
        raise
    except Exception as e:
        logger.exception("Unhandled exception in write tool — rolling back: %s", e)
        session.snapshots.restore_latest()
        raise MCPError(code=ErrorCode.INVALID_PARAMS,
                       message=f"Unexpected error: {e}", recoverable=False) from e
```

### Project Structure Notes

```
src/lcs_cad_mcp/
└── session/
    ├── __init__.py          # export DrawingSession, SnapshotManager
    ├── context.py           # THIS STORY — DrawingSession implementation
    ├── snapshot.py          # THIS STORY — SnapshotManager implementation
    ├── tool_wrapper.py      # THIS STORY — execute_write_tool wrapper
    └── event_log.py         # stub (populated later)
tests/
└── unit/
    └── session/
        ├── __init__.py
        └── test_snapshot.py  # THIS STORY
```

### Dependencies

- **Story 1-1** (scaffold): `session/context.py`, `session/snapshot.py` stubs exist; `errors.py` has `MCPError` and `ErrorCode`.
- **Story 2-2** (ezdxf lifecycle): `EzdxfBackend` with `self._doc`, `open_drawing`, `new_drawing` must work; `SnapshotManager` accesses `backend._doc` directly for serialisation.
- **Story 2-3** (metadata query): `get_drawing_metadata()` is used in tests to verify post-restore entity count.

### References

- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 2, Story 2-4]
- FR35 (rollback on failure): [Source: `_bmad-output/planning-artifacts/architecture.md`]
- NFR7 (drawing integrity), NFR8 (performance), NFR10 (server availability), NFR15 (reliability): [Source: `_bmad-output/planning-artifacts/architecture.md`]
- 6-step tool handler pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- ezdxf StringIO write: https://ezdxf.readthedocs.io/en/stable/drawing/management.html#save-to-io-stream

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/session/snapshot.py`
- `src/lcs_cad_mcp/session/context.py`
- `src/lcs_cad_mcp/session/tool_wrapper.py`
- `src/lcs_cad_mcp/session/__init__.py` (updated exports)
- `src/lcs_cad_mcp/errors.py` (updated with SNAPSHOT_NOT_FOUND, SESSION_DRAWING_NOT_OPEN)
- `tests/unit/session/__init__.py`
- `tests/unit/session/test_snapshot.py`
- `tests/conftest.py` (updated mock_session fixture)
