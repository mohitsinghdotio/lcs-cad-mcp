# Story 2.5: COM Backend — Drawing Lifecycle (Windows)

Status: ready-for-dev

## Story

As a **developer**,
I want **the COM backend to control a live AutoCAD (or ZWCAD/BricsCAD) session via Windows COM automation**,
so that **architects using AutoCAD on Windows can operate the full pipeline without switching applications**.

## Acceptance Criteria

1. **AC1:** `COMBackend.open_drawing(path: str) -> DrawingMetadata` opens a DWG or DXF file in the active AutoCAD/ZWCAD/BricsCAD COM session; if no session is active, attempts to launch AutoCAD via `win32com.client.Dispatch("AutoCAD.Application")`; raises `MCPError(ErrorCode.DRAWING_OPEN_FAILED)` on failure.
2. **AC2:** `COMBackend.new_drawing(name: str = "Untitled", units: str = "metric") -> DrawingMetadata` creates a new drawing in the live CAD session using the COM `Documents.Add()` API; returns `DrawingMetadata` reflecting the new empty drawing.
3. **AC3:** `COMBackend.save_drawing(path: str, dxf_version: str = "R2018") -> bool` saves the active document via the COM `Document.SaveAs()` API; supports both DWG and DXF output based on file extension.
4. **AC4:** `COMBackend.is_available() -> bool` returns `True` only on Windows (`sys.platform == "win32"`) AND when a supported COM application (AutoCAD, ZWCAD, or BricsCAD) is accessible via `win32com.client.GetActiveObject()`; returns `False` on all other platforms or when no CAD application is running — this check must complete within 2 seconds (NFR16).
5. **AC5:** COM connection loss mid-operation is detected via `pywintypes.com_error`; caught and re-raised as `MCPError(ErrorCode.BACKEND_UNAVAILABLE, recoverable=False)`; the ezdxf backend remains available as a fallback after COM failure.
6. **AC6:** On non-Windows platforms, `com_backend.py` is importable without error (all COM-specific imports are guarded by `if sys.platform == "win32":`) — a `COMBackend` class exists on all platforms but `is_available()` returns `False` and all methods raise `MCPError(BACKEND_UNAVAILABLE)` with message `"COM backend requires Windows"`.
7. **AC7:** `COMBackend` satisfies the same `CADBackend` Protocol contract as `EzdxfBackend` — the full 19-method signature is implemented (methods not yet fully implemented return a stub result or raise `MCPError(BACKEND_UNAVAILABLE, recoverable=False, suggested_action="Use ezdxf backend")`).
8. **AC8:** All tests that call `COMBackend` methods on non-Windows CI use a `MockCOMApplication` fixture (no real COM calls) — guarded by `pytest.mark.skipif(sys.platform != "win32", reason="COM backend Windows-only")`.

## Tasks / Subtasks

- [ ] Task 1: Implement `COMBackend` class skeleton in `backends/com_backend.py` (AC: 6, 7)
  - [ ] 1.1: Replace the stub `backends/com_backend.py` with the full class; wrap all `pywin32` imports in an `if sys.platform == "win32":` block at module level; define stub imports for non-Windows: `win32com = None`, `pywintypes = None`
  - [ ] 1.2: Define class `COMBackend:` with instance variables: `_app: Any | None = None` (the COM `Application` object), `_doc: Any | None = None` (the COM `Document` object), `_current_path: str | None = None`
  - [ ] 1.3: Add a `_win32_only_guard(self) -> None` private helper: if `sys.platform != "win32"` raise `MCPError(ErrorCode.BACKEND_UNAVAILABLE, message="COM backend requires Windows", recoverable=False, suggested_action="Set CAD_BACKEND=ezdxf or run on Windows")`
  - [ ] 1.4: Implement all 19 `CADBackend` Protocol methods as stubs initially (raise `MCPError(BACKEND_UNAVAILABLE, suggested_action="Use ezdxf backend")`) — to be replaced by real implementations in tasks 2-4

