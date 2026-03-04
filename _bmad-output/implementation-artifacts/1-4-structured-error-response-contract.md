# Story 1.4: Structured Error Response Contract

Status: review

## Story

As a **developer**,
I want **every MCP tool failure to return a standard structured error envelope**,
so that **AI clients can parse, react to, and surface errors consistently**.

## Acceptance Criteria

1. **AC1:** All tool errors return a response with this exact shape: `{ "success": false, "data": null, "error": { "code": str, "message": str, "recoverable": bool, "suggested_action": str } }`
2. **AC2:** `recoverable: true` errors do NOT trigger drawing rollback — the session and open drawing remain intact after a recoverable error
3. **AC3:** `recoverable: false` errors DO trigger drawing rollback — the open drawing is reverted to the last snapshot (integration test with stub rollback hook)
4. **AC4:** Error codes are defined as string constants on the `ErrorCode` class (e.g. `LAYER_NOT_FOUND`, `CLOSURE_FAILED`, `DCR_VIOLATION`) — no inline string literals in tool handlers
5. **AC5:** Unhandled exceptions in any tool handler are caught by a global exception handler and wrapped in the error envelope — the server never returns a raw Python traceback to the client

## Tasks / Subtasks

- [ ] Task 1: Implement `errors.py` fully — `MCPError` dataclass and `ErrorCode` constants (AC: 1, 4)
  - [ ] 1.1: Define `ErrorCode` class with all string constant attributes grouped by domain (Session, CAD Backend, Layer, Entity, Verification, DCR, Generic)
  - [ ] 1.2: Add `VALIDATION_ERROR = "VALIDATION_ERROR"` to `ErrorCode` (used by Story 1-5)
  - [ ] 1.3: Add `ROLLBACK_FAILED = "ROLLBACK_FAILED"` and `SNAPSHOT_FAILED = "SNAPSHOT_FAILED"` to `ErrorCode`
  - [ ] 1.4: Implement `MCPError` as a `@dataclass` with fields: `code: str`, `message: str = ""`, `recoverable: bool = True`, `suggested_action: str = ""`
  - [ ] 1.5: Implement `MCPError.to_response() -> dict` returning the exact envelope shape from AC1
  - [ ] 1.6: Write unit tests in `tests/unit/test_errors.py` asserting the `to_response()` output matches the AC1 contract exactly (field names, types, null values)

- [ ] Task 2: Define `MCPResponse` success helper for symmetric success/error envelopes (AC: 1)
  - [ ] 2.1: Add a `success_response(data: dict | list | None = None) -> dict` module-level function in `errors.py` that returns `{"success": True, "data": data, "error": None}`
  - [ ] 2.2: Update `cad_ping` (from Story 1-2) to use `success_response({"pong": True})` instead of an inline dict, demonstrating the pattern
  - [ ] 2.3: Write a unit test asserting `success_response({"x": 1})` returns `{"success": True, "data": {"x": 1}, "error": None}`

- [ ] Task 3: Implement global exception handler on the FastMCP server (AC: 5)
  - [ ] 3.1: Research the FastMCP 3.x API for attaching a global exception handler (e.g. `mcp.exception_handler`, middleware, or `lifespan` try/except pattern)
  - [ ] 3.2: Attach a handler in `server.py` that catches any `Exception` raised inside a tool, wraps it as `MCPError(code=ErrorCode.INTERNAL_ERROR, message=str(e), recoverable=False)`, and returns `.to_response()`
  - [ ] 3.3: Add `INTERNAL_ERROR = "INTERNAL_ERROR"` to `ErrorCode` for this purpose
  - [ ] 3.4: Confirm the handler is NOT triggered for `MCPError` that are deliberately raised by tool handlers (those must pass through as-is, already formatted)
  - [ ] 3.5: Write a unit test that registers a tool which raises `RuntimeError("boom")`, calls it, and asserts the response shape matches the error envelope with `code="INTERNAL_ERROR"`

