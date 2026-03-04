# Story 4.4: `predcr_run_setup` MCP Tool (Full PreDCR Initialization)

Status: ready-for-dev

## Story

As an **AI client**,
I want **to run a complete PreDCR initialization for a new drawing in a single tool call**,
so that **the AI can bootstrap a standards-compliant drawing from a high-level building description without manually orchestrating dozens of individual tool calls**.

## Acceptance Criteria

1. **AC1:** `predcr_run_setup(building_type: str, project_name: str, units: str)` MCP tool creates a new drawing (via `CADService`), sets drawing units, creates all PreDCR layers for the building type (via `LayerService` directly), and draws required placeholder entities (title block, site boundary reference) via `EntityService` directly.
2. **AC2:** Returns a comprehensive summary dict: `{"success": True, "data": {"drawing_name": str, "building_type": str, "units": str, "backend": str, "layers_created": int, "layers_skipped": int, "entities_created": int, "layer_names": list[str]}}`.
3. **AC3:** Setup is idempotent — calling `predcr_run_setup` on a drawing that already has PreDCR layers does not duplicate layers; existing layers are listed in the skipped count.
4. **AC4:** Entire setup completes within 30 seconds on the ezdxf backend (NFR2 sub-budget).
5. **AC5:** The drawing produced by `predcr_run_setup` passes `predcr_validate_drawing` (Story 4-5) immediately after setup with `valid: true, violations: []`.
6. **AC6:** Requires an active drawing session (`ctx.get_state("session")`); returns `MCPError(SESSION_NOT_STARTED)` if no session is open.
7. **AC7:** Takes a full snapshot before any writes; on failure at any stage (layer creation, entity drawing, unit setting) triggers rollback to the pre-setup state.
8. **AC8:** `units` parameter accepts `"mm"`, `"cm"`, `"m"` (metric) — mapped to ezdxf/AutoCAD unit codes internally. Invalid units string returns `MCPError(INVALID_PARAMS)`.

## Tasks / Subtasks

- [ ] Task 1: Define input/output schemas in `schemas.py` (AC: 1, 2, 8)
  - [ ] 1.1: Add `RunSetupInput(BaseModel)` with: `building_type: str` (normalize lowercase), `project_name: str` (strip, non-empty validator), `units: Literal["mm", "cm", "m"] = "mm"`.
  - [ ] 1.2: Add `RunSetupOutput(BaseModel)` with: `drawing_name: str`, `building_type: str`, `units: str`, `backend: str`, `layers_created: int`, `layers_skipped: int`, `entities_created: int`, `layer_names: list[str]`.
  - [ ] 1.3: Export `RunSetupInput`, `RunSetupOutput` from `schemas.py`.

- [ ] Task 2: Implement `PreDCRService.run_setup()` in `service.py` (AC: 1, 2, 3, 4, 5)
  - [ ] 2.1: Add `async def run_setup(self, building_type: str, project_name: str, units: str) -> dict` to `PreDCRService`.
  - [ ] 2.2: Set drawing units on the session backend — call `self._session.backend.set_units(units)` (map `"mm"` → ezdxf unit code 4, `"cm"` → 5, `"m"` → 6; use a small lookup dict).
  - [ ] 2.3: Create all PreDCR layers by calling `self.create_layers(building_type)` (the method implemented in Story 4-2, which calls `LayerService` internally). Capture `created` and `skipped` counts.
  - [ ] 2.4: Draw required placeholder entities by calling `EntityService(self._session)` directly:
    - Draw a title block text entity on `PREDCR-TEXT` layer: `EntityService.create_text(content=project_name, layer="PREDCR-TEXT", position=(0, 0))`.
    - Draw a site boundary polyline placeholder on `PREDCR-SITE-BOUNDARY` layer: `EntityService.create_polyline(points=[(0,0),(1,0),(1,1),(0,1),(0,0)], layer="PREDCR-SITE-BOUNDARY")`.
  - [ ] 2.5: Return the summary dict matching `RunSetupOutput` fields.

- [ ] Task 3: Implement `predcr_run_setup` tool handler in `tools.py` (AC: 1, 6, 7)
  - [ ] 3.1: Implement `async def predcr_run_setup(building_type: str, project_name: str, ctx: Context, units: str = "mm") -> dict`.
  - [ ] 3.2: Apply the full 6-step async tool handler pattern:
    - Step 1: `session = ctx.get_state("session")` — if `None`, return `MCPError(SESSION_NOT_STARTED).to_response()`.
    - Step 2: Validate via `RunSetupInput(building_type=building_type, project_name=project_name, units=units)` — on `ValidationError`, return `MCPError(INVALID_PARAMS).to_response()`.
    - Step 3: `snapshot_id = await session.snapshot.take()` — full snapshot before any writes.
    - Step 4: `result = await PreDCRService(session).run_setup(params.building_type, params.project_name, params.units)` — wrapped in try/except; on exception, call `await session.snapshot.rollback(snapshot_id)` then return error response.
    - Step 5: `await session.event_log.record("predcr_run_setup", result)`.
    - Step 6: Return `{"success": True, "data": result}`.
  - [ ] 3.3: The error response for setup failure should use code `"PREDCR_SETUP_FAILED"` with `recoverable=True` and `suggested_action="Check building_type and ensure drawing is writable."`.

