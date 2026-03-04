# Story 6.4: Minimum Entity Count Verification

Status: ready-for-dev

## Story

As a **developer**,
I want **a minimum entity count check that verifies required PreDCR layers have at least the required number of entities**,
so that **drawings with empty or under-populated required layers are flagged before scrutiny (FR16)**.

## Acceptance Criteria

1. **AC1:** `VerificationService.check_minimum_entities(building_type: str)` inspects each required PreDCR layer defined in `layer_registry.py` and verifies its actual entity count meets or exceeds `min_entity_count` defined per layer per building type.
2. **AC2:** Returns `list[VerificationFailure]` where each failure carries `entity_id="N/A"` (layer-level failure, not entity-level), `failure_type="MIN_ENTITY"`, `layer` (the deficient layer name), `description` (required count vs actual count), and `suggested_correction` (what entities need to be drawn).
3. **AC3:** Minimum entity counts are read exclusively from the PreDCR layer catalog in `layer_registry.py` (Story 4-1) — never hardcoded in `service.py`.
4. **AC4:** Layers that are optional for a given `building_type` are skipped — no failure is raised for an optional layer with zero entities.
5. **AC5:** The `verify_minimum_entities` MCP tool wraps `check_minimum_entities()`, follows the 6-step handler pattern (session → validate → NO snapshot → service call → event_log → return), and accepts `building_type: str` as input.
6. **AC6:** Unit tests cover: required layer with sufficient entities passes, required layer with zero entities fails, required layer with count below minimum fails, optional layer with zero entities passes, unknown building_type returns error.

## Tasks / Subtasks

- [ ] Task 1: Extend `schemas.py` with minimum entity count result type (AC: 2)
  - [ ] 1.1: Add `MinEntityCheckResult` Pydantic model with fields: `passed: bool`, `failures: list[VerificationFailure]`, `checked_layer_count: int`, `building_type: str`
  - [ ] 1.2: Export `MinEntityCheckResult` from `schemas.py`
  - [ ] 1.3: Confirm `VerificationFailure.failure_type` literal already includes `"MIN_ENTITY"` — no schema change needed

- [ ] Task 2: Review and confirm `layer_registry.py` interface for min entity counts (AC: 3)
  - [ ] 2.1: Review `src/lcs_cad_mcp/modules/predcr/layer_registry.py` — identify the `LayerDefinition` model field that specifies minimum entity counts; expected name: `min_entity_count: int` or `min_count: dict[str, int]` keyed by building_type
  - [ ] 2.2: Identify how optional vs required layers are encoded — expected: `required: bool` or `required_for: list[str]` field
  - [ ] 2.3: Document the accessed fields in a comment at the top of `check_minimum_entities()` implementation
  - [ ] 2.4: If the `layer_registry.py` interface does not yet support per-building-type counts, use a flat `min_entity_count: int` with a single default, and add a `TODO` comment for future Story 4-x enhancement

- [ ] Task 3: Implement `VerificationService.check_minimum_entities()` in `service.py` (AC: 1, 2, 3, 4)
  - [ ] 3.1: Import `LAYER_REGISTRY` from `src/lcs_cad_mcp/modules/predcr/layer_registry` — iterate over all `LayerDefinition` entries
  - [ ] 3.2: For each layer definition, check if it is required for `building_type` — if not required, skip it entirely (AC4)
  - [ ] 3.3: Retrieve the `min_entity_count` for this layer (from the registry, not hardcoded); if `min_entity_count == 0`, skip (layer has no minimum requirement)
  - [ ] 3.4: Call `EntityService.count_entities(layer=layer_name)` — or fall back to `len(EntityService.list_entities(layer=layer_name))` if `count_entities()` is not available
  - [ ] 3.5: If `actual_count < min_entity_count`, append `VerificationFailure(entity_id="N/A", failure_type="MIN_ENTITY", layer=layer_name, description=f"Layer '{layer_name}' has {actual_count} entities; requires at least {min_entity_count}", suggested_correction=f"Draw at least {min_entity_count - actual_count} more entity(ies) on layer '{layer_name}'")`
  - [ ] 3.6: Return complete `failures` list

