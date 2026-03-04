# Story 4.2: `predcr_create_layers` MCP Tool

Status: ready-for-dev

## Story

As an **AI client**,
I want **to create all required PreDCR layers for a building type in a single MCP tool call**,
so that **the architect doesn't need to specify 40+ layers individually and the drawing is immediately compliant (FR6)**.

## Acceptance Criteria

1. **AC1:** `predcr_create_layers(building_type: str)` MCP tool creates all layers from `PREDCR_LAYERS` matching the given building type in the active drawing by calling `LayerService.create()` directly (not via the `layer_create` MCP tool).
2. **AC2:** Returns a structured response dict: `{"success": True, "data": {"created": [layer_names], "skipped": [layer_names], "total_created": int, "total_skipped": int, "building_type": str}}`.
3. **AC3:** Already-existing layers with the same name are skipped (not errored) — the operation is idempotent; the response `skipped` list contains their names.
4. **AC4:** All successfully created layers satisfy `layer_validate_naming` with zero violations (NFR14) — the `LayerService.create()` path already enforces this; verify in tests.
5. **AC5:** Tool runs correctly on both ezdxf and COM backends (backend-agnostic via `CADBackend` protocol).
6. **AC6:** Full layer set creation for any supported building type completes within the 60-second pipeline budget (NFR2) — target < 5 seconds on ezdxf backend for 50 layers.
7. **AC7:** If the session is not started, returns `MCPError(SESSION_NOT_STARTED)` response dict without attempting any layer creation.
8. **AC8:** On partial failure mid-batch (e.g. backend error after N layers created), triggers snapshot rollback to restore the drawing to its pre-call state.

## Tasks / Subtasks

