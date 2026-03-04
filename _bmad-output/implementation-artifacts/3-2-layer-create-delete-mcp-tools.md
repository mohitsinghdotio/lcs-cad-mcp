# Story 3.2: `layer_create` and `layer_delete` MCP Tools

Status: ready-for-dev

## Story

As an **AI client**,
I want **to create and delete layers in the active drawing via MCP tools**,
so that **the drawing's layer structure can be built and managed programmatically with full error handling and rollback safety**.

## Acceptance Criteria

1. **AC1:** `layer_create(name, color, linetype, lineweight)` MCP tool creates a new layer in the active drawing via `LayerService`, propagating to both ezdxf and COM backends through `session.backend`.
2. **AC2:** Attempting to create a layer that already exists returns a structured error response with code `LAYER_ALREADY_EXISTS` — it does NOT raise an unhandled exception.
3. **AC3:** `layer_delete(name)` MCP tool removes a named layer from the active drawing; returns `LAYER_NOT_FOUND` if the layer does not exist; returns `LAYER_NOT_EMPTY` if the layer contains entities.
4. **AC4:** Both `layer_create` and `layer_delete` update the `LayerRegistry` (via `LayerService`) to reflect the change in memory immediately after the backend operation succeeds.
5. **AC5:** Both tools follow the 6-step tool handler pattern: (1) retrieve session from `ctx.get_state("session")`, (2) validate input params, (3) take snapshot (write operation), (4) call `LayerService`, (5) record to `event_log`, (6) return structured dict.
6. **AC6:** If no drawing session is active (`ctx.get_state("session")` returns `None`), both tools return `SESSION_NOT_STARTED` error without attempting backend access.
7. **AC7:** Unit tests cover: successful create, duplicate name error, successful delete, delete non-existent layer error, delete layer with entities error, and no-session error path.

## Tasks / Subtasks

- [ ] Task 1: Implement `LayerService.create_layer()` method (AC: 1, 2, 4)
  - [ ] 1.1: Add `create_layer(self, name: str, color: int = 7, linetype: str = "CONTINUOUS", lineweight: float = 0.25) -> LayerRecord` to `LayerService` in `service.py`
  - [ ] 1.2: Call `self.ensure_synced()` at the top of the method to populate registry from backend
  - [ ] 1.3: Check `self.registry.contains(name)` — if True, raise `MCPError(code=ErrorCode.LAYER_ALREADY_EXISTS, message=f"Layer '{name}' already exists", recoverable=True)`
  - [ ] 1.4: Call `self.session.backend.create_layer(name=name, color=color, linetype=linetype, lineweight=lineweight)`
  - [ ] 1.5: Construct a `LayerRecord` from the params and call `self.registry.add(record)` to keep in-memory registry in sync
  - [ ] 1.6: Return the new `LayerRecord`

- [ ] Task 2: Implement `LayerService.delete_layer()` method (AC: 3, 4)
  - [ ] 2.1: Add `delete_layer(self, name: str) -> None` to `LayerService`
  - [ ] 2.2: Call `self.ensure_synced()` at the top
  - [ ] 2.3: Check `self.registry.contains(name)` — if False, raise `MCPError(code=ErrorCode.LAYER_NOT_FOUND, message=f"Layer '{name}' not found", recoverable=True)`
  - [ ] 2.4: Call `self.session.backend.layer_has_entities(name)` — if True, raise `MCPError(code=ErrorCode.LAYER_NOT_EMPTY, message=f"Layer '{name}' contains entities; move or delete entities first", recoverable=True)`
  - [ ] 2.5: Call `self.session.backend.delete_layer(name)`
  - [ ] 2.6: Call `self.registry.remove(name)` to sync the in-memory registry

- [ ] Task 3: Add missing error codes to `errors.py` (AC: 2, 3)
  - [ ] 3.1: Open `src/lcs_cad_mcp/errors.py` and add to `ErrorCode`:
    - `LAYER_ALREADY_EXISTS = "LAYER_ALREADY_EXISTS"`
    - `LAYER_NOT_EMPTY = "LAYER_NOT_EMPTY"`
  - [ ] 3.2: Verify `LAYER_NOT_FOUND` and `SESSION_NOT_STARTED` already exist (from Story 1-1 stub); add if missing