- [ ] Task 4: Implement recoverable vs. non-recoverable error semantics (AC: 2, 3)
  - [ ] 4.1: In `session/context.py`, define a `DrawingSession` stub dataclass with a `rollback()` method that logs `"rollback triggered"` (real implementation in Story 2-1+)
  - [ ] 4.2: In `server.py` (or a middleware function), after catching an `MCPError`, check `error.recoverable`: if `False`, call `session.rollback()` if a session is active
  - [ ] 4.3: Write an integration test in `tests/integration/test_error_contract.py` that:
    - Registers a tool that returns `MCPError(code=ErrorCode.CLOSURE_FAILED, recoverable=False)`
    - Registers a stub session with a mock `rollback()` method
    - Calls the tool and asserts `rollback()` was invoked exactly once
  - [ ] 4.4: Write a parallel test confirming that `MCPError(recoverable=True)` does NOT invoke `rollback()`
  - [ ] 4.5: Ensure the rollback hook is only invoked when a session is active (i.e. `ctx.get_state("session")` is not `None`)

- [ ] Task 5: Add remaining `ErrorCode` constants covering all 10 modules (AC: 4)
  - [ ] 5.1: Document the complete intended `ErrorCode` set in `errors.py` module docstring, grouped by domain
  - [ ] 5.2: Add module-specific codes: `AREA_CALC_FAILED`, `REPORT_GENERATION_FAILED`, `WORKFLOW_STEP_FAILED`, `ARCHIVE_WRITE_FAILED`, `RULE_ENGINE_ERROR`, `CONFIG_NOT_LOADED`
  - [ ] 5.3: Add `FILE_NOT_FOUND = "FILE_NOT_FOUND"` and `PERMISSION_DENIED = "PERMISSION_DENIED"` for file I/O error paths
  - [ ] 5.4: Write a unit test that iterates all `ErrorCode` class attributes and asserts each value is a non-empty string equal to its attribute name (e.g. `ErrorCode.LAYER_NOT_FOUND == "LAYER_NOT_FOUND"`)

- [ ] Task 6: Document the error contract for tool authors (AC: 1, 4, 5)
  - [ ] 6.1: Add a `# HOW TO USE` block comment at the top of `errors.py` showing the three canonical patterns: (a) recoverable error, (b) non-recoverable error, (c) unhandled exception wrapping
  - [ ] 6.2: Update `docs/tool-api-reference.md` with an "Error Contract" section showing the exact JSON schema of both success and error responses

## Dev Notes

### Critical Architecture Constraints

1. **NEVER return an inline error dict from a tool handler.** The only two allowed return shapes are `success_response(data)` and `MCPError(...).to_response()`. Inline dicts like `{"success": False, "error": "something went wrong"}` violate the contract and will break AI client parsing.
2. **`MCPError` is a dataclass, not an exception.** Do NOT raise `MCPError` — return it via `.to_response()`. If you need to raise and catch across stack frames, define a separate `MCPException(Exception)` that carries an `MCPError` payload (not required in this story, but document the distinction).
3. **The global exception handler must NOT swallow `SystemExit` or `KeyboardInterrupt`.** These must re-raise so the server process can exit cleanly.
4. **`recoverable: bool` directly controls rollback invocation.** This is a binary contract — there is no "partial rollback" or "warn only" mode. If `recoverable=False`, rollback is invoked unconditionally (unless no session is active).
5. **ErrorCode values MUST equal their attribute names exactly** (i.e. `LAYER_NOT_FOUND = "LAYER_NOT_FOUND"`). This is enforced by a unit test (Task 5.4). Drift between attribute name and string value causes silent protocol failures in AI client error parsing.
6. **FORBIDDEN:** `try/except Exception: pass`, swallowing exceptions silently, returning raw exception messages that contain internal file paths or stack traces to the client.

### Module / Component Notes

**Complete `src/lcs_cad_mcp/errors.py`:**