- [ ] Task 4: Implement `verify_minimum_entities` MCP tool handler in `tools.py` (AC: 5)
  - [ ] 4.1: Define `@mcp.tool()` decorated async function `verify_minimum_entities(ctx: Context, building_type: str) -> dict`
  - [ ] 4.2: Step 1 — retrieve session: `session = ctx.get_state("drawing_session")`; if missing, return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 4.3: Step 2 — validate `building_type`: confirm it is non-empty and is a known building type in the registry; if unknown, return `MCPError(INVALID_PARAMS, f"Unknown building_type: '{building_type}'").to_response()`
  - [ ] 4.4: Step 3 — NO snapshot (read-only tool)
  - [ ] 4.5: Step 4 — call `VerificationService(session).check_minimum_entities(building_type=building_type)`; collect `failures`
  - [ ] 4.6: Step 5 — append to event log: `{"tool": "verify_minimum_entities", "building_type": building_type, "failure_count": len(failures)}`
  - [ ] 4.7: Step 6 — return `{"success": True, "data": {"passed": len(failures) == 0, "failures": [f.model_dump() for f in failures], "building_type": building_type, "checked_layer_count": <layers evaluated>}}`

- [ ] Task 5: Register `verify_minimum_entities` tool and update `__init__.py` (AC: 5)
  - [ ] 5.1: Add `verify_minimum_entities` to the `register(mcp)` call chain in `tools.py`
  - [ ] 5.2: Confirm `modules/verification/__init__.py` `register()` function picks up all four verify tools: `verify_closure`, `verify_containment`, `verify_naming`, `verify_minimum_entities`

- [ ] Task 6: Write unit tests for minimum entity count verification (AC: 6)
  - [ ] 6.1: Create `tests/unit/modules/verification/test_min_entity.py`
  - [ ] 6.2: Build `MockCADBackend` fixture with mock `LAYER_REGISTRY` data: one required layer with `min_entity_count=2` populated with 3 entities (pass), one required layer with `min_entity_count=1` and 0 entities (fail), one optional layer with `min_entity_count=1` and 0 entities (skip)
  - [ ] 6.3: Test `check_minimum_entities(building_type="residential")` returns zero failures when all required layers have sufficient entities
  - [ ] 6.4: Test `check_minimum_entities(building_type="residential")` returns one failure for the under-populated required layer
  - [ ] 6.5: Test optional layer with zero entities returns no failure for that layer
  - [ ] 6.6: Test unknown `building_type` — tool handler returns `INVALID_PARAMS` error (not a service-level test; test the tool handler directly)
  - [ ] 6.7: Mock `LAYER_REGISTRY` in tests using `unittest.mock.patch` so tests are not dependent on real PreDCR layer catalog data

- [ ] Task 7: Validate building type enumeration (AC: 5)
  - [ ] 7.1: Define `KNOWN_BUILDING_TYPES: frozenset[str]` in `layer_registry.py` or derive it from the registry keys — expose it for import in `tools.py` validation step
  - [ ] 7.2: In Step 2 of the tool handler, check `building_type.lower() in KNOWN_BUILDING_TYPES` — perform case-insensitive comparison
  - [ ] 7.3: Include the list of valid building types in the error response `suggested_action` field: `f"Valid building types: {sorted(KNOWN_BUILDING_TYPES)}"`

## Dev Notes

### Critical Architecture Constraints

1. **READ-ONLY tool — no snapshot.** `verify_minimum_entities` never mutates drawing state. Skip Step 3 (snapshot) of the 6-step handler pattern entirely.
2. **Minimum counts come exclusively from `layer_registry.py`.** Never hardcode minimum entity counts in `service.py` or `tools.py`. The registry is the single source of truth (owned by Story 4-1).
3. **Layer-level failures use `entity_id="N/A"`.** This check operates at the layer level, not the entity level — there is no specific entity handle to reference when a layer has too few entities. Use the sentinel value `"N/A"` for `entity_id`.
4. **`building_type` is a required parameter** for this check — different building types have different required layer sets. The tool must validate this parameter before calling the service.

### Module/Component Notes

**`service.py` — check_minimum_entities() skeleton:**