- [ ] Task 4: Implement `layer_create` MCP tool handler in `tools.py` (AC: 1, 2, 5, 6)
  - [ ] 4.1: Open `src/lcs_cad_mcp/modules/layers/tools.py`
  - [ ] 4.2: Define async handler `async def layer_create(name: str, color: int = 7, linetype: str = "CONTINUOUS", lineweight: float = 0.25, ctx: Context = ...) -> dict`:
    - [ ] 4.2.1: **Step 1** — `session = ctx.get_state("session")` — if `None`, return `MCPError(code=ErrorCode.SESSION_NOT_STARTED, ...).to_response()`
    - [ ] 4.2.2: **Step 2** — validate `name` not empty; validate `color` is 1–256; if invalid, return `MCPError(code=ErrorCode.INVALID_PARAMS, ...).to_response()`
    - [ ] 4.2.3: **Step 3** — call `session.snapshot.take()` (write operation, before mutation)
    - [ ] 4.2.4: **Step 4** — call `LayerService(session).create_layer(name, color, linetype, lineweight)`, catching `MCPError` and returning `.to_response()` on failure
    - [ ] 4.2.5: **Step 5** — call `session.event_log.record(action="layer_create", details={"name": name, "color": color, "linetype": linetype})`
    - [ ] 4.2.6: **Step 6** — return `{"success": True, "data": {"layer": record.to_dict()}, "error": None}`

- [ ] Task 5: Implement `layer_delete` MCP tool handler in `tools.py` (AC: 3, 5, 6)
  - [ ] 5.1: Define async handler `async def layer_delete(name: str, ctx: Context = ...) -> dict`:
    - [ ] 5.1.1: **Step 1** — retrieve session from `ctx.get_state("session")`; return `SESSION_NOT_STARTED` error if None
    - [ ] 5.1.2: **Step 2** — validate `name` not empty; return `INVALID_PARAMS` error if blank
    - [ ] 5.1.3: **Step 3** — call `session.snapshot.take()` (write operation)
    - [ ] 5.1.4: **Step 4** — call `LayerService(session).delete_layer(name)`, catching `MCPError`
    - [ ] 5.1.5: **Step 5** — call `session.event_log.record(action="layer_delete", details={"name": name})`
    - [ ] 5.1.6: **Step 6** — return `{"success": True, "data": {"deleted_layer": name}, "error": None}`

- [ ] Task 6: Register tools in `layers/__init__.py` (AC: 1, 3)
  - [ ] 6.1: Open `src/lcs_cad_mcp/modules/layers/__init__.py`
  - [ ] 6.2: Import `layer_create` and `layer_delete` from `tools.py`
  - [ ] 6.3: In `register(mcp)`, use `mcp.tool()(layer_create)` and `mcp.tool()(layer_delete)` to register both tools with FastMCP
  - [ ] 6.4: Confirm tool names exposed to MCP clients are `layer_create` and `layer_delete` (FastMCP uses the function name as tool name by default)

- [ ] Task 7: Write unit tests (AC: 7)
  - [ ] 7.1: Create `tests/unit/modules/layers/test_layer_create_delete.py`
  - [ ] 7.2: Test `LayerService.create_layer()` success — verify `MockCADBackend.create_layer` was called and registry contains the new layer
  - [ ] 7.3: Test `LayerService.create_layer()` duplicate — registry already has the layer; verify `MCPError` with `LAYER_ALREADY_EXISTS` is raised
  - [ ] 7.4: Test `LayerService.delete_layer()` success — registry has the layer, backend has no entities on it; verify `MockCADBackend.delete_layer` called and registry no longer contains layer
  - [ ] 7.5: Test `LayerService.delete_layer()` not found — verify `MCPError` with `LAYER_NOT_FOUND` raised
  - [ ] 7.6: Test `LayerService.delete_layer()` not empty — `MockCADBackend.layer_has_entities` returns True; verify `MCPError` with `LAYER_NOT_EMPTY` raised
  - [ ] 7.7: Test `layer_create` handler with no session — `ctx.get_state("session")` returns None; verify response has `success: False, error.code: "SESSION_NOT_STARTED"`
  - [ ] 7.8: Test `layer_delete` handler with no session — same as 7.7 pattern
  - [ ] 7.9: Verify snapshot is taken before service call in both handlers (mock `session.snapshot.take` and assert it was called)

## Dev Notes

### Critical Architecture Constraints

