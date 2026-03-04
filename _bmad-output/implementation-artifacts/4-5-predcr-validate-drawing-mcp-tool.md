# Story 4.5: `predcr_validate_drawing` MCP Tool

Status: ready-for-dev

## Story

As an **AI client**,
I want **to validate that a drawing conforms to all PreDCR structural requirements in a single tool call**,
so that **issues are caught and reported with actionable suggestions before the drawing enters the scrutiny pipeline**.

## Acceptance Criteria

1. **AC1:** `predcr_validate_drawing()` MCP tool checks all of the following in the active drawing: all required PreDCR layers for the drawing's building type are present (by name), all present PreDCR layers have properties matching their `LayerSpec` (color_index, linetype), and no required layer is missing from `PREDCR_LAYERS`.
2. **AC2:** Returns a structured response: `{"success": True, "data": {"valid": bool, "violations": list[{"layer": str, "issue": str, "suggestion": str}], "checked_layers": int, "building_type": str}}`.
3. **AC3:** A drawing produced by `predcr_run_setup` returns `valid: true, violations: []` immediately after setup (zero false positives on a clean PreDCR drawing).
4. **AC4:** Detected violation types include: `MISSING_LAYER` (required layer absent), `COLOR_MISMATCH` (layer exists but wrong color_index), `LINETYPE_MISMATCH` (layer exists but wrong linetype).
5. **AC5:** Requires an active drawing session (`ctx.get_state("session")`); returns `MCPError(SESSION_NOT_STARTED)` if no session is open. This is a read-intensive operation (inspects drawing state) — still requires session but does NOT take a snapshot (read-only in terms of drawing modifications).
6. **AC6:** Uses `LayerValidator` from the layers module (`lcs_cad_mcp.modules.layers`) to perform per-layer property checks — does not re-implement layer property comparison logic inline in the predcr module.
7. **AC7:** The `building_type` for validation is read from the drawing's session metadata (set during `predcr_run_setup`) or accepted as an optional parameter `building_type: str | None = None` — if `None`, attempts to read from session; returns `MCPError(INVALID_PARAMS)` if neither source provides it.

## Tasks / Subtasks

- [ ] Task 1: Define input/output schemas in `schemas.py` (AC: 2, 7)
  - [ ] 1.1: Add `ValidateDrawingInput(BaseModel)` with `building_type: str | None = None` (normalize to lowercase if provided).
  - [ ] 1.2: Add `ViolationDetail(BaseModel)` with `layer: str`, `issue: str` (short code: `"MISSING_LAYER"`, `"COLOR_MISMATCH"`, `"LINETYPE_MISMATCH"`), `suggestion: str` (human-readable fix guidance).
  - [ ] 1.3: Add `ValidateDrawingOutput(BaseModel)` with `valid: bool`, `violations: list[ViolationDetail]`, `checked_layers: int`, `building_type: str`.
  - [ ] 1.4: Export all three from `schemas.py`.

- [ ] Task 2: Implement `PreDCRService.validate_drawing()` in `service.py` (AC: 1, 2, 3, 4, 6, 7)
  - [ ] 2.1: Add `async def validate_drawing(self, building_type: str) -> dict` to `PreDCRService`.
  - [ ] 2.2: Fetch required specs via `get_layers_for_building_type(building_type)` from `layer_registry`.
  - [ ] 2.3: Fetch existing drawing layers via `LayerService(self._session).list_all()` — returns a list of `Layer` model instances (from Epic 3, Story 3-1).
  - [ ] 2.4: Build a lookup dict of existing layers by uppercase name: `existing = {layer.name.upper(): layer for layer in drawing_layers}`.
  - [ ] 2.5: For each `LayerSpec` in the required specs list:
    - If `spec.name.upper()` not in `existing`: add violation `ViolationDetail(layer=spec.name, issue="MISSING_LAYER", suggestion=f"Create layer '{spec.name}' with color_index={spec.color_index}, linetype='{spec.linetype}'.")`.
    - Else retrieve `actual = existing[spec.name.upper()]` and call `LayerValidator.check_properties(actual, spec)` (returns list of property mismatch strings); for each mismatch, add appropriate `ViolationDetail`.
  - [ ] 2.6: Return `{"valid": len(violations) == 0, "violations": [v.model_dump() for v in violations], "checked_layers": len(specs), "building_type": building_type}`.

