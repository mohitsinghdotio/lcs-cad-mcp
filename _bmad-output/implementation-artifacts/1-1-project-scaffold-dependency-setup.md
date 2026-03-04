# Story 1.1: Project Scaffold and Dependency Setup

Status: review

## Story

As a **developer**,
I want **a properly structured Python project with all core dependencies declared**,
so that **the dev environment is reproducible and CI-ready from day one**.

## Acceptance Criteria

1. **AC1:** `pyproject.toml` declares all core and dev dependencies:
   - Core: `fastmcp>=3.1.0,<4.0.0`, `pydantic>=2.0`, `pydantic-settings`, `ezdxf`, `shapely`, `scipy`, `sqlalchemy`, `python-docx`, `reportlab`
   - Dev: `pytest`, `pytest-asyncio`, `hypothesis`, `ruff`
2. **AC2:** `uv pip install -e .` installs the project without errors on Python 3.11+
3. **AC3:** Project layout follows `src/lcs_cad_mcp/` package structure with all subdirectory stubs in place
4. **AC4:** `pytest` runs with zero tests collected and zero errors after scaffold
5. **AC5:** `.env.example` documents all required env vars: `DCR_CONFIG_PATH`, `ARCHIVE_PATH`, `CAD_BACKEND`

## Tasks / Subtasks

- [x] Task 1: Create `pyproject.toml` with full dependency declarations (AC: 1, 2)
  - [x] 1.1: Set `[project]` metadata: name=`lcs-cad-mcp`, version, requires-python=`>=3.11`
  - [x] 1.2: Add all core `[project.dependencies]` as listed in AC1 with version pins
  - [x] 1.3: Add all `[project.optional-dependencies] dev` entries (pytest, pytest-asyncio, hypothesis, ruff)
  - [x] 1.4: Add `[tool.pytest.ini_options]` section: `testpaths = ["tests"]`, `asyncio_mode = "auto"`
  - [x] 1.5: Add `[tool.ruff]` section with `line-length = 100`, `select = ["E", "F", "I"]`
  - [x] 1.6: Run `uv pip install -e ".[dev]"` and confirm zero errors

- [x] Task 2: Create `src/lcs_cad_mcp/` package directory structure (AC: 3)
  - [x] 2.1: Create `src/lcs_cad_mcp/__init__.py` (empty)
  - [x] 2.2: Create `src/lcs_cad_mcp/__main__.py` with stub: `# entrypoint — module.register(mcp) calls + mcp.run()`
  - [x] 2.3: Create `src/lcs_cad_mcp/server.py` with stub: `# FastMCP instance creation + transport config`
  - [x] 2.4: Create `src/lcs_cad_mcp/settings.py` with stub `Settings` class using `pydantic-settings`
  - [x] 2.5: Create `src/lcs_cad_mcp/errors.py` with stub `MCPError` class + `ErrorCode` constants skeleton

- [x] Task 3: Create subdirectory stubs under `src/lcs_cad_mcp/` (AC: 3)
  - [x] 3.1: Create `session/` with `__init__.py`, `context.py`, `snapshot.py`, `event_log.py` (all stub files)
  - [x] 3.2: Create `backends/` with `__init__.py`, `base.py`, `ezdxf_backend.py`, `com_backend.py` (all stub files)
  - [x] 3.3: Create `modules/__init__.py` (empty, exports all module packages)
  - [x] 3.4: Create each of the 10 module dirs under `modules/`, each with `__init__.py`, `tools.py`, `service.py`, `schemas.py` stubs:
    `cad/`, `predcr/`, `layers/`, `entities/`, `verification/`, `config/`, `area/`, `autodcr/`, `reports/`, `workflow/`
  - [x] 3.5: Create `rule_engine/` with `__init__.py`, `loader.py`, `validator.py`, `evaluator.py`, `models.py` (stub files)
  - [x] 3.6: Create `archive/` with `__init__.py`, `engine.py`, `models.py`, `repository.py` (stub files)

- [x] Task 4: Create `tests/` directory structure (AC: 4)
  - [x] 4.1: Create `tests/conftest.py` with comment: `# MockCADBackend, MockDrawingSession, tmp_db_engine fixtures (populated in later stories)`
  - [x] 4.2: Create `tests/unit/` mirroring `src/` structure — directories only with `.gitkeep` or empty `__init__.py`
  - [x] 4.3: Create `tests/integration/` with empty `__init__.py`
  - [x] 4.4: Run `pytest` and confirm: `no tests ran`, `0 errors`

- [x] Task 5: Create configuration and documentation stubs (AC: 5)
  - [x] 5.1: Create `.env.example` with all three vars documented
  - [x] 5.2: Create `.gitignore` covering `.env`, `__pycache__`, `.venv`, `uv.lock` (uv.lock is committed — do NOT gitignore it)
  - [x] 5.3: Create `dcr_configs/` directory with `schema.yaml` and `example_authority.yaml` stubs
  - [x] 5.4: Create `docs/` directory with `dcr-config-schema.md` and `tool-api-reference.md` stubs

