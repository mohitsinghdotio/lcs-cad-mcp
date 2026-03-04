# Story 3.1: Layer Data Model and Registry

Status: ready-for-dev

## Story

As a **developer**,
I want **a typed Pydantic data model for layers and a runtime LayerRegistry backed by the CAD backend**,
so that **all layer operations work against a consistent, validated, case-insensitive data structure that mirrors the active drawing's state**.

## Acceptance Criteria

1. **AC1:** `LayerRecord` Pydantic v2 model defined in `src/lcs_cad_mcp/modules/layers/schemas.py` with fields: `name` (str), `color` (int), `linetype` (str), `lineweight` (float), `is_on` (bool), `is_frozen` (bool), `is_locked` (bool). All fields have sensible defaults (color=7/white, linetype="CONTINUOUS", lineweight=0.25, is_on=True, is_frozen=False, is_locked=False).
2. **AC2:** `LayerRegistry` class defined in `src/lcs_cad_mcp/modules/layers/service.py` (or a dedicated `registry.py`) that: holds all `LayerRecord` instances for the current drawing in a dict keyed by normalized (lowercased) name; exposes `sync_from_backend(backend: CADBackend)` to populate from the active drawing; exposes `get(name)`, `all()`, `contains(name)`, `add(record)`, `remove(name)` operations.
3. **AC3:** `LayerRegistry.sync_from_backend()` queries `session.backend` (via `CADBackend` Protocol) to retrieve all layers and populates the registry — never calls `ezdxf` directly.
4. **AC4:** Layer names are stored and compared case-insensitively. `registry.get("PLOT_BOUNDARY")` and `registry.get("plot_boundary")` both retrieve the same record.
5. **AC5:** Unit tests in `tests/unit/modules/layers/test_schemas.py` and `tests/unit/modules/layers/test_registry.py` cover: model construction with defaults, field validation errors (e.g. invalid color), registry CRUD, `sync_from_backend` with `MockCADBackend`, and case-insensitive lookup.

## Tasks / Subtasks

- [ ] Task 1: Define `LayerRecord` Pydantic model in `schemas.py` (AC: 1)
  - [ ] 1.1: Create `src/lcs_cad_mcp/modules/layers/schemas.py` with `LayerRecord(BaseModel)` containing all required fields and defaults
  - [ ] 1.2: Add `model_config = ConfigDict(frozen=False, str_strip_whitespace=True)` to allow in-place property updates
  - [ ] 1.3: Add Pydantic validator `@field_validator("name")` that strips whitespace and raises `ValueError` for empty names
  - [ ] 1.4: Add `color` field with type `int`, range validator 1–256 (ACI color index per AutoCAD convention), default 7
  - [ ] 1.5: Add `linetype` field (str, default "CONTINUOUS"), `lineweight` field (float, default 0.25), `is_on` (bool, default True), `is_frozen` (bool, default False), `is_locked` (bool, default False)
  - [ ] 1.6: Add `to_dict() -> dict` helper for serialization in tool responses

- [ ] Task 2: Define `LayerRegistry` class (AC: 2, 3, 4)
  - [ ] 2.1: Create `src/lcs_cad_mcp/modules/layers/registry.py` with `LayerRegistry` class
  - [ ] 2.2: Internal storage: `_layers: dict[str, LayerRecord]` keyed by `name.lower()`
  - [ ] 2.3: Implement `sync_from_backend(backend: CADBackend) -> None`: calls `backend.list_layers()` (returns list of dicts or `LayerRecord`-compatible data), clears registry, and repopulates
  - [ ] 2.4: Implement `get(name: str) -> LayerRecord | None`: looks up by `name.lower()`
  - [ ] 2.5: Implement `all() -> list[LayerRecord]`: returns all records sorted by name
  - [ ] 2.6: Implement `contains(name: str) -> bool`: case-insensitive membership test
  - [ ] 2.7: Implement `add(record: LayerRecord) -> None`: inserts/replaces by `record.name.lower()`
  - [ ] 2.8: Implement `remove(name: str) -> None`: deletes by `name.lower()`; raises `KeyError` if not found
  - [ ] 2.9: Implement `count() -> int`: returns number of tracked layers
  - [ ] 2.10: Add `__repr__` for debug visibility

