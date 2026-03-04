# Story 5.5: `entity_move`, `entity_copy`, `entity_delete`, and `entity_change_layer` MCP Tools

Status: ready-for-dev

## Story

As an **AI client**,
I want **to move, copy, delete, and reassign layers for existing drawing entities**,
so that **the AI can refine and correct the drawing geometry without redrawing entities from scratch, fulfilling FR10**.

## Acceptance Criteria

1. **AC1:** `entity_move(entity_id: str, displacement: tuple[float, float])` MCP tool translates the identified entity by the given (dx, dy) offset and returns `{"success": true, "data": {"entity_id": "<id>", "moved_by": [dx, dy]}}`
2. **AC2:** `entity_copy(entity_id: str, displacement: tuple[float, float])` MCP tool creates a copy of the entity at the given (dx, dy) offset and returns `{"success": true, "data": {"original_entity_id": "<id>", "new_entity_id": "<new_handle>", "displacement": [dx, dy]}}`
3. **AC3:** `entity_delete(entity_id: str)` MCP tool removes the entity from the drawing and returns `{"success": true, "data": {"entity_id": "<id>", "deleted": true}}`
4. **AC4:** `entity_change_layer(entity_id: str, new_layer: str)` MCP tool reassigns the entity to a different layer and returns `{"success": true, "data": {"entity_id": "<id>", "layer": "<new_layer>"}}`
5. **AC5:** All four tools return `ENTITY_NOT_FOUND` error if the `entity_id` does not exist in the current drawing
6. **AC6:** `entity_change_layer` additionally validates that `new_layer` exists; returns `LAYER_NOT_FOUND` if not
7. **AC7:** All four tools take a snapshot BEFORE mutating the drawing; no snapshot is taken if validation fails
8. **AC8:** All four tools work on both `EzdxfBackend` and `COMBackend` (COM stubs acceptable)
9. **AC9:** All four tools complete within 2 seconds (NFR1)

## Tasks / Subtasks

- [ ] Task 1: Implement `EntityService` mutation methods in `service.py` (AC: 1, 2, 3, 4, 5, 6, 8)
  - [ ] 1.1: Replace `move_entity` stub: call `self._backend.move_entity(entity_id=entity_id, dx=displacement[0], dy=displacement[1])` — raises `EntityNotFoundError` if entity absent; returns the moved `entity_id`
  - [ ] 1.2: Replace `copy_entity` stub: call `self._backend.copy_entity(entity_id=entity_id, dx=displacement[0], dy=displacement[1])` — returns the new entity handle string for the copy
  - [ ] 1.3: Replace `delete_entity` stub: call `self._backend.delete_entity(entity_id=entity_id)` — raises `EntityNotFoundError` if not found; returns the deleted entity_id
  - [ ] 1.4: Replace `change_layer` stub: call `self._backend.change_entity_layer(entity_id=entity_id, new_layer=new_layer)` — raises `EntityNotFoundError` or `LayerNotFoundError`; returns entity_id and new_layer
  - [ ] 1.5: Define internal `EntityNotFoundError(Exception)` and `LayerNotFoundError(Exception)` in `service.py`; service methods raise these; tool handlers catch them and translate to MCP error responses

- [ ] Task 2: Implement MCP tool handlers in `tools.py` following the 6-step pattern (AC: 1–9)
  - [ ] 2.1: Add async `entity_move(ctx, entity_id: str, displacement: tuple[float, float]) -> dict`
  - [ ] 2.2: Add async `entity_copy(ctx, entity_id: str, displacement: tuple[float, float]) -> dict`
  - [ ] 2.3: Add async `entity_delete(ctx, entity_id: str) -> dict`
  - [ ] 2.4: Add async `entity_change_layer(ctx, entity_id: str, new_layer: str) -> dict`
  - [ ] 2.5: Step 1 (all four) — Session: `session = ctx.get_state("drawing_session")`; `SESSION_NOT_STARTED` if None
  - [ ] 2.6: Step 2 (move/copy) — Validate `len(displacement) == 2`; return `INVALID_PARAMS` if not; for `entity_copy` also validate displacement is non-zero (warn if zero but do not error — a zero-displacement copy is valid)
  - [ ] 2.7: Step 2 (change_layer) — Validate `new_layer` is non-empty string
  - [ ] 2.8: Step 3 (change_layer only) — Validate `new_layer` exists via `session.backend.layer_exists(new_layer)`; return `LAYER_NOT_FOUND` if not
  - [ ] 2.9: Step 4 — Snapshot: `snapshot_id = await session.snapshot.take()` — ONLY after all validation passes
  - [ ] 2.10: Step 5 — Delegate to `EntityService(session).move_entity(...)` etc.; catch `EntityNotFoundError` → return `ENTITY_NOT_FOUND` response with `recoverable=True` and `suggested_action="Use entity_query to find valid entity IDs"` (note: snapshot was taken but no mutation occurred — snapshot entry is harmless)
  - [ ] 2.11: Step 6 — Append event_log entry with tool name, entity_id, and key params; return structured response

