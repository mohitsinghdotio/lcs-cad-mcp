# Story 5.6: `entity_query` MCP Tool

Status: ready-for-dev

## Story

As an **AI client**,
I want **to query drawing entities filtered by layer name, entity type, and/or spatial bounding box**,
so that **I can identify and target specific entities for subsequent modification, area computation, or verification without knowing entity handles in advance, fulfilling FR12**.

## Acceptance Criteria

1. **AC1:** `entity_query(layer: str | None = None, entity_type: str | None = None, bbox: dict | None = None)` MCP tool returns a list of `EntityRecord` objects matching all provided filters; all filters are optional and combinable
2. **AC2:** When `bbox` is provided as `{"min_x": float, "min_y": float, "max_x": float, "max_y": float}`, the query returns only entities whose bounding box INTERSECTS with the given bbox (not necessarily fully contained)
3. **AC3:** Returns `{"success": true, "data": {"entities": [...], "count": N}}` — `entities` is a JSON-serializable list of entity records with at minimum: `entity_id`, `entity_type`, `layer`, `bounding_box`
4. **AC4:** Returns `{"success": true, "data": {"entities": [], "count": 0}}` when no entities match — this is NOT an error condition
5. **AC5:** `entity_type` filter accepts the string values of the `EntityType` enum: `"POLYLINE"`, `"LINE"`, `"ARC"`, `"CIRCLE"`, `"TEXT"`, `"MTEXT"`, `"INSERT"`; unknown entity_type value returns `INVALID_PARAMS` error
6. **AC6:** This tool is read-only — no snapshot is taken and no drawing modifications occur
7. **AC7:** Works on both `EzdxfBackend` and `COMBackend`
8. **AC8:** Query completes within 2 seconds on drawings with up to 10,000 entities (NFR1)

## Tasks / Subtasks

- [ ] Task 1: Implement `EntityService.query_entities` in `service.py` (AC: 1, 2, 4, 6, 7)
  - [ ] 1.1: Replace `query_entities` stub with real implementation accepting `layer: str | None`, `entity_type: EntityType | None`, `bbox: BoundingBox | None`
  - [ ] 1.2: Call `self._backend.list_entities(layer=layer, entity_type=entity_type)` to retrieve a list of raw entity records matching the layer and type filters; backend returns `list[EntityRecord]`
  - [ ] 1.3: If `bbox` is provided, filter the backend-returned list in Python using `entity.bounding_box.intersects(bbox)` for each entity that has a non-None bounding_box; entities with `bounding_box=None` are excluded from bbox-filtered results
  - [ ] 1.4: Return the filtered `list[EntityRecord]`
  - [ ] 1.5: Handle the case where `layer=None` and `entity_type=None` and `bbox=None` — return ALL entities in the drawing (useful for inventorying the full drawing state)
  - [ ] 1.6: Add `_entity_type_from_dxftype(dxf_type: str) -> EntityType` helper mapping ezdxf DXF type strings to `EntityType` enum values: `"LWPOLYLINE"` → `POLYLINE`, `"POLYLINE"` → `POLYLINE`, `"LINE"` → `LINE`, `"ARC"` → `ARC`, `"CIRCLE"` → `CIRCLE`, `"TEXT"` → `TEXT`, `"MTEXT"` → `MTEXT`, `"INSERT"` → `INSERT`; unknown types are skipped (not raised as errors)

- [ ] Task 2: Implement `entity_query` MCP tool handler in `tools.py` (AC: 1–8)
  - [ ] 2.1: Add async `entity_query(ctx: Context, layer: str | None = None, entity_type: str | None = None, bbox: dict | None = None) -> dict`
  - [ ] 2.2: Step 1 — Session: `session = ctx.get_state("drawing_session")`; return `SESSION_NOT_STARTED` error if None
  - [ ] 2.3: Step 2 — Validate `entity_type` if provided: attempt `EntityType(entity_type.upper())`; if `ValueError`, return `INVALID_PARAMS` error listing valid values
  - [ ] 2.4: Step 2 — Validate `bbox` dict if provided: must have all four keys `min_x`, `min_y`, `max_x`, `max_y` as numeric values; validate `max_x > min_x` and `max_y > min_y`; return `INVALID_PARAMS` if malformed; construct `BoundingBox` from validated dict
  - [ ] 2.5: Step 3 — NO snapshot (read-only operation); add an inline comment `# Read-only query — no snapshot required`
  - [ ] 2.6: Step 4 — Call `EntityService(session).query_entities(layer=layer, entity_type=parsed_entity_type, bbox=parsed_bbox)`
  - [ ] 2.7: Step 5 — Event log: log the query parameters and result count (not the full entity list — avoid bloating the log)
  - [ ] 2.8: Step 6 — Return `{"success": True, "data": {"entities": [r.model_dump() for r in results], "count": len(results)}}`