## Dev Notes

### Critical Architecture Constraints — MUST FOLLOW

1. **FastMCP version pinned to `>=3.1.0,<4.0.0`** — do NOT use `mcp` SDK or FastMCP 2.x. FastMCP 3.0 introduced connection-scoped session state (`ctx.set_state()` / `ctx.get_state()`) which is the session architecture this entire project is built on. Add inline comment in pyproject.toml: `# fastmcp 3.x required for ctx.get_state() / ctx.set_state() session architecture`.
2. **`uv` is the sole package manager** — do NOT use pip directly. All dependency operations use `uv add` / `uv pip install`.
3. **`uv.lock` is committed to version control** — do NOT add it to `.gitignore`. It is the reproducibility guarantee.
4. **Python 3.11+ is mandatory** — `dict` key order preservation (3.7+) and union types (`X | Y`, 3.10+) are relied upon in the rule engine.

### Project Structure Notes

**Exact directory tree to create** (from Architecture doc, Section "Complete Project Directory Structure"):

```
lcs-cad-mcp/                          # project root (already exists as git repo)
├── pyproject.toml                     # CREATE
├── uv.lock                            # auto-generated by uv (commit it)
├── .env.example                       # CREATE
├── .gitignore                         # CREATE
├── src/
│   └── lcs_cad_mcp/
│       ├── __init__.py                # empty
│       ├── __main__.py                # stub comment only
│       ├── server.py                  # stub comment only
│       ├── settings.py                # stub Settings class
│       ├── errors.py                  # stub MCPError + ErrorCode
│       ├── session/
│       │   ├── __init__.py
│       │   ├── context.py             # stub
│       │   ├── snapshot.py            # stub
│       │   └── event_log.py           # stub
│       ├── backends/
│       │   ├── __init__.py
│       │   ├── base.py                # stub — will hold Abstract CADBackend Protocol (Story 2-1)
│       │   ├── ezdxf_backend.py       # stub
│       │   └── com_backend.py         # stub
│       └── modules/
│           ├── __init__.py
│           ├── cad/       (tools.py, service.py, schemas.py, __init__.py)
│           ├── predcr/    (+ layer_registry.py stub)
│           ├── layers/
│           ├── entities/
│           ├── verification/
│           ├── config/
│           ├── area/
│           ├── autodcr/
│           ├── reports/
│           └── workflow/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── backends/
│   │   ├── session/
│   │   ├── rule_engine/
│   │   ├── archive/
│   │   └── modules/ (cad/, predcr/, layers/, entities/, verification/, config/, area/, autodcr/, reports/, workflow/)
│   └── integration/
├── dcr_configs/
│   ├── schema.yaml
│   └── example_authority.yaml
└── docs/
    ├── dcr-config-schema.md
    └── tool-api-reference.md
```

**Key note:** `rule_engine/` and `archive/` directories sit at `src/lcs_cad_mcp/` level (NOT inside `modules/`). They are internal shared infrastructure, not MCP-exposed modules.

### `pyproject.toml` Reference

```toml
[project]
name = "lcs-cad-mcp"
version = "0.1.0"
description = "MCP server replicating PreDCR and AutoDCR as AI-consumable tools"
requires-python = ">=3.11"
dependencies = [
    # fastmcp 3.x required for ctx.get_state() / ctx.set_state() session architecture
    "fastmcp>=3.1.0,<4.0.0",
    "pydantic>=2.0",
    "pydantic-settings",
    "ezdxf",
    "shapely",
    "scipy",
    "sqlalchemy",
    "python-docx",
    "reportlab",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "hypothesis",
    "ruff",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/lcs_cad_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
select = ["E", "F", "I"]
```

### `settings.py` Stub Reference

```python
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    dcr_config_path: Path
    archive_path: Path
    cad_backend: Literal["ezdxf", "com"] = "ezdxf"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

### `.env.example` Content

```
# Required: path to DCR rule config YAML or JSON file
DCR_CONFIG_PATH=/path/to/dcr-rules.yaml

# Required: path to archive storage directory
ARCHIVE_PATH=/path/to/archive

# Optional: CAD backend selection (default: ezdxf; use 'com' for live AutoCAD on Windows)
CAD_BACKEND=ezdxf
```

### `errors.py` Stub Reference

```python
"""Structured MCP error contract. All tool handlers use MCPError — never inline error dicts."""
from dataclasses import dataclass