- [ ] Task 3: Wire `LayerRegistry` into `LayerService` (AC: 3)
  - [ ] 3.1: Update `src/lcs_cad_mcp/modules/layers/service.py` to import and instantiate `LayerRegistry`
  - [ ] 3.2: `LayerService.__init__(self, session: DrawingSession)` stores `self.session = session` and creates `self.registry = LayerRegistry()`
  - [ ] 3.3: Add `LayerService.ensure_synced() -> None` which calls `self.registry.sync_from_backend(self.session.backend)` — called lazily at the start of each service method
  - [ ] 3.4: Ensure `LayerService` never imports `ezdxf` directly — all backend calls go through `self.session.backend`

- [ ] Task 4: Update `layers/__init__.py` to register module (AC: 2)
  - [ ] 4.1: Update `src/lcs_cad_mcp/modules/layers/__init__.py` to expose a `register(mcp)` function stub (tools will be registered here in Stories 3-2 and 3-3)
  - [ ] 4.2: Import `LayerRecord` and `LayerRegistry` for package-level export

- [ ] Task 5: Write unit tests (AC: 5)
  - [ ] 5.1: Create `tests/unit/modules/layers/__init__.py` (empty)
  - [ ] 5.2: Create `tests/unit/modules/layers/test_schemas.py`:
    - [ ] 5.2.1: Test `LayerRecord` construction with all defaults
    - [ ] 5.2.2: Test `LayerRecord` with explicit values (name, color, linetype, lineweight)
    - [ ] 5.2.3: Test `field_validator` rejects empty name (raises `ValidationError`)
    - [ ] 5.2.4: Test color out-of-range (1–256) raises `ValidationError`
    - [ ] 5.2.5: Test `to_dict()` returns correct serialized form
  - [ ] 5.3: Create `tests/unit/modules/layers/test_registry.py`:
    - [ ] 5.3.1: Test empty registry returns `None` for `get()` and empty list for `all()`
    - [ ] 5.3.2: Test `add()` inserts and `contains()` returns True
    - [ ] 5.3.3: Test `get("UPPER")` and `get("upper")` return same record after `add()` with either casing
    - [ ] 5.3.4: Test `remove()` deletes entry; second `remove()` raises `KeyError`
    - [ ] 5.3.5: Test `sync_from_backend()` with `MockCADBackend` (from `conftest.py`) that returns 3 predefined layers — verify all 3 are in registry after sync
    - [ ] 5.3.6: Test `sync_from_backend()` clears stale data — add 5 records, sync with backend returning 2, registry has exactly 2

## Dev Notes

### Critical Architecture Constraints

1. **Never import `ezdxf` in `modules/layers/`** — all CAD access is exclusively via `session.backend` (a `CADBackend` Protocol instance). Violating this breaks the backend abstraction boundary. Add a comment `# CAD access: session.backend only — never import ezdxf` at the top of `service.py`.
2. **Pydantic v2 is required** — use `from pydantic import BaseModel, ConfigDict, field_validator`. Do NOT use Pydantic v1 validators (`@validator`) or `class Config`.
3. **CADBackend Protocol** (`backends/base.py`) must expose `list_layers() -> list[dict]` for `sync_from_backend()` to call. Verify this method exists (it is defined in Story 2-1/2-3); if it uses a different name, use that exact name.
4. **`LayerRegistry` is a plain Python class** — it is NOT a Pydantic model and NOT a singleton. A new instance is created per `LayerService` instantiation. This keeps state scoped to a single service call.
5. **Case-insensitive keying is non-negotiable** — AutoCAD layer names are case-insensitive. All dict keys must be `name.lower()` before storage and lookup.

### Module/Component Notes

**`schemas.py` — `LayerRecord`:**
```python
from pydantic import BaseModel, ConfigDict, field_validator

class LayerRecord(BaseModel):
    model_config = ConfigDict(frozen=False, str_strip_whitespace=True)

    name: str
    color: int = 7           # ACI color 7 = white/black (depends on background)
    linetype: str = "CONTINUOUS"
    lineweight: float = 0.25  # mm, default per AutoCAD convention
    is_on: bool = True
    is_frozen: bool = False
    is_locked: bool = False

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Layer name cannot be empty")
        return v.strip()

    @field_validator("color")
    @classmethod
    def color_in_range(cls, v: int) -> int:
        if not (1 <= v <= 256):
            raise ValueError(f"Color must be between 1 and 256 (ACI), got {v}")
        return v

    def to_dict(self) -> dict:
        return self.model_dump()
```