- [ ] Task 3: Extend `CADBackend` Protocol with `list_entities` (AC: 7)
  - [ ] 3.1: Add `list_entities(layer: str | None, entity_type: str | None) -> list[EntityRecord]` to `CADBackend` Protocol in `backends/base.py`; backend performs layer and type filtering natively when possible
  - [ ] 3.2: Implement `EzdxfBackend.list_entities`: iterate over `msp` (model space entities); filter by `entity.dxf.layer == layer` if layer is not None; filter by DXF type if entity_type is not None using `_entity_type_from_dxftype(entity.dxftype())`; build and return `EntityRecord` list with bounding_box computed per entity type
  - [ ] 3.3: Add `EzdxfBackend._get_entity_bbox(entity) -> BoundingBox | None` private method that dispatches to entity-type-specific bbox computation (reuse helpers from Stories 5-2, 5-3, 5-4 via import from `service.py` or inline)
  - [ ] 3.4: Add `COMBackend.list_entities` stub raising `NotImplementedError("COM backend entity listing: Story 5-6")`

- [ ] Task 4: Register `entity_query` in `entities/__init__.py` (AC: 1)
  - [ ] 4.1: Update `register(mcp)` to call `_register_query_tool(mcp)` from `tools.py`
  - [ ] 4.2: Verify `entity_query` appears in MCP tool registry
  - [ ] 4.3: Confirm all previously registered entity tools remain functional

- [ ] Task 5: Write unit tests with `MockCADBackend` (AC: 1–8)
  - [ ] 5.1: Create `tests/unit/modules/entities/test_query_tool.py`
  - [ ] 5.2: Extend `MockCADBackend` with `list_entities` — populate `_entities` with a fixture set of 10 test entities across 3 layers and 4 entity types
  - [ ] 5.3: Test `entity_query` with no filters → returns all 10 entities
  - [ ] 5.4: Test `entity_query` with `layer="PLOT-BOUNDARY"` → returns only entities on that layer
  - [ ] 5.5: Test `entity_query` with `entity_type="POLYLINE"` → returns only polyline entities
  - [ ] 5.6: Test `entity_query` with both `layer` and `entity_type` filters combined → AND logic (both conditions must match)
  - [ ] 5.7: Test `entity_query` with a `bbox` filter: create entities at known positions; bbox covering only 3 of them → returns exactly those 3
  - [ ] 5.8: Test `entity_query` with all three filters combined → correct intersection of all three filter conditions
  - [ ] 5.9: Test `entity_query` with filters that match nothing → `{"entities": [], "count": 0}`, success=True
  - [ ] 5.10: Test `entity_query` with invalid `entity_type="UNKNOWN"` → `INVALID_PARAMS` error
  - [ ] 5.11: Test `entity_query` with malformed bbox (missing `max_y` key) → `INVALID_PARAMS` error
  - [ ] 5.12: Test `entity_query` with inverted bbox (`max_x < min_x`) → `INVALID_PARAMS` error
  - [ ] 5.13: Test that NO snapshot is taken during `entity_query` (verify `session.snapshot.take` is never called)

- [ ] Task 6: Performance validation (AC: 8)
  - [ ] 6.1: Add a performance-oriented test with `MockCADBackend` returning 10,000 mock entities; time the query loop in Python; assert < 500ms for the Python-layer filtering alone (the 2s budget accounts for backend I/O in real usage)
  - [ ] 6.2: Document in test comments: "Full 2s NFR1 budget includes ezdxf iteration over 10k entities; Python-layer bbox filtering must not add O(n^2) complexity"

## Dev Notes

### Critical Architecture Constraints

