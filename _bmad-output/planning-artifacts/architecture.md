---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'step-06-structure', 'step-07-validation', 'step-08-complete']
inputDocuments:
  - prd.md
workflowType: 'architecture'
project_name: 'lcs-cad-mcp'
user_name: 'Mohit.singh2'
date: '2026-03-04'
lastStep: 8
status: 'complete'
completedAt: '2026-03-04'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:** 45 FRs across 8 modules:
- Drawing Management (FR1–5): Open, create, save, query, backend-select
- PreDCR Drawing Preparation (FR6–12): Layer creation, entity drawing, naming, modification
- Verification (FR13–18): Closure, containment, naming, minimum entity checks
- DCR Compliance Scrutiny (FR19–26): Rule loading, area computation, scrutiny pass, iterative correction
- Report Generation (FR27–31): PDF/DOCX/JSON reports, metadata, remediation hints
- Workflow Orchestration & Audit (FR32–36): Archival, retrieval, audit trail, rollback, end-to-end pipeline
- MCP Protocol & Integration (FR37–41): stdio/SSE transport, validation, structured errors, tool discovery
- System Configuration (FR42–45): Config via env vars, headless operation

**Non-Functional Requirements:** 24 NFRs across 6 dimensions:
- Performance: Single tool <2s, full PreDCR <60s, full scrutiny <30s, server startup <10s
- Data Integrity: Atomic writes, automatic rollback, ACID archival, corruption recovery
- Correctness: Area accuracy ±0.01 sqm, FSI to 3 decimal places, fully reproducible scrutiny
- Reliability: Tool failure isolation, COM loss detection with ezdxf fallback, structured validation errors
- Integration: Claude Desktop/Cursor/VS Code compatibility, AutoCAD 2018+ DXF, Pydantic-validated configs
- Security: Local-only data, read-only config during scrutiny, no auth for MVP

**Scale & Complexity:**
- Primary domain: Backend MCP server / developer tooling
- Complexity level: High — CAD automation, dual backends, geometry engine, regulatory rule engine, consequence-bearing compliance outputs
- Estimated architectural components: ~13 major components

### Technical Constraints & Dependencies

- **Python 3.11+** — runtime requirement
- **COM backend is Windows-only** — pywin32/pyautocad; deployment constraint for live AutoCAD mode. ezdxf reaches full parity FIRST; COM is an enhancement layer, not the foundation.
- **ezdxf backend is cross-platform** — primary development and test target
- **MCP protocol** — stdio (primary, local), SSE (secondary, remote); JSON-RPC 2.0
- **MCP is stateless at the protocol level** — session statefulness (current drawing context, rollback snapshots) is application-layer responsibility; must be explicitly designed
- **No external services** — all data stored locally; SQLite for archival; no cloud dependency
- **DXF/DWG output** — AutoCAD 2018 / DXF R2018 format default; configurable
- **Single developer** — modular build order with mock interfaces between modules is critical

### Cross-Cutting Concerns Identified

1. **Drawing State Management (First-Class Component)** — The hardest architectural problem in the system. Every tool reads or writes drawing state. "What is the current drawing?" must be answered by an explicit Session/Context object: current drawing reference, last-valid snapshot for rollback, and session metadata. All modules share this context; none own it. Must be designed before any module build begins.

2. **CAD Backend Abstraction** — A unified interface layer sits between all 60+ tools and the two backends. No module calls COM or ezdxf APIs directly. Designed around ezdxf's capabilities first.

3. **ToolRegistry Pattern** — All 60+ tools register their schema, handler, and module ownership at server startup via a central registry. Enables: consistent MCP dispatch, isolated module testing with mock backends, startup validation, and maintainable server entrypoint.

4. **Pydantic v2 Validation** — All MCP tool parameters validated via registered schemas before execution; validation errors return structured error responses, not exceptions.

5. **Structured Error Contract** — Every tool returns `{success, data, error{code, message, recoverable, suggested_action}}`; enforced uniformly across all 60+ tools.

6. **Audit Trail as Legal Artifact (Event Sourcing)** — Every tool invocation in a scrutiny run (tool name, params, outcome, timestamp, drawing state delta) is recorded as a reconstructible event log, not application logging. This is a legal defensibility requirement, not a debugging aid.

7. **Rule Engine Evaluation Pipeline** — The DCR rule engine needs explicit internal design: rule parse → validate → evaluate (order, independence vs. composition, violation categorization) → record. Rule evaluation reproducibility (NFR13) requires deterministic evaluation order.

8. **Config Management** — DCR_CONFIG_PATH, ARCHIVE_PATH, CAD_BACKEND resolved from environment at startup; no hardcoded paths. Rule config version (hash) captured at load, recorded per run.

9. **SQLite Single Point of Failure (Open Question)** — SQLite is the designated legal artifact store. Backup/recovery model for the archive is an open architectural decision. Acceptable for MVP scope, but must be explicitly decided and documented.

## Starter Template Evaluation

### Primary Technology Domain

Python MCP server — no conventional web starter templates apply. The foundational
scaffold decisions are: MCP framework selection and uv-based project structure.

### MCP Framework Options Considered

**Option A: Official `mcp` SDK (v2.6.1)**
- Anthropic's official Python SDK for MCP servers and clients
- FastMCP 1.0 was absorbed into the official SDK; low-level server primitives available
- Supports Streamable HTTP, Elicitation, Tool Output Schemas (MCP spec 2025-11-25)
- More verbose tool registration; requires more boilerplate per tool
- PyPI: `mcp`

**Option B: FastMCP 2.10.x (stable)**
- Full MCP spec 2025-11-25 compliance; battle-tested; stable API
- Decorator-based tool registration with minimal boilerplate
- Session state via module-level context object (manually managed)
- Lower risk for a compliance-critical system with legal-artifact outputs

**Option C: FastMCP 3.x (selected)**
- Powers ~70% of MCP servers; 1M+ daily downloads
- FastMCP 3.0 (Jan 2026): components, providers, transforms, native session state
- Session state persistence via `ctx.set_state()` / `ctx.get_state()` — connection-scoped,
  safe under sequential tool calls, architecturally cleaner than module-level singletons
