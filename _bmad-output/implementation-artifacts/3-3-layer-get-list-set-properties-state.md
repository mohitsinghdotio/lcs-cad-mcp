# Story 3.3: `layer_get`, `layer_list`, `layer_set_properties`, and `layer_set_state` MCP Tools

Status: ready-for-dev

## Story

As an **AI client**,
I want **to query layer details and modify layer properties and state via MCP tools**,
so that **the AI can inspect, verify, and adjust the full configuration of any layer in the active drawing**.

## Acceptance Criteria

1. **AC1:** `layer_get(name)` returns the full `LayerRecord` for the named layer as a structured dict; returns `LAYER_NOT_FOUND` error if the layer does not exist.
2. **AC2:** `layer_list(filter_prefix?, filter_frozen?, filter_locked?)` returns all layers in the active drawing as a list of `LayerRecord` dicts, optionally filtered by name prefix or boolean state flags.
3. **AC3:** `layer_set_color(name, color)`, `layer_set_linetype(name, linetype)` (together exposed as `layer_set_properties` or as individual tools per architecture naming) update the respective layer property via `LayerService` → `session.backend`; each requires snapshot before mutation.
4. **AC4:** `layer_freeze(name)`, `layer_thaw(name)`, `layer_lock(name)`, `layer_unlock(name)` toggle layer visibility/lock state via `LayerService` → `session.backend`; each requires snapshot before mutation.
5. **AC5:** All read-only tools (`layer_get`, `layer_list`) return `SESSION_NOT_STARTED` error if no drawing session is active; they do NOT take a snapshot (read-only, no mutation).
6. **AC6:** All write tools (`layer_set_color`, `layer_set_linetype`, `layer_freeze`, `layer_thaw`, `layer_lock`, `layer_unlock`) follow the full 6-step handler pattern including snapshot; they return `SESSION_NOT_STARTED` if no session active.
7. **AC7:** Unit tests cover all 8 tools: happy path, `LAYER_NOT_FOUND` error path, `SESSION_NOT_STARTED` error path, and filter logic for `layer_list`.

## Tasks / Subtasks

- [ ] Task 1: Implement `LayerService` read methods (AC: 1, 2)
  - [ ] 1.1: Add `get_layer(self, name: str) -> LayerRecord` to `LayerService`:
    - Call `self.ensure_synced()`
    - Lookup `self.registry.get(name)` — if None, raise `MCPError(code=ErrorCode.LAYER_NOT_FOUND, ...)`
    - Return the `LayerRecord`
  - [ ] 1.2: Add `list_layers(self, filter_prefix: str | None = None, filter_frozen: bool | None = None, filter_locked: bool | None = None) -> list[LayerRecord]` to `LayerService`:
    - Call `self.ensure_synced()`
    - Start with `layers = self.registry.all()`
    - Apply `filter_prefix`: keep layers where `record.name.lower().startswith(filter_prefix.lower())` if provided
    - Apply `filter_frozen`: keep layers where `record.is_frozen == filter_frozen` if provided
    - Apply `filter_locked`: keep layers where `record.is_locked == filter_locked` if provided
    - Return filtered list

- [ ] Task 2: Implement `LayerService` property write methods (AC: 3)
  - [ ] 2.1: Add `set_color(self, name: str, color: int) -> LayerRecord`:
    - `self.ensure_synced()`
    - Raise `LAYER_NOT_FOUND` if layer absent
    - Validate `color` in range 1–256; raise `INVALID_PARAMS` if not
    - Call `self.session.backend.set_layer_color(name, color)`
    - Update `self.registry.get(name).color = color`
    - Return updated `LayerRecord`
  - [ ] 2.2: Add `set_linetype(self, name: str, linetype: str) -> LayerRecord`:
    - Same guard pattern (session, lookup, validate non-empty linetype)
    - Call `self.session.backend.set_layer_linetype(name, linetype)`
    - Update registry record in place
    - Return updated `LayerRecord`