```python
from lcs_cad_mcp.modules.predcr.layer_registry import LAYER_REGISTRY


def check_minimum_entities(self, building_type: str) -> list[VerificationFailure]:
    failures: list[VerificationFailure] = []

    for layer_name, layer_def in LAYER_REGISTRY.items():
        # Skip layers not required for this building type
        if not self._is_required(layer_def, building_type):
            continue

        min_count = layer_def.min_entity_count  # or getattr(layer_def, 'min_entity_count', 0)
        if min_count == 0:
            continue  # no minimum requirement for this layer

        # Count actual entities on this layer
        entities = self._entity_svc.list_entities(layer=layer_name)
        actual_count = len(entities)

        if actual_count < min_count:
            failures.append(VerificationFailure(
                entity_id="N/A",
                failure_type="MIN_ENTITY",
                layer=layer_name,
                description=(
                    f"Layer '{layer_name}' has {actual_count} entity(ies); "
                    f"requires at least {min_count} for building type '{building_type}'"
                ),
                suggested_correction=(
                    f"Draw {min_count - actual_count} more entity(ies) on layer '{layer_name}'"
                ),
            ))

    return failures

def _is_required(self, layer_def, building_type: str) -> bool:
    # Adapt based on actual LayerDefinition schema from layer_registry.py
    if hasattr(layer_def, "required_for"):
        return building_type.lower() in [bt.lower() for bt in layer_def.required_for]
    if hasattr(layer_def, "required"):
        return layer_def.required  # flat boolean — applies to all building types
    return False  # unknown — treat as optional
```

**MinEntityCheckResult schema addition to `schemas.py`:**

```python
class MinEntityCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    failures: list[VerificationFailure]
    checked_layer_count: int
    building_type: str
```

**Building type validation in `tools.py`:**

```python
from lcs_cad_mcp.modules.predcr.layer_registry import KNOWN_BUILDING_TYPES

async def verify_minimum_entities(ctx: Context, building_type: str) -> dict:
    # Step 2: Validate building_type
    if building_type.lower() not in {bt.lower() for bt in KNOWN_BUILDING_TYPES}:
        return MCPError(
            code=ErrorCode.INVALID_PARAMS,
            message=f"Unknown building_type: '{building_type}'",
            suggested_action=f"Valid types: {sorted(KNOWN_BUILDING_TYPES)}",
        ).to_response()
```

### Project Structure Notes

Files modified or created for this story:

```
src/lcs_cad_mcp/modules/verification/
├── __init__.py       # updated: register() includes verify_minimum_entities
├── schemas.py        # updated: add MinEntityCheckResult
├── service.py        # updated: add check_minimum_entities(), _is_required()
└── tools.py          # updated: add verify_minimum_entities handler

src/lcs_cad_mcp/modules/predcr/
└── layer_registry.py # reviewed (not modified): must expose LAYER_REGISTRY dict and KNOWN_BUILDING_TYPES

tests/unit/modules/verification/
├── __init__.py       # already exists from Story 6-1
└── test_min_entity.py  # NEW
```

### Dependencies

- **Story 6-1** (`VerificationFailure` model in `schemas.py`; `VerificationService` class skeleton in `service.py`)
- **Story 4-1** (PreDCR layer catalog — `layer_registry.py` must define `LayerDefinition` with `min_entity_count` and `required` / `required_for` fields, and expose `LAYER_REGISTRY: dict[str, LayerDefinition]` and `KNOWN_BUILDING_TYPES: frozenset[str]`)
- **Story 5-6** (Entity listing — `EntityService.list_entities(layer=...)` must support layer-filtered queries; ideally also `count_entities(layer=...)` for efficiency)
- **Story 2-1** (CAD Backend — `DrawingSession` accessible via `ctx.get_state()`)

### References

- FR16: Minimum entity count requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 6, Story 6-4]
- NFR14: Zero false positives — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 6 NFR coverage]
- Layer registry design — [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Layer Registry"]
- PreDCR layer catalog — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 4, Story 4-1]
- 6-step tool handler pattern — [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/verification/__init__.py`
- `src/lcs_cad_mcp/modules/verification/schemas.py`
- `src/lcs_cad_mcp/modules/verification/service.py`
- `src/lcs_cad_mcp/modules/verification/tools.py`
- `tests/unit/modules/verification/test_min_entity.py`
