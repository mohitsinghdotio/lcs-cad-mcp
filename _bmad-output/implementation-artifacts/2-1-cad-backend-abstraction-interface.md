# Story 2.1: CAD Backend Abstraction Interface

Status: ready-for-dev

## Story

As a **developer**,
I want **a `typing.Protocol`-based abstract interface that defines the full contract for all CAD backends**,
so that **all higher-level tools, services, and modules are backend-agnostic and can work with both ezdxf and COM backends without modification**.

## Acceptance Criteria

1. **AC1:** `src/lcs_cad_mcp/backends/base.py` defines `CADBackend` as a `typing.Protocol` with all required methods fully type-annotated: `open_drawing`, `new_drawing`, `save_drawing`, `create_layer`, `delete_layer`, `list_layers`, `get_layer`, `draw_polyline`, `draw_line`, `draw_arc`, `draw_circle`, `add_text`, `insert_block`, `move_entity`, `copy_entity`, `delete_entity`, `query_entities`, `get_drawing_metadata`, `is_available`.
2. **AC2:** `BackendFactory` class in `backends/base.py` exposes a `get(backend_name: str) -> CADBackend` classmethod that returns the correct backend implementation instance based on the `CAD_BACKEND` env var or explicit argument; raises `MCPError(ErrorCode.BACKEND_UNAVAILABLE)` for unknown or unavailable backends.
3. **AC3:** Every method on `CADBackend` has a complete docstring describing parameters, return type, and any exceptions it may raise; return types use Pydantic schemas from `backends/base.py` or built-in types only — no ezdxf-specific types leak into the Protocol signature.
4. **AC4:** `tests/unit/backends/test_base.py` contains unit tests verifying: (a) a mock class satisfying the Protocol passes `isinstance` structural checks; (b) `BackendFactory.get("ezdxf")` returns an `EzdxfBackend` instance; (c) `BackendFactory.get("unknown")` raises `MCPError` with code `BACKEND_UNAVAILABLE`.
5. **AC5:** `MockCADBackend` fixture is added to `tests/conftest.py` for use by all subsequent story tests — it implements the full `CADBackend` Protocol with in-memory stubs and configurable return values.

## Tasks / Subtasks

- [ ] Task 1: Define `CADBackend` Protocol in `backends/base.py` (AC: 1, 3)
  - [ ] 1.1: Add module docstring explaining Protocol-based duck-typing approach and why `typing.Protocol` is chosen over ABC
  - [ ] 1.2: Define `DrawingMetadata` Pydantic model (fields: `file_path: str | None`, `dxf_version: str`, `units: str`, `extents_min: tuple[float, float]`, `extents_max: tuple[float, float]`, `entity_count: int`, `layer_count: int`)
  - [ ] 1.3: Define `LayerInfo` Pydantic model (fields: `name: str`, `color: int`, `linetype: str`, `lineweight: float`, `is_on: bool`, `is_frozen: bool`, `is_locked: bool`)
  - [ ] 1.4: Define `EntityInfo` Pydantic model (fields: `handle: str`, `entity_type: str`, `layer: str`, `geometry: dict`)
  - [ ] 1.5: Define `CADBackend` class with `@runtime_checkable` decorator and `typing.Protocol` base; add all 19 method signatures with `...` body; annotate every parameter and return type using only built-in types, `DrawingMetadata`, `LayerInfo`, `EntityInfo`
  - [ ] 1.6: Add docstring to every method on `CADBackend`: minimum one-line summary, `Args:` and `Returns:` sections, `Raises: MCPError` note

- [ ] Task 2: Implement `BackendFactory` in `backends/base.py` (AC: 2)
  - [ ] 2.1: Define `BackendFactory` class with class-level `_registry: dict[str, type[CADBackend]]` mapping names to implementation classes
  - [ ] 2.2: Implement `BackendFactory.register(name: str, cls: type[CADBackend]) -> None` classmethod for backends to self-register
  - [ ] 2.3: Implement `BackendFactory.get(backend_name: str | None = None) -> CADBackend` classmethod; if `backend_name` is None, read from `Settings().cad_backend`; raise `MCPError(ErrorCode.BACKEND_UNAVAILABLE)` for unknown names
  - [ ] 2.4: Add inline comment explaining lazy import pattern: backends self-register via `__init_subclass__` or explicit `BackendFactory.register()` call at module import time to avoid circular imports