**`registry.py` — `LayerRegistry`:**
```python
from __future__ import annotations
from lcs_cad_mcp.modules.layers.schemas import LayerRecord
# CAD access: session.backend only — never import ezdxf

class LayerRegistry:
    def __init__(self) -> None:
        self._layers: dict[str, LayerRecord] = {}

    def sync_from_backend(self, backend) -> None:
        """Repopulate registry from the active drawing via backend."""
        raw_layers = backend.list_layers()  # returns list[dict]
        self._layers = {
            layer_data["name"].lower(): LayerRecord(**layer_data)
            for layer_data in raw_layers
        }

    def get(self, name: str) -> LayerRecord | None:
        return self._layers.get(name.lower())

    def all(self) -> list[LayerRecord]:
        return sorted(self._layers.values(), key=lambda r: r.name.lower())

    def contains(self, name: str) -> bool:
        return name.lower() in self._layers

    def add(self, record: LayerRecord) -> None:
        self._layers[record.name.lower()] = record

    def remove(self, name: str) -> None:
        key = name.lower()
        if key not in self._layers:
            raise KeyError(f"Layer '{name}' not found in registry")
        del self._layers[key]

    def count(self) -> int:
        return len(self._layers)
```

**`service.py` — `LayerService` skeleton:**
```python
from __future__ import annotations
# CAD access: session.backend only — never import ezdxf
from lcs_cad_mcp.modules.layers.registry import LayerRegistry
from lcs_cad_mcp.modules.layers.schemas import LayerRecord

class LayerService:
    def __init__(self, session) -> None:
        self.session = session
        self.registry = LayerRegistry()
        self._synced = False

    def ensure_synced(self) -> None:
        if not self._synced:
            self.registry.sync_from_backend(self.session.backend)
            self._synced = True
```

### Project Structure Notes

Files created or modified by this story:

```
src/lcs_cad_mcp/modules/layers/
├── __init__.py          # add register(mcp) stub + export LayerRecord, LayerRegistry
├── schemas.py           # NEW — LayerRecord Pydantic model
├── registry.py          # NEW — LayerRegistry class
├── service.py           # UPDATE — add LayerRegistry instantiation and ensure_synced()
└── tools.py             # unchanged in this story (tools added in 3-2, 3-3)

tests/unit/modules/layers/
├── __init__.py          # NEW (empty)
├── test_schemas.py      # NEW — LayerRecord unit tests
└── test_registry.py     # NEW — LayerRegistry unit tests
```

### Dependencies

- **Story 2-1** (CADBackend abstract Protocol in `backends/base.py`) — `LayerRegistry.sync_from_backend()` relies on `backend.list_layers()` defined there.
- **Story 2-3** (ezdxf backend implementation) — `MockCADBackend` in `tests/conftest.py` must stub `list_layers()` returning `list[dict]` for registry sync tests.
- **Story 1-1** (project scaffold) — `tests/unit/modules/layers/` directory must exist (created as stub in Story 1-1, Task 4.2).
- **`conftest.py`** must provide `MockCADBackend` with a `list_layers()` method returning a configurable list of layer dicts.

### `MockCADBackend` Extension Required

If `conftest.py`'s `MockCADBackend` does not yet have `list_layers()`, add it:
```python
class MockCADBackend:
    def __init__(self, layers: list[dict] | None = None):
        self._layers = layers or [
            {"name": "0", "color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25,
             "is_on": True, "is_frozen": False, "is_locked": False},
        ]

    def list_layers(self) -> list[dict]:
        return self._layers
```

### References

- Architecture doc layer module structure: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Complete Project Directory Structure", layers/ subsection]
- CADBackend access pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "CAD Backend Access"]
- Pydantic v2 constraint: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Key Architecture Decisions"]
- Case-insensitive naming: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Story 3-1, AC4]
- Story definition: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 3, Story 3-1]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/layers/__init__.py`
- `src/lcs_cad_mcp/modules/layers/schemas.py`
- `src/lcs_cad_mcp/modules/layers/registry.py`
- `src/lcs_cad_mcp/modules/layers/service.py`
- `tests/unit/modules/layers/__init__.py`
- `tests/unit/modules/layers/test_schemas.py`
- `tests/unit/modules/layers/test_registry.py`
