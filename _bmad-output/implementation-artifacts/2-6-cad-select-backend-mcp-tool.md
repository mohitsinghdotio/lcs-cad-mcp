# Story 2.6: `cad_select_backend` MCP Tool

Status: ready-for-dev

## Story

As an **AI client**,
I want **to select the CAD backend at runtime via an MCP tool call**,
so that **the same MCP server works with or without AutoCAD installed, switching between headless ezdxf and live COM modes on demand** (FR5).

## Acceptance Criteria

1. **AC1:** `cad_select_backend(backend: Literal["ezdxf", "com"]) -> dict` is a registered MCP tool in `modules/cad/tools.py`; it switches the active session's backend by calling `CadService.select_backend(backend_name, session)`; returns `{ "success": True, "data": { "backend": "ezdxf", "available": True }, "error": null }` on success.
2. **AC2:** If `"com"` is requested on a non-Windows platform OR AutoCAD is not running (`COMBackend.is_available()` returns `False`), the tool returns a structured error response: `{ "success": False, "data": null, "error": { "code": "BACKEND_UNAVAILABLE", "message": "...", "recoverable": True, "suggested_action": "Use ezdxf backend or launch AutoCAD" } }` — the existing backend is left unchanged.
3. **AC3:** Backend selection via `CAD_BACKEND` env var at server startup is honoured — `CadService.select_backend` reads the default from `Settings().cad_backend` when called with no explicit override; the tool result reflects the actual backend in use after startup.
4. **AC4:** If a drawing is currently open when the backend is switched, the tool closes it (calling `session.close_drawing()`) and includes a warning field in the response: `{ "warning": "Active drawing closed during backend switch. Unsaved changes are lost." }`.
5. **AC5:** `modules/cad/__init__.py` contains only a `register(mcp: FastMCP) -> None` function that calls `tools.register(mcp)` — no business logic.
6. **AC6:** `modules/cad/tools.py` follows the 6-step tool handler pattern (steps 1 and 2 only — no snapshot for read/config tools, but session must exist): (1) get session from `ctx.get_state("session")`, (2) validate `backend` param via Pydantic, (3) skip snapshot (backend selection is not a write operation on the drawing document), (4) call `CadService(session).select_backend(backend_name)`, (5) record event in `session.event_log`, (6) return structured dict.
7. **AC7:** `modules/cad/service.py` implements `CadService.select_backend(backend_name: str) -> dict` using `BackendFactory.get(backend_name)` to instantiate the new backend; replaces `session.backend` and re-initialises `session.snapshots` with the new backend reference.
8. **AC8:** Unit tests cover: select ezdxf (success), select com on non-Windows (error, existing backend unchanged), select com with unavailable AutoCAD (error), select with open drawing (warning in response), select invalid backend name (validation error).

## Tasks / Subtasks

- [ ] Task 1: Implement `CadSelectBackendInput` Pydantic schema in `modules/cad/schemas.py` (AC: 6)
  - [ ] 1.1: Replace the stub `modules/cad/schemas.py` with a proper schema file
  - [ ] 1.2: Define `CadSelectBackendInput(BaseModel)` with field `backend: Literal["ezdxf", "com"]` and a field description: `Field(..., description="CAD backend to activate. 'ezdxf' for headless, 'com' for live AutoCAD (Windows only).")`
  - [ ] 1.3: Define `CadSelectBackendResult(BaseModel)` with fields: `backend: str`, `available: bool`, `warning: str | None = None`
  - [ ] 1.4: Define `CadOpenDrawingInput(BaseModel)` with field `path: str` (stub for future tools in this module — do not leave empty)
  - [ ] 1.5: Define `CadNewDrawingInput(BaseModel)` with fields `name: str = "Untitled"` and `units: Literal["metric", "imperial"] = "metric"` (stub)
  - [ ] 1.6: Define `CadSaveDrawingInput(BaseModel)` with fields `path: str` and `dxf_version: Literal["R12", "R2000", "R2007", "R2010", "R2013", "R2018"] = "R2018"` (stub)

