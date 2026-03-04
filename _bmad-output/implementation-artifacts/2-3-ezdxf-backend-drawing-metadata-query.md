# Story 2.3: ezdxf Backend — Drawing Metadata Query

Status: ready-for-dev

## Story

As a **developer**,
I want **the ezdxf backend to return complete drawing metadata and support entity/layer queries**,
so that **AI clients can understand drawing state and layer structure before issuing any drawing commands** (FR4).

## Acceptance Criteria

1. **AC1:** `EzdxfBackend.get_drawing_metadata() -> DrawingMetadata` returns a fully populated `DrawingMetadata` object including: `file_path`, `dxf_version`, `units`, `extents_min` (minimum XY of all entities), `extents_max` (maximum XY of all entities), `entity_count`, and `layer_count` — for both empty and populated drawings.
2. **AC2:** `EzdxfBackend.list_layers() -> list[LayerInfo]` returns all layers in the current drawing as a list of `LayerInfo` Pydantic objects; an empty drawing returns a list with exactly one entry (`{"name": "0", ...}` — the default ezdxf layer).
3. **AC3:** `EzdxfBackend.get_layer(name: str) -> LayerInfo` returns the `LayerInfo` for the named layer; raises `MCPError(ErrorCode.LAYER_NOT_FOUND)` if the layer does not exist.
4. **AC4:** `EzdxfBackend.query_entities(layer: str | None, entity_type: str | None, bounds: tuple[float, float, float, float] | None) -> list[EntityInfo]` returns matching entities; all three filter params are optional; when all are `None` returns every entity in model space; `bounds` is `(min_x, min_y, max_x, max_y)` — returns entities whose insertion point or start point falls within the rectangle.
5. **AC5:** All four methods raise `MCPError(ErrorCode.DRAWING_OPEN_FAILED, recoverable=True)` if called when no drawing is open (`self._doc is None`).
6. **AC6:** Unit tests cover: metadata for empty drawing, metadata for populated drawing (with known extents), list_layers, get_layer found, get_layer not found, query_entities with no filter, with layer filter, with type filter, with bounds filter, and combined filters.

## Tasks / Subtasks

- [ ] Task 1: Implement `get_drawing_metadata` with full extents calculation (AC: 1, 5)
  - [ ] 1.1: Add a `_require_open_doc(self) -> None` private helper that raises `MCPError(DRAWING_OPEN_FAILED, recoverable=True)` if `self._doc is None` — call this at the top of every method that needs an open document
  - [ ] 1.2: Implement extents calculation: iterate over all entities in `self._doc.modelspace()` using `ezdxf.bbox.extents(msp)` from `ezdxf.bbox` module; handle the `ezdxf.bbox.BoundingBox.is_empty` case for drawings with no entities (return `extents_min=(0.0, 0.0), extents_max=(0.0, 0.0)`)
  - [ ] 1.3: Populate all `DrawingMetadata` fields: `file_path=self._current_path`, `dxf_version=self._doc.dxfversion`, `units` from `$INSUNITS` header, `entity_count=len(list(msp))`, `layer_count=len(list(self._doc.layers))`
  - [ ] 1.4: Return the completed `DrawingMetadata` model

- [ ] Task 2: Implement `list_layers` (AC: 2, 5)
  - [ ] 2.1: Call `self._require_open_doc()`
  - [ ] 2.2: Iterate over `self._doc.layers` table; for each layer entry extract: `name`, `color` (`layer.dxf.color`), `linetype` (`layer.dxf.linetype`), `lineweight` (`layer.dxf.lineweight / 100.0` — ezdxf stores lineweight in hundredths of mm)
  - [ ] 2.3: Extract layer state flags: `is_on = layer.is_on()`, `is_frozen = layer.is_frozen()`, `is_locked = layer.is_locked()`
  - [ ] 2.4: Construct a `LayerInfo` for each layer and return the list
  - [ ] 2.5: Add defensive handling: if a layer attribute is missing (rare in malformed DXF), use the default value from the `LayerInfo` model

- [ ] Task 3: Implement `get_layer` (AC: 3, 5)
  - [ ] 3.1: Call `self._require_open_doc()`
  - [ ] 3.2: Perform case-insensitive layer name lookup: `name.upper()` comparison against all layers in `self._doc.layers` (AutoCAD convention — layer names are case-insensitive)
  - [ ] 3.3: If no match found, raise `MCPError(ErrorCode.LAYER_NOT_FOUND, message=f"Layer '{name}' not found", recoverable=True)`
  - [ ] 3.4: Return the matching `LayerInfo` built using the same attribute extraction as in `list_layers`