- [ ] Task 3: Extend `CADBackend` Protocol and implement in `EzdxfBackend` (AC: 8)
  - [ ] 3.1: Add `entity_exists(entity_id: str) -> bool` to Protocol — checks if handle is in the drawing
  - [ ] 3.2: Add `move_entity(entity_id: str, dx: float, dy: float) -> None` to Protocol
  - [ ] 3.3: Add `copy_entity(entity_id: str, dx: float, dy: float) -> str` to Protocol — returns new entity handle
  - [ ] 3.4: Add `delete_entity(entity_id: str) -> None` to Protocol
  - [ ] 3.5: Add `change_entity_layer(entity_id: str, new_layer: str) -> None` to Protocol
  - [ ] 3.6: Implement `EzdxfBackend.entity_exists`: `entity = self._doc.entitydb.get(entity_id); return entity is not None`
  - [ ] 3.7: Implement `EzdxfBackend.move_entity`: get entity by handle from `entitydb`; call `entity.translate(dx, dy, 0)` or use ezdxf's `move` transformation; raise `EntityNotFoundError` if not found
  - [ ] 3.8: Implement `EzdxfBackend.copy_entity`: get entity by handle; use `entity.copy()` to create a deep copy; translate the copy by `(dx, dy, 0)`; add copy to `msp`; return new entity's handle
  - [ ] 3.9: Implement `EzdxfBackend.delete_entity`: get entity; call `msp.delete_entity(entity)`; raise `EntityNotFoundError` if not found
  - [ ] 3.10: Implement `EzdxfBackend.change_entity_layer`: get entity; set `entity.dxf.layer = new_layer`; raise `EntityNotFoundError` if not found
  - [ ] 3.11: Add `COMBackend` stubs for all 5 methods raising `NotImplementedError("COM backend entity mutation: Story 5-5")`

- [ ] Task 4: Register all four tools in `entities/__init__.py` (AC: 1–4)
  - [ ] 4.1: Update `register(mcp)` to call `_register_mutation_tools(mcp)` from `tools.py`
  - [ ] 4.2: Verify all four tool names in MCP registry: `entity_move`, `entity_copy`, `entity_delete`, `entity_change_layer`
  - [ ] 4.3: Confirm previously registered tools (5-2, 5-3, 5-4) are still registered and functional

- [ ] Task 5: Write unit tests with `MockCADBackend` (AC: 1–9)
  - [ ] 5.1: Create `tests/unit/modules/entities/test_mutation_tools.py`
  - [ ] 5.2: Extend `MockCADBackend` with: `entity_exists`, `move_entity`, `copy_entity`, `delete_entity`, `change_entity_layer`; store a dict `_entities: dict[str, dict]` as in-memory drawing state
  - [ ] 5.3: Test `entity_move` happy path: known entity_id, valid displacement → success response, mock backend records translation
  - [ ] 5.4: Test `entity_move` with unknown entity_id → `ENTITY_NOT_FOUND` error, no backend mutation call
  - [ ] 5.5: Test `entity_copy` happy path: known entity_id → returns both `original_entity_id` and `new_entity_id` (different values)
  - [ ] 5.6: Test `entity_copy` with unknown entity_id → `ENTITY_NOT_FOUND` error
  - [ ] 5.7: Test `entity_copy` with zero displacement `[0.0, 0.0]` → succeeds (zero displacement is valid, just creates a coincident copy)
  - [ ] 5.8: Test `entity_delete` happy path: known entity_id → success, entity removed from mock state
  - [ ] 5.9: Test `entity_delete` with unknown entity_id → `ENTITY_NOT_FOUND` error
  - [ ] 5.10: Test `entity_change_layer` happy path: known entity_id, existing layer → success, layer updated in mock state
  - [ ] 5.11: Test `entity_change_layer` with unknown entity_id → `ENTITY_NOT_FOUND` error
  - [ ] 5.12: Test `entity_change_layer` with non-existent `new_layer` → `LAYER_NOT_FOUND` error (validated before snapshot)
  - [ ] 5.13: Test snapshot behavior: for all 4 tools, snapshot is taken once on success; snapshot is NOT taken if validation fails pre-snapshot

- [ ] Task 6: Event log entries for audit trail (AC: 1–4)
  - [ ] 6.1: For `entity_move` event log: `{"tool": "entity_move", "entity_id": "...", "displacement": [dx, dy], "snapshot_id": "..."}`
  - [ ] 6.2: For `entity_copy` event log: `{"tool": "entity_copy", "original_entity_id": "...", "new_entity_id": "...", "displacement": [dx, dy], "snapshot_id": "..."}`
  - [ ] 6.3: For `entity_delete` event log: `{"tool": "entity_delete", "entity_id": "...", "snapshot_id": "..."}`
  - [ ] 6.4: For `entity_change_layer` event log: `{"tool": "entity_change_layer", "entity_id": "...", "new_layer": "...", "snapshot_id": "..."}`
  - [ ] 6.5: Add test asserting event_log contains the correct entry after each successful operation

## Dev Notes

### Critical Architecture Constraints

