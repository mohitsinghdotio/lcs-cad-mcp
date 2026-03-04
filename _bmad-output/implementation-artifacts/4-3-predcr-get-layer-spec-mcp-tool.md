# Story 4.3: `predcr_get_layer_spec` and `predcr_list_layer_specs` MCP Tools

Status: ready-for-dev

## Story

As an **AI client**,
I want **to query the PreDCR layer specification catalog for a specific layer or for all layers of a building type**,
so that **the AI can reference the correct layer name, color, and linetype for each entity type without guessing**.

## Acceptance Criteria

1. **AC1:** `predcr_get_layer_spec(layer_name: str)` MCP tool returns the full `LayerSpec` data for the named layer as a structured dict: `{"name": str, "color_index": int, "linetype": str, "required_for": list[str], "entity_types": list[str]}`. Lookup is case-insensitive.
2. **AC2:** `predcr_list_layer_specs(building_type: str)` MCP tool returns all `LayerSpec` entries matching the given building type as a list of spec dicts, plus a count: `{"specs": [...], "total": int, "building_type": str}`.
3. **AC3:** `predcr_get_layer_spec` returns a structured error `{"success": False, "error": {"code": "LAYER_SPEC_NOT_FOUND", ...}}` when the layer name is not in `PREDCR_LAYERS`.
4. **AC4:** `predcr_list_layer_specs` returns a structured error `{"success": False, "error": {"code": "INVALID_PARAMS", ...}}` for an unknown `building_type` string.
5. **AC5:** Both tools are **read-only** — they do NOT require an active drawing session (`ctx.get_state("session")` is not checked); they query `PREDCR_LAYERS` in-memory. No snapshot is taken.
6. **AC6:** Both tools respond in < 100ms (pure in-memory lookup, NFR1 well within budget).
7. **AC7:** `predcr_list_layer_specs` accepts an optional `entity_type: str | None = None` filter — when provided, returns only specs whose `entity_types` list contains the given entity type string (case-insensitive).

## Tasks / Subtasks

- [ ] Task 1: Define schemas for both tools in `schemas.py` (AC: 1, 2)
  - [ ] 1.1: Add `GetLayerSpecInput(BaseModel)` with `layer_name: str` (strip whitespace validator).
  - [ ] 1.2: Add `LayerSpecData(BaseModel)` with `name: str`, `color_index: int`, `linetype: str`, `required_for: list[str]`, `entity_types: list[str]` — used as the serialized form of `LayerSpec` in responses.
  - [ ] 1.3: Add `ListLayerSpecsInput(BaseModel)` with `building_type: str` (normalize lowercase) and `entity_type: str | None = None` (normalize uppercase if provided, for entity type matching).
  - [ ] 1.4: Add `ListLayerSpecsOutput(BaseModel)` with `specs: list[LayerSpecData]`, `total: int`, `building_type: str`.

- [ ] Task 2: Implement service methods for catalog queries in `service.py` (AC: 1, 2, 3, 4, 7)
  - [ ] 2.1: Add `def get_layer_spec(self, layer_name: str) -> LayerSpec` to `PreDCRService` — calls `get_layer_by_name(layer_name)` from `layer_registry`; raises `LayerSpecNotFoundError(layer_name)` if result is `None`.
  - [ ] 2.2: Add `def list_layer_specs(self, building_type: str, entity_type: str | None = None) -> list[LayerSpec]` — calls `get_layers_for_building_type(building_type)` (which raises `ValueError` for unknown type); if `entity_type` is provided, further filters to specs where `entity_type.upper()` is in `spec.entity_types`.
  - [ ] 2.3: Define `LayerSpecNotFoundError(ValueError)` in `schemas.py` or `service.py` — used by the tool handler to produce the `LAYER_SPEC_NOT_FOUND` error response.
  - [ ] 2.4: Both methods are synchronous `def` (not `async def`) since they are pure in-memory lookups with no I/O. The tool handlers are still `async def` wrappers.

- [ ] Task 3: Implement `predcr_get_layer_spec` tool handler in `tools.py` (AC: 1, 3, 5, 6)
  - [ ] 3.1: Implement `async def predcr_get_layer_spec(layer_name: str, ctx: Context) -> dict` following the read-only tool handler pattern (3-step: validate → service call → return; NO session check, NO snapshot).
  - [ ] 3.2: Validate `layer_name` via `GetLayerSpecInput`; on `ValidationError` return `MCPError(INVALID_PARAMS).to_response()`.
  - [ ] 3.3: Call `PreDCRService(session=None).get_layer_spec(params.layer_name)` — note: `PreDCRService` must accept `session=None` for read-only catalog operations (guard against accidentally using session in read-only methods).
  - [ ] 3.4: On `LayerSpecNotFoundError`, return `MCPError("LAYER_SPEC_NOT_FOUND", f"Layer spec '{layer_name}' not found in PreDCR catalog.", recoverable=True).to_response()`.
  - [ ] 3.5: On success, return `{"success": True, "data": spec.model_dump()}`.