- [ ] Task 3: Implement `LayerService` state write methods (AC: 4)
  - [ ] 3.1: Add `freeze_layer(self, name: str) -> LayerRecord`:
    - `self.ensure_synced()`, `LAYER_NOT_FOUND` guard
    - Call `self.session.backend.freeze_layer(name)`
    - Set `self.registry.get(name).is_frozen = True`
    - Return `LayerRecord`
  - [ ] 3.2: Add `thaw_layer(self, name: str) -> LayerRecord`:
    - Same pattern; call `self.session.backend.thaw_layer(name)`; set `is_frozen = False`
  - [ ] 3.3: Add `lock_layer(self, name: str) -> LayerRecord`:
    - Same pattern; call `self.session.backend.lock_layer(name)`; set `is_locked = True`
  - [ ] 3.4: Add `unlock_layer(self, name: str) -> LayerRecord`:
    - Same pattern; call `self.session.backend.unlock_layer(name)`; set `is_locked = False`

- [ ] Task 4: Implement `layer_get` MCP tool handler (AC: 1, 5)
  - [ ] 4.1: Add `async def layer_get(name: str, ctx: Context = ...) -> dict` in `tools.py`:
    - **Step 1**: session guard — `SESSION_NOT_STARTED` if None
    - **Step 2**: validate `name` not empty — `INVALID_PARAMS` if blank
    - *(No Step 3 — read-only, no snapshot)*
    - **Step 4**: `LayerService(session).get_layer(name)`, catch `MCPError`
    - **Step 5**: `session.event_log.record(action="layer_get", details={"name": name})`
    - **Step 6**: return `{"success": True, "data": {"layer": record.to_dict()}, "error": None}`

- [ ] Task 5: Implement `layer_list` MCP tool handler (AC: 2, 5)
  - [ ] 5.1: Add `async def layer_list(filter_prefix: str | None = None, filter_frozen: bool | None = None, filter_locked: bool | None = None, ctx: Context = ...) -> dict` in `tools.py`:
    - **Step 1**: session guard
    - **Step 2**: no param validation needed (all optional)
    - *(No snapshot — read-only)*
    - **Step 4**: `LayerService(session).list_layers(filter_prefix, filter_frozen, filter_locked)`, catch `MCPError`
    - **Step 5**: log `action="layer_list"` with filter details
    - **Step 6**: return `{"success": True, "data": {"layers": [r.to_dict() for r in records], "count": len(records)}, "error": None}`

- [ ] Task 6: Implement property write tool handlers (AC: 3, 6)
  - [ ] 6.1: Add `async def layer_set_color(name: str, color: int, ctx: Context = ...) -> dict` (6-step, with snapshot):
    - Steps 1-2 (session, validate color 1-256), Step 3 (snapshot), Step 4 (service), Step 5 (event_log), Step 6 (return updated layer)
  - [ ] 6.2: Add `async def layer_set_linetype(name: str, linetype: str, ctx: Context = ...) -> dict` (6-step, with snapshot):
    - Steps 1-2 (session, validate linetype non-empty), Step 3 (snapshot), Step 4 (service), Step 5, Step 6

- [ ] Task 7: Implement state write tool handlers (AC: 4, 6)
  - [ ] 7.1: Add `async def layer_freeze(name: str, ctx: Context = ...) -> dict` (6-step with snapshot)
  - [ ] 7.2: Add `async def layer_thaw(name: str, ctx: Context = ...) -> dict` (6-step with snapshot)
  - [ ] 7.3: Add `async def layer_lock(name: str, ctx: Context = ...) -> dict` (6-step with snapshot)
  - [ ] 7.4: Add `async def layer_unlock(name: str, ctx: Context = ...) -> dict` (6-step with snapshot)
  - [ ] 7.5: All 4 functions: Step 1 session guard, Step 2 validate name, Step 3 `session.snapshot.take()`, Step 4 service call catching `MCPError`, Step 5 `event_log.record()`, Step 6 return `{"success": True, "data": {"layer": record.to_dict()}, "error": None}`

- [ ] Task 8: Register all new tools in `layers/__init__.py` (AC: 1, 2, 3, 4)
  - [ ] 8.1: Import all 8 new tool functions from `tools.py`
  - [ ] 8.2: In `register(mcp)`, add `mcp.tool()` decorator call for each:
    `layer_get`, `layer_list`, `layer_set_color`, `layer_set_linetype`, `layer_freeze`, `layer_thaw`, `layer_lock`, `layer_unlock`
  - [ ] 8.3: Confirm all tool names match the architecture naming convention (`layer_` prefix + verb/noun)