- [ ] Task 2: Implement `CadService.select_backend` in `modules/cad/service.py` (AC: 7)
  - [ ] 2.1: Replace the stub `modules/cad/service.py` with the `CadService` class
  - [ ] 2.2: Define `class CadService:` with constructor `__init__(self, session: DrawingSession)` — store `self._session = session`
  - [ ] 2.3: Implement `select_backend(self, backend_name: str) -> dict`:
    - Call `BackendFactory.get(backend_name)` to get a new backend instance
    - Call `new_backend.is_available()` — if `False`, raise `MCPError(ErrorCode.BACKEND_UNAVAILABLE, message=f"Backend '{backend_name}' is not available on this system", recoverable=True, suggested_action="Use ezdxf backend or ensure AutoCAD is running")`
    - Check `self._session.is_drawing_open` — if `True`, call `self._session.close_drawing()` and set `warning = "Active drawing closed during backend switch. Unsaved changes are lost."`
    - Replace `self._session.backend = new_backend`
    - Re-initialise `self._session.snapshots = SnapshotManager(backend=new_backend)`
    - Return `{"backend": backend_name, "available": True, "warning": warning}`
  - [ ] 2.4: Add stub methods for later tool stories: `open_drawing`, `new_drawing`, `save_drawing`, `get_metadata` — each raises `NotImplementedError("Implemented in Story 2-2 / 2-3")` for now (these are filled out in parallel with the backend stories; here they are explicit stubs)

- [ ] Task 3: Implement `cad_select_backend` tool in `modules/cad/tools.py` (AC: 1, 6)
  - [ ] 3.1: Replace the stub `modules/cad/tools.py` with the actual tool registration module
  - [ ] 3.2: Define `register(mcp: FastMCP) -> None` function that uses `@mcp.tool()` decorator to register tools
  - [ ] 3.3: Implement `async def cad_select_backend(backend: str, ctx: Context) -> dict`:
    - Step 1: `session: DrawingSession | None = ctx.get_state("session")` — if None, return `MCPError(SESSION_NOT_STARTED).to_response()`
    - Step 2: Validate via `CadSelectBackendInput(backend=backend)` — catch `ValidationError` and return structured error
    - Step 3: Skip snapshot (not a drawing write operation)
    - Step 4: `result = CadService(session).select_backend(backend)` — catch `MCPError` and return `.to_response()`
    - Step 5: `session.event_log.record("cad_select_backend", {"backend": backend})` (no-op if event_log is stub)
    - Step 6: Return `{"success": True, "data": result, "error": None}`
  - [ ] 3.4: Add `@mcp.tool()` decorator with `name="cad_select_backend"` and `description="Switch the active CAD backend between headless ezdxf and live AutoCAD COM. On non-Windows, only 'ezdxf' is available."`
  - [ ] 3.5: Add type annotations to the tool function matching FastMCP 3.x tool signature conventions (ctx: `fastmcp.Context`)

- [ ] Task 4: Implement `modules/cad/__init__.py` register function (AC: 5)
  - [ ] 4.1: Replace the stub `modules/cad/__init__.py` with:
    ```python
    """CAD module — drawing lifecycle and backend selection tools."""
    from fastmcp import FastMCP
    from lcs_cad_mcp.modules.cad import tools

    def register(mcp: FastMCP) -> None:
        """Register all CAD module tools with the MCP server."""
        tools.register(mcp)
    ```
  - [ ] 4.2: Confirm no business logic, no imports of ezdxf, no service calls in `__init__.py`

- [ ] Task 5: Wire `modules/cad` into `server.py` and `__main__.py` (AC: 3)
  - [ ] 5.1: In `server.py` (or `__main__.py`), import and call `from lcs_cad_mcp.modules.cad import register as register_cad` and `register_cad(mcp)`
  - [ ] 5.2: Confirm the MCP server starts without error after wiring: `python -m lcs_cad_mcp` should log tool registration
  - [ ] 5.3: Confirm `cad_select_backend` appears in `tools/list` response from the MCP server

- [ ] Task 6: Handle initial session creation (AC: 3)
  - [ ] 6.1: Implement session initialisation on first MCP connection in `server.py` using FastMCP lifecycle hooks or the `on_connect` pattern; create a `DrawingSession` with the default backend from `Settings().cad_backend`; call `ctx.set_state("session", session)`
  - [ ] 6.2: The default backend from env var must be validated: if `CAD_BACKEND=com` on non-Windows, log a WARNING and fall back to `ezdxf`; do NOT crash the server on startup
  - [ ] 6.3: Add `BACKEND_SELECTED_AT_STARTUP` to event log on session creation