- [ ] Task 4: Implement `query_entities` with three filter types (AC: 4, 5)
  - [ ] 4.1: Call `self._require_open_doc()`
  - [ ] 4.2: Build base query: `entities = list(self._doc.modelspace())` — start with all model-space entities
  - [ ] 4.3: Apply layer filter: if `layer is not None`, filter to `e.dxf.layer.upper() == layer.upper()` (case-insensitive)
  - [ ] 4.4: Apply entity type filter: if `entity_type is not None`, filter to `e.dxftype() == entity_type.upper()` (e.g. `"LINE"`, `"LWPOLYLINE"`, `"CIRCLE"`, `"ARC"`, `"TEXT"`, `"INSERT"`)
  - [ ] 4.5: Apply bounds filter: if `bounds is not None` (min_x, min_y, max_x, max_y), extract each entity's representative point (use `e.dxf.start` for LINE, `e.dxf.center` for CIRCLE/ARC, `e.dxf.insert` for INSERT/TEXT, first vertex for LWPOLYLINE); keep entity if its point falls within `[min_x, max_x] x [min_y, max_y]`
  - [ ] 4.6: Convert each surviving entity to `EntityInfo`: `handle=e.dxf.handle`, `entity_type=e.dxftype()`, `layer=e.dxf.layer`, `geometry=_extract_geometry(e)` where `_extract_geometry` is a private method that returns a type-specific dict
  - [ ] 4.7: Implement `_extract_geometry(entity) -> dict` private method: returns `{"start": [...], "end": [...]}` for LINE; `{"center": [...], "radius": ...}` for CIRCLE; `{"center": [...], "radius": ..., "start_angle": ..., "end_angle": ...}` for ARC; `{"points": [...], "closed": ...}` for LWPOLYLINE; `{"insert": [...], "text": ...}` for TEXT/MTEXT; `{"insert": [...], "name": ...}` for INSERT; `{}` for unknown types

- [ ] Task 5: Write unit tests in `tests/unit/backends/test_ezdxf_metadata.py` (AC: 6)
  - [ ] 5.1: Create `tests/unit/backends/test_ezdxf_metadata.py`
  - [ ] 5.2: Test `get_drawing_metadata` on a new empty drawing: verify `entity_count=0`, `layer_count=1`, `extents_min=(0.0, 0.0)`, `extents_max=(0.0, 0.0)`
  - [ ] 5.3: Test `get_drawing_metadata` on a drawing with a known LINE entity: verify extents reflect the line's start/end coordinates
  - [ ] 5.4: Test `list_layers` on empty drawing returns exactly one layer named `"0"`
  - [ ] 5.5: Test `list_layers` after creating two additional layers returns three layers; verify all `LayerInfo` fields are populated
  - [ ] 5.6: Test `get_layer("0")` returns the default layer with correct defaults
  - [ ] 5.7: Test `get_layer("nonexistent")` raises `MCPError` with code `LAYER_NOT_FOUND`
  - [ ] 5.8: Test `get_layer` is case-insensitive: `get_layer("layer1")` finds layer named `"LAYER1"`
  - [ ] 5.9: Test `query_entities()` with no filters returns all entities
  - [ ] 5.10: Test `query_entities(layer="walls")` returns only entities on layer "walls"
  - [ ] 5.11: Test `query_entities(entity_type="LINE")` returns only LINE entities
  - [ ] 5.12: Test `query_entities(bounds=(0, 0, 100, 100))` returns only entities whose point falls within the rectangle
  - [ ] 5.13: Test all four methods raise `MCPError(DRAWING_OPEN_FAILED)` when `self._doc is None`

- [ ] Task 6: Integration verification — expose metadata via MCP tool (AC: 1)
  - [ ] 6.1: Verify `modules/cad/tools.py` has a placeholder for `cad_get_metadata` tool (this tool is implemented in Story 2-3 as it depends on `get_drawing_metadata`); if stub exists, confirm it will call `CadService.get_metadata()` which calls `backend.get_drawing_metadata()`
  - [ ] 6.2: Run `pytest tests/unit/backends/ -v` — all tests pass
  - [ ] 6.3: Run `ruff check src/lcs_cad_mcp/backends/ezdxf_backend.py` — zero errors

## Dev Notes

### Critical Architecture Constraints

1. **`ezdxf.bbox` is the correct extents API** — Do NOT manually iterate entities to compute extents. Use `ezdxf.bbox.extents(msp, fast=True)` from the `ezdxf.bbox` module. Check `bbox.is_empty` before accessing `.extmin` and `.extmax`.
2. **Case-insensitive layer names** — AutoCAD, ZWCAD, and BricsCAD all treat layer names as case-insensitive. All layer lookups must normalise to uppercase. Store `LayerInfo.name` as returned by ezdxf (preserving original case), but compare with `.upper()`.
3. **`geometry` dict is loosely typed** — The `EntityInfo.geometry: dict` field is intentionally untyped. Downstream modules (entities module, verification module) know what geometry keys to expect per entity type. Do NOT add a separate Pydantic model per entity type in this story — that belongs in the entities module (Epic 5).
4. **Bounds filter uses insertion/start point only** — For this story, bounds filtering uses a single representative point per entity. Full bounding-box overlap testing (e.g. for lines that span the filter region) is NOT required here and belongs in the area module (Epic 7). Clearly document this limitation in the method docstring.
5. **FORBIDDEN:** Do not import anything from `modules/` in `backends/`. Backends are the lowest layer — they know nothing about MCP modules, PreDCR rules, or business logic.