1. **6-Step Tool Handler is mandatory** — both `layer_create` and `layer_delete` must follow the exact sequence: (1) session, (2) validate, (3) snapshot, (4) service, (5) event_log, (6) return. Do NOT collapse steps or reorder them. Snapshot must come BEFORE any mutation.
2. **Never import `ezdxf` in `modules/layers/`** — all backend interaction goes exclusively through `session.backend`. The comment `# CAD access: session.backend only — never import ezdxf` must appear at the top of both `service.py` and `tools.py`.
3. **`MCPError` is a dataclass, not an exception** — `MCPError` is raised via `raise` (since service methods raise it) or returned via `.to_response()` at the tool layer. The tool handler must `try`/`except MCPError` around the service call and return `.to_response()` on catch.
4. **`session.snapshot.take()` is a write guard** — it must always be called before any mutation (create, delete, rename, modify). Read-only tools (layer_list, layer_get) do NOT call snapshot.
5. **Tool name convention** — FastMCP uses the Python function name as the MCP tool name. Function names `layer_create` and `layer_delete` must match exactly — no `_handler` suffix, no aliases.
6. **`CADBackend` must expose `create_layer()`, `delete_layer()`, `layer_has_entities()`** — verify these exist in `backends/base.py` from Story 2-1. If method signatures differ, use the exact signature defined there.

### Module/Component Notes

**Complete 6-step tool handler example (`layer_create`):**
```python
# tools.py
# CAD access: session.backend only — never import ezdxf
from fastmcp import Context
from lcs_cad_mcp.errors import MCPError, ErrorCode
from lcs_cad_mcp.modules.layers.service import LayerService


async def layer_create(
    name: str,
    color: int = 7,
    linetype: str = "CONTINUOUS",
    lineweight: float = 0.25,
    ctx: Context = Context(),
) -> dict:
    # Step 1: retrieve session
    session = ctx.get_state("session")
    if session is None:
        return MCPError(
            code=ErrorCode.SESSION_NOT_STARTED,
            message="No active drawing session. Call cad_open or cad_create first.",
            recoverable=True,
            suggested_action="Call cad_open or cad_create to start a session.",
        ).to_response()

    # Step 2: validate inputs
    if not name or not name.strip():
        return MCPError(
            code=ErrorCode.INVALID_PARAMS,
            message="Layer name cannot be empty.",
            recoverable=True,
        ).to_response()
    if not (1 <= color <= 256):
        return MCPError(
            code=ErrorCode.INVALID_PARAMS,
            message=f"Color must be 1–256 (ACI), got {color}.",
            recoverable=True,
        ).to_response()

    # Step 3: snapshot (write operation — must come before mutation)
    session.snapshot.take()

    # Step 4: service call
    try:
        record = LayerService(session).create_layer(name, color, linetype, lineweight)
    except MCPError as err:
        return err.to_response()

    # Step 5: event log
    session.event_log.record(
        action="layer_create",
        details={"name": name, "color": color, "linetype": linetype, "lineweight": lineweight},
    )

    # Step 6: return success
    return {"success": True, "data": {"layer": record.to_dict()}, "error": None}
```

**`LayerService` create/delete methods:**
```python
# service.py
# CAD access: session.backend only — never import ezdxf
from lcs_cad_mcp.errors import MCPError, ErrorCode
from lcs_cad_mcp.modules.layers.registry import LayerRegistry
from lcs_cad_mcp.modules.layers.schemas import LayerRecord


class LayerService:
    def __init__(self, session) -> None:
        self.session = session
        self.registry = LayerRegistry()
        self._synced = False

    def ensure_synced(self) -> None:
        if not self._synced:
            self.registry.sync_from_backend(self.session.backend)
            self._synced = True

    def create_layer(
        self,
        name: str,
        color: int = 7,
        linetype: str = "CONTINUOUS",
        lineweight: float = 0.25,
    ) -> LayerRecord:
        self.ensure_synced()
        if self.registry.contains(name):
            raise MCPError(
                code=ErrorCode.LAYER_ALREADY_EXISTS,
                message=f"Layer '{name}' already exists in the drawing.",
                recoverable=True,
                suggested_action="Use layer_get to inspect the existing layer.",
            )
        self.session.backend.create_layer(
            name=name, color=color, linetype=linetype, lineweight=lineweight
        )
        record = LayerRecord(name=name, color=color, linetype=linetype, lineweight=lineweight)
        self.registry.add(record)
        return record

    def delete_layer(self, name: str) -> None:
        self.ensure_synced()
        if not self.registry.contains(name):
            raise MCPError(
                code=ErrorCode.LAYER_NOT_FOUND,
                message=f"Layer '{name}' does not exist in the drawing.",
                recoverable=True,
                suggested_action="Call layer_list to see available layers.",
            )
        if self.session.backend.layer_has_entities(name):
            raise MCPError(
                code=ErrorCode.LAYER_NOT_EMPTY,
                message=f"Layer '{name}' contains entities and cannot be deleted.",
                recoverable=True,
                suggested_action="Move or delete all entities on this layer first.",
            )
        self.session.backend.delete_layer(name)
        self.registry.remove(name)
```