- [ ] Task 3: Implement `LayerValidator.check_properties()` in the layers module (AC: 4, 6)
  - [ ] 3.1: Create or update `src/lcs_cad_mcp/modules/layers/validator.py` (may already have a stub from Story 3-4).
  - [ ] 3.2: Add `class LayerValidator` with static method `check_properties(layer: Layer, spec: LayerSpec) -> list[ViolationDetail]`.
  - [ ] 3.3: Check `color_index` mismatch: if `layer.color_index != spec.color_index`, append `ViolationDetail(layer=layer.name, issue="COLOR_MISMATCH", suggestion=f"Set layer '{layer.name}' color to {spec.color_index} (current: {layer.color_index}).")`.
  - [ ] 3.4: Check `linetype` mismatch (case-insensitive): if `layer.linetype.upper() != spec.linetype.upper()`, append `ViolationDetail(layer=layer.name, issue="LINETYPE_MISMATCH", suggestion=f"Set layer '{layer.name}' linetype to '{spec.linetype}' (current: '{layer.linetype}').")`.
  - [ ] 3.5: Return the list of violations (empty if all properties match).
  - [ ] 3.6: Import `LayerValidator` in `predcr/service.py` from `lcs_cad_mcp.modules.layers.validator`.

- [ ] Task 4: Implement `predcr_validate_drawing` tool handler in `tools.py` (AC: 1, 5, 7)
  - [ ] 4.1: Implement `async def predcr_validate_drawing(ctx: Context, building_type: str | None = None) -> dict`.
  - [ ] 4.2: Apply read-with-session handler pattern:
    - Step 1: `session = ctx.get_state("session")` — if `None`, return `MCPError(SESSION_NOT_STARTED).to_response()`.
    - Step 2: Validate input — `params = ValidateDrawingInput(building_type=building_type)`. Resolve `building_type`: `bt = params.building_type or session.metadata.get("building_type")`. If `bt` is still `None`, return `MCPError(INVALID_PARAMS, "building_type not provided and not found in session metadata.").to_response()`.
    - Step 3: NO snapshot taken (read-only drawing inspection).
    - Step 4: `result = await PreDCRService(session).validate_drawing(bt)`.
    - Step 5: `await session.event_log.record("predcr_validate_drawing", {"building_type": bt, "valid": result["valid"], "violation_count": len(result["violations"])})` — log a concise summary only (not the full violation list).
    - Step 6: Return `{"success": True, "data": result}`.
  - [ ] 4.3: Wrap Step 4 in `try/except Exception as e` — return `MCPError("PREDCR_VALIDATION_FAILED", str(e), recoverable=True).to_response()` on unexpected error.
  - [ ] 4.4: No rollback needed (read-only; no writes occurred).

- [ ] Task 5: Register `predcr_validate_drawing` in `__init__.py` (AC: 1)
  - [ ] 5.1: Add `predcr_validate_drawing` to `register(mcp)` in `predcr/__init__.py`.
  - [ ] 5.2: Confirm exposed tool name is exactly `predcr_validate_drawing`.

- [ ] Task 6: Write unit tests (AC: 1, 2, 3, 4, 5, 6, 7)
  - [ ] 6.1: Create `tests/unit/modules/predcr/test_predcr_validate_drawing.py`.
  - [ ] 6.2: Create `tests/unit/modules/layers/test_layer_validator.py` for the `LayerValidator` tests.
  - [ ] 6.3: Test clean drawing — mock `LayerService.list_all()` to return `Layer` objects exactly matching all `PREDCR_LAYERS` specs for `"residential"`; assert `valid=True`, `violations=[]`.
  - [ ] 6.4: Test missing layer — omit one required layer from the mock; assert `violations` contains one entry with `issue="MISSING_LAYER"` naming the missing layer.
  - [ ] 6.5: Test color mismatch — include all layers but change one `color_index` in the mock; assert `violations` contains `issue="COLOR_MISMATCH"` with correct suggestion.
  - [ ] 6.6: Test linetype mismatch — change one layer's linetype; assert `violations` contains `issue="LINETYPE_MISMATCH"`.
  - [ ] 6.7: Test multiple violations — missing 2 layers + 1 color mismatch; assert `violations` has 3 entries, `valid=False`.
  - [ ] 6.8: Test SESSION_NOT_STARTED — `ctx.get_state("session")` returns `None`; assert `error.code == "SESSION_NOT_STARTED"`.
  - [ ] 6.9: Test building_type from session metadata — `building_type=None` parameter but `session.metadata["building_type"] = "commercial"`; assert validation runs with `"commercial"` building type.
  - [ ] 6.10: Test building_type from neither source — `building_type=None` and session has no `"building_type"` in metadata; assert `error.code == "INVALID_PARAMS"`.
  - [ ] 6.11: Test `LayerValidator.check_properties()` directly — pass a `Layer` with mismatched `color_index`; assert returns one `ViolationDetail` with `issue="COLOR_MISMATCH"`. Pass a perfectly matching `Layer`; assert returns `[]`.
  - [ ] 6.12: Test no snapshot taken — mock `session.snapshot.take` and assert it is never called.
  - [ ] 6.13: Test event_log records a concise summary (not the full violations list).