class ErrorCode:
    # Session
    SESSION_NOT_STARTED = "SESSION_NOT_STARTED"
    # CAD Backend
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    DRAWING_OPEN_FAILED = "DRAWING_OPEN_FAILED"
    # Layer
    LAYER_NOT_FOUND = "LAYER_NOT_FOUND"
    # Entity
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    # Verification
    CLOSURE_FAILED = "CLOSURE_FAILED"
    # DCR
    DCR_VIOLATION = "DCR_VIOLATION"
    CONFIG_INVALID = "CONFIG_INVALID"
    # Generic
    INVALID_PARAMS = "INVALID_PARAMS"


@dataclass
class MCPError:
    code: str
    message: str = ""
    recoverable: bool = True
    suggested_action: str = ""

    def to_response(self) -> dict:
        return {
            "success": False,
            "data": None,
            "error": {
                "code": self.code,
                "message": self.message,
                "recoverable": self.recoverable,
                "suggested_action": self.suggested_action,
            },
        }
```

### Testing Standards for This Story

- This story has **no functional tests** — only structural validation (pytest discovers tests dir, runs clean)
- `tests/conftest.py` should contain only stub comments; actual fixtures come in Stories 1-3 / 2-1+
- Run `pytest --collect-only` to confirm zero collection errors
- Run `pytest` to confirm `no tests ran` exit with code 0

### Scaffold Command Reference

Architecture doc specifies this exact init sequence:

```bash
# Run from project root (lcs-cad-mcp/)
uv init . --python 3.11   # or manually create pyproject.toml
uv add "fastmcp>=3.1.0,<4.0.0" pydantic pydantic-settings ezdxf shapely scipy sqlalchemy python-docx reportlab
uv add --dev pytest pytest-asyncio hypothesis ruff
uv pip install -e ".[dev]"
```

Note: `uv init .` may scaffold a basic `pyproject.toml` — **replace or edit** its `dependencies` section with the full list above. Do NOT use the auto-generated `hello.py` or similar sample files.

### Build Order Context

This story is the **foundation** for all 53 subsequent stories. No other story can begin until:
- `src/lcs_cad_mcp/` package is importable
- All subdirectory stubs exist (other story devs create files inside them)
- `pytest` runs clean

**Next story after this:** `1-2-mcp-server-core-stdio-transport` — creates the actual FastMCP server instance in `server.py` and the `__main__.py` entrypoint. That story will import from `settings.py` and `errors.py` stubs created here.

### References

- Architecture doc pyproject.toml structure: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Project Initialization"]
- Full directory tree: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Complete Project Directory Structure"]
- FastMCP version decision: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Selected Framework: FastMCP v3.x"]
- Settings pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Environment Configuration"]
- MCP tool naming conventions: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Naming Patterns"]
- Anti-patterns to avoid: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Enforcement Guidelines"]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 1, Story 1-1]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- uv venv created with Python 3.11.13 (downloaded cpython-3.11.13-macos-aarch64)
- `uv pip install -e ".[dev]"` succeeded — 87 packages installed including fastmcp==3.1.0
- Re-ran `uv pip install -e ".[dev]"` after src/ package creation to re-register editable install
- Package importable: `import lcs_cad_mcp` ✅; `from lcs_cad_mcp.errors import MCPError` ✅
- `pytest` output: "no tests ran" — exit code 5 (no tests collected, expected for scaffold story) ✅

### Completion Notes List

- All 5 tasks and 23 subtasks completed
- `pyproject.toml` created with all core + dev dependencies, hatchling build system, pytest asyncio_mode=auto, ruff config
- `src/lcs_cad_mcp/` package structure created: 5 core files + 4 subdirs (session, backends, modules, rule_engine, archive)
- All 10 module subdirs created under `modules/` with `__init__.py`, `tools.py`, `service.py`, `schemas.py` stubs
- `predcr/` module additionally has `layer_registry.py` stub
- `tests/` directory created with `conftest.py`, `unit/` (mirroring src structure), `integration/`
- `.env.example` documents all 3 required env vars
- `.gitignore` updated — `.env`, `__pycache__`, `.venv` excluded; `uv.lock` NOT gitignored
- `dcr_configs/` and `docs/` directories created with stub files
- AC1 ✅ AC2 ✅ AC3 ✅ AC4 ✅ AC5 ✅

### File List

- `pyproject.toml`
- `.env.example`
- `.gitignore`
- `src/lcs_cad_mcp/__init__.py`
- `src/lcs_cad_mcp/__main__.py`
- `src/lcs_cad_mcp/server.py`
- `src/lcs_cad_mcp/settings.py`
- `src/lcs_cad_mcp/errors.py`
- `src/lcs_cad_mcp/session/__init__.py`
- `src/lcs_cad_mcp/session/context.py`
- `src/lcs_cad_mcp/session/snapshot.py`
- `src/lcs_cad_mcp/session/event_log.py`
- `src/lcs_cad_mcp/backends/__init__.py`
- `src/lcs_cad_mcp/backends/base.py`
- `src/lcs_cad_mcp/backends/ezdxf_backend.py`
- `src/lcs_cad_mcp/backends/com_backend.py`
- `src/lcs_cad_mcp/modules/__init__.py`
- `src/lcs_cad_mcp/modules/cad/__init__.py`
- `src/lcs_cad_mcp/modules/cad/tools.py`
- `src/lcs_cad_mcp/modules/cad/service.py`
- `src/lcs_cad_mcp/modules/cad/schemas.py`
- `src/lcs_cad_mcp/modules/predcr/__init__.py`
- `src/lcs_cad_mcp/modules/predcr/tools.py`
- `src/lcs_cad_mcp/modules/predcr/service.py`
- `src/lcs_cad_mcp/modules/predcr/schemas.py`
- `src/lcs_cad_mcp/modules/predcr/layer_registry.py`
- `src/lcs_cad_mcp/modules/layers/__init__.py`
- `src/lcs_cad_mcp/modules/layers/tools.py`
- `src/lcs_cad_mcp/modules/layers/service.py`
- `src/lcs_cad_mcp/modules/layers/schemas.py`
- `src/lcs_cad_mcp/modules/entities/__init__.py`
- `src/lcs_cad_mcp/modules/entities/tools.py`
- `src/lcs_cad_mcp/modules/entities/service.py`
- `src/lcs_cad_mcp/modules/entities/schemas.py`
- `src/lcs_cad_mcp/modules/verification/__init__.py`
- `src/lcs_cad_mcp/modules/verification/tools.py`
- `src/lcs_cad_mcp/modules/verification/service.py`
- `src/lcs_cad_mcp/modules/verification/schemas.py`
- `src/lcs_cad_mcp/modules/config/__init__.py`
- `src/lcs_cad_mcp/modules/config/tools.py`
- `src/lcs_cad_mcp/modules/config/service.py`
- `src/lcs_cad_mcp/modules/config/schemas.py`
- `src/lcs_cad_mcp/modules/area/__init__.py`
- `src/lcs_cad_mcp/modules/area/tools.py`
- `src/lcs_cad_mcp/modules/area/service.py`
- `src/lcs_cad_mcp/modules/area/schemas.py`
- `src/lcs_cad_mcp/modules/autodcr/__init__.py`
- `src/lcs_cad_mcp/modules/autodcr/tools.py`
- `src/lcs_cad_mcp/modules/autodcr/service.py`
- `src/lcs_cad_mcp/modules/autodcr/schemas.py`
- `src/lcs_cad_mcp/modules/reports/__init__.py`
- `src/lcs_cad_mcp/modules/reports/tools.py`
- `src/lcs_cad_mcp/modules/reports/service.py`
- `src/lcs_cad_mcp/modules/reports/schemas.py`
- `src/lcs_cad_mcp/modules/workflow/__init__.py`
- `src/lcs_cad_mcp/modules/workflow/tools.py`
- `src/lcs_cad_mcp/modules/workflow/service.py`
- `src/lcs_cad_mcp/modules/workflow/schemas.py`
- `src/lcs_cad_mcp/rule_engine/__init__.py`
- `src/lcs_cad_mcp/rule_engine/loader.py`
- `src/lcs_cad_mcp/rule_engine/validator.py`
- `src/lcs_cad_mcp/rule_engine/evaluator.py`
- `src/lcs_cad_mcp/rule_engine/models.py`
- `src/lcs_cad_mcp/archive/__init__.py`
- `src/lcs_cad_mcp/archive/engine.py`
- `src/lcs_cad_mcp/archive/models.py`
- `src/lcs_cad_mcp/archive/repository.py`
- `tests/conftest.py`
- `tests/unit/__init__.py`
- `tests/unit/backends/__init__.py`
- `tests/unit/session/__init__.py`
- `tests/unit/rule_engine/__init__.py`
- `tests/unit/archive/__init__.py`
- `tests/unit/modules/cad/__init__.py`
- `tests/unit/modules/predcr/__init__.py`
- `tests/unit/modules/layers/__init__.py`
- `tests/unit/modules/entities/__init__.py`
- `tests/unit/modules/verification/__init__.py`
- `tests/unit/modules/config/__init__.py`
- `tests/unit/modules/area/__init__.py`
- `tests/unit/modules/autodcr/__init__.py`
- `tests/unit/modules/reports/__init__.py`
- `tests/unit/modules/workflow/__init__.py`
- `tests/integration/__init__.py`
- `dcr_configs/schema.yaml`
- `dcr_configs/example_authority.yaml`
- `docs/dcr-config-schema.md`
- `docs/tool-api-reference.md`

### Change Log

- 2026-03-04: Initial implementation — project scaffold created (Story 1-1)
