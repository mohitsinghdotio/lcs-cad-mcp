# Story 2.2: ezdxf Backend — Drawing Lifecycle

Status: ready-for-dev

## Story

As a **developer**,
I want **the ezdxf backend to fully implement the `open_drawing`, `new_drawing`, and `save_drawing` methods of the `CADBackend` Protocol**,
so that **the full CAD pipeline works headlessly without AutoCAD installed, enabling cross-platform operation and CI testing** (FR5, FR45).

## Acceptance Criteria

1. **AC1:** `EzdxfBackend.open_drawing(path: str) -> DrawingMetadata` opens an existing DXF or DWG file using `ezdxf.readfile()`; returns a populated `DrawingMetadata` object; raises `MCPError(ErrorCode.DRAWING_OPEN_FAILED)` if the file does not exist or is corrupt.
2. **AC2:** `EzdxfBackend.new_drawing(name: str = "Untitled", units: str = "metric") -> DrawingMetadata` creates a blank DXF document using `ezdxf.new(dxfversion="R2018")`; initialises the model space; returns `DrawingMetadata` reflecting the empty drawing.
3. **AC3:** `EzdxfBackend.save_drawing(path: str, dxf_version: str = "R2018") -> bool` saves the current in-memory document to the specified path in DXF format; the `dxf_version` parameter controls the output version (default `"R2018"`); returns `True` on success; raises `MCPError(ErrorCode.DRAWING_OPEN_FAILED)` if no drawing is currently open.
4. **AC4:** After `save_drawing`, the output DXF file passes `ezdxf.audit()` with zero critical errors — verifying structural correctness and compatibility with AutoCAD, ZWCAD, and BricsCAD (NFR21).
5. **AC5:** `EzdxfBackend.is_available() -> bool` always returns `True` on any platform (ezdxf is pure Python with no system dependencies).
6. **AC6:** `BackendFactory.register("ezdxf", EzdxfBackend)` is called at import time in `backends/__init__.py` so `BackendFactory.get("ezdxf")` works end-to-end.
7. **AC7:** Unit tests in `tests/unit/backends/test_ezdxf_backend.py` cover: open existing file, open missing file (error), new drawing, save drawing, audit pass, and is_available.

## Tasks / Subtasks

- [ ] Task 1: Implement `EzdxfBackend` class skeleton in `backends/ezdxf_backend.py` (AC: 5, 6)
  - [ ] 1.1: Replace the stub file with a full class definition: `class EzdxfBackend:` (no explicit inheritance needed — structural typing via Protocol)
  - [ ] 1.2: Add instance variable `_doc: ezdxf.document.Drawing | None = None` to hold the open document
  - [ ] 1.3: Add instance variable `_current_path: str | None = None` to track the file path of the open drawing
  - [ ] 1.4: Implement `is_available(self) -> bool: return True` with docstring
  - [ ] 1.5: Add import guard: `import ezdxf` at top of module; add inline comment `# ezdxf import allowed ONLY in backends/ — see architecture enforcement rules`

- [ ] Task 2: Implement `open_drawing` (AC: 1)
  - [ ] 2.1: Implement `open_drawing(self, path: str) -> DrawingMetadata` using `ezdxf.readfile(path)`
  - [ ] 2.2: Wrap in `try/except (FileNotFoundError, ezdxf.DXFError)` — on exception raise `MCPError(code=ErrorCode.DRAWING_OPEN_FAILED, message=str(e), recoverable=False)`
  - [ ] 2.3: On success, store the document in `self._doc` and path in `self._current_path`
  - [ ] 2.4: Call `self.get_drawing_metadata()` to build and return the `DrawingMetadata` response (reuse the metadata extraction logic)
  - [ ] 2.5: Add docstring: describes path parameter, DWG note (ezdxf reads DXF natively; DWG requires ODA converter — log a warning if `.dwg` extension detected)

- [ ] Task 3: Implement `new_drawing` (AC: 2)
  - [ ] 3.1: Implement `new_drawing(self, name: str = "Untitled", units: str = "metric") -> DrawingMetadata`
  - [ ] 3.2: Call `ezdxf.new(dxfversion="R2018")` to create the document; store in `self._doc`
  - [ ] 3.3: Set drawing units via `self._doc.header["$INSUNITS"]`: `metric` → 4 (millimetres), `imperial` → 1 (inches); log warning for unrecognised unit strings, default to metric
  - [ ] 3.4: Set `self._current_path = None` (new drawing has no file path yet)
  - [ ] 3.5: Return `DrawingMetadata` with `dxf_version="R2018"`, `entity_count=0`, `layer_count=1` (ezdxf always creates layer "0" by default), `units=units`

