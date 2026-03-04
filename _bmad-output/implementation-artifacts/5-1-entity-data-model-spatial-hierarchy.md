# Story 5.1: Entity Data Model and Spatial Hierarchy

Status: ready-for-dev

## Story

As a **developer**,
I want **typed Pydantic v2 data models for all entity types and their spatial containment relationships**,
so that **containment checking, area computation, and drawing scrutiny work on a well-structured, type-safe entity graph**.

## Acceptance Criteria

1. **AC1:** `EntityRecord` base Pydantic v2 model exists in `src/lcs_cad_mcp/modules/entities/schemas.py` with fields: `entity_id: str`, `entity_type: EntityType`, `layer: str`, `bounding_box: BoundingBox | None`, `properties: dict[str, Any]`
2. **AC2:** `EntityType` enum covers all supported CAD entity types: `POLYLINE`, `LINE`, `ARC`, `CIRCLE`, `TEXT`, `MTEXT`, `INSERT`
3. **AC3:** Concrete subtype schemas exist: `PolylineEntityRecord` (vertices: list[tuple[float, float]], closed: bool), `LineEntityRecord` (start, end: tuple[float, float]), `ArcEntityRecord` (center, radius, start_angle, end_angle), `CircleEntityRecord` (center, radius), `TextEntityRecord` (position, text_content, height, style), `BlockRefEntityRecord` (block_name, position, scale, rotation)
4. **AC4:** `BoundingBox` model with `min_x, min_y, max_x, max_y: float` and `contains(other: BoundingBox) -> bool` and `intersects(other: BoundingBox) -> bool` methods
5. **AC5:** `SpatialHierarchy` model encodes parent-child containment: `parent_entity_id: str | None`, `child_entity_ids: list[str]`; represents the hierarchy: plot_boundary > building_footprint > floor_plates > rooms/spaces
6. **AC6:** `EntityService` skeleton class in `src/lcs_cad_mcp/modules/entities/service.py` with `__init__(self, session: DrawingSession)` — accesses drawing entities exclusively via `session.backend`, never importing ezdxf directly
7. **AC7:** `src/lcs_cad_mcp/modules/entities/__init__.py` exports a `register(mcp)` function stub that will wire tools to the MCP instance (no tools registered yet in this story)
8. **AC8:** Unit tests in `tests/unit/modules/entities/test_schemas.py` validate model construction, field validation, and BoundingBox geometry methods

## Tasks / Subtasks

- [ ] Task 1: Define `EntityType` enum and `BoundingBox` model in `schemas.py` (AC: 1, 2, 4)
  - [ ] 1.1: Create `EntityType(str, Enum)` with values: `POLYLINE = "POLYLINE"`, `LINE = "LINE"`, `ARC = "ARC"`, `CIRCLE = "CIRCLE"`, `TEXT = "TEXT"`, `MTEXT = "MTEXT"`, `INSERT = "INSERT"`
  - [ ] 1.2: Create `BoundingBox(BaseModel)` with `min_x, min_y, max_x, max_y: float`
  - [ ] 1.3: Add `contains(self, other: "BoundingBox") -> bool` — returns True if `other` lies fully within `self`
  - [ ] 1.4: Add `intersects(self, other: "BoundingBox") -> bool` — returns True if bounding boxes overlap
  - [ ] 1.5: Add `model_config = ConfigDict(frozen=True)` to `BoundingBox` so it is hashable/immutable

- [ ] Task 2: Define `EntityRecord` base model and all concrete subtypes (AC: 1, 2, 3)
  - [ ] 2.1: Create `EntityRecord(BaseModel)` with: `entity_id: str`, `entity_type: EntityType`, `layer: str`, `bounding_box: BoundingBox | None = None`, `properties: dict[str, Any] = Field(default_factory=dict)`
  - [ ] 2.2: Create `PolylineEntityRecord(EntityRecord)` with: `entity_type: Literal[EntityType.POLYLINE]`, `vertices: list[tuple[float, float]]`, `closed: bool = False`; add validator ensuring `len(vertices) >= 2`
  - [ ] 2.3: Create `LineEntityRecord(EntityRecord)` with: `entity_type: Literal[EntityType.LINE]`, `start: tuple[float, float]`, `end: tuple[float, float]`
  - [ ] 2.4: Create `ArcEntityRecord(EntityRecord)` with: `entity_type: Literal[EntityType.ARC]`, `center: tuple[float, float]`, `radius: float`, `start_angle: float`, `end_angle: float`; add validator `radius > 0`
  - [ ] 2.5: Create `CircleEntityRecord(EntityRecord)` with: `entity_type: Literal[EntityType.CIRCLE]`, `center: tuple[float, float]`, `radius: float`; add validator `radius > 0`
  - [ ] 2.6: Create `TextEntityRecord(EntityRecord)` with: `entity_type: Literal[EntityType.TEXT | EntityType.MTEXT]`, `position: tuple[float, float]`, `text_content: str`, `height: float = 2.5`, `style: str = "Standard"`
  - [ ] 2.7: Create `BlockRefEntityRecord(EntityRecord)` with: `entity_type: Literal[EntityType.INSERT]`, `block_name: str`, `position: tuple[float, float]`, `scale: float = 1.0`, `rotation: float = 0.0`
  - [ ] 2.8: Create `AnyEntityRecord` discriminated union type alias using `Annotated[Union[...], Field(discriminator="entity_type")]`