- OpenTelemetry instrumentation built-in
- Granular authorization and dynamic component enable/disable per client
- Full MCP spec 2025-11-25 compliance
- PyPI: `fastmcp`

### Selected Framework: FastMCP v3.x

**Rationale:**
- **Connection-scoped session state** (`ctx.set_state()` / `ctx.get_state()`) directly
  addresses Drawing State Management — state is scoped to the MCP connection, not global,
  preventing cross-session contamination. A module-level singleton in 2.x would be fragile.
- **Decorator-based registration** (`@mcp.tool`) keeps 60+ tool definitions clean and
  module-owned without a monolithic server entrypoint.
- **OpenTelemetry built-in** provides the instrumentation layer for the legal audit trail
  without custom middleware.
- **Dominant ecosystem choice** maximizes compatibility confidence with Claude Desktop,
  Cursor, VS Code Copilot.

**Version Pinning Decision:** `fastmcp>=3.1.0,<4.0.0`
FastMCP 3.0 was released January 2026 — recent, but minor versions are stable within the
constraint. Pinning below 4.0 avoids breaking API changes. Upgrade path: evaluate 4.x
once it releases and has 2+ months of community production usage. Document this pin in
pyproject.toml with an inline comment.

**Build-Order Constraint:** `backends/base.py` (the abstract CAD backend interface) is the
FIRST file written in the project. All 10 modules depend on this contract. No module
implementation begins until this interface is stable and reviewed.

### Project Initialization

**Scaffold command (uv + FastMCP):**

```bash
uv init lcs-cad-mcp --python 3.11
cd lcs-cad-mcp
uv add "fastmcp>=3.1.0,<4.0.0" pydantic ezdxf shapely scipy sqlalchemy python-docx reportlab
uv add --dev pytest pytest-asyncio hypothesis ruff
```

**Project structure:**

```
lcs-cad-mcp/
├── pyproject.toml              # uv-managed; fastmcp pinned >=3.1.0,<4.0.0
├── src/
│   └── lcs_cad_mcp/
│       ├── __main__.py         # server entrypoint; registers all module tools
│       ├── server.py           # FastMCP server instance + startup config
│       ├── session/            # DrawingSession — first-class component
│       │   ├── context.py      # DrawingSession object; current drawing ref + metadata
│       │   ├── snapshot.py     # Last-valid-state snapshot for rollback
│       │   └── event_log.py    # Per-session event log → persists to SQLite on write
│       ├── backends/           # CAD backend abstraction — FIRST module built
│       │   ├── base.py         # Abstract CADBackend interface (defines contract for all modules)
│       │   ├── ezdxf_backend.py  # Primary; cross-platform; all modules built against this
│       │   └── com_backend.py    # Windows-only enhancement; secondary priority
│       ├── modules/            # 10 feature modules, each registers its own tools
│       │   ├── cad/
│       │   ├── predcr/
│       │   ├── layers/
│       │   ├── entities/
│       │   ├── verification/
│       │   ├── autodcr/
│       │   ├── config/
│       │   ├── area/
│       │   ├── reports/
│       │   └── workflow/
│       ├── rule_engine/        # DCR rule parsing + deterministic evaluation pipeline
│       ├── archive/            # SQLite + SQLAlchemy; ACID archival + event log persistence
│       └── errors.py           # Structured error contract types
└── tests/
    ├── conftest.py             # Shared fixtures: MockCADBackend, MockDrawingSession
    ├── unit/
    │   └── modules/            # Mirrors src/modules/ structure exactly
    │       ├── cad/
    │       ├── predcr/
    │       ├── layers/
    │       ├── entities/
    │       ├── verification/
    │       ├── autodcr/
    │       ├── config/
    │       ├── area/
    │       ├── reports/
    │       └── workflow/
    └── integration/            # End-to-end pipeline tests
```

**Key structural decisions:**
- `session/` is a module, not a file — `DrawingSession` is too complex for a single file
- `event_log.py` writes to SQLite via the archive layer — survives server crash mid-scrutiny
- Test structure mirrors module structure exactly — scales cleanly to 200+ test files
- `conftest.py` at root of tests — `MockCADBackend` and `MockDrawingSession` fixtures
  shared across all unit tests; no module needs to redefine test infrastructure

**Architectural Decisions Provided by This Setup:**

- **Language & Runtime:** Python 3.11+, src layout, uv package management
- **MCP Framework:** FastMCP 3.x (pinned >=3.1.0,<4.0.0) — connection-scoped session state, decorator registration, OTel
- **Validation:** Pydantic v2 (all tool params and data models)
- **CAD (headless):** ezdxf — primary; all modules developed against this first
- **CAD (live):** COM/pywin32 — Windows-only enhancement; secondary priority
- **Geometry:** Shapely + scipy — area/FSI computation
- **Archival:** SQLite + SQLAlchemy — ACID transactions; event log persistence
- **Reports:** ReportLab (PDF), python-docx (DOCX)
- **Testing:** pytest + pytest-asyncio + hypothesis; shared conftest fixtures
- **Linting:** ruff (replaces flake8 + black + isort)

**Note:** Project initialization using the scaffold command above should be the
first implementation story (Epic 1, Story 1). `backends/base.py` should be the
second story before any module work begins.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- DrawingSession lifecycle model (explicit via workflow tools)
- Drawing rollback mechanism (hybrid: in-memory + phase-boundary disk checkpoints)
- Environment configuration approach (pydantic-settings, startup validation)
- Rule engine evaluation order (declaration order, deterministic)

**Important Decisions (Shape Architecture):**
- SQLAlchemy usage: ORM + startup schema creation (no Alembic for MVP)
- Logging/observability: FastMCP OTel + stdlib logging

**Deferred Decisions (Post-MVP):**
- Alembic migrations (Phase 2, when multi-instance deployment begins)
- structlog (add when debugging complexity warrants it)

### Data Architecture