1. **Read-only operation — NO snapshot.** `entity_query` is a pure query tool. The 6-step pattern is adapted: Step 3 (layer check) is replaced by Step 3 (no snapshot, read-only note). Skipping the snapshot is intentional and correct for read-only tools.
2. **Filtering responsibility split:** The `CADBackend.list_entities()` method performs layer and entity_type filtering at the source (where it can be most efficient — e.g., ezdxf iteration naturally hits all entities). The `EntityService` performs the bbox intersection filter in Python after receiving the backend list. This split avoids encoding spatial geometry logic in the backend interface.
3. **BoundingBox intersects, not contains.** AC2 explicitly requires intersection (overlap), not containment. An entity whose bounding box partially overlaps the query bbox is returned. This is the standard CAD selection behavior (crossing selection).
4. **Entities with `bounding_box=None` are excluded from bbox-filtered queries.** If an entity's bbox cannot be computed (e.g., complex INSERT blocks), it is not returned in bbox-filtered results. It IS returned in layer-only or type-only queries.
5. **Empty result is success.** A query returning zero entities is `{"success": True, "data": {"entities": [], "count": 0}}` — never an error. This is critical for AI agents that may query a layer before drawing on it to confirm it is empty.
6. **EntityService is the only caller of `session.backend.list_entities()`** — tool handler delegates, never calls backend directly.

### Module/Component Notes

**Tool parameter definitions for MCP clients:**

`entity_query`:
- `layer: str | None = None` — filter by exact layer name; `None` means all layers
- `entity_type: str | None = None` — filter by entity type string (case-insensitive); valid: `"POLYLINE"`, `"LINE"`, `"ARC"`, `"CIRCLE"`, `"TEXT"`, `"MTEXT"`, `"INSERT"`; `None` means all types
- `bbox: dict | None = None` — spatial filter as `{"min_x": float, "min_y": float, "max_x": float, "max_y": float}`; `None` means no spatial filter

**Response schema:**
```python
{
    "success": True,
    "data": {
        "count": 3,
        "entities": [
            {
                "entity_id": "1F3A",
                "entity_type": "POLYLINE",
                "layer": "PLOT-BOUNDARY",
                "bounding_box": {"min_x": 0.0, "min_y": 0.0, "max_x": 100.0, "max_y": 80.0},
                "properties": {}
            },
            {
                "entity_id": "2B7C",
                "entity_type": "LINE",
                "layer": "SETBACK-FRONT",
                "bounding_box": {"min_x": 5.0, "min_y": 5.0, "max_x": 95.0, "max_y": 5.0},
                "properties": {}
            }
        ]
    }
}
```

**EzdxfBackend.list_entities implementation sketch:**
```python
def list_entities(self, layer: str | None, entity_type: str | None) -> list[EntityRecord]:
    results = []
    for entity in self._doc.modelspace():
        # Filter by layer
        if layer is not None and entity.dxf.layer != layer:
            continue
        # Filter by entity type
        etype = self._entity_type_from_dxftype(entity.dxftype())
        if etype is None:
            continue  # skip unknown/unsupported types
        if entity_type is not None and etype.value != entity_type.upper():
            continue
        # Build EntityRecord
        bbox = self._get_entity_bbox(entity)
        record = EntityRecord(
            entity_id=entity.dxf.handle,
            entity_type=etype,
            layer=entity.dxf.layer,
            bounding_box=bbox,
        )
        results.append(record)
    return results
```

**DXF type → EntityType mapping:**
| DXF type string | EntityType |
|---|---|
| `LWPOLYLINE` | `POLYLINE` |
| `POLYLINE` | `POLYLINE` |
| `LINE` | `LINE` |
| `ARC` | `ARC` |
| `CIRCLE` | `CIRCLE` |
| `TEXT` | `TEXT` |
| `MTEXT` | `MTEXT` |
| `INSERT` | `INSERT` |
| All others | skip (return None) |

### Project Structure Notes

Files modified by this story:
```
src/lcs_cad_mcp/
├── backends/
│   ├── base.py              # list_entities to Protocol
│   ├── ezdxf_backend.py     # implement list_entities, _get_entity_bbox, _entity_type_from_dxftype
│   └── com_backend.py       # stub list_entities
└── modules/entities/
    ├── __init__.py           # register() includes query tool
    ├── service.py            # query_entities implemented; _entity_type_from_dxftype helper
    └── tools.py              # entity_query handler

tests/unit/modules/entities/
└── test_query_tool.py        # new
```

### Dependencies

- **Story 5-1 (Entity Data Models):** `EntityRecord`, `EntityType`, `BoundingBox.intersects()`, `EntityService` skeleton — all required
- **Story 5-2 (draw_polyline / draw_line):** `layer_exists()`, session integration; query tool builds on the same module infrastructure
- **Epic 6 (Verification Engine):** Stories 6-1 through 6-4 depend on `entity_query` to list entities for verification. This story must be complete before any Epic 6 story can start.

### References

- FR12 (entity query): [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Functional Requirements"]
- Entity query filter spec: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Entity Module — Query"]
- Read-only tool pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 5, Story 5-6]

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
- `tests/unit/modules/entities/test_query_tool.py`