- [ ] Task 2: Implement `is_available` and COM connection management (AC: 4, 5)
  - [ ] 2.1: Implement `is_available(self) -> bool`: if `sys.platform != "win32"` return `False`; attempt `win32com.client.GetActiveObject("AutoCAD.Application")` in a `try/except pywintypes.com_error`; also try `"ZwSoft.ZwCAD"` and `"BricscadApp.AcadApplication"` as fallbacks; set timeout guard using `threading.Timer` or `concurrent.futures.ThreadPoolExecutor` with a 2-second timeout; return `True` if any app responds, `False` otherwise
  - [ ] 2.2: Implement `_connect_or_launch(self) -> None` private method: first tries `GetActiveObject` for all three COM prog IDs; if all fail, tries `win32com.client.Dispatch("AutoCAD.Application")` to launch AutoCAD; wraps in `try/except pywintypes.com_error`; on failure raises `MCPError(BACKEND_UNAVAILABLE, recoverable=False)`
  - [ ] 2.3: Implement `_get_active_document(self) -> Any` private method: calls `self._app.ActiveDocument` and stores result in `self._doc`; wraps in `try/except pywintypes.com_error` and raises `MCPError(DRAWING_OPEN_FAILED)` on COM error

- [ ] Task 3: Implement `open_drawing`, `new_drawing`, `save_drawing` (AC: 1, 2, 3, 5)
  - [ ] 3.1: Implement `open_drawing(self, path: str) -> DrawingMetadata`:
    - Call `self._win32_only_guard()` then `self._connect_or_launch()`
    - Use `self._app.Documents.Open(path)` to open the file
    - Store result in `self._doc` and `self._current_path = path`
    - Call `get_drawing_metadata()` and return the result
    - Wrap all COM calls in `try/except pywintypes.com_error` → raise `MCPError(DRAWING_OPEN_FAILED, recoverable=False)`
  - [ ] 3.2: Implement `new_drawing(self, name: str = "Untitled", units: str = "metric") -> DrawingMetadata`:
    - Call `self._win32_only_guard()` then `self._connect_or_launch()`
    - Use `self._app.Documents.Add()` to create a new document
    - Store in `self._doc`; set `self._current_path = None`
    - Return `get_drawing_metadata()`
  - [ ] 3.3: Implement `save_drawing(self, path: str, dxf_version: str = "R2018") -> bool`:
    - Call `self._win32_only_guard()`
    - If `self._doc is None` raise `MCPError(DRAWING_OPEN_FAILED, recoverable=True)`
    - Determine save format: `.dwg` extension → `acSaveAsFormatDWG` (COM constant); `.dxf` extension → `acSaveAsFormatDXF`
    - Call `self._doc.SaveAs(path, format_const)` via COM
    - Update `self._current_path = path`; return `True`
    - Wrap in `try/except pywintypes.com_error` → raise `MCPError(DRAWING_OPEN_FAILED, recoverable=True)`

- [ ] Task 4: Implement `get_drawing_metadata` for COM backend (AC: 1)
  - [ ] 4.1: Implement `get_drawing_metadata(self) -> DrawingMetadata`:
    - Call `self._win32_only_guard()` and guard `self._doc is None` → `MCPError(DRAWING_OPEN_FAILED)`
    - Read `self._doc.Name`, `self._doc.ActiveLayer.Name`, entity count via `self._doc.ModelSpace.Count`
    - Read extents via `self._app.GetExtent()` or `self._doc.Limits` COM property
    - Construct and return `DrawingMetadata` with all fields populated
  - [ ] 4.2: Implement `list_layers(self) -> list[LayerInfo]`:
    - Iterate `self._doc.Layers` COM collection
    - Construct `LayerInfo` for each: name, color, linetype, on/frozen/locked state via COM properties `Layer.LayerOn`, `Layer.Freeze`, `Layer.Lock`
  - [ ] 4.3: Implement `get_layer(self, name: str) -> LayerInfo`:
    - Search `list_layers()` result case-insensitively
    - Raise `MCPError(LAYER_NOT_FOUND)` if not found

- [ ] Task 5: Register `COMBackend` with `BackendFactory` (Story 2-1 extension) (AC: 5)
  - [ ] 5.1: In `backends/__init__.py`, add import of `COMBackend` guarded by `sys.platform == "win32"` check
  - [ ] 5.2: Register: `BackendFactory.register("com", COMBackend)` inside the platform guard
  - [ ] 5.3: On non-Windows, still register a stub that raises `MCPError(BACKEND_UNAVAILABLE)` on instantiation — so `BackendFactory.get("com")` raises a clean error on any platform

