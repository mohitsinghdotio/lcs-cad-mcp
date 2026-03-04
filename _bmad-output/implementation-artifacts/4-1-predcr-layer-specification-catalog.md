# Story 4.1: PreDCR Layer Specification Catalog

Status: ready-for-dev

## Story

As a **developer**,
I want **a catalog of all required PreDCR layers per building type defined as a Pydantic model and a static Python registry**,
so that **the system can auto-create the correct layer set for any building type with a single authoritative source of truth**.

## Acceptance Criteria

1. **AC1:** `LayerSpec` Pydantic v2 model defined in `layer_registry.py` with fields: `name: str`, `color_index: int`, `linetype: str`, `required_for: list[str]` (building types), `entity_types: list[str]` (entity type suffixes expected on this layer).
2. **AC2:** `PREDCR_LAYERS: list[LayerSpec]` constant in `layer_registry.py` contains complete layer definitions for Residential, Commercial, and Industrial building types (40–50 layers total covering walls, columns, doors, windows, stairs, ramps, toilets, lifts, site, setback, and annotation layers).
3. **AC3:** Helper functions `get_layers_for_building_type(building_type: str) -> list[LayerSpec]` and `get_layer_by_name(name: str) -> LayerSpec | None` are implemented and exported from `layer_registry.py`.
4. **AC4:** The registry can be extended for new building types by adding entries to `PREDCR_LAYERS` with the new building type string in `required_for` — no code changes needed outside `layer_registry.py`.
5. **AC5:** Unit tests in `tests/unit/modules/predcr/test_layer_registry.py` verify: catalog loads without Pydantic validation errors, each building type returns at least 30 layers, all `color_index` values are in range 1–256, all `linetype` strings are valid AutoCAD linetype names, no duplicate layer names exist in the registry.
6. **AC6:** `layer_registry.py` is importable without a running CAD session or MCP server (pure data module — no backend imports).

## Tasks / Subtasks

- [ ] Task 1: Define `LayerSpec` Pydantic model in `layer_registry.py` (AC: 1, 6)
  - [ ] 1.1: Create `src/lcs_cad_mcp/modules/predcr/layer_registry.py` replacing the stub.
  - [ ] 1.2: Define `LayerSpec(BaseModel)` with fields: `name: str`, `color_index: int` (Field ge=1, le=256), `linetype: str` (e.g. "Continuous", "DASHED", "CENTER"), `required_for: list[str]` (building type keys e.g. `["residential", "commercial"]`), `entity_types: list[str]` (e.g. `["WALL", "COLUMN"]`).
  - [ ] 1.3: Add `model_config = ConfigDict(frozen=True)` so specs are immutable at runtime.
  - [ ] 1.4: Verify `LayerSpec` has no imports from `backends/`, `session/`, or any MCP module — pure data only.

- [ ] Task 2: Populate `PREDCR_LAYERS` registry with all required layer definitions (AC: 2, 4)
  - [ ] 2.1: Add wall and structural layers: e.g. `PREDCR-WALL-EXT` (color 7, Continuous, residential+commercial+industrial), `PREDCR-WALL-INT` (color 8, Continuous), `PREDCR-COLUMN` (color 5, Continuous).
  - [ ] 2.2: Add opening layers: `PREDCR-DOOR` (color 3, Continuous), `PREDCR-WINDOW` (color 4, Continuous), `PREDCR-DOOR-EXT`, `PREDCR-WINDOW-EXT`.
  - [ ] 2.3: Add vertical circulation layers: `PREDCR-STAIR` (color 6, Continuous), `PREDCR-RAMP` (color 6, Continuous), `PREDCR-LIFT` (color 2, Continuous).
  - [ ] 2.4: Add sanitation/service layers: `PREDCR-TOILET` (color 3, HIDDEN), `PREDCR-SHAFT` (color 1, CENTER), `PREDCR-DUCT` (color 1, CENTER).
  - [ ] 2.5: Add site and boundary layers: `PREDCR-SITE-BOUNDARY` (color 2, DASHED), `PREDCR-SETBACK` (color 1, DASHED), `PREDCR-ROAD` (color 7, Continuous).
  - [ ] 2.6: Add annotation and dimension layers: `PREDCR-DIMENSION` (color 7, Continuous), `PREDCR-TEXT` (color 7, Continuous), `PREDCR-HATCH` (color 8, Continuous).
  - [ ] 2.7: Add building-type-specific layers — e.g. `PREDCR-PARKING` (color 3, Continuous, required_for=["commercial", "residential"]), `PREDCR-LOADING` (commercial+industrial only), `PREDCR-MACHINERY` (industrial only).
  - [ ] 2.8: Ensure total PREDCR_LAYERS count is >= 40. Add comment header in the file noting this is the authoritative PreDCR layer catalog.

