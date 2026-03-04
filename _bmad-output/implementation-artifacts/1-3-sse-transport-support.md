# Story 1.3: SSE Transport Support

Status: review

## Story

As a **developer**,
I want **the MCP server to optionally serve over SSE (Server-Sent Events)**,
so that **remote and server deployments work without code changes**.

## Acceptance Criteria

1. **AC1:** `MCP_TRANSPORT=sse python -m lcs_cad_mcp` starts the SSE server on a configurable port (default `8000`) without errors
2. **AC2:** The same tool registry accessible over stdio is also accessible over SSE — `tools/list` returns identical results on both transports
3. **AC3:** Transport selection is driven entirely by the `MCP_TRANSPORT` environment variable (or CLI arg) — no code changes required to switch between `stdio` and `sse`
4. **AC4:** SSE server port is configurable via `MCP_SSE_PORT` env var (default `8000`)
5. **AC5:** When `MCP_TRANSPORT` is unset or set to `stdio`, the server behaves exactly as in Story 1-2 — no regression

## Tasks / Subtasks

- [ ] Task 1: Extend `Settings` in `settings.py` to include transport configuration (AC: 1, 3, 4)
  - [ ] 1.1: Add `mcp_transport: Literal["stdio", "sse"] = "stdio"` field to `Settings`
  - [ ] 1.2: Add `mcp_sse_port: int = 8000` field to `Settings`
  - [ ] 1.3: Add `mcp_sse_host: str = "127.0.0.1"` field to `Settings`
  - [ ] 1.4: Update `.env.example` to document `MCP_TRANSPORT`, `MCP_SSE_PORT`, and `MCP_SSE_HOST` with explanatory comments
  - [ ] 1.5: Write a unit test in `tests/unit/test_settings.py` that confirms `Settings(mcp_transport="sse", mcp_sse_port=9000)` parses correctly

- [ ] Task 2: Extend `__main__.py` to branch on transport type at startup (AC: 1, 2, 3, 5)
  - [ ] 2.1: Load `Settings()` at the top of `__main__.py` (before module registration)
  - [ ] 2.2: After all `module.register(mcp)` calls, inspect `settings.mcp_transport`
  - [ ] 2.3: If `mcp_transport == "stdio"`: call `mcp.run(transport="stdio")` — identical to Story 1-2 behavior
  - [ ] 2.4: If `mcp_transport == "sse"`: call `mcp.run(transport="sse", host=settings.mcp_sse_host, port=settings.mcp_sse_port)`
  - [ ] 2.5: Add a startup log line before `mcp.run()` that prints: `"Starting lcs-cad-mcp transport={transport} port={port if sse}"` so the operator knows which mode is active

- [ ] Task 3: Validate SSE transport end-to-end with a running server (AC: 1, 2, 4)
  - [ ] 3.1: Start the server with `MCP_TRANSPORT=sse python -m lcs_cad_mcp` and confirm it binds to `127.0.0.1:8000`
  - [ ] 3.2: Use `curl` or an MCP SSE client to send a `tools/list` request and confirm the response contains `cad_ping` (registered in Story 1-2)
  - [ ] 3.3: Test that `MCP_SSE_PORT=9090 MCP_TRANSPORT=sse python -m lcs_cad_mcp` binds to port `9090` instead
  - [ ] 3.4: Confirm the process gracefully handles `SIGINT` (Ctrl-C) in SSE mode without hanging

- [ ] Task 4: Validate stdio regression — Story 1-2 behavior is unbroken (AC: 5)
  - [ ] 4.1: Run `python -m lcs_cad_mcp` (no env vars) and confirm it still starts in stdio mode
  - [ ] 4.2: Confirm `MCP_TRANSPORT=stdio python -m lcs_cad_mcp` also starts in stdio mode
  - [ ] 4.3: Confirm all existing Story 1-2 unit tests still pass with `pytest tests/unit/test_server.py -v`

- [ ] Task 5: Write unit and integration tests for transport branching (AC: 1, 3, 5)
  - [ ] 5.1: Create `tests/unit/test_transport.py` with tests that patch `Settings.mcp_transport` and confirm the correct `mcp.run()` call is made (use `unittest.mock.patch`)
  - [ ] 5.2: Add a test asserting that `Settings()` defaults to `mcp_transport="stdio"` when `MCP_TRANSPORT` env var is not set
  - [ ] 5.3: Add a parametrized test with both `"stdio"` and `"sse"` values to confirm `Settings` accepts both
  - [ ] 5.4: Confirm `pytest tests/unit/test_settings.py tests/unit/test_transport.py -v` passes