- [ ] Task 3: Define `SpatialHierarchy` model (AC: 5)
  - [ ] 3.1: Create `SpatialHierarchyNode(BaseModel)` with: `entity_id: str`, `entity_type: EntityType`, `layer: str`, `parent_entity_id: str | None = None`, `child_entity_ids: list[str] = Field(default_factory=list)`
  - [ ] 3.2: Create `SpatialHierarchy(BaseModel)` with: `nodes: dict[str, SpatialHierarchyNode] = Field(default_factory=dict)` mapping `entity_id` to node
  - [ ] 3.3: Add `add_node(node: SpatialHierarchyNode) -> None` method to `SpatialHierarchy`
  - [ ] 3.4: Add `get_children(entity_id: str) -> list[SpatialHierarchyNode]` method
  - [ ] 3.5: Add `get_ancestors(entity_id: str) -> list[SpatialHierarchyNode]` method walking parent chain
  - [ ] 3.6: Add docstring documenting the intended hierarchy: `plot_boundary > building_footprint > floor_plates > rooms/spaces`

- [ ] Task 4: Create `EntityService` skeleton in `service.py` (AC: 6)
  - [ ] 4.1: Import `DrawingSession` from `session.context` (type annotation only — use `TYPE_CHECKING` guard if needed to avoid circular import)
  - [ ] 4.2: Define `class EntityService` with `__init__(self, session: "DrawingSession")` storing `self._session = session`
  - [ ] 4.3: Add property `self._backend` returning `self._session.backend` — this is the ONLY permitted access path to CAD entities; add inline comment `# Never import ezdxf directly in this module`
  - [ ] 4.4: Add stub method stubs (all raising `NotImplementedError`): `draw_polyline`, `draw_line`, `draw_arc`, `draw_circle`, `draw_text`, `insert_block`, `move_entity`, `copy_entity`, `delete_entity`, `change_layer`, `query_entities`, `close_polyline`
  - [ ] 4.5: Add docstring to class: `"""Entity operations always access drawing data via session.backend. Direct ezdxf imports are prohibited in this module."""`

- [ ] Task 5: Wire up `__init__.py` register stub and update exports (AC: 7)
  - [ ] 5.1: In `src/lcs_cad_mcp/modules/entities/__init__.py` define `def register(mcp) -> None:` with body `pass  # MCP tool registration wired in Story 5-2 through 5-7`
  - [ ] 5.2: Export `EntityRecord`, `EntityType`, `BoundingBox`, `SpatialHierarchy`, `EntityService` from `__init__.py`
  - [ ] 5.3: Ensure `src/lcs_cad_mcp/modules/__init__.py` imports and re-exports `entities.register` so `__main__.py` can call it uniformly

- [ ] Task 6: Write unit tests for schemas and BoundingBox (AC: 8)
  - [ ] 6.1: Create `tests/unit/modules/entities/__init__.py` (empty)
  - [ ] 6.2: Create `tests/unit/modules/entities/test_schemas.py`
  - [ ] 6.3: Test `EntityType` — all 7 values present and correct string values
  - [ ] 6.4: Test `BoundingBox.contains()` — inner box fully inside outer (True), partial overlap (False), identical boxes (True)
  - [ ] 6.5: Test `BoundingBox.intersects()` — overlapping (True), adjacent edge (True), completely separate (False)
  - [ ] 6.6: Test `PolylineEntityRecord` — valid construction with 3 vertices; validator rejects 1 vertex
  - [ ] 6.7: Test `ArcEntityRecord` / `CircleEntityRecord` — validator rejects `radius <= 0`
  - [ ] 6.8: Test `SpatialHierarchy.get_children()` and `get_ancestors()` with a 3-level hierarchy fixture