- [ ] Task 6: Implement snapshot/rollback for COM backend (AC: from Story 2-4 AC6)
  - [ ] 6.1: Implement `SnapshotManager._take_com_snapshot(self)` strategy: since COM backend has no in-memory document, snapshot by saving to a temp DXF file: `tmpfile = tempfile.NamedTemporaryFile(suffix=".dxf", delete=False)`; call `self._backend.save_drawing(tmpfile.name)`; store the temp file path as the checkpoint value
  - [ ] 6.2: Implement `SnapshotManager._restore_com_snapshot(self, checkpoint_id)`: re-open the temp DXF via `self._backend.open_drawing(tmpfile_path)`; delete the temp file after restore
  - [ ] 6.3: Update `SnapshotManager.take()` to dispatch: if `isinstance(self._backend, EzdxfBackend)` use string serialisation; if `isinstance(self._backend, COMBackend)` use temp-file strategy
  - [ ] 6.4: Clean up temp files in `SnapshotManager.clear()` to avoid temp dir accumulation

- [ ] Task 7: Write tests in `tests/unit/backends/test_com_backend.py` (AC: 8)
  - [ ] 7.1: Create `tests/unit/backends/test_com_backend.py`
  - [ ] 7.2: Define `MockCOMApplication` and `MockCOMDocument` classes that simulate the COM API surface used by `COMBackend`
  - [ ] 7.3: Add `com_backend_with_mock` pytest fixture that monkeypatches `win32com.client.GetActiveObject` and `win32com.client.Dispatch` with `MockCOMApplication`
  - [ ] 7.4: Test `COMBackend.is_available()` returns `False` on non-Windows (always runs in CI)
  - [ ] 7.5: Mark remaining COM tests with `@pytest.mark.skipif(sys.platform != "win32", reason="COM backend Windows-only")`
  - [ ] 7.6: Test `COMBackend` is importable on all platforms (no `ImportError`)
  - [ ] 7.7: Test `_win32_only_guard()` raises `MCPError(BACKEND_UNAVAILABLE)` on non-Windows (using monkeypatch of `sys.platform`)
  - [ ] 7.8: Test that all Protocol methods exist on `COMBackend` (structural check without actually calling COM)

- [ ] Task 8: Verify ruff lint and CI compatibility (AC: 6, 8)
  - [ ] 8.1: Run `ruff check src/lcs_cad_mcp/backends/com_backend.py` — zero errors
  - [ ] 8.2: Run `pytest tests/unit/backends/test_com_backend.py -v` on macOS/Linux — only non-Windows tests run, all pass
  - [ ] 8.3: Run `pytest tests/unit/ -v` — no regressions from Stories 2-1 through 2-4

## Dev Notes

### Critical Architecture Constraints

1. **`pywin32` import is ONLY permitted in `backends/com_backend.py`** — same rule as ezdxf. All `import win32com` statements must be inside `if sys.platform == "win32":` blocks or inside function bodies with a platform guard.
2. **COM errors must NEVER crash the server** — Every COM API call must be wrapped in `try/except pywintypes.com_error`. A COM disconnection should result in `MCPError(BACKEND_UNAVAILABLE, recoverable=False)` — the server stays running and the ezdxf backend is still available.
3. **`is_available()` has a 2-second timeout** (NFR16) — `GetActiveObject` can hang if a CAD application is loading. Implement with `concurrent.futures.ThreadPoolExecutor(max_workers=1)` and `executor.submit(...).result(timeout=2.0)`. Catch `TimeoutError` and return `False`.
4. **COM constants** — AutoCAD COM uses integer constants for file formats, version codes, etc. Do NOT hardcode integer literals. Define a `_AcSaveAsType` dict at module level mapping string names to integer values. Document the source (AutoCAD ActiveX API reference).
5. **Snapshot strategy for COM** — There is no in-memory document object to serialise. The only safe strategy is a temp-file round-trip via the backend's `save_drawing` / `open_drawing`. This is slower than the ezdxf string strategy — acceptable per NFR8 (rollback is a rare recovery path).
6. **ZWCAD and BricsCAD COM ProgIDs differ from AutoCAD** — Try all three in `_connect_or_launch()`: `"AutoCAD.Application"`, `"ZwSoft.ZwCAD"`, `"BricscadApp.AcadApplication"`. Store which one connected in `self._com_progid` for logging.
7. **FORBIDDEN:** Do not instantiate `COMBackend` at module import time. `BackendFactory.get("com")` creates instances on demand only.