- [ ] Task 9: Write unit tests (AC: 7)
  - [ ] 9.1: Create `tests/unit/modules/layers/test_layer_read_tools.py`:
    - [ ] 9.1.1: Test `layer_get` happy path — `MockCADBackend` with the layer; verify response `data.layer.name` matches
    - [ ] 9.1.2: Test `layer_get` LAYER_NOT_FOUND — layer not in backend; verify error code
    - [ ] 9.1.3: Test `layer_get` SESSION_NOT_STARTED — session is None; verify error code
    - [ ] 9.1.4: Test `layer_list` with no filters — verify all layers returned
    - [ ] 9.1.5: Test `layer_list` with `filter_prefix="WALL"` — only WALL* layers returned
    - [ ] 9.1.6: Test `layer_list` with `filter_frozen=True` — only frozen layers returned
    - [ ] 9.1.7: Test `layer_list` with `filter_locked=True` — only locked layers returned
    - [ ] 9.1.8: Test `layer_list` SESSION_NOT_STARTED
    - [ ] 9.1.9: Verify neither `layer_get` nor `layer_list` calls `session.snapshot.take()`
  - [ ] 9.2: Create `tests/unit/modules/layers/test_layer_write_tools.py`:
    - [ ] 9.2.1: Test `layer_set_color` happy path — backend `set_layer_color` called; registry updated; returned layer has new color
    - [ ] 9.2.2: Test `layer_set_color` LAYER_NOT_FOUND
    - [ ] 9.2.3: Test `layer_set_color` INVALID_PARAMS (color=0 or color=300)
    - [ ] 9.2.4: Test `layer_set_color` SESSION_NOT_STARTED
    - [ ] 9.2.5: Test `layer_set_linetype` happy path
    - [ ] 9.2.6: Test `layer_freeze` happy path — `is_frozen=True` in returned layer
    - [ ] 9.2.7: Test `layer_thaw` happy path — `is_frozen=False` in returned layer
    - [ ] 9.2.8: Test `layer_lock` happy path — `is_locked=True` in returned layer
    - [ ] 9.2.9: Test `layer_unlock` happy path — `is_locked=False` in returned layer
    - [ ] 9.2.10: Verify snapshot IS called for all write tools (assert `session.snapshot.take` invoked)

## Dev Notes

### Critical Architecture Constraints

1. **Read-only tools do NOT take snapshots** — `layer_get` and `layer_list` must NOT call `session.snapshot.take()`. Snapshots are only for write/mutation operations. This is a fundamental rule: snapshot before write, never on read.
2. **6-step order is non-negotiable for write tools** — snapshot (step 3) must come before any service call (step 4). Never reorder.
3. **Never import `ezdxf` in `modules/layers/`** — backend calls exclusively via `session.backend`. Comment `# CAD access: session.backend only — never import ezdxf` must appear in `tools.py` and `service.py`.
4. **Registry in-place update** — after a write operation (set_color, freeze, etc.), update the `LayerRecord` in the registry directly (e.g., `record.color = new_color`). Because `LayerRecord` has `ConfigDict(frozen=False)`, field mutation is permitted. Do NOT re-sync the entire registry on every write — that is wasteful and breaks the caching contract.
5. **`CADBackend` method names must match exactly** — the methods `set_layer_color`, `set_layer_linetype`, `freeze_layer`, `thaw_layer`, `lock_layer`, `unlock_layer` must exist in `backends/base.py`. Verify the exact names before coding; if they differ, use the names from the Protocol.
6. **Pydantic v2 field mutation** — `LayerRecord` uses `ConfigDict(frozen=False)` so field assignment (e.g., `record.color = 3`) is valid. Do NOT call `model_copy(update=...)` unless you need an immutable copy; direct assignment is preferred for in-registry updates.

### Module/Component Notes