- [ ] Task 4: Implement `predcr_list_layer_specs` tool handler in `tools.py` (AC: 2, 4, 5, 6, 7)
  - [ ] 4.1: Implement `async def predcr_list_layer_specs(building_type: str, ctx: Context, entity_type: str | None = None) -> dict` as a read-only tool handler.
  - [ ] 4.2: Validate input via `ListLayerSpecsInput(building_type=building_type, entity_type=entity_type)`; on `ValidationError` return `MCPError(INVALID_PARAMS).to_response()`.
  - [ ] 4.3: Call `PreDCRService(session=None).list_layer_specs(params.building_type, params.entity_type)`.
  - [ ] 4.4: On `ValueError` (unknown building type from registry), return `MCPError(INVALID_PARAMS, str(e)).to_response()`.
  - [ ] 4.5: On success, return `{"success": True, "data": {"specs": [s.model_dump() for s in specs], "total": len(specs), "building_type": params.building_type}}`.

- [ ] Task 5: Register both tools in `__init__.py` (AC: 1, 2)
  - [ ] 5.1: Add both `predcr_get_layer_spec` and `predcr_list_layer_specs` to the `register(mcp)` function in `predcr/__init__.py`.
  - [ ] 5.2: Confirm that FastMCP exposes tool names as `predcr_get_layer_spec` and `predcr_list_layer_specs` (underscore-separated, matching the MCP tool naming convention).

- [ ] Task 6: Write unit tests (AC: 1, 2, 3, 4, 5, 6, 7)
  - [ ] 6.1: Create `tests/unit/modules/predcr/test_predcr_get_layer_spec.py`.
  - [ ] 6.2: Test `predcr_get_layer_spec("PREDCR-WALL-EXT")` — returns `{"success": True, "data": {"name": "PREDCR-WALL-EXT", "color_index": 7, ...}}`.
  - [ ] 6.3: Test case-insensitivity — `predcr_get_layer_spec("predcr-wall-ext")` returns same result as uppercase.
  - [ ] 6.4: Test not found — `predcr_get_layer_spec("NONEXISTENT-LAYER")` returns `{"success": False, "error": {"code": "LAYER_SPEC_NOT_FOUND", ...}}`.
  - [ ] 6.5: Test empty `layer_name` — `predcr_get_layer_spec("")` returns `INVALID_PARAMS` error.
  - [ ] 6.6: Test `predcr_list_layer_specs("residential")` — `data.total >= 30`, all specs have `"residential"` in `required_for`.
  - [ ] 6.7: Test `predcr_list_layer_specs("commercial", entity_type="WALL")` — returns only specs with `"WALL"` in `entity_types`.
  - [ ] 6.8: Test unknown building type — `predcr_list_layer_specs("martian")` returns `INVALID_PARAMS` error.
  - [ ] 6.9: Test that neither tool calls `ctx.get_state("session")` — mock the ctx and assert `get_state` is never invoked.
  - [ ] 6.10: Test that no snapshot is taken — mock `session.snapshot.take` and assert it is never called.

- [ ] Task 7: Run tests and lint (AC: all)
  - [ ] 7.1: Run `pytest tests/unit/modules/predcr/test_predcr_get_layer_spec.py -v` — all tests pass.
  - [ ] 7.2: Run `ruff check src/lcs_cad_mcp/modules/predcr/` — zero violations.

## Dev Notes

### Critical Architecture Constraints

1. **These tools are read-only — NO session required** — `predcr_get_layer_spec` and `predcr_list_layer_specs` query the in-memory `PREDCR_LAYERS` catalog only. They must NOT require an active session, NOT take a snapshot, and NOT write to the event log. This is an intentional design decision: catalog queries work even before any drawing is opened.
2. **`PreDCRService` must support `session=None`** — guard read-only methods against accidentally accessing `self._session`. A clean pattern: `if self._session is None and is_write_operation: raise RuntimeError(...)`. Alternatively, create a `PreDCRCatalogService` that has no session at all and only exposes read methods.
3. **3-step handler for read-only tools** — read-only tool handlers follow: validate → service call → return. The 6-step pattern (session, snapshot, event_log) applies only to write tools (Story 4-2, 4-4, 4-5).
4. **`LayerSpec.model_dump()` for serialization** — use Pydantic v2's `.model_dump()` to serialize `LayerSpec` into the response dict. Do not manually construct dicts from spec fields.
5. **Tool naming** — the FastMCP-exposed tool names MUST be `predcr_get_layer_spec` and `predcr_list_layer_specs` (not `predcr_get_layer_spec_tool` or any other variant).