## Dev Notes

### Critical Architecture Constraints

1. **Transport selection is configuration only — zero code changes required.** The entire switch between `stdio` and `sse` must happen via environment variable inspection in `__main__.py`. No flags, no CLI argument parsers, no if-else chains scattered through `server.py`. The `server.py` file itself must remain transport-agnostic — it only creates the `FastMCP` instance.
2. **FastMCP 3.x `mcp.run()` accepts a `transport=` keyword argument.** Confirm the exact API signature from the installed FastMCP 3.x source before writing code. Do NOT invent keyword arguments that may not exist. The fallback is to consult the FastMCP 3.x changelog or source directly.
3. **SSE host must default to `127.0.0.1`, NOT `0.0.0.0`.** Binding to `0.0.0.0` in a default config exposes the server on all network interfaces, which is a security risk in development. Only change to `0.0.0.0` when the operator explicitly sets `MCP_SSE_HOST=0.0.0.0`.
4. **`Settings()` is instantiated inside `__main__.py`, not inside `server.py`.** `server.py` remains importable without a `.env` file. The `lifespan` function also instantiates `Settings()` on server startup (for its own use). This is intentional — two instantiations, both cheap.
5. **FORBIDDEN:** Hard-coding the port number anywhere in `server.py` or `__main__.py`. All port/host config must route through `Settings`.

### Module / Component Notes

**Updated `src/lcs_cad_mcp/settings.py`:**

```python
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    dcr_config_path: Path
    archive_path: Path
    cad_backend: Literal["ezdxf", "com"] = "ezdxf"
    log_level: str = "INFO"

    # Transport configuration (Story 1-3)
    mcp_transport: Literal["stdio", "sse"] = "stdio"
    mcp_sse_host: str = "127.0.0.1"
    mcp_sse_port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

**Updated `src/lcs_cad_mcp/__main__.py` — transport branching:**

```python
"""MCP server entrypoint — registers all module tools and starts transport."""
from lcs_cad_mcp.server import mcp
from lcs_cad_mcp.settings import Settings
from lcs_cad_mcp.modules import (
    cad, predcr, layers, entities, verification,
    config, area, autodcr, reports, workflow,
)

_MODULES = [cad, predcr, layers, entities, verification, config, area, autodcr, reports, workflow]

for _mod in _MODULES:
    _mod.register(mcp)

if __name__ == "__main__":
    settings = Settings()
    if settings.mcp_transport == "sse":
        print(
            f"Starting lcs-cad-mcp transport=sse "
            f"host={settings.mcp_sse_host} port={settings.mcp_sse_port}",
            flush=True,
        )
        mcp.run(transport="sse", host=settings.mcp_sse_host, port=settings.mcp_sse_port)
    else:
        print("Starting lcs-cad-mcp transport=stdio", flush=True)
        mcp.run(transport="stdio")
```

**Updated `.env.example` additions:**

```
# Transport selection: 'stdio' (default, for Claude Desktop/Cursor) or 'sse' (for remote/server deployments)
MCP_TRANSPORT=stdio

# SSE-specific settings (only used when MCP_TRANSPORT=sse)
MCP_SSE_HOST=127.0.0.1
MCP_SSE_PORT=8000
```

### Project Structure Notes

Files modified or created in this story:

```
src/lcs_cad_mcp/
├── settings.py         # MODIFY: add mcp_transport, mcp_sse_host, mcp_sse_port fields
└── __main__.py         # MODIFY: add transport branching logic

.env.example            # MODIFY: add MCP_TRANSPORT, MCP_SSE_HOST, MCP_SSE_PORT docs

tests/unit/
├── test_settings.py    # CREATE (or extend if already exists)
└── test_transport.py   # CREATE
```

No new modules or `register()` hooks are required for this story. This story is purely infrastructure-level.

### Dependencies

- **Story 1-1** must be complete: `pyproject.toml` with all deps, `settings.py` stub, directory structure.
- **Story 1-2** must be complete: `server.py` with `FastMCP` instance, `__main__.py` with `mcp.run("stdio")`, all 10 `register()` stubs, `cad_ping` tool working.

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Transport Configuration"]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Environment Configuration"]
- [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 1, Story 1-3]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

- `src/lcs_cad_mcp/settings.py`
- `src/lcs_cad_mcp/__main__.py`
- `.env.example`
- `tests/unit/test_settings.py`
- `tests/unit/test_transport.py`