- [ ] Task 4: Implement `save_drawing` (AC: 3, 4)
  - [ ] 4.1: Implement `save_drawing(self, path: str, dxf_version: str = "R2018") -> bool`
  - [ ] 4.2: Guard: if `self._doc is None` raise `MCPError(ErrorCode.DRAWING_OPEN_FAILED, "No drawing is currently open", recoverable=True)`
  - [ ] 4.3: Map `dxf_version` string to ezdxf constant: build a dict `{"R12": "AC1009", "R2000": "AC1015", "R2004": "AC1018", "R2007": "AC1021", "R2010": "AC1024", "R2013": "AC1027", "R2018": "AC1032"}`; use `self._doc.dxfversion` upgrade path via `doc.header["$ACADVER"]` override or `ezdxf.upright()` as appropriate
  - [ ] 4.4: Call `self._doc.saveas(path)` to write the file; update `self._current_path = path`
  - [ ] 4.5: Run `auditor = self._doc.audit()` post-save; log any audit errors at WARNING level; return `True` (audit failures are warnings, not errors — callers can check logs)
  - [ ] 4.6: Wrap the entire save in `try/except OSError` — on failure raise `MCPError(ErrorCode.DRAWING_OPEN_FAILED, message=str(e), recoverable=True)`

- [ ] Task 5: Register `EzdxfBackend` with `BackendFactory` (AC: 6)
  - [ ] 5.1: In `backends/__init__.py`, add: `from lcs_cad_mcp.backends.ezdxf_backend import EzdxfBackend` inside a `try/except ImportError` block
  - [ ] 5.2: Call `BackendFactory.register("ezdxf", EzdxfBackend)` immediately after the import succeeds
  - [ ] 5.3: Confirm `BackendFactory.get("ezdxf")` returns an `EzdxfBackend` instance in a smoke test

- [ ] Task 6: Write unit tests in `tests/unit/backends/test_ezdxf_backend.py` (AC: 7)
  - [ ] 6.1: Create `tests/unit/backends/test_ezdxf_backend.py`
  - [ ] 6.2: Test `EzdxfBackend.is_available()` returns `True`
  - [ ] 6.3: Test `open_drawing` with a real minimal DXF fixture (create it in-test using `ezdxf.new()` + `doc.saveas(tmp_path / "test.dxf")`)
  - [ ] 6.4: Test `open_drawing` with a non-existent path raises `MCPError` with code `DRAWING_OPEN_FAILED`
  - [ ] 6.5: Test `new_drawing("TestDraw", "metric")` returns `DrawingMetadata` with `layer_count=1`, `entity_count=0`
  - [ ] 6.6: Test `save_drawing(str(tmp_path / "out.dxf"))` creates the file on disk; assert file exists and is non-empty
  - [ ] 6.7: Test `save_drawing` on a brand-new drawing runs `ezdxf.audit()` without critical errors
  - [ ] 6.8: Test `save_drawing` with no open document raises `MCPError` with `recoverable=True`

- [ ] Task 7: Verify ruff lint and pytest pass (AC: all)
  - [ ] 7.1: Run `ruff check src/lcs_cad_mcp/backends/ezdxf_backend.py` — fix all issues
  - [ ] 7.2: Run `pytest tests/unit/backends/test_ezdxf_backend.py -v` — all tests green
  - [ ] 7.3: Run `pytest tests/unit/backends/ -v` — confirm Story 2-1 tests still pass alongside new tests

## Dev Notes

### Critical Architecture Constraints

1. **`import ezdxf` is ONLY permitted in `backends/ezdxf_backend.py`** — no other file in the project may import ezdxf directly. This is an enforced architecture rule. If any service or module needs CAD data, it calls `backend.method()` and receives `DrawingMetadata`, `LayerInfo`, or `EntityInfo` Pydantic objects — never raw ezdxf objects.
2. **DWG support caveat** — ezdxf cannot read native DWG files without the ODA File Converter installed. If a `.dwg` path is passed to `open_drawing`, log a `WARNING` and attempt `ezdxf.readfile()` anyway (some DWG variants may load). If it fails, raise `MCPError(DRAWING_OPEN_FAILED)`. Do NOT silently convert or attempt format detection.
3. **`self._doc` is the single source of truth** — `EzdxfBackend` is a stateful object; each instance holds exactly one open document. `BackendFactory.get("ezdxf")` creates a new instance per call. The session (`DrawingSession`) in `session/context.py` is responsible for holding the backend instance across requests.
4. **DXF version pinning** — Default output is DXF R2018 (`AC1032`). This is the minimum version required for full PreDCR/AutoDCR layer and entity support per NFR19. Never downgrade to R12 or R2000 unless explicitly requested.
5. **FORBIDDEN in this file:** business logic, PreDCR rule evaluation, layer naming validation, entity counting beyond what metadata needs.

### Module/Component Notes

**File:** `src/lcs_cad_mcp/backends/ezdxf_backend.py`