- [ ] Task 3: Implement `MockCADBackend` and update `tests/conftest.py` (AC: 5)
  - [ ] 3.1: Create `tests/unit/backends/__init__.py` (empty)
  - [ ] 3.2: Define `MockCADBackend` in `tests/conftest.py` that satisfies `CADBackend` Protocol; every method returns a sensible stub value (e.g., `get_drawing_metadata()` returns `DrawingMetadata` with zeroed extents)
  - [ ] 3.3: Add `mock_backend` pytest fixture that returns a `MockCADBackend` instance
  - [ ] 3.4: Add `mock_session` pytest fixture that returns a `DrawingSession` (from `session/context.py` stub) with `.backend = mock_backend`

- [ ] Task 4: Write unit tests in `tests/unit/backends/test_base.py` (AC: 4)
  - [ ] 4.1: Test `isinstance(MockCADBackend(), CADBackend)` is `True` when Protocol has `@runtime_checkable`
  - [ ] 4.2: Test a class missing one required method fails the `isinstance` check
  - [ ] 4.3: Test `BackendFactory.get("ezdxf")` import path (mock `EzdxfBackend` registration to avoid ezdxf import dependency in this test)
  - [ ] 4.4: Test `BackendFactory.get("unknown_backend")` raises `MCPError` with `.code == ErrorCode.BACKEND_UNAVAILABLE`
  - [ ] 4.5: Test `BackendFactory.get()` with no arg reads `Settings().cad_backend` env var (patch `os.environ["CAD_BACKEND"] = "ezdxf"`)

- [ ] Task 5: Update `backends/__init__.py` to wire self-registration (AC: 2)
  - [ ] 5.1: In `backends/__init__.py`, import `EzdxfBackend` and call `BackendFactory.register("ezdxf", EzdxfBackend)` — guard with `try/except ImportError` so tests without ezdxf installed still run
  - [ ] 5.2: Import `COMBackend` and call `BackendFactory.register("com", COMBackend)` guarded by `sys.platform == "win32"` check
  - [ ] 5.3: Add `__all__ = ["CADBackend", "BackendFactory", "DrawingMetadata", "LayerInfo", "EntityInfo"]` to `backends/__init__.py`

- [ ] Task 6: Verify Protocol contract completeness against architecture spec (AC: 1, 3)
  - [ ] 6.1: Cross-check all 19 methods listed in the Epic 2 Specific Context against the Protocol definition; add any missing method signatures
  - [ ] 6.2: Run `ruff check src/lcs_cad_mcp/backends/base.py` and fix all lint errors
  - [ ] 6.3: Run `pytest tests/unit/backends/test_base.py -v` and confirm all tests pass

## Dev Notes

### Critical Architecture Constraints

1. **`typing.Protocol` NOT `ABC`** — Use `typing.Protocol` with `@runtime_checkable` decorator. This enables structural subtyping (duck typing): the ezdxf backend and COM backend do NOT need to explicitly inherit from `CADBackend`. This is the chosen pattern per architecture spec.
2. **No ezdxf types in Protocol signatures** — The Protocol's method signatures must use only Python built-ins, Pydantic models defined in `base.py`, and standard library types. `ezdxf.document.Drawing`, `ezdxf.layouts.Layout`, etc. must NEVER appear in `base.py`. Leaking backend-specific types breaks the abstraction.
3. **This file is the FOUNDATION** — All 10 modules (cad, predcr, layers, entities, verification, config, area, autodcr, reports, workflow) type-annotate their `service.py` with `backend: CADBackend`. If the Protocol changes after Story 2-2+, it is a breaking change requiring coordination.
4. **`BackendFactory.get()` must be cheap** — It creates a new backend instance per call; backends must not perform expensive initialization in `__init__`. Connection/file handles are opened on first use (lazy open).
5. **FORBIDDEN:** Do not import `ezdxf` or `win32com` in `base.py` — circular import risk and breaks non-Windows CI.

### Module/Component Notes

**File:** `src/lcs_cad_mcp/backends/base.py`