**SQLAlchemy Usage:** ORM with startup schema creation
- Model classes: `ScrutinyRun`, `ToolEvent`, `ConfigVersion`, `ArchiveRecord`, `Session`
- Schema initialized via `Base.metadata.create_all(engine)` at server startup
- `IF NOT EXISTS` semantics ensure idempotent startup
- No migration framework for MVP; schema changes require manual DB reset during development
- **Upgrade path:** Add Alembic in Phase 2 when deployed instances require schema evolution
- **Rationale:** Single developer, local SQLite, greenfield — migration overhead not justified

**Archive Schema (core tables):**
- `sessions` — session_id, project_name, started_at, ended_at, status
- `tool_events` — event_id, session_id, tool_name, params_json, outcome, timestamp
- `scrutiny_runs` — run_id, session_id, config_version_hash, drawing_path, started_at, completed_at
- `rule_results` — result_id, run_id, rule_id, status (pass/fail/deviation), computed, permissible
- `config_versions` — version_hash, file_path, loaded_at, content_snapshot
- `reports` — report_id, run_id, format (pdf/docx/json), file_path, generated_at

### Session Lifecycle

**Model:** Explicit session boundaries via workflow tools
- `workflow_start(project_name)` → creates `DrawingSession`, opens archive session record,
  begins event log. Must be called before any drawing operation.
- `workflow_end()` → flushes event log to SQLite, closes archive session record, clears
  in-memory session state. Connection cleanup also triggers end if not explicitly called.
- `DrawingSession` holds: session_id, project_name, current drawing reference, in-memory
  rollback snapshot, disk checkpoint paths, event buffer
- **1:1 mapping:** one session = one archive record = one event log = one scrutiny run chain
- **AI client contract:** `workflow_start` is the required first tool call for any pipeline.
  Calling drawing tools without an active session returns a structured error:
  `SESSION_NOT_STARTED / recoverable: false`

### Drawing Rollback Mechanism

**Model:** Hybrid — in-memory for per-operation speed; disk checkpoint at phase boundaries

**In-memory rollback (all write operations):**
- Before any entity/layer write: deep-copy the ezdxf `Drawing` object in memory
- On `recoverable: false` error: swap back to the in-memory copy
- Fast (no disk I/O); sufficient for single-operation failures

**Disk checkpoint (phase boundaries):**
- Written before `autodcr_run_scrutiny` begins → `{ARCHIVE_PATH}/checkpoints/{session_id}_pre_scrutiny.dxf`
- Written before `cad_save_drawing` / `cad_export_drawing` → `{ARCHIVE_PATH}/checkpoints/{session_id}_pre_save.dxf`
- On server restart/crash: checkpoint file is the recovery artifact (satisfies NFR10)
- Checkpoint files are cleaned up after successful session end

**Rationale:** In-memory rollback handles the common case (tool failure mid-edit) with no I/O
overhead. Disk checkpoints protect against server crashes at the highest-risk phase boundaries.

### Environment Configuration

**Approach:** `pydantic-settings` — typed `Settings` class, validates at startup

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    dcr_config_path: Path
    archive_path: Path
    cad_backend: Literal["ezdxf", "com"] = "ezdxf"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

- Reads from OS env vars first, `.env` file as fallback
- Server fails fast with a clear `ValidationError` if required fields are missing
- `CAD_BACKEND` defaults to `ezdxf` — safe default, no AutoCAD required
- **Updated scaffold command:** Add `pydantic-settings` to initialization:
  `uv add "fastmcp>=3.1.0,<4.0.0" pydantic pydantic-settings ezdxf shapely scipy sqlalchemy python-docx reportlab`

### Logging & Observability

**Approach:** FastMCP OpenTelemetry (built-in) + Python stdlib `logging`

- **OTel:** FastMCP emits spans per tool call — tool name, params, duration, outcome.
  Provides machine-readable traces for the legal audit trail and performance monitoring.
- **stdlib logging:** Module-level `logger = logging.getLogger(__name__)` for human-readable
  debug/info output during development. Log level controlled via `Settings.log_level`.
- **No structlog for MVP** — add in Phase 2 when structured log querying is needed.
- **Log format:** JSON-structured when `LOG_LEVEL=INFO` or higher (production);
  human-readable when `LOG_LEVEL=DEBUG` (development).

### Rule Engine Evaluation Order

**Decision:** Config declaration order — rules evaluated in the order they appear in the
YAML/JSON config file.

- Python `dict` preserves insertion order (3.7+); PyYAML preserves YAML key order by default
- Config authors control evaluation sequence; what you write is what runs
- **Constraint:** Config tooling and serializers must preserve key order — document this
  explicitly in the DCR config schema spec
- **Reproducibility guarantee (NFR13):** Same config file + same drawing = same evaluation
  order = same results. Config file content hash is stored with every scrutiny run.

### Decision Impact Analysis

**Implementation Sequence (order matters):**
1. `pydantic-settings` Settings class — validates deployment before any code runs
2. `backends/base.py` abstract CADBackend interface — contract everything depends on
3. `session/` module (context, snapshot, event_log) — shared state used by all modules
4. `archive/` module (SQLAlchemy models + `create_all`) — event log persistence target
5. `backends/ezdxf_backend.py` — primary backend implementation
6. Feature modules (in PRD build order): cad → predcr → verification → area → autodcr → reports → workflow
7. `backends/com_backend.py` — after all modules tested against ezdxf

**Cross-Component Dependencies:**
- All modules → session/ (read/write DrawingSession)
- All modules → backends/base.py (CADBackend interface)
- session/event_log → archive/ (SQLite persistence)
- workflow/ → all other modules (orchestrates end-to-end pipeline)
- rule_engine/ → archive/config_versions (version hash recording)
- autodcr/ → rule_engine/ + area/ (scrutiny depends on both)

## Implementation Patterns & Consistency Rules

### Critical Conflict Points Identified