**`layer_get` and `layer_list` handlers (read-only — no snapshot):**
```python
# tools.py
# CAD access: session.backend only — never import ezdxf
from fastmcp import Context
from lcs_cad_mcp.errors import MCPError, ErrorCode
from lcs_cad_mcp.modules.layers.service import LayerService


async def layer_get(name: str, ctx: Context = Context()) -> dict:
    # Step 1: session
    session = ctx.get_state("session")
    if session is None:
        return MCPError(code=ErrorCode.SESSION_NOT_STARTED,
                        message="No active drawing session.",
                        suggested_action="Call cad_open or cad_create first.").to_response()
    # Step 2: validate
    if not name or not name.strip():
        return MCPError(code=ErrorCode.INVALID_PARAMS, message="Layer name cannot be empty.").to_response()
    # Step 3: SKIPPED — read-only, no snapshot
    # Step 4: service
    try:
        record = LayerService(session).get_layer(name)
    except MCPError as err:
        return err.to_response()
    # Step 5: event log
    session.event_log.record(action="layer_get", details={"name": name})
    # Step 6: return
    return {"success": True, "data": {"layer": record.to_dict()}, "error": None}


async def layer_list(
    filter_prefix: str | None = None,
    filter_frozen: bool | None = None,
    filter_locked: bool | None = None,
    ctx: Context = Context(),
) -> dict:
    session = ctx.get_state("session")
    if session is None:
        return MCPError(code=ErrorCode.SESSION_NOT_STARTED,
                        message="No active drawing session.").to_response()
    # No snapshot — read-only
    try:
        records = LayerService(session).list_layers(filter_prefix, filter_frozen, filter_locked)
    except MCPError as err:
        return err.to_response()
    session.event_log.record(action="layer_list", details={
        "filter_prefix": filter_prefix,
        "filter_frozen": filter_frozen,
        "filter_locked": filter_locked,
        "count": len(records),
    })
    return {
        "success": True,
        "data": {"layers": [r.to_dict() for r in records], "count": len(records)},
        "error": None,
    }
```

**Write handler pattern (`layer_set_color` as canonical example):**
```python
async def layer_set_color(name: str, color: int, ctx: Context = Context()) -> dict:
    # Step 1
    session = ctx.get_state("session")
    if session is None:
        return MCPError(code=ErrorCode.SESSION_NOT_STARTED, ...).to_response()
    # Step 2
    if not name or not name.strip():
        return MCPError(code=ErrorCode.INVALID_PARAMS, message="Layer name cannot be empty.").to_response()
    if not (1 <= color <= 256):
        return MCPError(code=ErrorCode.INVALID_PARAMS,
                        message=f"Color must be 1–256, got {color}.").to_response()
    # Step 3: snapshot — WRITE OPERATION
    session.snapshot.take()
    # Step 4: service
    try:
        record = LayerService(session).set_color(name, color)
    except MCPError as err:
        return err.to_response()
    # Step 5: event log
    session.event_log.record(action="layer_set_color", details={"name": name, "color": color})
    # Step 6: return
    return {"success": True, "data": {"layer": record.to_dict()}, "error": None}
```

**`LayerService.list_layers()` with filter composition:**
```python
def list_layers(
    self,
    filter_prefix: str | None = None,
    filter_frozen: bool | None = None,
    filter_locked: bool | None = None,
) -> list[LayerRecord]:
    self.ensure_synced()
    layers = self.registry.all()  # sorted by name.lower()
    if filter_prefix is not None:
        layers = [r for r in layers if r.name.lower().startswith(filter_prefix.lower())]
    if filter_frozen is not None:
        layers = [r for r in layers if r.is_frozen == filter_frozen]
    if filter_locked is not None:
        layers = [r for r in layers if r.is_locked == filter_locked]
    return layers
```

**`__init__.py` complete `register()` after this story:**
```python
# layers/__init__.py
from lcs_cad_mcp.modules.layers.tools import (
    layer_create,
    layer_delete,
    layer_get,
    layer_list,
    layer_set_color,
    layer_set_linetype,
    layer_freeze,
    layer_thaw,
    layer_lock,
    layer_unlock,
)


def register(mcp) -> None:
    """Register all layer management MCP tools with the FastMCP server."""
    mcp.tool()(layer_create)
    mcp.tool()(layer_delete)
    mcp.tool()(layer_get)
    mcp.tool()(layer_list)
    mcp.tool()(layer_set_color)
    mcp.tool()(layer_set_linetype)
    mcp.tool()(layer_freeze)
    mcp.tool()(layer_thaw)
    mcp.tool()(layer_lock)
    mcp.tool()(layer_unlock)
```