1. **6-step handler pattern** — same strict ordering as Stories 5-2 through 5-4. Validation (Step 2+3) must occur BEFORE snapshot (Step 4). Catching `EntityNotFoundError` after snapshot in Step 5 is acceptable — the snapshot was taken but no mutation happened; the snapshot entry is a minor overhead, not a correctness violation.
2. **Snapshot before every mutation** — `entity_move`, `entity_copy`, `entity_delete`, and `entity_change_layer` are all irreversible write operations. Each requires a pre-mutation snapshot for rollback support.
3. **EntityService raises domain exceptions; tool handlers translate them** — `EntityNotFoundError` and `LayerNotFoundError` are internal service-layer exceptions defined in `service.py`. Tool handlers in `tools.py` catch these and return structured MCPError responses. This keeps error translation in the presentation layer (tools.py) and business logic in the service layer.
4. **ezdxf entity handle lookup:** In ezdxf, entity handles are looked up via `doc.entitydb[handle]` (which raises `KeyError` if not found) or `doc.entitydb.get(handle)` (returns `None`). The `EntityNotFoundError` must be raised for `None` returns, not silently ignored.
5. **COM backend copy:** On real COM/AutoCAD, `copy_entity` would use AutoCAD's `Copy` command with a displacement. The stub preserves the interface contract without COM API knowledge.

### Module/Component Notes

**Tool parameter definitions for MCP clients:**

`entity_move`:
- `entity_id: str` — entity handle (returned by any draw tool)
- `displacement: tuple[float, float]` — `(dx, dy)` translation vector in drawing units

`entity_copy`:
- `entity_id: str` — entity handle to copy from
- `displacement: tuple[float, float]` — `(dx, dy)` offset for the copy relative to original

`entity_delete`:
- `entity_id: str` — entity handle to remove

`entity_change_layer`:
- `entity_id: str` — entity handle to reassign
- `new_layer: str` — target layer name (must exist in drawing)

**Response schemas:**
```python
# entity_move
{"success": True, "data": {"entity_id": "1F3A", "moved_by": [10.0, 5.0]}}

# entity_copy
{"success": True, "data": {"original_entity_id": "1F3A", "new_entity_id": "2B7C", "displacement": [10.0, 5.0]}}

# entity_delete
{"success": True, "data": {"entity_id": "1F3A", "deleted": True}}

# entity_change_layer
{"success": True, "data": {"entity_id": "1F3A", "layer": "ROOM-BEDROOM"}}

# ENTITY_NOT_FOUND error (all tools)
{
    "success": False,
    "error": {
        "code": "ENTITY_NOT_FOUND",
        "message": "Entity '1F3A' not found in current drawing",
        "recoverable": True,
        "suggested_action": "Use entity_query to find valid entity IDs"
    }
}
```

**ezdxf entity manipulation reference:**
```python
# Move entity
entity = self._doc.entitydb.get(entity_id)
if entity is None:
    raise EntityNotFoundError(entity_id)
entity.translate(dx, dy, 0)  # in-place translation

# Copy entity (ezdxf 1.x)
copy = entity.copy()
copy.translate(dx, dy, 0)
self._doc.modelspace().add_entity(copy)
new_handle = copy.dxf.handle
```

### Project Structure Notes

Files modified by this story:
```
src/lcs_cad_mcp/
├── backends/
│   ├── base.py              # entity_exists, move_entity, copy_entity, delete_entity, change_entity_layer to Protocol
│   ├── ezdxf_backend.py     # implement all 5 mutation methods
│   └── com_backend.py       # stubs for all 5 mutation methods
└── modules/entities/
    ├── __init__.py           # register() includes mutation tools
    ├── service.py            # move_entity, copy_entity, delete_entity, change_layer implemented; EntityNotFoundError, LayerNotFoundError defined
    └── tools.py              # entity_move, entity_copy, entity_delete, entity_change_layer handlers

tests/unit/modules/entities/
└── test_mutation_tools.py    # new
```

### Dependencies

- **Story 5-2 (draw_polyline / draw_line):** 6-step handler pattern, session snapshot integration, `layer_exists()` — all reused here
- **Story 5-1 (Entity Data Models):** `EntityService` skeleton, `EntityRecord` types
- **EzdxfBackend (Story 2-x):** Entity handle lookup via `doc.entitydb`, entity manipulation APIs

### References

- FR10 (entity modification): [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Functional Requirements"]
- 6-step tool handler: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- Snapshot / rollback: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Snapshot / Rollback"]
- ErrorCode constants: [Source: `src/lcs_cad_mcp/errors.py` — `ENTITY_NOT_FOUND`, `LAYER_NOT_FOUND`]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 5, Story 5-5]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/backends/base.py`
- `src/lcs_cad_mcp/backends/ezdxf_backend.py`
- `src/lcs_cad_mcp/backends/com_backend.py`
- `src/lcs_cad_mcp/modules/entities/__init__.py`
- `src/lcs_cad_mcp/modules/entities/service.py`
- `src/lcs_cad_mcp/modules/entities/tools.py`
- `tests/unit/modules/entities/test_mutation_tools.py`