9 areas where AI agents could make incompatible choices across modules:
1. Tool function internal structure
2. Module-to-server registration pattern
3. DrawingSession access inside a tool
4. CAD backend access pattern
5. Structured error construction
6. Pydantic model naming for tool I/O
7. SQLAlchemy model organization
8. Inter-module communication
9. Naming conventions (DB, code, files)

---

### Naming Patterns

**MCP Tool Naming:** `{module}_{action}` — established in PRD
- Module prefixes are fixed: `cad_`, `predcr_`, `layer_`, `entity_`, `verify_`,
  `autodcr_`, `config_`, `area_`, `report_`, `workflow_`
- Actions use snake_case verbs: `open`, `create`, `run`, `get`, `list`, `delete`,
  `generate`, `validate`, `compute`

**Python Code Naming:** PEP 8 throughout — no exceptions
- Functions/methods/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `SCREAMING_SNAKE_CASE`
- Private members: `_leading_underscore`
- Module files: `snake_case.py`

**Error Code Naming:** `SCREAMING_SNAKE_CASE` noun phrases
- Format: `{NOUN}_{CONDITION}` — e.g., `LAYER_NOT_FOUND`, `CLOSURE_FAILED`,
  `DCR_VIOLATION`, `SESSION_NOT_STARTED`, `BACKEND_UNAVAILABLE`
- All error codes defined in `errors.py` as string constants — no inline strings

**Database Naming:** `snake_case` for all tables and columns
- Tables: plural nouns — `sessions`, `tool_events`, `scrutiny_runs`, `rule_results`,
  `config_versions`, `reports`
- Columns: `snake_case` — `session_id`, `started_at`, `config_version_hash`
- Foreign keys: `{referenced_table_singular}_id` — `session_id`, `run_id`
- Boolean columns: `is_{condition}` — `is_compliant`, `is_archived`

**Pydantic Model Naming:**
- Input schemas: `{ToolName}Params` — e.g., `OpenDrawingParams`, `RunScrutinyParams`
- Output schemas: `{ToolName}Result` — e.g., `OpenDrawingResult`, `RunScrutinyResult`
- Shared data models: descriptive nouns — `LayerSpec`, `RuleResult`, `AreaSummary`

---

### Structure Patterns

**Module Registration Pattern** — every module exposes a single `register(mcp)` function:

```python
# src/lcs_cad_mcp/modules/cad/__init__.py
from fastmcp import FastMCP
from .tools import open_drawing, new_drawing, save_drawing

def register(mcp: FastMCP) -> None:
    mcp.tool(name="cad_open_drawing")(open_drawing)
    mcp.tool(name="cad_new_drawing")(new_drawing)
    mcp.tool(name="cad_save_drawing")(save_drawing)
```

```python
# src/lcs_cad_mcp/__main__.py
from lcs_cad_mcp import modules
from lcs_cad_mcp.server import mcp

for module in [modules.cad, modules.predcr, modules.layers, ...]:
    module.register(mcp)

mcp.run()
```

**Module Internal Structure** — every module directory contains:
```
modules/cad/
├── __init__.py     # register(mcp) only — no business logic
├── tools.py        # tool handler functions (thin layer)
├── service.py      # business logic (testable without MCP)
└── schemas.py      # Pydantic input/output models for this module
```

**SQLAlchemy Models Organization:**
```
archive/
├── __init__.py
├── engine.py       # engine + session factory
├── models.py       # ALL SQLAlchemy models in one file (simpler for MVP)
└── repository.py   # query functions (no raw SQL in business logic)
```

---

### Tool Function Anatomy Pattern

**Every MCP tool handler follows this exact 6-step structure — no exceptions:**

```python
# modules/cad/tools.py
from fastmcp import Context
from lcs_cad_mcp.session.context import DrawingSession
from lcs_cad_mcp.errors import MCPError, ErrorCode
from .schemas import OpenDrawingParams, OpenDrawingResult
from .service import CadService

async def open_drawing(params: OpenDrawingParams, ctx: Context) -> dict:
    """Open an existing DWG or DXF file for processing."""
    # 1. Get session — raises SESSION_NOT_STARTED if missing
    session: DrawingSession = ctx.get_state("session")
    if session is None:
        return MCPError(ErrorCode.SESSION_NOT_STARTED, recoverable=False).to_response()

    # 2. Validate domain constraints (Pydantic already validated params)

    # 3. Snapshot before mutation (write tools only)
    # checkpoint = session.snapshot.take()

    # 4. Execute via service (no ezdxf/COM imports in tool handlers)
    try:
        result = CadService(session).open_drawing(params.path, params.backend)
    except Exception as e:
        return MCPError(ErrorCode.DRAWING_OPEN_FAILED, str(e), recoverable=False).to_response()

    # 5. Log event
    session.event_log.record("cad_open_drawing", params.model_dump(), result)

    # 6. Return structured response
    return {"success": True, "data": OpenDrawingResult(**result).model_dump(), "error": None}
```

**Rules:**
- Tool handlers are `async` — always
- Tool handlers are **thin** — no business logic; delegate to `service.py`
- Tool handlers never import `ezdxf` or `pywin32` directly
- Tool handlers always record to `session.event_log`
- Tool handlers always return `{"success": bool, "data": dict|None, "error": dict|None}`

---

### Format Patterns

**MCP Tool Response — always this exact shape:**

```json
{"success": true, "data": { ... }, "error": null}
```
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "LAYER_NOT_FOUND",
    "message": "Layer 'PLOT_BOUNDARY' does not exist in current drawing",
    "recoverable": true,
    "suggested_action": "Call predcr_create_layers to initialize required layers first"
  }
}
```

**`MCPError` helper in `errors.py`** — never construct error dicts inline:
```python
class MCPError:
    def __init__(self, code: str, message: str = "", recoverable: bool = True,
                 suggested_action: str = ""):
        ...
    def to_response(self) -> dict:
        return {"success": False, "data": None, "error": {...}}