```python
from __future__ import annotations
from typing import Protocol, runtime_checkable
from pydantic import BaseModel


class DrawingMetadata(BaseModel):
    file_path: str | None = None
    dxf_version: str = "R2018"
    units: str = "metric"
    extents_min: tuple[float, float] = (0.0, 0.0)
    extents_max: tuple[float, float] = (0.0, 0.0)
    entity_count: int = 0
    layer_count: int = 0


class LayerInfo(BaseModel):
    name: str
    color: int = 7
    linetype: str = "Continuous"
    lineweight: float = 0.25
    is_on: bool = True
    is_frozen: bool = False
    is_locked: bool = False


class EntityInfo(BaseModel):
    handle: str
    entity_type: str
    layer: str
    geometry: dict  # backend-specific geometry dict, e.g. {"start": [x,y], "end": [x,y]}


@runtime_checkable
class CADBackend(Protocol):
    def is_available(self) -> bool: ...
    def open_drawing(self, path: str) -> DrawingMetadata: ...
    def new_drawing(self, name: str = "Untitled", units: str = "metric") -> DrawingMetadata: ...
    def save_drawing(self, path: str, dxf_version: str = "R2018") -> bool: ...
    def create_layer(self, name: str, color: int = 7, linetype: str = "Continuous",
                     lineweight: float = 0.25) -> LayerInfo: ...
    def delete_layer(self, name: str) -> bool: ...
    def list_layers(self) -> list[LayerInfo]: ...
    def get_layer(self, name: str) -> LayerInfo: ...
    def draw_polyline(self, points: list[tuple[float, float]], layer: str,
                      closed: bool = False) -> EntityInfo: ...
    def draw_line(self, start: tuple[float, float], end: tuple[float, float],
                  layer: str) -> EntityInfo: ...
    def draw_arc(self, center: tuple[float, float], radius: float, start_angle: float,
                 end_angle: float, layer: str) -> EntityInfo: ...
    def draw_circle(self, center: tuple[float, float], radius: float,
                    layer: str) -> EntityInfo: ...
    def add_text(self, text: str, position: tuple[float, float], height: float,
                 layer: str) -> EntityInfo: ...
    def insert_block(self, name: str, position: tuple[float, float],
                     scale: float, layer: str) -> EntityInfo: ...
    def move_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo: ...
    def copy_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo: ...
    def delete_entity(self, handle: str) -> bool: ...
    def query_entities(self, layer: str | None = None, entity_type: str | None = None,
                       bounds: tuple[float, float, float, float] | None = None
                       ) -> list[EntityInfo]: ...
    def get_drawing_metadata(self) -> DrawingMetadata: ...
```

**`BackendFactory` key pattern:**
```python
class BackendFactory:
    _registry: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, backend_cls: type) -> None:
        cls._registry[name] = backend_cls

    @classmethod
    def get(cls, backend_name: str | None = None) -> CADBackend:
        from lcs_cad_mcp.settings import Settings
        name = backend_name or Settings().cad_backend
        if name not in cls._registry:
            from lcs_cad_mcp.errors import MCPError, ErrorCode
            raise MCPError(
                code=ErrorCode.BACKEND_UNAVAILABLE,
                message=f"Backend '{name}' is not registered or not available",
                recoverable=False,
            )
        return cls._registry[name]()
```

### Project Structure Notes

```
src/lcs_cad_mcp/
├── backends/
│   ├── __init__.py        # register ezdxf + COM backends
│   ├── base.py            # THIS STORY — CADBackend Protocol + BackendFactory + Pydantic models
│   ├── ezdxf_backend.py   # Story 2-2 (stub exists from Story 1-1)
│   └── com_backend.py     # Story 2-5 (stub exists from Story 1-1)
tests/
├── conftest.py            # Add MockCADBackend + mock_backend + mock_session fixtures
└── unit/
    └── backends/
        ├── __init__.py
        └── test_base.py   # THIS STORY — BackendFactory + Protocol tests
```

### Dependencies

- **Story 1-1** (project scaffold): `backends/base.py` stub file exists; `errors.py` with `MCPError` and `ErrorCode` exists; `settings.py` with `Settings.cad_backend` field exists.
- **Story 1-5** (Pydantic validation framework): Establishes pattern for Pydantic model usage in this project.
- No story in Epic 2 or beyond can begin until this Protocol is stable and tests pass.

### References

- Protocol definition: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 2, Story 2-1]
- Architecture enforcement: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "CAD Backend Abstraction Layer"]
- Anti-patterns: FORBIDDEN list in architecture spec — "import ezdxf outside backends/", "global singletons"
- typing.Protocol docs: https://docs.python.org/3/library/typing.html#typing.Protocol

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
- `src/lcs_cad_mcp/backends/__init__.py`
- `tests/conftest.py` (updated with MockCADBackend fixtures)
- `tests/unit/backends/__init__.py`
- `tests/unit/backends/test_base.py`