**`__init__.py` registration:**
```python
# layers/__init__.py
from lcs_cad_mcp.modules.layers.tools import layer_create, layer_delete
# (layer_list, layer_get, etc. registered in Story 3-3)


def register(mcp) -> None:
    """Register all layer MCP tools with the FastMCP server."""
    mcp.tool()(layer_create)
    mcp.tool()(layer_delete)
```

### Project Structure Notes

Files created or modified by this story:

```
src/lcs_cad_mcp/
├── errors.py                          # MODIFY — add LAYER_ALREADY_EXISTS, LAYER_NOT_EMPTY error codes
└── modules/layers/
    ├── __init__.py                    # MODIFY — register layer_create, layer_delete
    ├── schemas.py                     # unchanged (from 3-1)
    ├── registry.py                    # unchanged (from 3-1)
    ├── service.py                     # MODIFY — add create_layer(), delete_layer()
    └── tools.py                       # MODIFY — implement layer_create, layer_delete handlers

tests/unit/modules/layers/
└── test_layer_create_delete.py        # NEW — unit tests for create/delete
```

### MCP Tool Response Contract

All tools return a consistent dict structure. Do NOT deviate:
```python
# Success:
{"success": True, "data": {...}, "error": None}

# Failure:
{
    "success": False,
    "data": None,
    "error": {
        "code": "LAYER_ALREADY_EXISTS",
        "message": "...",
        "recoverable": True,
        "suggested_action": "...",
    }
}
```

### Dependencies

- **Story 3-1** (LayerRecord, LayerRegistry, LayerService skeleton) — this story extends `service.py` and `tools.py` stubs from 3-1.
- **Story 2-4** (snapshot mechanism in `session/snapshot.py`) — `session.snapshot.take()` must be callable. If the snapshot API is different (e.g., `session.take_snapshot()`), use the actual API from that story.
- **Story 2-1/2-3** (CADBackend Protocol + ezdxf backend) — `backend.create_layer()`, `backend.delete_layer()`, `backend.layer_has_entities()` must exist with those exact signatures. Confirm against `backends/base.py`.
- **Story 1-2** (FastMCP server + `Context` import) — `Context` is imported from `fastmcp`; confirm the import path used in other tool files.
- **`conftest.py`** must provide `MockCADBackend` with stubs for `create_layer()`, `delete_layer()`, `layer_has_entities()`.

### MockCADBackend Extension for Tests

```python
class MockCADBackend:
    def __init__(self, layers=None, layers_with_entities=None):
        self._layers = layers or []
        self._layers_with_entities = set(layers_with_entities or [])
        self.calls = []  # call log for assertion

    def list_layers(self) -> list[dict]:
        return self._layers

    def create_layer(self, name, color, linetype, lineweight) -> None:
        self.calls.append(("create_layer", name))
        self._layers.append({"name": name, "color": color, "linetype": linetype,
                              "lineweight": lineweight, "is_on": True,
                              "is_frozen": False, "is_locked": False})

    def delete_layer(self, name: str) -> None:
        self.calls.append(("delete_layer", name))
        self._layers = [l for l in self._layers if l["name"].lower() != name.lower()]

    def layer_has_entities(self, name: str) -> bool:
        return name.lower() in {n.lower() for n in self._layers_with_entities}
```

### References

- 6-step tool handler pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- CAD backend access pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "CAD Backend Access"]
- Error code naming convention: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Naming Conventions"]
- MCP tool response contract: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "MCP Tool Response Structure"]
- Story definition: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 3, Story 3-2]
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

- `src/lcs_cad_mcp/errors.py`
- `src/lcs_cad_mcp/modules/layers/__init__.py`
- `src/lcs_cad_mcp/modules/layers/service.py`
- `src/lcs_cad_mcp/modules/layers/tools.py`
- `tests/unit/modules/layers/test_layer_create_delete.py`