```

**Datetime format:** ISO 8601 strings in all DB storage and JSON output:
`"2026-03-04T14:23:01Z"` — never Unix timestamps, never date-only strings

**Area values:** Always stored and returned as `float`, rounded to 4 decimal places
in display contexts; never truncated in computation contexts.

---

### Process Patterns

**Session Access:**
- Tools access `DrawingSession` via `ctx.get_state("session")`
- Session is set by `workflow_start` via `ctx.set_state("session", session)`
- No module imports or instantiates `DrawingSession` directly — only `workflow/` creates it

**CAD Backend Access:**
- All CAD operations go through `session.backend` (a `CADBackend` instance)
- `session.backend` is set at session creation based on `Settings.cad_backend`
- No module imports `ezdxf` or `pywin32` at module level — only `backends/` does

**Inter-Module Communication:**
- Modules call each other via **direct Python function calls** to service classes —
  never via MCP tool calls (avoid protocol overhead and circular dispatch)
- Example: `autodcr` calls `AreaService.compute_all()` directly, not `area_compute_all` tool

**Validation Pattern:**
- Pydantic validates tool input params automatically (FastMCP integration)
- Domain validation (e.g., "layer must exist") happens in `service.py`, raises `MCPError`
- Never use `raise` in tool handlers — always `return MCPError(...).to_response()`

**Snapshot Pattern (write tools only):**
```python
checkpoint = session.snapshot.take()
try:
    result = service.mutate(...)
except Exception:
    session.snapshot.restore(checkpoint)
    return MCPError(...).to_response()