### Module/Component Notes

**`backends/com_backend.py` key structure:**

```python
"""COM backend — Windows-only AutoCAD/ZWCAD/BricsCAD automation via pywin32."""
from __future__ import annotations
import sys
import logging
import concurrent.futures
from typing import Any

from lcs_cad_mcp.backends.base import DrawingMetadata, LayerInfo, EntityInfo
from lcs_cad_mcp.errors import MCPError, ErrorCode

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    import win32com.client
    import pywintypes
else:
    win32com = None  # type: ignore
    pywintypes = None  # type: ignore

_COM_PROGIDS = ["AutoCAD.Application", "ZwSoft.ZwCAD", "BricscadApp.AcadApplication"]

_AcSaveAsType = {
    "dwg": 12,    # acNative (latest DWG)
    "dxf": 4,     # acDXF (generic DXF)
    "dxf2018": 4, # acDXF (version set separately if needed)
}

_CONNECT_TIMEOUT_SECONDS = 2.0


class COMBackend:
    """Implements CADBackend Protocol via Windows COM automation."""

    def __init__(self) -> None:
        self._app: Any | None = None
        self._doc: Any | None = None
        self._current_path: str | None = None
        self._com_progid: str | None = None

    def _win32_only_guard(self) -> None:
        if sys.platform != "win32":
            raise MCPError(
                code=ErrorCode.BACKEND_UNAVAILABLE,
                message="COM backend requires Windows",
                recoverable=False,
                suggested_action="Set CAD_BACKEND=ezdxf or run on Windows",
            )

    def is_available(self) -> bool:
        if sys.platform != "win32":
            return False
        def _check() -> bool:
            for progid in _COM_PROGIDS:
                try:
                    win32com.client.GetActiveObject(progid)
                    return True
                except pywintypes.com_error:
                    continue
            return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_check)
            try:
                return future.result(timeout=_CONNECT_TIMEOUT_SECONDS)
            except (concurrent.futures.TimeoutError, Exception):
                return False
```

**Snapshot dispatch in `session/snapshot.py`** (Task 6 addition):
```python
def take(self) -> str:
    # Dispatch on backend type for snapshot strategy
    from lcs_cad_mcp.backends.ezdxf_backend import EzdxfBackend
    from lcs_cad_mcp.backends.com_backend import COMBackend
    if isinstance(self._backend, EzdxfBackend):
        return self._take_ezdxf_snapshot()
    elif isinstance(self._backend, COMBackend):
        return self._take_com_snapshot()
    # fallback: no-op
    return ""
```

### Project Structure Notes

```
src/lcs_cad_mcp/
├── backends/
│   ├── __init__.py       # updated: register COMBackend (Windows-gated)
│   └── com_backend.py    # THIS STORY — full COM lifecycle
└── session/
    └── snapshot.py       # updated: COM snapshot strategy (Task 6)
tests/
└── unit/
    └── backends/
        └── test_com_backend.py   # THIS STORY
```

### Dependencies

- **Story 2-1** (CADBackend Protocol): `CADBackend` Protocol with all 19 method signatures; `BackendFactory` registration mechanism; `DrawingMetadata`, `LayerInfo`, `EntityInfo` models.
- **Story 2-2** (ezdxf lifecycle): `EzdxfBackend` pattern is the reference implementation; `COMBackend` must mirror the same public API.
- **Story 2-3** (metadata query): `list_layers`, `get_layer` patterns; COM equivalents follow the same return type contract.
- **Story 2-4** (snapshot/rollback): `SnapshotManager` is extended in this story to support the COM temp-file snapshot strategy.

### References

- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 2, Story 2-5]
- NFR16 (COM timeout), NFR10 (server availability): [Source: `_bmad-output/planning-artifacts/architecture.md`]
- pywin32 COM automation: https://pywin32.readthedocs.io/en/latest/
- AutoCAD ActiveX API reference: https://help.autodesk.com/view/OARX/2024/ENU/
- ZWCAD COM API: https://www.zwcad.com/developer/
- BricsCAD COM API: https://www.bricsys.com/en-US/bricscad/developer/

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/backends/com_backend.py`
- `src/lcs_cad_mcp/backends/__init__.py` (updated: COM registration)
- `src/lcs_cad_mcp/session/snapshot.py` (updated: COM snapshot strategy)
- `tests/unit/backends/test_com_backend.py`