### Module/Component Notes

**Extensions to `EzdxfBackend` in `backends/ezdxf_backend.py`:**

```python
import ezdxf.bbox  # for extents calculation

def _require_open_doc(self) -> None:
    if self._doc is None:
        raise MCPError(code=ErrorCode.DRAWING_OPEN_FAILED,
                       message="No drawing is currently open", recoverable=True)

def get_drawing_metadata(self) -> DrawingMetadata:
    self._require_open_doc()
    msp = self._doc.modelspace()
    bbox = ezdxf.bbox.extents(msp, fast=True)
    if bbox.is_empty:
        extents_min = (0.0, 0.0)
        extents_max = (0.0, 0.0)
    else:
        extents_min = (bbox.extmin.x, bbox.extmin.y)
        extents_max = (bbox.extmax.x, bbox.extmax.y)
    return DrawingMetadata(
        file_path=self._current_path,
        dxf_version=self._doc.dxfversion,
        units="metric" if self._doc.header.get("$INSUNITS", 4) == 4 else "imperial",
        extents_min=extents_min,
        extents_max=extents_max,
        entity_count=len(list(msp)),
        layer_count=len(list(self._doc.layers)),
    )

def list_layers(self) -> list[LayerInfo]:
    self._require_open_doc()
    result = []
    for layer in self._doc.layers:
        result.append(LayerInfo(
            name=layer.dxf.name,
            color=abs(layer.dxf.color),  # negative color = layer off in some DXF versions
            linetype=getattr(layer.dxf, "linetype", "Continuous"),
            lineweight=getattr(layer.dxf, "lineweight", 25) / 100.0,
            is_on=layer.is_on(),
            is_frozen=layer.is_frozen(),
            is_locked=layer.is_locked(),
        ))
    return result

def get_layer(self, name: str) -> LayerInfo:
    self._require_open_doc()
    for layer_info in self.list_layers():
        if layer_info.name.upper() == name.upper():
            return layer_info
    raise MCPError(code=ErrorCode.LAYER_NOT_FOUND,
                   message=f"Layer '{name}' not found", recoverable=True)
```

**`_extract_geometry` private helper:**
```python
def _extract_geometry(self, entity) -> dict:
    etype = entity.dxftype()
    if etype == "LINE":
        return {"start": list(entity.dxf.start[:2]), "end": list(entity.dxf.end[:2])}
    elif etype in ("CIRCLE", "ARC"):
        g = {"center": list(entity.dxf.center[:2]), "radius": entity.dxf.radius}
        if etype == "ARC":
            g["start_angle"] = entity.dxf.start_angle
            g["end_angle"] = entity.dxf.end_angle
        return g
    elif etype == "LWPOLYLINE":
        return {"points": [list(p[:2]) for p in entity.get_points()],
                "closed": entity.is_closed}
    elif etype in ("TEXT", "MTEXT"):
        return {"insert": list(entity.dxf.insert[:2]),
                "text": getattr(entity.dxf, "text", "")}
    elif etype == "INSERT":
        return {"insert": list(entity.dxf.insert[:2]), "name": entity.dxf.name}
    return {}
```

### Project Structure Notes

```
src/lcs_cad_mcp/
└── backends/
    └── ezdxf_backend.py   # Extended in this story (methods added to existing class)
tests/
└── unit/
    └── backends/
        └── test_ezdxf_metadata.py   # NEW — metadata + query tests
```

This story adds methods to the `EzdxfBackend` class created in Story 2-2. It does NOT create new files in the `backends/` directory.

### Dependencies

- **Story 2-1** (CADBackend Protocol): `DrawingMetadata`, `LayerInfo`, `EntityInfo` models must exist; `CADBackend` Protocol defines `get_drawing_metadata`, `list_layers`, `get_layer`, `query_entities` signatures.
- **Story 2-2** (ezdxf lifecycle): `EzdxfBackend` class with `self._doc`, `self._current_path`, and `_require_open_doc` helper must exist; `open_drawing` and `new_drawing` are needed for the test fixtures to create open drawings.

### References

- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 2, Story 2-3]
- ezdxf bbox API: https://ezdxf.readthedocs.io/en/stable/math/bbox.html
- ezdxf layer table: https://ezdxf.readthedocs.io/en/stable/tables/layer_table_entry.html
- ezdxf entity query: https://ezdxf.readthedocs.io/en/stable/query.html
- FR4 metadata requirement: [Source: `_bmad-output/planning-artifacts/architecture.md`]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/backends/ezdxf_backend.py` (extended with new methods)
- `tests/unit/backends/test_ezdxf_metadata.py`