```

---

### Enforcement Guidelines

**All AI Agents MUST:**

1. Follow the 6-step tool handler anatomy — no shortcuts, no inline logic
2. Use `MCPError` from `errors.py` — never construct error dicts inline
3. Register tools via `module.register(mcp)` — never register in `__main__.py` directly
4. Access CAD backend via `session.backend` — never import `ezdxf`/`pywin32` in modules
5. Access `DrawingSession` via `ctx.get_state("session")` — never as a global or singleton
6. Name all error codes using `ErrorCode` constants from `errors.py`
7. Record every tool invocation to `session.event_log` — no exceptions
8. Use `snake_case` for all DB columns and Python identifiers

**Anti-Patterns (explicitly forbidden):**
- ❌ Business logic in tool handler functions
- ❌ `import ezdxf` outside of `backends/` directory
- ❌ Inline error dict construction
- ❌ Calling MCP tools from within other MCP tools
- ❌ Module-level singletons for drawing state (use `ctx.get_state`)
- ❌ Skipping `session.event_log.record()` in any tool handler
- ❌ Storing datetimes as Unix timestamps in the database

## Project Structure & Boundaries

### Complete Project Directory Structure

```
lcs-cad-mcp/
├── pyproject.toml                    # uv-managed; all dependencies pinned
├── uv.lock                           # lockfile — committed to version control
├── .env.example                      # template for required env vars
├── .gitignore
├── README.md
├── src/
│   └── lcs_cad_mcp/
│       ├── __init__.py
│       ├── __main__.py               # entrypoint: calls module.register(mcp) for all modules, then mcp.run()
│       ├── server.py                 # FastMCP instance creation + transport config
│       ├── settings.py               # pydantic-settings Settings class (DCR_CONFIG_PATH, ARCHIVE_PATH, CAD_BACKEND)
│       ├── errors.py                 # MCPError class + ErrorCode string constants
│       │
│       ├── session/                  # DrawingSession — first-class component (FR32–36)
│       │   ├── __init__.py
│       │   ├── context.py            # DrawingSession dataclass: session_id, project_name, backend, event_buffer
│       │   ├── snapshot.py           # SnapshotManager: in-memory ezdxf copy + disk checkpoint write/restore
│       │   └── event_log.py          # EventLog: buffer tool events, flush to SQLite via archive.repository
│       │
│       ├── backends/                 # CAD backend abstraction — FIRST built (FR5, FR44–45)
│       │   ├── __init__.py
│       │   ├── base.py               # Abstract CADBackend Protocol (open, save, create, draw_*, query_*, layer_*)
│       │   ├── ezdxf_backend.py      # PRIMARY: ezdxf implementation of CADBackend
│       │   └── com_backend.py        # SECONDARY: COM/pywin32 implementation (Windows-only)
│       │
│       ├── modules/
│       │   ├── __init__.py           # exports all module packages for __main__.py iteration
│       │   │
│       │   ├── cad/                  # FR1–5: Drawing Management
│       │   │   ├── __init__.py       # register(mcp): cad_open_drawing, cad_new_drawing, cad_save_drawing,
│       │   │   │                     #   cad_get_metadata, cad_select_backend
│       │   │   ├── tools.py          # async tool handlers (thin, 6-step anatomy)
│       │   │   ├── service.py        # CadService: open/create/save/metadata logic via session.backend
│       │   │   └── schemas.py        # OpenDrawingParams, NewDrawingParams, SaveDrawingParams, etc.
│       │   │
│       │   ├── predcr/               # FR6–9: PreDCR Drawing Preparation
│       │   │   ├── __init__.py       # register(mcp): predcr_create_layers, predcr_assign_name,
│       │   │   │                     #   predcr_insert_block, predcr_close_polyline
│       │   │   ├── tools.py
│       │   │   ├── service.py        # PreDCRService: orchestrates layer + entity creation per building type
│       │   │   ├── schemas.py
│       │   │   └── layer_registry.py # PreDCR layer name/type/color spec (source of truth for naming convention)
│       │   │
│       │   ├── layers/               # FR6: Layer Management System
│       │   │   ├── __init__.py       # register(mcp): layer_create, layer_list, layer_get,
│       │   │   │                     #   layer_delete, layer_rename, layer_set_color, layer_set_linetype, layer_freeze
│       │   │   ├── tools.py
│       │   │   ├── service.py        # LayerService: full layer CRUD via session.backend
│       │   │   └── schemas.py
│       │   │
│       │   ├── entities/             # FR7–12: Entity Management & Spatial Hierarchy
│       │   │   ├── __init__.py       # register(mcp): entity_draw_polyline, entity_draw_line,
│       │   │   │                     #   entity_draw_arc, entity_draw_circle, entity_draw_text,
│       │   │   │                     #   entity_insert_mtext, entity_modify, entity_move, entity_copy,
│       │   │   │                     #   entity_delete, entity_query
│       │   │   ├── tools.py
│       │   │   ├── service.py        # EntityService: draw/modify/query via session.backend
│       │   │   └── schemas.py
│       │   │
│       │   ├── verification/         # FR13–18: Verification Engine
│       │   │   ├── __init__.py       # register(mcp): verify_closure, verify_containment,
│       │   │   │                     #   verify_naming, verify_minimum_entities, verify_all
│       │   │   ├── tools.py
│       │   │   ├── service.py        # VerificationService: runs all checks, returns structured failures
│       │   │   └── schemas.py
│       │   │
│       │   ├── config/               # FR19–20: DCR Rule Config System
│       │   │   ├── __init__.py       # register(mcp): config_load, config_validate,
│       │   │   │                     #   config_get_version, config_list_rules
│       │   │   ├── tools.py
│       │   │   ├── service.py        # ConfigService: delegates to rule_engine.loader + validator
│       │   │   └── schemas.py
│       │   │
│       │   ├── area/                 # FR22: Area Computation Engine
│       │   │   ├── __init__.py       # register(mcp): area_compute_plot, area_compute_buildup,
│       │   │   │                     #   area_compute_carpet, area_compute_fsi,
│       │   │   │                     #   area_compute_coverage, area_compute_all
│       │   │   ├── tools.py
│       │   │   ├── service.py        # AreaService: Shapely polygon ops; all results float, 4dp
│       │   │   └── schemas.py
│       │   │
│       │   ├── autodcr/              # FR21–26: AutoDCR Scrutiny Engine
│       │   │   ├── __init__.py       # register(mcp): autodcr_run_scrutiny, autodcr_get_violations,
│       │   │   │                     #   autodcr_get_remediation, autodcr_run_dry_run,
│       │   │   │                     #   autodcr_get_rule_result, autodcr_rerun
│       │   │   ├── tools.py
│       │   │   ├── service.py        # AutoDCRService: calls AreaService + rule_engine.evaluator
│       │   │   └── schemas.py
│       │   │
│       │   ├── reports/              # FR27–31: Report Generation
│       │   │   ├── __init__.py       # register(mcp): report_generate_pdf, report_generate_docx,
│       │   │   │                     #   report_generate_json, report_get_remediation_suggestions
│       │   │   ├── tools.py
│       │   │   ├── service.py        # ReportService: ReportLab (PDF), python-docx (DOCX), JSON dump
│       │   │   └── schemas.py
│       │   │
│       │   └── workflow/             # FR32–36: Workflow Orchestration & Audit
│       │       ├── __init__.py       # register(mcp): workflow_start, workflow_end,
│       │       │                     #   workflow_run_pipeline, workflow_get_archive,
│       │       │                     #   workflow_get_audit_trail
│       │       ├── tools.py
│       │       ├── service.py        # WorkflowService: creates DrawingSession, orchestrates full pipeline
│       │       └── schemas.py
│       │
│       ├── rule_engine/              # DCR rule evaluation (internal — not exposed as MCP tools directly)
│       │   ├── __init__.py
│       │   ├── loader.py             # YAML/JSON parser; preserves key insertion order
│       │   ├── validator.py          # Pydantic schema validation on load; hashes config content
│       │   ├── evaluator.py          # Deterministic rule evaluation loop (declaration order)
│       │   └── models.py             # Rule, RuleResult, DCRConfig, ViolationRecord Pydantic models
│       │
│       └── archive/                  # SQLite + SQLAlchemy persistence (internal — not MCP-exposed)
│           ├── __init__.py
│           ├── engine.py             # SQLite engine + sessionmaker factory; create_all on startup
│           ├── models.py             # ALL ORM models: Session, ToolEvent, ScrutinyRun,
│           │                         #   RuleResult, ConfigVersion, Report
│           └── repository.py         # Query functions: save_session, record_event, save_run, etc.
│
├── tests/
│   ├── conftest.py                   # MockCADBackend, MockDrawingSession, tmp_db_engine fixtures
│   ├── unit/
│   │   ├── backends/
│   │   │   ├── test_ezdxf_backend.py
│   │   │   └── test_com_backend.py
│   │   ├── session/
│   │   │   ├── test_context.py
│   │   │   ├── test_snapshot.py
│   │   │   └── test_event_log.py
│   │   ├── rule_engine/
│   │   │   ├── test_loader.py        # order preservation, YAML/JSON parity
│   │   │   ├── test_validator.py     # schema error cases
│   │   │   └── test_evaluator.py    # property-based: same input → same output (hypothesis)
│   │   ├── archive/
│   │   │   ├── test_models.py
│   │   │   └── test_repository.py
│   │   └── modules/                  # mirrors src/modules/ exactly
│   │       ├── cad/
│   │       ├── predcr/
│   │       ├── layers/
│   │       ├── entities/
│   │       ├── verification/
│   │       ├── autodcr/
│   │       ├── config/
│   │       ├── area/
│   │       ├── reports/
│   │       └── workflow/
│   └── integration/
│       ├── test_predcr_pipeline.py   # layers + entities + verification end-to-end
│       ├── test_scrutiny_pipeline.py # area + autodcr + rule_engine end-to-end
│       ├── test_full_pipeline.py     # workflow_start → full pipeline → workflow_end
│       └── test_report_generation.py # scrutiny run → all 3 report formats
│
├── dcr_configs/
│   ├── schema.yaml                   # Pydantic-generated JSON schema for DCR rule configs
│   └── example_authority.yaml        # Reference rule set for testing and onboarding
│
└── docs/
    ├── dcr-config-schema.md          # Config authoring guide (rule format, field reference)
    └── tool-api-reference.md         # All 60+ tools: name, params, response, error codes
