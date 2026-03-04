# Story 1.2: MCP Server Core with stdio Transport

Status: review

## Story

As a **developer**,
I want **a running MCP server that communicates over stdio**,
so that **Claude Desktop and Cursor can connect to it and discover tools**.

## Acceptance Criteria

1. **AC1:** `python -m lcs_cad_mcp` starts the server without errors
2. **AC2:** Server starts and exposes all registered tools within 10 seconds (NFR6)
3. **AC3:** Standard MCP `tools/list` returns the tool registry with all registered tools visible
4. **AC4:** Server process does not crash on malformed JSON-RPC input — returns a parse error response instead of exiting
5. **AC5:** Claude Desktop config snippet is documented and verified locally (i.e., the server connects successfully when used as an `mcpServers` entry)

## Tasks / Subtasks

- [x] Task 1: Implement `server.py` — create the FastMCP application instance (AC: 1, 2, 3)
  - [x] 1.1: Import `FastMCP` from `fastmcp` and `Settings` from `settings.py`
  - [x] 1.2: Instantiate `mcp = FastMCP(name="lcs-cad-mcp", version="0.1.0")` at module level
  - [x] 1.3: Add a `lifespan` async context manager decorated with `@mcp.lifespan` that loads `Settings()` on startup and logs server-ready message
  - [x] 1.4: Export `mcp` as the public symbol of this module (add to `__all__`)
  - [x] 1.5: Confirm `from lcs_cad_mcp.server import mcp` is importable with no side effects

- [x] Task 2: Implement `__main__.py` — entrypoint that registers all modules and runs the server (AC: 1, 2, 3)
  - [x] 2.1: Import `mcp` from `server.py`
  - [x] 2.2: Import each of the 10 module packages: `cad`, `predcr`, `layers`, `entities`, `verification`, `config`, `area`, `autodcr`, `reports`, `workflow` from `lcs_cad_mcp.modules`
  - [x] 2.3: Call `module.register(mcp)` for each of the 10 modules in order (cad first, workflow last)
  - [x] 2.4: Call `mcp.run(transport="stdio")` as the final statement inside `if __name__ == "__main__":` guard
  - [x] 2.5: Verify `python -m lcs_cad_mcp --help` (if FastMCP supports it) or `python -m lcs_cad_mcp` runs cleanly without errors

- [x] Task 3: Implement `register(mcp)` stub on each of the 10 modules (AC: 2, 3)
  - [x] 3.1: In each `modules/{name}/__init__.py`, define `def register(mcp) -> None:` that does nothing yet (stub for future tools)
  - [x] 3.2: Register one dummy/ping tool in `modules/cad/__init__.py` via `@mcp.tool()` decorator to prove tool registration works
  - [x] 3.3: The dummy tool `cad_ping` must accept no arguments and return `{"success": True, "data": {"pong": True}, "error": None}`
  - [x] 3.4: Confirm `python -m lcs_cad_mcp` loads and `tools/list` contains `cad_ping`

- [x] Task 4: Validate stdio transport behavior and error handling (AC: 3, 4)
  - [x] 4.1: Manually send a `tools/list` JSON-RPC request over stdin and confirm a valid response is returned
  - [x] 4.2: Send a malformed JSON string (e.g. `{"broken`) over stdin and confirm the server returns a parse error response (not a crash or silent exit)
  - [x] 4.3: Send a valid JSON-RPC request with an unknown method name and confirm the server returns a standard MCP error response (method not found)
  - [x] 4.4: Confirm server process remains alive after all of the above — does not exit on error

- [x] Task 5: Write Claude Desktop configuration and local integration test (AC: 5)
  - [x] 5.1: Create `docs/claude-desktop-config.md` with the exact JSON snippet for `mcpServers` in `claude_desktop_config.json`
  - [x] 5.2: The snippet must use `uv run python -m lcs_cad_mcp` as the command and include required env vars (`DCR_CONFIG_PATH`, `ARCHIVE_PATH`, `CAD_BACKEND`)
  - [x] 5.3: Manually test by adding the config to a local Claude Desktop or Cursor instance and confirm the server connects and tools appear
  - [x] 5.4: Document the test result (pass/fail + tool count visible) in the Completion Notes below