- [ ] Task 4: Register `predcr_run_setup` tool in `__init__.py` (AC: 1)
  - [ ] 4.1: Add `predcr_run_setup` to the `register(mcp)` function in `predcr/__init__.py`.
  - [ ] 4.2: Verify tool name exposed to MCP clients is exactly `predcr_run_setup`.

- [ ] Task 5: Write unit tests — mock-based (AC: 1, 2, 3, 6, 7)
  - [ ] 5.1: Create `tests/unit/modules/predcr/test_predcr_run_setup.py`.
  - [ ] 5.2: Build fixtures: `MockCADBackend` with `set_units()` spy, `MockLayerService` with `create()` that tracks calls, `MockEntityService` with `create_text()` and `create_polyline()` spies, `MockSession` with `snapshot.take()` and `snapshot.rollback()`, `MockEventLog`.
  - [ ] 5.3: Test happy path — `predcr_run_setup("residential", "MyProject", "mm")`: verify `backend.set_units` called with correct code, `layer_service.create` called >= 30 times, `entity_service.create_text` called once with `layer="PREDCR-TEXT"`, `entity_service.create_polyline` called once with `layer="PREDCR-SITE-BOUNDARY"`, response `success=True`, `layers_created >= 30`.
  - [ ] 5.4: Test idempotency — mock `LayerService.create` to raise `LayerAlreadyExistsError` for all layers; verify response `layers_skipped >= 30`, `layers_created == 0`, `success=True` (idempotent, not an error).
  - [ ] 5.5: Test SESSION_NOT_STARTED — `ctx.get_state("session")` returns `None`; assert response `error.code == "SESSION_NOT_STARTED"`.
  - [ ] 5.6: Test invalid units — `predcr_run_setup("residential", "X", "furlongs")`; assert response `error.code == "INVALID_PARAMS"`.
  - [ ] 5.7: Test rollback on entity creation failure — mock `EntityService.create_text` to raise `RuntimeError`; verify `snapshot.rollback(snapshot_id)` called; response is error dict.
  - [ ] 5.8: Test `event_log.record` called once with action `"predcr_run_setup"` on success; not called on error.
  - [ ] 5.9: Test snapshot taken before any service call — use call-order tracking to assert `snapshot.take()` precedes `LayerService.create` calls.

- [ ] Task 6: Integration validation — drawing passes `predcr_validate_drawing` (AC: 5)
  - [ ] 6.1: Write integration test (or end-to-end test stub) that: opens a temp ezdxf drawing session, calls `predcr_run_setup("residential", "Test", "mm")`, then calls `PreDCRService.validate_drawing()` (Story 4-5), asserts `valid=True`.
  - [ ] 6.2: Mark this test with `@pytest.mark.integration` and skip in unit-only CI runs.

- [ ] Task 7: Performance validation (AC: 4)
  - [ ] 7.1: Add a test or script that measures wall-clock time of `predcr_run_setup("residential", "PerfTest", "mm")` against ezdxf backend — assert elapsed < 30 seconds.
  - [ ] 7.2: Document expected layer count and entity count in test comments as a performance baseline.

## Dev Notes

### Critical Architecture Constraints

1. **NEVER call `predcr_create_layers` MCP tool from `predcr_run_setup`** — `PreDCRService.run_setup()` calls `self.create_layers()` (the service method, not the MCP tool). Similarly it calls `EntityService` directly, not `entity_draw_polyline` MCP tool. No MCP-to-MCP calls.
2. **Single snapshot for the entire setup** — take ONE snapshot at the start of the tool handler, not one per sub-operation. This ensures the rollback point is the drawing state before any part of setup ran.
3. **Idempotency is at the layer level** — `LayerAlreadyExistsError` from `LayerService.create()` is caught and counted as `skipped`. Entity creation idempotency (if title block already exists) is best-effort for now; placeholder entities may be duplicated on repeated calls if the drawing already has them. Document this limitation in code comments.
4. **Units mapping must be internal** — the `"mm"` / `"cm"` / `"m"` to ezdxf unit code mapping belongs in `service.py` (or a small constant dict in `schemas.py`), not in `tools.py`. The tool handler deals only with Pydantic-validated strings.
5. **`EntityService` import is direct** — import from `lcs_cad_mcp.modules.entities.service import EntityService`. Do not import from the entities MCP tools module.

### Module/Component Notes

**Unit code mapping (ezdxf / AutoCAD INSUNITS):**

```python
UNIT_CODE_MAP = {
    "mm": 4,  # Millimeters
    "cm": 5,  # Centimeters
    "m":  6,  # Meters
}
```

**`PreDCRService.run_setup()` orchestration flow:**