- [ ] Task 7: End-to-end AC5 integration test (AC: 3, 5)
  - [ ] 7.1: Write integration test using ezdxf backend: call `predcr_run_setup("residential", "IntegTest", "mm")`, then call `predcr_validate_drawing(building_type="residential")`, assert `valid=True` and `violations=[]`.
  - [ ] 7.2: Mark with `@pytest.mark.integration` for optional CI gate.
  - [ ] 7.3: Document any known limitations (e.g. if entity validation is not yet wired in — future Epic 6 hook).

- [ ] Task 8: Lint and full test run (AC: all)
  - [ ] 8.1: Run `pytest tests/unit/modules/predcr/test_predcr_validate_drawing.py tests/unit/modules/layers/test_layer_validator.py -v` — all pass.
  - [ ] 8.2: Run `ruff check src/lcs_cad_mcp/modules/predcr/ src/lcs_cad_mcp/modules/layers/validator.py` — zero violations.

## Dev Notes

### Critical Architecture Constraints

1. **Read-only for drawing modifications — but NOT session-free** — unlike `predcr_get_layer_spec`, this tool REQUIRES a session (to read the actual drawing's layers). It does NOT take a snapshot because it makes no writes. This is a distinct hybrid: session-required + no-snapshot + event-log-only-on-success.
2. **`LayerValidator` lives in the layers module** — violation detection logic for layer property comparison belongs in `src/lcs_cad_mcp/modules/layers/validator.py`, not inline in `predcr/service.py`. This keeps the validation logic reusable by both the predcr module and any future layer-level validation tools. Import it; don't duplicate it.
3. **`ViolationDetail` is defined in `predcr/schemas.py`** — but `LayerValidator.check_properties()` in the layers module needs to return violations in this shape. To avoid circular imports, `ViolationDetail` can either: (a) be a plain `TypedDict` or `dict` returned by `LayerValidator` and then wrapped in the `predcr/schemas.py` Pydantic model in the service layer, or (b) be defined in a shared `lcs_cad_mcp.types` module. Preferred: approach (a) — `LayerValidator` returns `list[dict]`, `PreDCRService.validate_drawing()` wraps them in `ViolationDetail`.
4. **Building type from session metadata** — `predcr_run_setup` (Story 4-4) must store `building_type` in session metadata at setup time: `session.metadata["building_type"] = building_type`. This must be implemented in Story 4-4 if not already done, so that `predcr_validate_drawing` can read it for sessionless-parameter scenarios.
5. **No entity-level validation in this story** — AC4 mentions connecting to the Verification Engine (Epic 6) for closure/containment/naming checks. This story implements only layer-level validation (presence + properties). The Epic 6 hook is a future extension. Add a `TODO: Epic 6 hook — entity validation` comment at the appropriate place in `validate_drawing()`.

### Module/Component Notes

**`LayerValidator` in `layers/validator.py`:**

```python
"""Layer property validation utilities. Used by predcr module and future verification tools."""

class LayerValidator:
    @staticmethod
    def check_properties(layer, spec) -> list[dict]:
        """
        Compare a Layer's actual properties against a LayerSpec.
        Returns a list of violation dicts: {layer, issue, suggestion}.
        """
        violations = []
        if layer.color_index != spec.color_index:
            violations.append({
                "layer": layer.name,
                "issue": "COLOR_MISMATCH",
                "suggestion": (
                    f"Set layer '{layer.name}' color_index to {spec.color_index} "
                    f"(currently {layer.color_index})."
                ),
            })
        if layer.linetype.upper() != spec.linetype.upper():
            violations.append({
                "layer": layer.name,
                "issue": "LINETYPE_MISMATCH",
                "suggestion": (
                    f"Set layer '{layer.name}' linetype to '{spec.linetype}' "
                    f"(currently '{layer.linetype}')."
                ),
            })
        return violations
```

**`PreDCRService.validate_drawing()` outline:**

```python
async def validate_drawing(self, building_type: str) -> dict:
    specs = get_layers_for_building_type(building_type)
    drawing_layers = await LayerService(self._session).list_all()
    existing = {layer.name.upper(): layer for layer in drawing_layers}

    violations = []
    for spec in specs:
        key = spec.name.upper()
        if key not in existing:
            violations.append({
                "layer": spec.name,
                "issue": "MISSING_LAYER",
                "suggestion": (
                    f"Create layer '{spec.name}' with color_index={spec.color_index}, "
                    f"linetype='{spec.linetype}'."
                ),
            })
        else:
            prop_violations = LayerValidator.check_properties(existing[key], spec)
            violations.extend(prop_violations)

    # TODO: Epic 6 hook — entity validation (closure, containment, naming checks)

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "checked_layers": len(specs),
        "building_type": building_type,
    }
```

**Tool handler — building_type resolution logic:**

```python
bt = params.building_type or session.metadata.get("building_type")
if bt is None:
    return MCPError(
        ErrorCode.INVALID_PARAMS,
        "building_type not provided and not stored in session metadata. "
        "Pass building_type explicitly or call predcr_run_setup first.",
    ).to_response()
```

**Violation issue codes (constants):**

```python
# In schemas.py or a constants block
class ViolationIssue:
    MISSING_LAYER = "MISSING_LAYER"
    COLOR_MISMATCH = "COLOR_MISMATCH"
    LINETYPE_MISMATCH = "LINETYPE_MISMATCH"
```

### Project Structure Notes

```
src/lcs_cad_mcp/modules/predcr/
├── __init__.py    # register(mcp) — adds predcr_validate_drawing
├── layer_registry.py  # Story 4-1
├── tools.py       # THIS STORY — predcr_validate_drawing handler
├── service.py     # THIS STORY — PreDCRService.validate_drawing()
└── schemas.py     # THIS STORY — ValidateDrawingInput, ViolationDetail, ValidateDrawingOutput

src/lcs_cad_mcp/modules/layers/
├── __init__.py
├── tools.py       # Epic 3 (unchanged by this story)
├── service.py     # Epic 3 — LayerService.list_all() (must exist)
├── schemas.py     # Epic 3
└── validator.py   # THIS STORY — LayerValidator.check_properties() (new or extended from Story 3-4)

tests/unit/modules/predcr/
├── __init__.py
├── test_layer_registry.py           # Story 4-1
├── test_predcr_create_layers.py     # Story 4-2
├── test_predcr_get_layer_spec.py    # Story 4-3
├── test_predcr_run_setup.py         # Story 4-4
└── test_predcr_validate_drawing.py  # THIS STORY

tests/unit/modules/layers/
└── test_layer_validator.py          # THIS STORY (new test file)
```

### Dependencies

- **Story 4-1** — `PREDCR_LAYERS`, `get_layers_for_building_type`, `LayerSpec` must be complete.
- **Story 3-4** — `layers/validator.py` stub from PreDCR layer naming validation; `LayerValidator.check_properties()` extends or is added alongside the existing `layer_validate_naming` function.
- **Story 3-3** — `LayerService.list_all()` (the `layer_list` MCP tool's underlying service method) must return `list[Layer]` with `color_index` and `linetype` fields.
- **Story 4-4** — `predcr_run_setup` must store `building_type` in session metadata so that `predcr_validate_drawing` can read it from session when the parameter is omitted. Coordinate with Story 4-4 dev.
- **Epic 6** — Verification Engine hooks are explicitly out of scope for this story (AC4 wording: "Connects to Verification Engine (Epic 6)" — this is a future hook, documented via TODO comment).

### References

- Story 4-5 requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 4-5]
- AC4 note on Epic 6 hook: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 4-5 AC4: "Connects to Verification Engine (Epic 6) for closure/containment/naming checks"]
- Violation struct `{layer, issue, suggestion}`: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 4-5 AC2]
- 6-step handler pattern: [Source: Mandatory architecture context — "6-STEP TOOL HANDLER (async)"]
- Layer module validator pattern: [Source: Mandatory architecture context — "predcr_validate_drawing() — validates current drawing has all required PreDCR layers; uses LayerValidator from layers module"]
- Session metadata building_type: [Source: Story 4-4 architecture — session.metadata used to persist setup configuration]
- NFR14 zero false positives: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 3-4 AC4, Story 4-2 AC4]
- AC3 (clean drawing passes): [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 4-5 AC3]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/predcr/__init__.py` (updated — register predcr_validate_drawing)
- `src/lcs_cad_mcp/modules/predcr/tools.py` (updated — predcr_validate_drawing handler)
- `src/lcs_cad_mcp/modules/predcr/service.py` (updated — PreDCRService.validate_drawing)
- `src/lcs_cad_mcp/modules/predcr/schemas.py` (updated — ValidateDrawingInput, ViolationDetail, ValidateDrawingOutput)
- `src/lcs_cad_mcp/modules/layers/validator.py` (new or updated — LayerValidator.check_properties)
- `tests/unit/modules/predcr/test_predcr_validate_drawing.py`
- `tests/unit/modules/layers/test_layer_validator.py`