- [ ] Task 7: Write unit tests in `tests/unit/modules/cad/test_cad_select_backend.py` (AC: 8)
  - [ ] 7.1: Create `tests/unit/modules/__init__.py`, `tests/unit/modules/cad/__init__.py`, `tests/unit/modules/cad/test_cad_select_backend.py`
  - [ ] 7.2: Test `CadService(mock_session).select_backend("ezdxf")` returns `{"backend": "ezdxf", "available": True, "warning": None}` when `mock_session.is_drawing_open = False`
  - [ ] 7.3: Test `CadService(mock_session).select_backend("ezdxf")` with `mock_session.is_drawing_open = True` returns `warning` text and calls `mock_session.close_drawing()`
  - [ ] 7.4: Test `CadService.select_backend("com")` raises `MCPError(BACKEND_UNAVAILABLE)` when `COMBackend.is_available()` returns `False` (monkeypatch `is_available`)
  - [ ] 7.5: Test `CadService.select_backend("unknown")` raises `MCPError(BACKEND_UNAVAILABLE)` from `BackendFactory.get()`
  - [ ] 7.6: Test tool handler: mock `ctx.get_state("session")` returning `None` → response contains `error.code == "SESSION_NOT_STARTED"`
  - [ ] 7.7: Test tool handler: mock session with valid backend → response `success: True`, `data.backend == "ezdxf"`
  - [ ] 7.8: Test that after `select_backend`, `session.snapshots._backend` is the new backend instance (not the old one)

- [ ] Task 8: Verify full test suite and ruff lint (AC: all)
  - [ ] 8.1: Run `ruff check src/lcs_cad_mcp/modules/cad/` — zero errors
  - [ ] 8.2: Run `pytest tests/unit/modules/cad/ -v` — all tests pass
  - [ ] 8.3: Run `pytest tests/unit/ -v` — no regressions across all Epic 2 stories
  - [ ] 8.4: Run `python -m lcs_cad_mcp` (or equivalent server start) and confirm `cad_select_backend` appears in tool list

## Dev Notes

### Critical Architecture Constraints

1. **`modules/cad/__init__.py` contains ONLY `register(mcp)`** — no service calls, no imports of ezdxf, no backend logic. This is a hard architecture rule. The `__init__.py` is a registration entry point only.
2. **`tools.py` is thin** — no business logic in `tools.py`. The tool handler validates input, delegates to `CadService`, and formats the response. All logic lives in `service.py`.
3. **`cad_select_backend` does NOT take a snapshot** — It is a configuration operation, not a drawing write operation. The 6-step pattern's step 3 (snapshot) is explicitly skipped. Document this in an inline comment.
4. **Session is per-connection, not global** — `ctx.get_state("session")` returns the `DrawingSession` for the current connection only. Different MCP clients can have different active backends simultaneously. Never use a module-level global for the session.
5. **`select_backend` replaces the backend AND re-creates the SnapshotManager** — After switching backends, `session.snapshots` must be re-initialised with the new backend reference. Old snapshots from the previous backend are meaningless and must be discarded.
6. **FORBIDDEN in this story:** drawing entity operations, layer operations, PreDCR logic, inline error dicts (use `MCPError.to_response()`), MCP-to-MCP calls.

### Module/Component Notes

**`modules/cad/` full file structure after this story:**

```
modules/cad/
├── __init__.py     # register(mcp) only
├── tools.py        # @mcp.tool() decorators — thin handlers
├── service.py      # CadService class — business logic
└── schemas.py      # Pydantic input/output models
```