### Project Structure Notes

Files created or modified by this story:

```
src/lcs_cad_mcp/modules/layers/
├── __init__.py          # MODIFY — register all 10 layer tools (8 new + 2 from 3-2)
├── service.py           # MODIFY — add get_layer, list_layers, set_color, set_linetype,
│                        #           freeze_layer, thaw_layer, lock_layer, unlock_layer
└── tools.py             # MODIFY — add layer_get, layer_list, layer_set_color,
                         #           layer_set_linetype, layer_freeze, layer_thaw,
                         #           layer_lock, layer_unlock

tests/unit/modules/layers/
├── test_layer_read_tools.py    # NEW — tests for layer_get, layer_list
└── test_layer_write_tools.py   # NEW — tests for set_color, set_linetype, freeze/thaw/lock/unlock
```

### `CADBackend` Methods Required

The following methods must exist in `backends/base.py` (Protocol) and implemented in `ezdxf_backend.py`. Verify exact signatures before coding:

| Method | Parameters | Returns |
|---|---|---|
| `set_layer_color` | `name: str, color: int` | `None` |
| `set_layer_linetype` | `name: str, linetype: str` | `None` |
| `freeze_layer` | `name: str` | `None` |
| `thaw_layer` | `name: str` | `None` |
| `lock_layer` | `name: str` | `None` |
| `unlock_layer` | `name: str` | `None` |

If method names differ in the actual `CADBackend` Protocol, use the names from that source — do NOT rename them to match this doc.

### MockCADBackend Extension for Tests

Add these stubs to `MockCADBackend` in `conftest.py` if not present:
```python
def set_layer_color(self, name: str, color: int) -> None:
    self.calls.append(("set_layer_color", name, color))
    for layer in self._layers:
        if layer["name"].lower() == name.lower():
            layer["color"] = color

def set_layer_linetype(self, name: str, linetype: str) -> None:
    self.calls.append(("set_layer_linetype", name, linetype))
    for layer in self._layers:
        if layer["name"].lower() == name.lower():
            layer["linetype"] = linetype

def freeze_layer(self, name: str) -> None:
    self.calls.append(("freeze_layer", name))
    for layer in self._layers:
        if layer["name"].lower() == name.lower():
            layer["is_frozen"] = True

def thaw_layer(self, name: str) -> None:
    for layer in self._layers:
        if layer["name"].lower() == name.lower():
            layer["is_frozen"] = False

def lock_layer(self, name: str) -> None:
    for layer in self._layers:
        if layer["name"].lower() == name.lower():
            layer["is_locked"] = True

def unlock_layer(self, name: str) -> None:
    for layer in self._layers:
        if layer["name"].lower() == name.lower():
            layer["is_locked"] = False
```

### Dependencies

- **Story 3-2** (`LayerService` skeleton with `ensure_synced()`, `LayerRegistry`, `LayerRecord`) — this story adds more methods to those same classes.
- **Story 2-4** (snapshot mechanism) — `session.snapshot.take()` is called in all write tool handlers.
- **Story 2-1/2-3** (`CADBackend` Protocol + ezdxf backend) — all new backend methods (`set_layer_color`, etc.) must be defined there.
- **Story 1-2** (FastMCP `Context` import and tool registration pattern).

### References

- Tool naming conventions — `layer_` prefix: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Naming Patterns"]
- 6-step handler pattern (read vs. write distinction): [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- `layer_list` filter design: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 3-3, AC2]
- `layer_set_properties` / `layer_set_state` split: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 3-3, AC3/AC4]
- Anti-patterns: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Enforcement Guidelines"]
- Story definition: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 3, Story 3-3]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/layers/__init__.py`
- `src/lcs_cad_mcp/modules/layers/service.py`
- `src/lcs_cad_mcp/modules/layers/tools.py`
- `tests/unit/modules/layers/test_layer_read_tools.py`
- `tests/unit/modules/layers/test_layer_write_tools.py`