```

### Architectural Boundaries

**MCP Tool Boundary (external interface):**
- The only interface AI clients use. All 60+ tools registered at startup via `module.register(mcp)`.
- Input crosses boundary as JSON-validated Pydantic params; output crosses as `{success, data, error}` dict.
- No business logic at this boundary — handlers delegate immediately to `service.py`.

**CAD Backend Boundary:**
- Defined by `backends/base.py` (`CADBackend` Protocol).
- Only `backends/ezdxf_backend.py` and `backends/com_backend.py` cross this boundary into CAD libraries.
- All modules access the backend exclusively via `session.backend` — never by direct import.

**Rule Engine Boundary:**
- `rule_engine/` is an internal service called only by `modules/config/service.py` (load/validate)
  and `modules/autodcr/service.py` (evaluate).
- Rule configs are read-only during evaluation (NFR23). The evaluator never writes to config files.

**Archive Boundary:**
- `archive/` is accessed only by `session/event_log.py` (event persistence) and
  `modules/workflow/service.py` (session + run archival).
- No module queries the archive directly except `workflow/` (for FR33: retrieve archived runs).

**Session Boundary:**
- `session/` is created and owned exclusively by `modules/workflow/service.py`.
- All other modules receive `DrawingSession` via `ctx.get_state("session")` — read/use only.
- No module outside `workflow/` sets session state.

### Requirements to Structure Mapping

| FR Category | FR IDs | Primary Location |
|---|---|---|
| Drawing Management | FR1–5 | `modules/cad/` |
| PreDCR Preparation | FR6–9 | `modules/predcr/` + `modules/layers/` + `predcr/layer_registry.py` |
| Entity Management | FR7–12 | `modules/entities/` |
| Verification | FR13–18 | `modules/verification/` |
| DCR Config | FR19–20 | `modules/config/` + `rule_engine/loader.py` + `rule_engine/validator.py` |
| Area Computation | FR22 | `modules/area/` |
| DCR Scrutiny | FR21–26 | `modules/autodcr/` + `rule_engine/evaluator.py` + `modules/area/` |
| Report Generation | FR27–31 | `modules/reports/` |
| Workflow & Audit | FR32–36 | `modules/workflow/` + `session/` + `archive/` |
| MCP Protocol | FR37–41 | `server.py` + `errors.py` + all `schemas.py` |
| System Config | FR42–45 | `settings.py` + `backends/base.py` |

### Integration Points & Data Flow

**Request path (every tool call):**
```
AI Client → MCP (stdio/SSE) → FastMCP dispatcher
  → tool handler (tools.py)
    → ctx.get_state("session") → DrawingSession
    → service.py → session.backend (CADBackend) → ezdxf / COM
    → session.event_log.record() → archive/repository → SQLite
  → {"success", "data", "error"} → AI Client
```

**Scrutiny path (autodcr_run_scrutiny):**
```
autodcr/tools.py
  → disk checkpoint (session/snapshot.py → ARCHIVE_PATH/checkpoints/)
  → AutoDCRService.run_scrutiny()
    → AreaService.compute_all() (direct Python call)
    → rule_engine/evaluator.evaluate(rules, areas, drawing)
    → archive/repository.save_scrutiny_run()
```

**Pipeline path (workflow_run_pipeline):**
```
WorkflowService.run_full_pipeline()
  → PreDCRService.setup()
  → VerificationService.run_all()
  → AreaService.compute_all()
  → AutoDCRService.run_scrutiny()
  → ReportService.generate_all()
  → archive/repository.save_session()
```

### Development Workflow Integration

**Local development:**
```bash
cp .env.example .env
uv run python -m lcs_cad_mcp   # starts MCP server on stdio
```

**Run tests:**
```bash
uv run pytest tests/unit/        # fast, no AutoCAD required
uv run pytest tests/integration/ # requires ezdxf; no AutoCAD
```

**Claude Desktop config:**
```json
{
  "mcpServers": {
    "lcs-cad-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "lcs_cad_mcp"],
      "env": {
        "DCR_CONFIG_PATH": "/path/to/dcr-rules.yaml",
        "ARCHIVE_PATH": "/path/to/archive",
        "CAD_BACKEND": "ezdxf"
      }
    }
  }
}
```

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices are mutually compatible:
- FastMCP 3.x + Pydantic v2 + pydantic-settings share the Pydantic ecosystem — no conflicts
- SQLAlchemy ORM + SQLite + startup `create_all` is a standard, well-tested combination
- ezdxf + Shapely are both pure Python — no C-extension conflicts or version constraints
- pytest + pytest-asyncio + hypothesis: standard async + property-based testing stack
- ruff covers linting, formatting, and import sorting in a single tool — no configuration overlap

**Pattern Consistency:**
- 6-step tool handler anatomy uses Pydantic params → aligns with Pydantic v2 validation decision ✅
- `ctx.get_state("session")` → directly supported by FastMCP 3.x session state API ✅
- `module.register(mcp)` → clean fit with FastMCP's `mcp.tool()` decorator ✅
- `MCPError.to_response()` → consistent with structured error contract decision ✅
- Hybrid rollback → `session/snapshot.py` + `ARCHIVE_PATH/checkpoints/` directly supported by structure ✅

**Structure Alignment:**
- `backends/` enforces the CAD backend abstraction boundary ✅
- `session/` as a module (not a file) supports the DrawingSession complexity ✅
- `archive/` as a dedicated module supports ACID archival and event log persistence ✅
- `rule_engine/` separate from `modules/` enforces the read-only rule engine boundary ✅
- Test structure mirrors module structure → enables isolated module testing with MockCADBackend ✅

### Requirements Coverage Validation

**Functional Requirements: 45/45 covered**

| FR Category | FRs | Status |
|---|---|---|
| Drawing Management | FR1–5 | ✅ modules/cad/ |
| PreDCR Preparation | FR6–9 | ✅ modules/predcr/ + layers/ + entities/ |
| Entity Management | FR7–12 | ✅ modules/entities/ |
| Verification | FR13–18 | ✅ modules/verification/ |
| DCR Config | FR19–20 | ✅ modules/config/ + rule_engine/ |
| Area Computation | FR22 | ✅ modules/area/ |
| DCR Scrutiny | FR21–26 | ✅ modules/autodcr/ + rule_engine/ + area/ |
| Report Generation | FR27–31 | ✅ modules/reports/ |
| Workflow & Audit | FR32–36 | ✅ modules/workflow/ + session/ + archive/ |
| MCP Protocol | FR37–41 | ✅ server.py + errors.py + schemas.py |
| System Config | FR42–45 | ✅ settings.py + backends/base.py |

**Non-Functional Requirements: 24/24 addressed**

- Performance (NFR1–6): Thin tool handler + service delegation minimises per-call overhead.
  Performance budgets validated through integration tests.
- Data Integrity (NFR7–10): Hybrid rollback (NFR7–8), ACID SQLite archival (NFR9),
  disk checkpoint recovery (NFR10). ✅
- Correctness (NFR11–14): Shapely polygon ops (NFR11–12), declaration-order evaluation
  with config hash recording (NFR13), verification coverage (NFR14). ✅
- Reliability (NFR15–17): Structured error returns prevent server state corruption (NFR15).
  COM failover via `is_available()` probe (NFR16). Pydantic validation returns structured
  errors, not exceptions (NFR17). ✅
- Integration (NFR18–21): FastMCP 3.x compatibility (NFR18), configurable DXF format via
  Settings (NFR19), Pydantic-validated DCR configs (NFR20), ezdxf produces standard DXF (NFR21). ✅
- Security (NFR22–24): Local-only architecture (NFR22), rule engine boundary enforces
  read-only config access (NFR23), no auth for MVP (NFR24). ✅

**Gap Resolved — NFR16 (COM failover):**
Add `is_available() -> bool` to the `CADBackend` abstract protocol in `backends/base.py`.
Session creation in `WorkflowService` probes the configured backend; if `is_available()`
returns `False`, it falls back to `ezdxf` and logs a warning.

```python
# backends/base.py — required addition
class CADBackend(Protocol):
    def is_available(self) -> bool: ...
    # ... all other drawing operation methods