**FastMCP 3.x tool registration pattern** (tools.py):
```python
from fastmcp import FastMCP, Context
from lcs_cad_mcp.modules.cad.schemas import CadSelectBackendInput
from lcs_cad_mcp.modules.cad.service import CadService
from lcs_cad_mcp.session.context import DrawingSession
from lcs_cad_mcp.errors import MCPError, ErrorCode


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="cad_select_backend",
              description="Switch the active CAD backend between headless ezdxf "
                          "and live AutoCAD COM. On non-Windows, only 'ezdxf' is available.")
    async def cad_select_backend(backend: str, ctx: Context) -> dict:
        # Step 1: get session
        session: DrawingSession | None = ctx.get_state("session")
        if session is None:
            return MCPError(code=ErrorCode.SESSION_NOT_STARTED,
                            message="No active session. Start the server first.",
                            recoverable=False).to_response()
        # Step 2: validate input
        try:
            validated = CadSelectBackendInput(backend=backend)
        except Exception as e:
            return MCPError(code=ErrorCode.INVALID_PARAMS,
                            message=str(e), recoverable=True).to_response()
        # Step 3: skip snapshot (config-only operation, no drawing mutation)
        # Step 4: delegate to service
        try:
            result = CadService(session).select_backend(validated.backend)
        except MCPError as e:
            return e.to_response()
        # Step 5: record event
        if hasattr(session, "event_log"):
            session.event_log.record("cad_select_backend", {"backend": validated.backend})
        # Step 6: return success
        return {"success": True, "data": result, "error": None}
```

**Session initialisation in `server.py`** (or FastMCP lifecycle hook):
```python
from fastmcp import FastMCP
from lcs_cad_mcp.settings import Settings
from lcs_cad_mcp.session.context import DrawingSession
from lcs_cad_mcp.backends import BackendFactory

mcp = FastMCP("lcs-cad-mcp")

@mcp.on_connect()
async def on_connect(ctx):
    settings = Settings()
    backend = BackendFactory.get(settings.cad_backend)
    if not backend.is_available():
        import logging
        logging.warning("Default backend '%s' not available, falling back to ezdxf",
                        settings.cad_backend)
        backend = BackendFactory.get("ezdxf")
    session = DrawingSession(backend=backend)
    ctx.set_state("session", session)
```

### Project Structure Notes

```
src/lcs_cad_mcp/
├── modules/
│   └── cad/
│       ├── __init__.py   # THIS STORY — register() only
│       ├── tools.py      # THIS STORY — cad_select_backend tool + stubs
│       ├── service.py    # THIS STORY — CadService.select_backend + method stubs
│       └── schemas.py    # THIS STORY — input/output Pydantic models
└── server.py             # UPDATED — session initialisation on connect
tests/
└── unit/
    └── modules/
        └── cad/
            ├── __init__.py
            └── test_cad_select_backend.py   # THIS STORY
```

### Dependencies

- **Story 1-2** (MCP server core): `FastMCP` instance and `server.py` must exist; the `@mcp.tool()` registration pattern must work; `ctx.get_state()` / `ctx.set_state()` available (FastMCP 3.x).
- **Story 1-4** (error response contract): `MCPError.to_response()` format must be established before tools return structured errors.
- **Story 1-5** (Pydantic validation): `CadSelectBackendInput` uses Pydantic v2; validation error handling pattern established.
- **Story 2-1** (CADBackend Protocol): `BackendFactory.get()` must work; `CADBackend.is_available()` called in `CadService.select_backend`.
- **Story 2-4** (snapshot/rollback): `DrawingSession` and `SnapshotManager` must be fully implemented; `session.close_drawing()` and `session.snapshots` must work correctly when backend is switched.
- **Story 2-5** (COM backend): `COMBackend.is_available()` called during backend validation; `BackendFactory.get("com")` must be registered (even if it raises on non-Windows).

### References

- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 2, Story 2-6]
- FR5 (backend selection), FR44 (env var backend): [Source: `_bmad-output/planning-artifacts/architecture.md`]
- 6-step tool handler pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- FastMCP 3.x tool registration: https://github.com/jlowin/fastmcp (v3.x docs)
- Module pattern (`__init__.py` register-only): [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Module Pattern"]
- Anti-patterns: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Enforcement Guidelines"]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/cad/__init__.py`
- `src/lcs_cad_mcp/modules/cad/tools.py`
- `src/lcs_cad_mcp/modules/cad/service.py`
- `src/lcs_cad_mcp/modules/cad/schemas.py`
- `src/lcs_cad_mcp/server.py` (updated: session initialisation on connect)
- `tests/unit/modules/__init__.py`
- `tests/unit/modules/cad/__init__.py`
- `tests/unit/modules/cad/test_cad_select_backend.py`