- [ ] Task 1: Implement `PreDCRService.create_layers(building_type)` in `service.py` (AC: 1, 3, 8)
  - [ ] 1.1: Create/replace stub `src/lcs_cad_mcp/modules/predcr/service.py` with `PreDCRService` class.
  - [ ] 1.2: `__init__(self, session: DrawingSession)` — stores session reference; imports `LayerService` from the layers module (direct import, NOT via MCP tool call).
  - [ ] 1.3: Implement `async def create_layers(self, building_type: str) -> dict` — calls `get_layers_for_building_type(building_type)` from `layer_registry`, then iterates specs calling `LayerService(self.session).create(name=spec.name, color_index=spec.color_index, linetype=spec.linetype)` for each.
  - [ ] 1.4: Track created vs. skipped: catch `LAYER_ALREADY_EXISTS` errors from `LayerService.create()` and add the layer name to `skipped` list instead of re-raising.
  - [ ] 1.5: On any other `LayerService` error mid-batch, re-raise immediately (the tool handler's rollback in Step 3 will restore state).
  - [ ] 1.6: Return `{"created": [...], "skipped": [...], "total_created": int, "total_skipped": int, "building_type": building_type}`.

- [ ] Task 2: Define input/output schemas in `schemas.py` (AC: 2)
  - [ ] 2.1: Add `CreateLayersInput(BaseModel)` with `building_type: str` field; add `Annotated` validator that normalizes to lowercase and rejects empty string.
  - [ ] 2.2: Add `CreateLayersOutput(BaseModel)` with `created: list[str]`, `skipped: list[str]`, `total_created: int`, `total_skipped: int`, `building_type: str`.
  - [ ] 2.3: Export both from `schemas.py`.

- [ ] Task 3: Implement `predcr_create_layers` tool handler in `tools.py` (AC: 1, 2, 7, 8)
  - [ ] 3.1: Create/replace stub `src/lcs_cad_mcp/modules/predcr/tools.py`.
  - [ ] 3.2: Implement the 6-step async tool handler pattern:
    - Step 1: `session = ctx.get_state("session")` — if `None`, return `MCPError(SESSION_NOT_STARTED).to_response()`.
    - Step 2: Validate `building_type` via `CreateLayersInput(building_type=building_type)` — on `ValidationError`, return `MCPError(INVALID_PARAMS).to_response()`.
    - Step 3: Take snapshot — `snapshot_id = await session.snapshot.take()` (write operation guard).
    - Step 4: Call `result = await PreDCRService(session).create_layers(building_type)`.
    - Step 5: `await session.event_log.record("predcr_create_layers", result)`.
    - Step 6: Return `{"success": True, "data": result}`.
  - [ ] 3.3: Wrap Step 4 in `try/except Exception as e` — on failure call `await session.snapshot.rollback(snapshot_id)` then return `MCPError("PREDCR_CREATE_LAYERS_FAILED", str(e), recoverable=True).to_response()`.
  - [ ] 3.4: Annotate the tool function with FastMCP tool decorator so it is registered on the `mcp` instance. The tool name exposed to clients must be `predcr_create_layers`.

- [ ] Task 4: Register the tool in `__init__.py` (AC: 1)
  - [ ] 4.1: Update `src/lcs_cad_mcp/modules/predcr/__init__.py` — add `register(mcp)` function body that calls `mcp.tool()(predcr_create_layers_handler)` (or equivalent FastMCP 3.x registration pattern).
  - [ ] 4.2: Ensure the `register` function is called from `src/lcs_cad_mcp/__main__.py` or `server.py` during server startup (verify existing registration chain, add if missing).

- [ ] Task 5: Write unit tests (AC: 1, 2, 3, 6, 7, 8)
  - [ ] 5.1: Create `tests/unit/modules/predcr/test_predcr_create_layers.py`.
  - [ ] 5.2: Build a `MockCADBackend` fixture (or import from `tests/conftest.py`) and a `MockDrawingSession` that provides `snapshot.take()`, `snapshot.rollback()`, `event_log.record()`, and `ctx.get_state("session")`.
  - [ ] 5.3: Test happy path — `predcr_create_layers("residential")` with an empty drawing creates all residential layers; response `total_created >= 30` and `skipped == []`.
  - [ ] 5.4: Test idempotency — call `predcr_create_layers("residential")` twice; second call: `created == []`, `total_skipped >= 30`.
  - [ ] 5.5: Test SESSION_NOT_STARTED — `ctx.get_state("session")` returns `None`; tool returns `{"success": False, "error": {"code": "SESSION_NOT_STARTED", ...}}`.
  - [ ] 5.6: Test invalid building_type — `predcr_create_layers("unknown_type")` raises `ValueError` in service which is caught and returned as structured error.
  - [ ] 5.7: Test rollback on partial failure — mock `LayerService.create` to succeed for first 5 layers then raise `RuntimeError`; verify `snapshot.rollback()` was called with the correct snapshot_id.
  - [ ] 5.8: Test that `event_log.record` is called exactly once on success with action `"predcr_create_layers"`.

- [ ] Task 6: Verify cross-backend compatibility and performance (AC: 5, 6)
  - [ ] 6.1: Run integration test (or manual test) against ezdxf backend — create a temp DXF file, open session, call `predcr_create_layers("commercial")`, assert layer count in DXF matches expected.
  - [ ] 6.2: Measure wall-clock time for full residential layer set creation on ezdxf backend — assert < 5 seconds (well within 60s NFR2 budget).
  - [ ] 6.3: Run `ruff check src/lcs_cad_mcp/modules/predcr/` — zero violations.

## Dev Notes

### Critical Architecture Constraints

1. **NEVER call `layer_create` MCP tool from `predcr_create_layers`** — this is a hard anti-pattern. `PreDCRService` calls `LayerService` directly (class instantiation and method call), bypassing the MCP dispatch layer entirely. Calling an MCP tool from another tool creates circular dependency and violates the single-session contract.
2. **6-step handler pattern is mandatory** — every MCP write tool in this project follows: session-check → validate → snapshot → service-call → event-log → return. Do not skip or reorder steps.
3. **Snapshot before any write** — `session.snapshot.take()` must be called before `PreDCRService.create_layers()`. This is a batch write operation modifying potentially 40+ layers; rollback on failure restores the exact pre-call state.
4. **Async throughout** — the tool handler, `PreDCRService.create_layers`, and `LayerService.create` are all `async def`. Do not use synchronous blocking calls.
5. **`building_type` normalization** — normalize to lowercase in `CreateLayersInput` before passing to `get_layers_for_building_type`. The registry keys are lowercase; user input may be mixed case.

### Module/Component Notes

**`PreDCRService` in `service.py`:**

```python
from lcs_cad_mcp.modules.predcr.layer_registry import get_layers_for_building_type
from lcs_cad_mcp.modules.layers.service import LayerService


class PreDCRService:
    def __init__(self, session):
        self._session = session

    async def create_layers(self, building_type: str) -> dict:
        specs = get_layers_for_building_type(building_type)
        layer_svc = LayerService(self._session)
        created, skipped = [], []
        for spec in specs:
            try:
                await layer_svc.create(
                    name=spec.name,
                    color_index=spec.color_index,
                    linetype=spec.linetype,
                )
                created.append(spec.name)
            except LayerAlreadyExistsError:
                skipped.append(spec.name)
        return {
            "created": created,
            "skipped": skipped,
            "total_created": len(created),
            "total_skipped": len(skipped),
            "building_type": building_type,
        }
```

**Tool handler skeleton in `tools.py`:**

```python
async def predcr_create_layers(building_type: str, ctx: Context) -> dict:
    # Step 1: Session check
    session = ctx.get_state("session")
    if session is None:
        return MCPError(ErrorCode.SESSION_NOT_STARTED, "No active drawing session.").to_response()
    # Step 2: Validate
    try:
        params = CreateLayersInput(building_type=building_type)
    except ValidationError as e:
        return MCPError(ErrorCode.INVALID_PARAMS, str(e)).to_response()
    # Step 3: Snapshot
    snapshot_id = await session.snapshot.take()
    # Step 4: Service call
    try:
        result = await PreDCRService(session).create_layers(params.building_type)
    except Exception as e:
        await session.snapshot.rollback(snapshot_id)
        return MCPError("PREDCR_CREATE_LAYERS_FAILED", str(e), recoverable=True).to_response()
    # Step 5: Event log
    await session.event_log.record("predcr_create_layers", result)
    # Step 6: Return
    return {"success": True, "data": result}
```

**`LAYER_ALREADY_EXISTS` handling:** Import the specific error class from the layers module (defined in Story 3-2). Do not use bare `except Exception` for the skip-logic — only catch `LayerAlreadyExistsError`.

### Project Structure Notes

```
src/lcs_cad_mcp/modules/predcr/
├── __init__.py          # register(mcp) — calls mcp.tool()(predcr_create_layers)
├── layer_registry.py    # Story 4-1 (dependency)
├── tools.py             # THIS STORY — predcr_create_layers handler
├── service.py           # THIS STORY — PreDCRService.create_layers()
└── schemas.py           # THIS STORY — CreateLayersInput, CreateLayersOutput

tests/unit/modules/predcr/
├── __init__.py
├── test_layer_registry.py       # Story 4-1
└── test_predcr_create_layers.py # THIS STORY
```

### Dependencies

- **Story 4-1** — `layer_registry.py` with `PREDCR_LAYERS` and `get_layers_for_building_type` must be complete.
- **Story 3-2** — `LayerService.create()` and `LayerAlreadyExistsError` must be implemented and importable.
- **Epic 2 (Stories 2-1 through 2-4)** — `DrawingSession`, `CADBackend` protocol, `snapshot`, `event_log` must be fully implemented.
- **Story 1-2** — FastMCP `mcp` instance and `ctx: Context` pattern must be established.

### References

- Story 4-2 requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 4-2]
- 6-step tool handler pattern: [Source: Mandatory architecture context — "6-STEP TOOL HANDLER (async)"]
- Anti-pattern — never call MCP tools from MCP tools: [Source: Mandatory architecture context — "NEVER call layer_ MCP tools from predcr tools — call LayerService directly"]
- FastMCP 3.x Context / `ctx.get_state`: [Source: Architecture doc — "Selected Framework: FastMCP v3.x"]
- MCPError contract: [Source: `src/lcs_cad_mcp/errors.py` — Story 1-1]
- NFR2 (60s pipeline budget): [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 4 NFR coverage]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/predcr/__init__.py` (updated — register)
- `src/lcs_cad_mcp/modules/predcr/service.py` (new — PreDCRService)
- `src/lcs_cad_mcp/modules/predcr/tools.py` (new — predcr_create_layers)
- `src/lcs_cad_mcp/modules/predcr/schemas.py` (new — CreateLayersInput, CreateLayersOutput)
- `tests/unit/modules/predcr/test_predcr_create_layers.py`