```

### Implementation Readiness Validation ✅

**Decision Completeness:** All critical decisions documented with versions and rationale.
Deferred decisions (Alembic, structlog) explicitly noted with upgrade paths.

**Structure Completeness:** Complete directory tree defined. Every file named and annotated.
All FR categories mapped to specific locations. Integration points and data flows documented.

**Pattern Completeness:** All 9 conflict points addressed. Concrete code examples provided
for tool anatomy, module registration, error handling, and snapshot patterns.
Anti-patterns explicitly enumerated.

### Gap Analysis Results

| Priority | Gap | Status |
|---|---|---|
| ⚠️ Important | NFR16: COM backend failover mechanism | Resolved — `is_available()` added to protocol spec |
| ℹ️ Nice-to-have | No CI/CD pipeline defined | Acceptable for single-developer MVP |
| ℹ️ Nice-to-have | No doc generation tooling | docs/ written manually for MVP |

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (45 FRs, 24 NFRs, 9 cross-cutting concerns)
- [x] Scale and complexity assessed (High — CAD + geometry + rule engine + legal archival)
- [x] Technical constraints identified (COM Windows-only, MCP stateless, ezdxf primary)
- [x] Cross-cutting concerns mapped (9 identified, all addressed)

**✅ Architectural Decisions**
- [x] MCP framework: FastMCP 3.x pinned >=3.1.0,<4.0.0
- [x] Session lifecycle: explicit via workflow_start/end
- [x] Rollback: hybrid in-memory + disk checkpoint
- [x] Config: pydantic-settings with startup validation
- [x] Logging: FastMCP OTel + stdlib logging
- [x] Rule evaluation: declaration order, reproducible
- [x] Database: SQLAlchemy ORM + startup create_all

**✅ Implementation Patterns**
- [x] 6-step tool handler anatomy with code example
- [x] Module registration pattern with code example
- [x] Naming conventions: MCP tools, Python code, DB, Pydantic models, error codes
- [x] Structured error contract with MCPError helper
- [x] Session access, CAD backend access, inter-module communication patterns
- [x] 8 anti-patterns explicitly forbidden

**✅ Project Structure**
- [x] Complete directory tree with all files annotated
- [x] All 10 modules + 4 cross-cutting components defined
- [x] 5 architectural boundaries defined
- [x] FR-to-structure mapping table complete
- [x] 3 data flow paths documented (request, scrutiny, pipeline)

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION**

**Confidence Level: High**

**Key Strengths:**
- DrawingSession as first-class component solves the hardest architectural problem upfront
- CAD backend abstraction enables full development and testing without AutoCAD
- 6-step tool anatomy enforces consistency across all 60+ tools by convention
- Legal audit trail built into session lifecycle — not bolted on afterward
- Externalized rule engine enables authority-agnostic deployment without code changes
- Modular build order enables progressive testing with mock interfaces throughout

**Areas for Future Enhancement:**
- Alembic migrations when multi-instance deployment begins (Phase 2)
- structlog for structured log querying (Phase 2)
- COM backend after all modules tested against ezdxf (Phase 1 late)
- Batch processing architecture (Phase 2)

### Implementation Handoff

**Build order (strictly follow):**
1. `settings.py` + `errors.py` — foundation before anything runs
2. `backends/base.py` (with `is_available()`) — contract all modules depend on
3. `session/` (context, snapshot, event_log) — shared state layer
4. `archive/` (engine, models, repository) — persistence layer
5. `backends/ezdxf_backend.py` — primary backend implementation
6. Feature modules in dependency order: `cad` → `predcr` → `layers` → `entities` → `verification` → `area` → `config` → `autodcr` → `reports` → `workflow`
7. `backends/com_backend.py` — after all modules tested against ezdxf
8. Integration tests — after all modules complete

**First implementation story:**
```bash
uv init lcs-cad-mcp --python 3.11
cd lcs-cad-mcp
uv add "fastmcp>=3.1.0,<4.0.0" pydantic pydantic-settings ezdxf shapely scipy sqlalchemy python-docx reportlab
uv add --dev pytest pytest-asyncio hypothesis ruff
```