### Module/Component Notes

**Read-only tool handler pattern (3-step):**

```python
async def predcr_get_layer_spec(layer_name: str, ctx: Context) -> dict:
    # Step 1: Validate
    try:
        params = GetLayerSpecInput(layer_name=layer_name)
    except ValidationError as e:
        return MCPError(ErrorCode.INVALID_PARAMS, str(e)).to_response()
    # Step 2: Service call (no session, no snapshot)
    try:
        spec = PreDCRService(session=None).get_layer_spec(params.layer_name)
    except LayerSpecNotFoundError as e:
        return MCPError("LAYER_SPEC_NOT_FOUND", str(e), recoverable=True).to_response()
    # Step 3: Return
    return {"success": True, "data": spec.model_dump()}
```

**`PreDCRService` read-only methods (synchronous, no I/O):**

```python
def get_layer_spec(self, layer_name: str) -> LayerSpec:
    spec = get_layer_by_name(layer_name)
    if spec is None:
        raise LayerSpecNotFoundError(f"'{layer_name}' not found in PREDCR_LAYERS")
    return spec

def list_layer_specs(
    self, building_type: str, entity_type: str | None = None
) -> list[LayerSpec]:
    specs = get_layers_for_building_type(building_type)  # raises ValueError on unknown type
    if entity_type is not None:
        et_upper = entity_type.upper()
        specs = [s for s in specs if et_upper in s.entity_types]
    return specs
```

**`entity_type` filter behavior:** Entity type values in `LayerSpec.entity_types` are stored as uppercase strings (e.g. `"WALL"`, `"DOOR"`). The `entity_type` parameter is normalized to uppercase before comparison to allow case-insensitive user input.

**`predcr_list_layer_specs` with `entity_type=None`:** When no `entity_type` filter is provided, returns the full set for the building type — this satisfies the original AC from the epics file: "Returns full catalog if no entity_type filter provided."

### Project Structure Notes

```
src/lcs_cad_mcp/modules/predcr/
├── __init__.py       # register(mcp) — adds predcr_get_layer_spec, predcr_list_layer_specs
├── layer_registry.py # Story 4-1 (dependency)
├── tools.py          # THIS STORY — adds predcr_get_layer_spec, predcr_list_layer_specs
├── service.py        # THIS STORY — adds get_layer_spec(), list_layer_specs() methods
└── schemas.py        # THIS STORY — GetLayerSpecInput, ListLayerSpecsInput, LayerSpecData, ListLayerSpecsOutput

tests/unit/modules/predcr/
├── __init__.py
├── test_layer_registry.py           # Story 4-1
├── test_predcr_create_layers.py     # Story 4-2
└── test_predcr_get_layer_spec.py    # THIS STORY
```

### Dependencies

- **Story 4-1** — `PREDCR_LAYERS`, `get_layer_by_name`, `get_layers_for_building_type`, `LayerSpec` must be complete.
- **Story 4-2** — `PreDCRService` class skeleton must exist (this story adds read-only methods to it); if developed in parallel, coordinate on the class structure to avoid merge conflicts.
- **Story 1-2** — FastMCP `mcp` instance and `ctx: Context` import path must be established.

### References

- Story 4-3 requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 4-3]
- Read-only vs. write tool handler distinction: [Source: Mandatory architecture context — "6-STEP TOOL HANDLER (async)" applies to write tools; read-only tools skip session/snapshot/event-log steps]
- MCP tool prefix convention: [Source: Mandatory architecture context — "MCP tool prefix: predcr_ → predcr_create_layers, predcr_get_layer_spec, predcr_run_setup, predcr_validate_drawing"]
- `layer_registry.py` helpers: [Source: Story 4-1 — `get_layer_by_name`, `get_layers_for_building_type`]
- Pydantic v2 `.model_dump()`: [Source: Architecture doc — "Pydantic v2" dependency]
- AC detail for no entity_type filter: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 4-3 AC2: "Returns full catalog if no entity_type filter provided"]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/predcr/__init__.py` (updated — register predcr_get_layer_spec, predcr_list_layer_specs)
- `src/lcs_cad_mcp/modules/predcr/tools.py` (updated — predcr_get_layer_spec, predcr_list_layer_specs handlers)
- `src/lcs_cad_mcp/modules/predcr/service.py` (updated — get_layer_spec, list_layer_specs methods)
- `src/lcs_cad_mcp/modules/predcr/schemas.py` (updated — GetLayerSpecInput, ListLayerSpecsInput, LayerSpecData, ListLayerSpecsOutput)
- `tests/unit/modules/predcr/test_predcr_get_layer_spec.py`