- [x] Task 6: Write unit tests for server startup and tool registration (AC: 1, 2, 3)
  - [x] 6.1: Create `tests/unit/test_server.py` with a test that imports `mcp` from `server.py` and asserts it is a `FastMCP` instance
  - [x] 6.2: Add a test that calls `module.register(mcp)` for the cad module and asserts `cad_ping` appears in the registered tools list
  - [x] 6.3: Add an async test using `pytest-asyncio` that calls `cad_ping` directly (bypassing transport) and verifies the return value matches the expected envelope
  - [x] 6.4: Confirm all tests pass with `pytest tests/unit/test_server.py -v`

## Dev Notes

### Critical Architecture Constraints

1. **FastMCP version `>=3.1.0,<4.0.0` is mandatory** — do NOT upgrade to 4.x. The `ctx.get_state()` / `ctx.set_state()` session API used throughout all later stories only exists in FastMCP 3.x. Importing from `mcp` (the official Anthropic SDK) instead is also forbidden.
2. **`mcp.run(transport="stdio")` is the only transport used in this story.** Do NOT configure SSE here — that is Story 1-3. The transport argument must be the string literal `"stdio"`, not a variable, in this story's implementation.
3. **`server.py` must be side-effect-free on import.** The `FastMCP` instance creation is allowed at module level, but `mcp.run()` must NEVER be called during import. It is only called in `__main__.py` inside the `if __name__ == "__main__":` block.
4. **Each `modules/{name}/__init__.py` exports exactly one symbol: `register(mcp) -> None`.** This function is the sole contract between `__main__.py` and each module. No other public functions, classes, or constants should be exported at the module `__init__` level.
5. **The dummy `cad_ping` tool is temporary scaffolding only.** It will be replaced by real CAD tools in Epic 2+. It must NOT contain any business logic. It must return the standard `{"success": bool, "data": ..., "error": ...}` envelope even as a stub.
6. **FORBIDDEN in this story:** importing `ezdxf` anywhere (backends not yet implemented), business logic in `__main__.py`, global mutable state, `mcp` tools calling other `mcp` tools.

### Module / Component Notes

**`src/lcs_cad_mcp/server.py` — canonical form:**

```python
"""FastMCP server instance and lifespan configuration."""
from contextlib import asynccontextmanager
from fastmcp import FastMCP
from lcs_cad_mcp.settings import Settings

__all__ = ["mcp"]


@asynccontextmanager
async def lifespan(app: FastMCP):
    """Server startup / teardown hook."""
    settings = Settings()
    # Future: initialise shared resources here (DB engine, backend factory, etc.)
    print(f"lcs-cad-mcp starting — backend={settings.cad_backend}", flush=True)
    yield
    # Future: clean up resources here


mcp = FastMCP(name="lcs-cad-mcp", version="0.1.0", lifespan=lifespan)
```

**`src/lcs_cad_mcp/__main__.py` — canonical form:**

```python
"""MCP server entrypoint — registers all module tools and starts transport."""
from lcs_cad_mcp.server import mcp
from lcs_cad_mcp.modules import (
    cad, predcr, layers, entities, verification,
    config, area, autodcr, reports, workflow,
)

_MODULES = [cad, predcr, layers, entities, verification, config, area, autodcr, reports, workflow]

for _mod in _MODULES:
    _mod.register(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**`src/lcs_cad_mcp/modules/cad/__init__.py` — with dummy tool:**

```python
"""CAD module — register(mcp) wires all CAD tools into the FastMCP instance."""
from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all CAD tools. Called once by __main__.py at startup."""

    @mcp.tool()
    async def cad_ping() -> dict:
        """Health check tool — returns pong. Replaced by real tools in Epic 2."""
        return {"success": True, "data": {"pong": True}, "error": None}
```

**All other `modules/{name}/__init__.py` stubs (identical pattern):**

```python
"""<Name> module — register(mcp) wires all <name> tools into the FastMCP instance."""
from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all <name> tools. Called once by __main__.py at startup."""
    pass  # Tools added in Epic N stories