```python
async def run_setup(self, building_type: str, project_name: str, units: str) -> dict:
    # 1. Set units
    unit_code = UNIT_CODE_MAP[units]
    await self._session.backend.set_units(unit_code)

    # 2. Create all PreDCR layers (reuse create_layers service method)
    layer_result = await self.create_layers(building_type)

    # 3. Draw placeholder entities
    entity_svc = EntityService(self._session)
    entities_created = 0
    await entity_svc.create_text(
        content=project_name,
        layer="PREDCR-TEXT",
        position=(0.0, 0.0),
        height=5.0,
    )
    entities_created += 1
    await entity_svc.create_polyline(
        points=[(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0), (0.0, 0.0)],
        layer="PREDCR-SITE-BOUNDARY",
    )
    entities_created += 1

    # 4. Build summary
    return {
        "drawing_name": self._session.drawing_name,
        "building_type": building_type,
        "units": units,
        "backend": self._session.backend.name,
        "layers_created": layer_result["total_created"],
        "layers_skipped": layer_result["total_skipped"],
        "entities_created": entities_created,
        "layer_names": layer_result["created"] + layer_result["skipped"],
    }
```

**Tool handler — concise form:**

```python
async def predcr_run_setup(
    building_type: str, project_name: str, ctx: Context, units: str = "mm"
) -> dict:
    session = ctx.get_state("session")
    if session is None:
        return MCPError(ErrorCode.SESSION_NOT_STARTED, "No active drawing session.").to_response()
    try:
        params = RunSetupInput(building_type=building_type, project_name=project_name, units=units)
    except ValidationError as e:
        return MCPError(ErrorCode.INVALID_PARAMS, str(e)).to_response()
    snapshot_id = await session.snapshot.take()
    try:
        result = await PreDCRService(session).run_setup(
            params.building_type, params.project_name, params.units
        )
    except Exception as e:
        await session.snapshot.rollback(snapshot_id)
        return MCPError(
            "PREDCR_SETUP_FAILED", str(e), recoverable=True,
            suggested_action="Check building_type and ensure drawing is writable."
        ).to_response()
    await session.event_log.record("predcr_run_setup", result)
    return {"success": True, "data": result}
```

**`EntityService` method signatures expected (from Epic 5):**
- `create_text(content: str, layer: str, position: tuple[float, float], height: float = 2.5) -> str` (returns entity handle)
- `create_polyline(points: list[tuple[float, float]], layer: str) -> str` (returns entity handle)

If these methods are not yet fully implemented (Epic 5 may not be complete), use a service stub that records calls without backend interaction — document this in the completion notes.

### Project Structure Notes

```
src/lcs_cad_mcp/modules/predcr/
├── __init__.py    # register(mcp) — adds predcr_run_setup
├── layer_registry.py  # Story 4-1
├── tools.py       # THIS STORY — predcr_run_setup handler (+ 4-2, 4-3 handlers)
├── service.py     # THIS STORY — PreDCRService.run_setup() (+ 4-2, 4-3 methods)
└── schemas.py     # THIS STORY — RunSetupInput, RunSetupOutput

tests/unit/modules/predcr/
├── __init__.py
├── test_layer_registry.py       # Story 4-1
├── test_predcr_create_layers.py # Story 4-2
├── test_predcr_get_layer_spec.py # Story 4-3
└── test_predcr_run_setup.py     # THIS STORY
```

### Dependencies

- **Story 4-2** — `PreDCRService.create_layers()` must be implemented; `predcr_run_setup` calls it as a service method.
- **Story 2-2** — `DrawingSession.backend.set_units()` must be part of the `CADBackend` protocol.
- **Epic 5 (Entity Management)** — `EntityService.create_text()` and `EntityService.create_polyline()` are called. If Epic 5 is not yet complete at dev time, use a stub/mock. Document in completion notes.
- **Story 4-5** — `predcr_validate_drawing` is listed as a dependency of AC5 (drawing passes validation after setup); integration test in Task 6 requires Story 4-5 to be implemented first. Unit tests do not require 4-5.

### References

- Story 4-4 requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 4-4]
- 6-step tool handler pattern: [Source: Mandatory architecture context — "6-STEP TOOL HANDLER (async)"]
- Anti-pattern — no MCP-to-MCP calls: [Source: Mandatory architecture context — "NEVER call layer_ MCP tools from predcr tools — call LayerService directly"]
- NFR2 (60s pipeline, 30s setup sub-budget): [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 4 NFR coverage, Story 4-4 AC4]
- EntityService direct call: [Source: Mandatory architecture context — "PreDCRService orchestrates: reads layer_registry.py specs → calls LayerService (directly) → calls EntityService (directly)"]
- ezdxf INSUNITS values: [Source: ezdxf documentation — `Drawing.units` / INSUNITS variable]
- Workflow story 11-x: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 11 — `predcr_run_setup` is called by the full pipeline workflow]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/predcr/__init__.py` (updated — register predcr_run_setup)
- `src/lcs_cad_mcp/modules/predcr/tools.py` (updated — predcr_run_setup handler)
- `src/lcs_cad_mcp/modules/predcr/service.py` (updated — PreDCRService.run_setup)
- `src/lcs_cad_mcp/modules/predcr/schemas.py` (updated — RunSetupInput, RunSetupOutput)
- `tests/unit/modules/predcr/test_predcr_run_setup.py`