```python
"""ezdxf CAD backend — headless DXF read/write. Only file that may import ezdxf."""
from __future__ import annotations
import logging
import ezdxf  # allowed ONLY in backends/ — architecture rule
from lcs_cad_mcp.backends.base import DrawingMetadata, LayerInfo, EntityInfo
from lcs_cad_mcp.errors import MCPError, ErrorCode

logger = logging.getLogger(__name__)

_DXF_VERSION_MAP = {
    "R12": "AC1009", "R2000": "AC1015", "R2004": "AC1018",
    "R2007": "AC1021", "R2010": "AC1024", "R2013": "AC1027", "R2018": "AC1032",
}

_UNITS_MAP = {"metric": 4, "imperial": 1}  # $INSUNITS values


class EzdxfBackend:
    """Implements CADBackend Protocol using ezdxf (headless, cross-platform)."""

    def __init__(self) -> None:
        self._doc: ezdxf.document.Drawing | None = None
        self._current_path: str | None = None

    def is_available(self) -> bool:
        """Always True — ezdxf is pure Python, no system dependencies."""
        return True

    def open_drawing(self, path: str) -> DrawingMetadata:
        """Open an existing DXF file. Raises MCPError on failure."""
        try:
            self._doc = ezdxf.readfile(path)
            self._current_path = path
        except FileNotFoundError as e:
            raise MCPError(code=ErrorCode.DRAWING_OPEN_FAILED,
                           message=f"File not found: {path}", recoverable=False) from e
        except ezdxf.DXFError as e:
            raise MCPError(code=ErrorCode.DRAWING_OPEN_FAILED,
                           message=f"DXF parse error: {e}", recoverable=False) from e
        return self.get_drawing_metadata()

    def new_drawing(self, name: str = "Untitled", units: str = "metric") -> DrawingMetadata:
        """Create a blank R2018 DXF document in memory."""
        self._doc = ezdxf.new(dxfversion="R2018")
        self._doc.header["$INSUNITS"] = _UNITS_MAP.get(units, 4)
        self._current_path = None
        return self.get_drawing_metadata()

    def save_drawing(self, path: str, dxf_version: str = "R2018") -> bool:
        """Save current drawing to path. Runs audit post-save. Returns True on success."""
        if self._doc is None:
            raise MCPError(code=ErrorCode.DRAWING_OPEN_FAILED,
                           message="No drawing is currently open", recoverable=True)
        try:
            self._doc.saveas(path)
            self._current_path = path
        except OSError as e:
            raise MCPError(code=ErrorCode.DRAWING_OPEN_FAILED,
                           message=f"Save failed: {e}", recoverable=True) from e
        auditor = self._doc.audit()
        if auditor.has_errors:
            for err in auditor.errors:
                logger.warning("DXF audit error: %s", err)
        return True

    def get_drawing_metadata(self) -> DrawingMetadata:
        """Extract metadata from current open document."""
        if self._doc is None:
            raise MCPError(code=ErrorCode.DRAWING_OPEN_FAILED,
                           message="No drawing is currently open", recoverable=True)
        msp = self._doc.modelspace()
        return DrawingMetadata(
            file_path=self._current_path,
            dxf_version=self._doc.dxfversion,
            units="metric" if self._doc.header.get("$INSUNITS", 4) == 4 else "imperial",
            entity_count=len(list(msp)),
            layer_count=len(list(self._doc.layers)),
        )
```

### Project Structure Notes

```
src/lcs_cad_mcp/
├── backends/
│   ├── __init__.py           # updated: register EzdxfBackend with BackendFactory
│   ├── base.py               # Story 2-1 (Protocol + DrawingMetadata + BackendFactory)
│   └── ezdxf_backend.py      # THIS STORY — full lifecycle implementation
tests/
└── unit/
    └── backends/
        ├── test_base.py          # Story 2-1 tests
        └── test_ezdxf_backend.py # THIS STORY
```

**DXF fixture helper** for tests (add to `tests/conftest.py` or inline in test file):
```python
import pytest, ezdxf
from pathlib import Path

@pytest.fixture
def dxf_file(tmp_path: Path) -> Path:
    doc = ezdxf.new("R2018")
    path = tmp_path / "fixture.dxf"
    doc.saveas(str(path))
    return path
```

### Dependencies

- **Story 1-1** (scaffold): `backends/ezdxf_backend.py` stub exists; `errors.py` has `MCPError` and `ErrorCode`.
- **Story 2-1** (CADBackend Protocol): `DrawingMetadata`, `LayerInfo`, `EntityInfo`, and `BackendFactory` must exist before this story's implementation is started. The `EzdxfBackend` class must structurally satisfy the `CADBackend` Protocol.

### References

- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 2, Story 2-2]
- ezdxf readfile API: https://ezdxf.readthedocs.io/en/stable/drawing/management.html
- ezdxf new drawing: https://ezdxf.readthedocs.io/en/stable/drawing/drawing.html
- DXF version constants: https://ezdxf.readthedocs.io/en/stable/dxfentities/dxfgfx.html
- ezdxf audit: https://ezdxf.readthedocs.io/en/stable/audit.html
- NFR21 compatibility requirement: [Source: `_bmad-output/planning-artifacts/architecture.md`]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/backends/ezdxf_backend.py`
- `src/lcs_cad_mcp/backends/__init__.py` (updated)
- `tests/unit/backends/test_ezdxf_backend.py`
- `tests/conftest.py` (updated with `dxf_file` fixture)