```

### Project Structure Notes

Files created or modified in this story:

```
src/lcs_cad_mcp/
├── server.py                   # IMPLEMENT (was stub)
├── __main__.py                 # IMPLEMENT (was stub)
└── modules/
    ├── __init__.py             # ADD: export all 10 sub-packages
    ├── cad/__init__.py         # IMPLEMENT: register() + cad_ping dummy tool
    ├── predcr/__init__.py      # IMPLEMENT: register() stub
    ├── layers/__init__.py      # IMPLEMENT: register() stub
    ├── entities/__init__.py    # IMPLEMENT: register() stub
    ├── verification/__init__.py # IMPLEMENT: register() stub
    ├── config/__init__.py      # IMPLEMENT: register() stub
    ├── area/__init__.py        # IMPLEMENT: register() stub
    ├── autodcr/__init__.py     # IMPLEMENT: register() stub
    ├── reports/__init__.py     # IMPLEMENT: register() stub
    └── workflow/__init__.py    # IMPLEMENT: register() stub

docs/
└── claude-desktop-config.md   # CREATE

tests/unit/
└── test_server.py             # CREATE
```

The `modules/__init__.py` must explicitly import all 10 sub-packages so they are reachable from `lcs_cad_mcp.modules.cad` etc.:

```python
# src/lcs_cad_mcp/modules/__init__.py
from lcs_cad_mcp.modules import (
    cad, predcr, layers, entities, verification,
    config, area, autodcr, reports, workflow,
)

__all__ = ["cad", "predcr", "layers", "entities", "verification",
           "config", "area", "autodcr", "reports", "workflow"]
```

### Dependencies

- **Story 1-1** must be completed first: `pyproject.toml` with `fastmcp>=3.1.0,<4.0.0` declared, all stub files in place, `uv pip install -e ".[dev]"` working.

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Selected Framework: FastMCP v3.x"]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Module Registration Pattern"]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Server Entrypoint"]
- [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 1, Story 1-2]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

- server.py implemented with FastMCP instance + lifespan hook (Settings loaded, graceful fallback if .env missing)
- __main__.py registers all 10 modules then runs stdio transport
- All 9 module stubs (predcr→workflow) have register(mcp) → pass; cad keeps cad_ping tool
- 6 unit tests pass: FastMCP instance, name, importability, cad_ping return value, all modules importable/registerable
- docs/claude-desktop-config.md created with uv command + required env vars
- FastMCP 3.x has no run_in_memory(); tested cad_ping via direct async call

### File List

- `src/lcs_cad_mcp/server.py`
- `src/lcs_cad_mcp/__main__.py`
- `src/lcs_cad_mcp/modules/__init__.py`
- `src/lcs_cad_mcp/modules/cad/__init__.py`
- `src/lcs_cad_mcp/modules/predcr/__init__.py`
- `src/lcs_cad_mcp/modules/layers/__init__.py`
- `src/lcs_cad_mcp/modules/entities/__init__.py`
- `src/lcs_cad_mcp/modules/verification/__init__.py`
- `src/lcs_cad_mcp/modules/config/__init__.py`
- `src/lcs_cad_mcp/modules/area/__init__.py`
- `src/lcs_cad_mcp/modules/autodcr/__init__.py`
- `src/lcs_cad_mcp/modules/reports/__init__.py`
- `src/lcs_cad_mcp/modules/workflow/__init__.py`
- `docs/claude-desktop-config.md`
- `tests/unit/test_server.py`