## Dev Notes

### Critical Architecture Constraints

1. **EntityService MUST NOT import ezdxf directly.** All entity data access goes via `session.backend`. This is enforced by the architecture so that the same `EntityService` works identically against both `EzdxfBackend` and `COMBackend`. Any direct `import ezdxf` in `modules/entities/` is an anti-pattern that will break COM backend support.
2. **Pydantic v2 only.** Use `model_config = ConfigDict(...)`, `Field(...)`, `@field_validator`, `@model_validator` — never Pydantic v1 `@validator` or `class Config`. The project mandates `pydantic>=2.0`.
3. **Discriminated unions.** The `AnyEntityRecord` union must use Pydantic v2's discriminated union syntax (`Field(discriminator="entity_type")`) so that the MCP response serializer can deserialize the correct subtype from JSON without ambiguity.
4. **No MCP tools registered in this story.** Story 5-1 is pure data models + service skeleton. The `register(mcp)` function remains a stub (`pass`). MCP tool registration begins in Story 5-2.

### Module/Component Notes

**`schemas.py` structure:**
```python
from enum import Enum
from typing import Annotated, Any, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator

class EntityType(str, Enum):
    POLYLINE = "POLYLINE"
    LINE = "LINE"
    ARC = "ARC"
    CIRCLE = "CIRCLE"
    TEXT = "TEXT"
    MTEXT = "MTEXT"
    INSERT = "INSERT"

class BoundingBox(BaseModel):
    model_config = ConfigDict(frozen=True)
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def contains(self, other: "BoundingBox") -> bool:
        return (self.min_x <= other.min_x and self.min_y <= other.min_y
                and self.max_x >= other.max_x and self.max_y >= other.max_y)

    def intersects(self, other: "BoundingBox") -> bool:
        return not (other.max_x < self.min_x or other.min_x > self.max_x
                    or other.max_y < self.min_y or other.min_y > self.max_y)

class EntityRecord(BaseModel):
    entity_id: str
    entity_type: EntityType
    layer: str
    bounding_box: BoundingBox | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
```

**Spatial hierarchy levels (per PreDCR conventions):**
- Level 0 — Plot boundary (single closed polyline on `PLOT-BOUNDARY` layer)
- Level 1 — Building footprint (closed polyline on `BLDG-FOOTPRINT` layer, contained within plot)
- Level 2 — Floor plates (closed polylines per floor on `FLOOR-{n}` layers)
- Level 3 — Rooms/spaces (closed polylines on `ROOM-*` layers, contained within their floor plate)

**`entity_id` convention:** The string value of the ezdxf DXF handle (e.g., `"1F3A"`) or a UUID string for entities created via COM backend. Entity IDs are opaque to consumers — they exist purely for referencing entities across tool calls.

### Project Structure Notes

Files created/modified by this story:
```
src/lcs_cad_mcp/modules/entities/
├── __init__.py        # register(mcp) stub + exports
├── schemas.py         # EntityType, BoundingBox, EntityRecord subtypes, SpatialHierarchy
├── service.py         # EntityService skeleton
└── tools.py           # untouched (stubs from Story 1-1 remain)

tests/unit/modules/entities/
├── __init__.py        # new (empty)
└── test_schemas.py    # new — schema unit tests
```

### Dependencies

- **Epic 2 (CADBackend Protocol, Story 2-1):** `EntityService.__init__` accepts a `DrawingSession`; the `session.backend` protocol must be defined. This story uses a type annotation only — `MockCADBackend` in tests substitutes for the real backend.
- **Epic 3 (Layer Management, Story 3-1):** The `layer` field on `EntityRecord` holds a layer name string. Layer existence validation happens in the tool handlers (Stories 5-2+), not in the data model. No direct import of layer module needed here.
- **Story 1-1 (Project Scaffold):** The `entities/` module directory stub already exists; this story fills it with real content.

### References

- Entity data model: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Entity Module"]
- Spatial hierarchy levels: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Spatial Hierarchy"]
- EntityService backend access constraint: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Anti-patterns / Enforcement Guidelines"]
- MCP tool naming: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Naming Patterns"]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 5, Story 5-1]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/entities/__init__.py`
- `src/lcs_cad_mcp/modules/entities/schemas.py`
- `src/lcs_cad_mcp/modules/entities/service.py`
- `tests/unit/modules/entities/__init__.py`
- `tests/unit/modules/entities/test_schemas.py`