```python
"""
Structured MCP error contract.

HOW TO USE:
  # (a) Recoverable error — session stays intact
  return MCPError(code=ErrorCode.LAYER_NOT_FOUND, message="Layer 'walls' not found",
                  recoverable=True, suggested_action="Call layer_list to see available layers").to_response()

  # (b) Non-recoverable error — triggers rollback
  return MCPError(code=ErrorCode.CLOSURE_FAILED, message="Polygon is not closed",
                  recoverable=False).to_response()

  # (c) Success
  return success_response({"layer_count": 5})
"""
from dataclasses import dataclass, field


def success_response(data: dict | list | None = None) -> dict:
    """Return a standard success envelope. Use for ALL successful tool returns."""
    return {"success": True, "data": data, "error": None}


class ErrorCode:
    # Session
    SESSION_NOT_STARTED = "SESSION_NOT_STARTED"
    SESSION_ALREADY_ACTIVE = "SESSION_ALREADY_ACTIVE"
    # CAD Backend
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    DRAWING_OPEN_FAILED = "DRAWING_OPEN_FAILED"
    DRAWING_SAVE_FAILED = "DRAWING_SAVE_FAILED"
    SNAPSHOT_FAILED = "SNAPSHOT_FAILED"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    # Layer
    LAYER_NOT_FOUND = "LAYER_NOT_FOUND"
    LAYER_ALREADY_EXISTS = "LAYER_ALREADY_EXISTS"
    # Entity
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    ENTITY_INVALID = "ENTITY_INVALID"
    # Verification
    CLOSURE_FAILED = "CLOSURE_FAILED"
    GEOMETRY_INVALID = "GEOMETRY_INVALID"
    # DCR
    DCR_VIOLATION = "DCR_VIOLATION"
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_NOT_LOADED = "CONFIG_NOT_LOADED"
    # Area
    AREA_CALC_FAILED = "AREA_CALC_FAILED"
    # Reports
    REPORT_GENERATION_FAILED = "REPORT_GENERATION_FAILED"
    # Workflow
    WORKFLOW_STEP_FAILED = "WORKFLOW_STEP_FAILED"
    # Archive
    ARCHIVE_WRITE_FAILED = "ARCHIVE_WRITE_FAILED"
    # Rule Engine
    RULE_ENGINE_ERROR = "RULE_ENGINE_ERROR"
    # File I/O
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    # Generic
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_PARAMS = "INVALID_PARAMS"


@dataclass
class MCPError:
    code: str
    message: str = ""
    recoverable: bool = True
    suggested_action: str = ""

    def to_response(self) -> dict:
        return {
            "success": False,
            "data": None,
            "error": {
                "code": self.code,
                "message": self.message,
                "recoverable": self.recoverable,
                "suggested_action": self.suggested_action,
            },
        }
```

**Global exception handler pattern in `server.py`** (FastMCP 3.x approach — confirm API from installed source):

```python
# After mcp = FastMCP(...) instantiation:

@mcp.exception_handler(Exception)
async def handle_unhandled_exception(exc: Exception) -> dict:
    """Catch-all: wraps any unhandled exception in the standard error envelope."""
    if isinstance(exc, (SystemExit, KeyboardInterrupt)):
        raise  # Never swallow process-level signals
    from lcs_cad_mcp.errors import MCPError, ErrorCode
    return MCPError(
        code=ErrorCode.INTERNAL_ERROR,
        message=str(exc),
        recoverable=False,
        suggested_action="Check server logs for full traceback.",
    ).to_response()
```

Note: If FastMCP 3.x does not expose `mcp.exception_handler()`, wrap the tool execution body in `server.py`'s lifespan or use a decorator-based approach. The goal is: no raw traceback ever reaches the MCP client.

**`session/context.py` stub for rollback integration (Task 4.1):**

```python
"""Drawing session context. Full implementation in Story 2-1."""
from dataclasses import dataclass, field


@dataclass
class DrawingSession:
    drawing_path: str = ""
    _snapshot_data: bytes | None = field(default=None, repr=False)

    def rollback(self) -> None:
        """Revert to last snapshot. Real implementation in Story 2-1."""
        print(f"[DrawingSession] rollback triggered for {self.drawing_path}", flush=True)
```

### Project Structure Notes

Files modified or created in this story:

```
src/lcs_cad_mcp/
├── errors.py               # IMPLEMENT fully (was stub)
├── server.py               # MODIFY: attach global exception handler
└── session/
    └── context.py          # MODIFY: add DrawingSession stub with rollback()

tests/unit/
├── test_errors.py          # CREATE
└── test_server.py          # MODIFY: add exception handler tests

tests/integration/
└── test_error_contract.py  # CREATE

docs/
└── tool-api-reference.md   # MODIFY: add Error Contract section
```

### Dependencies

- **Story 1-1** must be complete: all stubs in place, `errors.py` skeleton with `MCPError` and `ErrorCode` class names defined.
- **Story 1-2** must be complete: `server.py` with `FastMCP` instance (`mcp`), `cad_ping` tool working — the global exception handler is attached to `mcp`.

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern (6-Step)"]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Error Contract"]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Enforcement Guidelines"]
- [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 1, Story 1-4]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

- `src/lcs_cad_mcp/errors.py`
- `src/lcs_cad_mcp/server.py`
- `src/lcs_cad_mcp/session/context.py`
- `tests/unit/test_errors.py`
- `tests/unit/test_server.py`
- `tests/integration/test_error_contract.py`
- `docs/tool-api-reference.md`