- [ ] Task 3: Implement helper functions (AC: 3)
  - [ ] 3.1: Implement `get_layers_for_building_type(building_type: str) -> list[LayerSpec]` — filters `PREDCR_LAYERS` where `building_type.lower()` is in `spec.required_for`. Raise `ValueError` for completely unknown building type strings (not found in any spec's `required_for`).
  - [ ] 3.2: Implement `get_layer_by_name(name: str) -> LayerSpec | None` — case-insensitive name lookup over `PREDCR_LAYERS`. Returns `None` if not found.
  - [ ] 3.3: Implement `get_all_building_types() -> list[str]` — returns a deduplicated sorted list of all building type strings referenced in `PREDCR_LAYERS`.
  - [ ] 3.4: Export all three functions and `LayerSpec` + `PREDCR_LAYERS` from `__init__.py` of the predcr module.

- [ ] Task 4: Update `src/lcs_cad_mcp/modules/predcr/__init__.py` (AC: 4, 6)
  - [ ] 4.1: Import and re-export `LayerSpec`, `PREDCR_LAYERS`, `get_layers_for_building_type`, `get_layer_by_name`, `get_all_building_types` from `layer_registry`.
  - [ ] 4.2: Keep `register(mcp)` stub in `__init__.py` (to be filled by Story 4-2, 4-3, 4-4, 4-5).

- [ ] Task 5: Write unit tests (AC: 5, 6)
  - [ ] 5.1: Create `tests/unit/modules/predcr/` directory with `__init__.py` (empty) and `test_layer_registry.py`.
  - [ ] 5.2: Test: `PREDCR_LAYERS` imports without error; `len(PREDCR_LAYERS) >= 40`.
  - [ ] 5.3: Test: No duplicate `name` values in `PREDCR_LAYERS` — assert `len({s.name for s in PREDCR_LAYERS}) == len(PREDCR_LAYERS)`.
  - [ ] 5.4: Test: All `color_index` values satisfy `1 <= color_index <= 256`.
  - [ ] 5.5: Test: All `linetype` values are from an allowed set: `{"Continuous", "DASHED", "HIDDEN", "CENTER", "DASHDOT", "BORDER"}`.
  - [ ] 5.6: Test `get_layers_for_building_type("residential")` returns >= 30 specs.
  - [ ] 5.7: Test `get_layers_for_building_type("commercial")` returns >= 30 specs.
  - [ ] 5.8: Test `get_layers_for_building_type("industrial")` returns >= 20 specs.
  - [ ] 5.9: Test `get_layer_by_name("PREDCR-WALL-EXT")` returns the correct `LayerSpec` with expected color_index; test `get_layer_by_name("nonexistent")` returns `None`.
  - [ ] 5.10: Test `get_all_building_types()` returns a sorted list containing `["commercial", "industrial", "residential"]`.
  - [ ] 5.11: Test that `LayerSpec` is frozen — attempting `spec.name = "X"` raises `ValidationError` or `TypeError`.

- [ ] Task 6: Run full test suite and confirm clean pass (AC: 5)
  - [ ] 6.1: Run `pytest tests/unit/modules/predcr/test_layer_registry.py -v` — all tests pass.
  - [ ] 6.2: Run `python -c "from lcs_cad_mcp.modules.predcr.layer_registry import PREDCR_LAYERS; print(len(PREDCR_LAYERS))"` — prints >= 40 with no import errors.
  - [ ] 6.3: Run `ruff check src/lcs_cad_mcp/modules/predcr/layer_registry.py` — zero violations.

## Dev Notes

### Critical Architecture Constraints

1. **`layer_registry.py` is pure data** — it MUST NOT import from `backends/`, `session/`, `server.py`, or any MCP-specific module. It is a standalone data catalog importable by any module without side effects.
2. **`PREDCR_LAYERS` is the single source of truth** — all other PreDCR tools (Stories 4-2 through 4-5) and downstream modules (Epic 6 verification) read from this registry. Never define PreDCR layer specs anywhere else.
3. **Pydantic v2 with `frozen=True`** — `LayerSpec` uses `ConfigDict(frozen=True)`. This makes instances hashable and prevents accidental mutation at runtime.
4. **Building type keys are lowercase strings** — `"residential"`, `"commercial"`, `"industrial"`. All lookups must normalize to lowercase. Never use enums for building type at this layer to keep extensibility without code changes.
5. **No MCP tool in this story** — Story 4-1 delivers data infrastructure only. The MCP tools `predcr_get_layer_spec` and `predcr_list_layer_specs` that expose this data are built in Story 4-3.

### Module/Component Notes

**`layer_registry.py` structure:**

```python
"""
PreDCR Layer Specification Catalog — authoritative source of truth for all PreDCR layer definitions.
No MCP or CAD backend imports. Pure data module.
"""
from pydantic import BaseModel, ConfigDict, Field


class LayerSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str                          # e.g. "PREDCR-WALL-EXT"
    color_index: int = Field(ge=1, le=256)  # AutoCAD color index (ACI)
    linetype: str                      # e.g. "Continuous", "DASHED"
    required_for: list[str]            # building type keys, lowercase
    entity_types: list[str]            # expected entity type suffixes on this layer


PREDCR_LAYERS: list[LayerSpec] = [
    LayerSpec(
        name="PREDCR-WALL-EXT",
        color_index=7,
        linetype="Continuous",
        required_for=["residential", "commercial", "industrial"],
        entity_types=["WALL"],
    ),
    # ... remaining 39+ layers
]


def get_layers_for_building_type(building_type: str) -> list[LayerSpec]:
    bt = building_type.lower()
    result = [s for s in PREDCR_LAYERS if bt in s.required_for]
    if not result:
        raise ValueError(f"Unknown building type: {building_type!r}. "
                         f"Known types: {get_all_building_types()}")
    return result


def get_layer_by_name(name: str) -> LayerSpec | None:
    name_upper = name.upper()
    return next((s for s in PREDCR_LAYERS if s.name.upper() == name_upper), None)


def get_all_building_types() -> list[str]:
    types: set[str] = set()
    for spec in PREDCR_LAYERS:
        types.update(spec.required_for)
    return sorted(types)
```

**Layer naming convention:** All PreDCR layer names follow the pattern `PREDCR-<CATEGORY>[-<QUALIFIER>]`. The `PREDCR-` prefix is what the Epic 3 Story 3-4 naming validator checks.

**Color index reference (AutoCAD ACI):**
- 1=Red, 2=Yellow, 3=Green, 4=Cyan, 5=Blue, 6=Magenta, 7=White/Black, 8=Dark grey

### Project Structure Notes

```
src/lcs_cad_mcp/modules/predcr/
├── __init__.py          # register(mcp) stub + re-exports from layer_registry
├── layer_registry.py    # THIS STORY — LayerSpec + PREDCR_LAYERS + helpers
├── tools.py             # stub (filled by 4-2, 4-3, 4-4, 4-5)
├── service.py           # stub PreDCRService (filled by 4-2+)
└── schemas.py           # stub (filled by 4-2+)

tests/unit/modules/predcr/
├── __init__.py
└── test_layer_registry.py   # THIS STORY
```

### Dependencies

- **Story 3-4** (PreDCR layer naming validation) — must be complete; the `PREDCR-` prefix convention validated by Story 3-4's `layer_validate_naming` must align with the `name` values in `PREDCR_LAYERS`.
- **Epic 2** (backends) — not a runtime dependency for this story (pure data), but downstream stories (4-2+) that consume this catalog require Epic 2 to be complete.
- **Pydantic v2** — `BaseModel`, `ConfigDict`, `Field` from `pydantic` (not `pydantic.v1`).

### References

- Epic 4 goal: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 4: PreDCR Engine]
- Story 4-1 requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 4-1]
- Architecture — PreDCR module structure: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Module Structure: predcr/"]
- Architecture — layer_registry.py as source of truth: [Source: Mandatory architecture context in task instructions]
- LayerSpec fields specification: [Source: Mandatory architecture context — `layer_registry.py: dict/list of LayerSpec (name, color_index, linetype, required, building_types, entity_types_expected)`]
- Story 3-4 naming convention: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 3-4]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/predcr/layer_registry.py`
- `src/lcs_cad_mcp/modules/predcr/__init__.py` (updated)
- `tests/unit/modules/predcr/__init__.py`
- `tests/unit/modules/predcr/test_layer_registry.py`
