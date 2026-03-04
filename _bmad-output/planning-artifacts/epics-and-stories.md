# Epics and Stories — lcs-cad-mcp

**Project:** lcs-cad-mcp
**Author:** Bob (SM) + John (PM) + Winston (Architect) — BMAD Party Mode
**Date:** 2026-03-04
**Source:** PRD v1 + Architecture v1
**Build Order (dependency-driven):** Epic 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11

---

## Story Sizing Convention

| Size | Effort |
|---|---|
| XS | < 2 hours |
| S | 2–4 hours |
| M | 4–8 hours (half day) |
| L | 1–1.5 days |
| XL | Split required |

---

## Epic 1: MCP Server Foundation

**Goal:** A running MCP server that registers tools, validates inputs, returns structured responses, and is testable end-to-end before any domain logic is built.

**FR coverage:** FR37, FR38, FR39, FR40, FR41
**NFR coverage:** NFR6, NFR15, NFR17

---

### Story 1-1: Project scaffold and dependency setup

**As a** developer
**I want** a properly structured Python project with all core dependencies declared
**So that** the dev environment is reproducible and CI-ready from day one

**Acceptance Criteria**
- [ ] AC1: `pyproject.toml` declares all dependencies (mcp/FastMCP, pydantic v2, ezdxf, shapely, sqlalchemy, reportlab, python-docx, pytest, hypothesis)
- [ ] AC2: `uv pip install -e .` installs the project without errors on Python 3.11+
- [ ] AC3: Project layout follows `src/lcs_cad_mcp/` package structure
- [ ] AC4: `pytest` runs with zero tests (but no errors) after scaffold
- [ ] AC5: `.env.example` documents all required env vars (DCR_CONFIG_PATH, ARCHIVE_PATH, CAD_BACKEND)

**Technical Notes**
- Use `uv` as primary package manager
- Module structure: `server.py`, `tools/`, `backends/`, `engines/`, `models/`, `db/`

**Dependencies:** None
**Size:** S

---

### Story 1-2: MCP server core with stdio transport

**As a** developer
**I want** a running MCP server that communicates over stdio
**So that** Claude Desktop and Cursor can connect to it and discover tools

**Acceptance Criteria**
- [ ] AC1: `python -m lcs_cad_mcp` starts the server without errors
- [ ] AC2: Server starts and exposes all registered tools within 10 seconds (NFR6)
- [ ] AC3: Standard MCP `tools/list` returns the tool registry
- [ ] AC4: Server process does not crash on malformed JSON-RPC input — returns parse error response
- [ ] AC5: Claude Desktop config snippet documented and tested locally

**Technical Notes**
- Use FastMCP or official `mcp` SDK
- stdio is primary transport (FR37)

**Dependencies:** Story 1-1
**Size:** M

---

### Story 1-3: SSE transport support

**As a** developer
**I want** the MCP server to optionally serve over SSE
**So that** remote and server deployments work without code changes

**Acceptance Criteria**
- [ ] AC1: `CAD_BACKEND=ezdxf MCP_TRANSPORT=sse python -m lcs_cad_mcp` starts SSE server on configurable port
- [ ] AC2: Same tool registry accessible over SSE as over stdio
- [ ] AC3: Transport selection via env var, not code changes (FR38)

**Dependencies:** Story 1-2
**Size:** S

---

### Story 1-4: Structured error response contract

**As a** developer
**I want** every MCP tool failure to return a standard structured error envelope
**So that** AI clients can parse, react to, and surface errors consistently

**Acceptance Criteria**
- [ ] AC1: All tool errors return: `{ success, data, error: { code, message, recoverable, suggested_action } }`
- [ ] AC2: `recoverable: true` errors do NOT trigger drawing rollback
- [ ] AC3: `recoverable: false` errors DO trigger drawing rollback (integration test with stub)
- [ ] AC4: Error codes are defined as an enum/constant set (e.g. `LAYER_NOT_FOUND`, `CLOSURE_FAILED`, `DCR_VIOLATION`)
- [ ] AC5: Unhandled exceptions are caught and wrapped in the error envelope — server never returns a raw traceback

**Technical Notes**
- Define `MCPResponse` Pydantic model used by all tools
- Define `ErrorCode` enum
- Global exception handler at server level

**Dependencies:** Story 1-2
**Size:** M

---

### Story 1-5: Pydantic input validation framework

**As a** developer
**I want** all MCP tool inputs validated by Pydantic schemas before execution
**So that** malformed parameters return validation errors, not unhandled exceptions (NFR17)

**Acceptance Criteria**
- [ ] AC1: Every tool defines a Pydantic v2 input model
- [ ] AC2: Missing required parameters return a structured validation error (FR39)
- [ ] AC3: Type coercion errors return a structured validation error
- [ ] AC4: Validation errors set `success: false`, `error.code: VALIDATION_ERROR`, `recoverable: true`
- [ ] AC5: Tool parameter schemas are exposed via MCP `tools/list` (FR41)

**Dependencies:** Story 1-4
**Size:** M

---

## Epic 2: CAD Interface Layer

**Goal:** A unified CAD backend abstraction exposing drawing lifecycle (open/create/save/close) and metadata over both ezdxf (headless) and COM (live AutoCAD) backends, with rollback capability.

**FR coverage:** FR1, FR2, FR3, FR4, FR5
**NFR coverage:** NFR7, NFR8, NFR10, NFR16, NFR19, NFR21

---

### Story 2-1: CAD backend abstraction interface

**As a** developer
**I want** a Python abstract base class that defines the contract for all CAD backends
**So that** all higher-level tools are backend-agnostic

**Acceptance Criteria**
- [ ] AC1: `CADBackend` ABC defines: `open_drawing`, `create_drawing`, `save_drawing`, `close_drawing`, `get_metadata`, `get_entities`, `get_layers`, `snapshot`, `rollback`
- [ ] AC2: `BackendFactory.get(CAD_BACKEND)` returns the correct implementation based on env config
- [ ] AC3: All methods have type-annotated signatures and docstrings
- [ ] AC4: Unit tests verify factory returns correct backend type

**Dependencies:** Story 1-5
**Size:** S

---

### Story 2-2: ezdxf backend — drawing lifecycle

**As a** developer
**I want** the ezdxf backend to open, create, and save DXF files
**So that** the full pipeline works without AutoCAD installed (headless mode, FR5, FR45)

**Acceptance Criteria**
- [ ] AC1: `cad_open_drawing(path)` opens an existing DXF/DWG file via ezdxf — returns success with drawing handle
- [ ] AC2: `cad_create_drawing(name, units)` creates a blank DXF document
- [ ] AC3: `cad_save_drawing(path, format)` saves as DXF R2018 by default; format version configurable (NFR19)
- [ ] AC4: `cad_close_drawing()` releases the document from memory cleanly
- [ ] AC5: Output DXF files open without errors in AutoCAD, ZWCAD, and BricsCAD (NFR21) — verified with ezdxf audit

**Technical Notes**
- Use `ezdxf.new()` and `ezdxf.readfile()`
- DXF output version: `ezdxf.DXF2018` by default

**Dependencies:** Story 2-1
**Size:** M

---

### Story 2-3: ezdxf backend — drawing metadata query

**As a** developer
**I want** the ezdxf backend to return drawing metadata
**So that** AI clients can understand drawing state before issuing commands

**Acceptance Criteria**
- [ ] AC1: `cad_get_metadata()` returns: units, extents (min/max XY), entity count, layer count, DXF version (FR4)
- [ ] AC2: Returns correct values for both empty and populated drawings
- [ ] AC3: Returns structured error if no drawing is open

**Dependencies:** Story 2-2
**Size:** S

---

### Story 2-4: Drawing state snapshot and rollback

**As a** developer
**I want** the CAD layer to snapshot drawing state before write operations and roll back on failure
**So that** drawing files are never left in a partially written or corrupted state (FR35, NFR7, NFR8)

**Acceptance Criteria**
- [ ] AC1: `snapshot()` saves the current drawing state (in-memory copy or temp file)
- [ ] AC2: `rollback()` restores the drawing to the last snapshot state
- [ ] AC3: After rollback, drawing is identical to the pre-operation state (byte-level for file mode)
- [ ] AC4: Rollback is triggered automatically when a tool returns `recoverable: false`
- [ ] AC5: Server remains operational after a rollback — subsequent tool calls succeed (NFR15, NFR10)
- [ ] AC6: Both ezdxf and COM backends implement snapshot/rollback

**Dependencies:** Story 2-2
**Size:** L

---

### Story 2-5: COM backend — drawing lifecycle (Windows)

**As a** developer
**I want** the COM backend to control a live AutoCAD session
**So that** architects using AutoCAD can operate the full pipeline without switching applications

**Acceptance Criteria**
- [ ] AC1: `cad_open_drawing(path)` opens a DWG/DXF in the active AutoCAD/ZWCAD/BricsCAD session via COM
- [ ] AC2: `cad_create_drawing()` creates a new drawing in the live CAD session
- [ ] AC3: `cad_save_drawing()` saves via COM save command
- [ ] AC4: COM connection loss is detected and reported without crashing the server (NFR16)
- [ ] AC5: On COM connection loss, server reports error with `recoverable: false` and ezdxf backend remains available as fallback
- [ ] AC6: All operations on COM backend also pass tests on ezdxf backend (same interface contract)

**Technical Notes**
- Use `pywin32` / `win32com.client`
- Windows-only; tests mocked on non-Windows CI

**Dependencies:** Story 2-4
**Size:** L

---

### Story 2-6: `cad_select_backend` MCP tool

**As an** AI client
**I want** to select the CAD backend at runtime
**So that** the same MCP server works with or without AutoCAD (FR5)

**Acceptance Criteria**
- [ ] AC1: `cad_select_backend(backend: "ezdxf" | "com")` switches the active backend
- [ ] AC2: Returns error if COM backend requested on non-Windows or AutoCAD not running
- [ ] AC3: Backend can also be set via `CAD_BACKEND` env var at server start (FR44)
- [ ] AC4: Switching backends closes the current drawing if one is open (with warning in response)

**Dependencies:** Story 2-5
**Size:** S

---

## Epic 3: Layer Management System

**Goal:** Complete layer lifecycle management with PreDCR naming validation, exposed as MCP tools.

**FR coverage:** (FR6 partial, FR12 partial)
**NFR coverage:** NFR14

---

### Story 3-1: Layer data model and registry

**As a** developer
**I want** a typed data model for layers and a runtime registry
**So that** all layer operations work against a consistent, validated data structure

**Acceptance Criteria**
- [ ] AC1: `Layer` Pydantic model: name, color, linetype, lineweight, is_on, is_frozen, is_locked
- [ ] AC2: `LayerRegistry` holds all layers for the current drawing, synced with backend on open
- [ ] AC3: Registry operations are unit-tested against ezdxf mock
- [ ] AC4: Layer names are stored and compared case-insensitively (AutoCAD convention)

**Dependencies:** Story 2-3
**Size:** S

---

### Story 3-2: `layer_create` and `layer_delete` MCP tools

**As an** AI client
**I want** to create and delete layers
**So that** the drawing's layer structure can be built programmatically

**Acceptance Criteria**
- [ ] AC1: `layer_create(name, color, linetype, lineweight)` creates a layer in the active drawing on both backends
- [ ] AC2: Creating a duplicate layer name returns a structured error (`LAYER_ALREADY_EXISTS`)
- [ ] AC3: `layer_delete(name)` removes a layer; fails if layer contains entities (`LAYER_NOT_EMPTY`)
- [ ] AC4: Both operations update the LayerRegistry
- [ ] AC5: Both operations are wrapped in snapshot/rollback (write operations)

**Dependencies:** Story 3-1, Story 2-4
**Size:** M

---

### Story 3-3: `layer_get`, `layer_list`, `layer_set_properties`, `layer_set_state` MCP tools

**As an** AI client
**I want** to query and modify layer properties
**So that** the AI can verify and adjust layer configuration

**Acceptance Criteria**
- [ ] AC1: `layer_get(name)` returns full Layer model for a named layer
- [ ] AC2: `layer_list(filter?)` returns all layers, optionally filtered by prefix or property
- [ ] AC3: `layer_set_properties(name, color?, linetype?, lineweight?)` updates layer properties
- [ ] AC4: `layer_set_state(name, is_on?, is_frozen?, is_locked?)` updates layer visibility/lock state
- [ ] AC5: All read operations return error if no drawing open

**Dependencies:** Story 3-2
**Size:** M

---

### Story 3-4: PreDCR layer naming validation

**As a** developer
**I want** a validation engine that checks layer names against PreDCR naming conventions
**So that** layers created by the system are guaranteed to match authority requirements (NFR14)

**Acceptance Criteria**
- [ ] AC1: `layer_validate_naming(name, building_type)` returns `valid: bool, violations: list[str]`
- [ ] AC2: PreDCR layer naming rules are defined as a configurable data structure (not hard-coded strings)
- [ ] AC3: Validation catches: wrong prefix, wrong separator, unsupported entity type suffix
- [ ] AC4: Zero false positives on known-correct PreDCR layer names (NFR14)
- [ ] AC5: Validation is used internally by `layer_create` and reports naming issues in the structured error

**Technical Notes**
- PreDCR layer naming spec to be sourced from the legacy AutoDCR_PreDCR docs
- Store layer spec as YAML or Python dataclass catalog

**Dependencies:** Story 3-1
**Size:** M

---

## Epic 4: PreDCR Engine

**Goal:** Automated PreDCR drawing preparation — bulk layer creation per building type, entity naming, and full PreDCR setup from a natural language building description.

**FR coverage:** FR6, FR7, FR8, FR9, FR10, FR11, FR12
**NFR coverage:** NFR2 (60s full pipeline)

---

### Story 4-1: PreDCR layer specification catalog

**As a** developer
**I want** a catalog of all required PreDCR layers per building type
**So that** the system can auto-create the correct layer set for any building type

**Acceptance Criteria**
- [ ] AC1: Catalog defines required layers (name, color, linetype, lineweight) for: Residential, Commercial, Industrial building types
- [ ] AC2: Catalog is stored as YAML data files, not hard-coded Python
- [ ] AC3: Catalog can be extended for new building types without code changes
- [ ] AC4: Unit tests verify catalog loads without schema errors for each building type

**Technical Notes**
- Parse the legacy PreDCR spec document to extract layer definitions
- Layer count per building type: ~40–50 layers expected

**Dependencies:** Story 3-4
**Size:** M

---

### Story 4-2: `predcr_create_layers` MCP tool

**As an** AI client
**I want** to create all required PreDCR layers for a building type in a single call
**So that** the architect doesn't need to specify 40+ layers individually (FR6)

**Acceptance Criteria**
- [ ] AC1: `predcr_create_layers(building_type)` creates all required layers from the catalog in the active drawing
- [ ] AC2: Returns list of created layer names and count
- [ ] AC3: Already-existing layers are skipped (not errored) — idempotent operation
- [ ] AC4: All created layers pass `layer_validate_naming` with zero violations (NFR14)
- [ ] AC5: Runs on both ezdxf and COM backends
- [ ] AC6: Full layer set creation completes within the 60s pipeline budget (NFR2)

**Dependencies:** Story 4-1, Story 3-2
**Size:** M

---

### Story 4-3: `predcr_get_layer_spec` MCP tool

**As an** AI client
**I want** to query the PreDCR layer specification for a building type
**So that** the AI can reference the correct layer for each entity type

**Acceptance Criteria**
- [ ] AC1: `predcr_get_layer_spec(building_type, entity_type?)` returns layer name(s) for the requested entity type
- [ ] AC2: Returns full catalog if no entity_type filter provided
- [ ] AC3: Returns structured error for unknown building_type or entity_type

**Dependencies:** Story 4-1
**Size:** S

---

### Story 4-4: `predcr_run_setup` MCP tool (full PreDCR initialization)

**As an** AI client
**I want** to run a complete PreDCR initialization for a new drawing in a single tool call
**So that** the AI can bootstrap a compliant drawing from a high-level building description

**Acceptance Criteria**
- [ ] AC1: `predcr_run_setup(building_type, project_name, units)` creates a new drawing, sets units, creates all PreDCR layers
- [ ] AC2: Returns a summary: drawing name, layer count, units, backend used
- [ ] AC3: Setup is idempotent — calling on an existing PreDCR drawing does not duplicate layers
- [ ] AC4: Entire setup completes within 30 seconds on ezdxf backend
- [ ] AC5: Drawing produced passes `predcr_validate_drawing` after setup (Story 4-5)

**Dependencies:** Story 4-2, Story 2-2
**Size:** M

---

### Story 4-5: `predcr_validate_drawing` MCP tool

**As an** AI client
**I want** to validate that a drawing conforms to PreDCR requirements
**So that** issues are caught before running the scrutiny pipeline

**Acceptance Criteria**
- [ ] AC1: `predcr_validate_drawing()` checks: all required layers present, layer naming valid, layer properties match spec
- [ ] AC2: Returns `valid: bool, violations: list[{layer, issue, suggestion}]`
- [ ] AC3: Clean PreDCR drawing returns `valid: true, violations: []`
- [ ] AC4: Connects to Verification Engine (Epic 6) for closure/containment/naming checks

**Dependencies:** Story 4-1, Story 3-4
**Size:** M

---

## Epic 5: Entity Management

**Goal:** Full entity drawing, modification, and query capability across both backends, with PreDCR-compliant naming and layer placement.

**FR coverage:** FR7, FR8, FR9, FR10, FR12
**NFR coverage:** NFR1 (2s per entity tool)

---

### Story 5-1: Entity data model and spatial hierarchy

**As a** developer
**I want** typed data models for all entity types and their spatial relationships
**So that** containment checking, area computation, and scrutiny work on a well-structured entity graph

**Acceptance Criteria**
- [ ] AC1: `Entity` base model: id, type, layer, handle (CAD reference), bounding_box
- [ ] AC2: Subtypes: `PolylineEntity`, `LineEntity`, `ArcEntity`, `CircleEntity`, `TextEntity`, `BlockRefEntity`
- [ ] AC3: `SpatialHierarchy` represents parent/child containment relationships
- [ ] AC4: Entity models are Pydantic v2

**Dependencies:** Story 3-1
**Size:** S

---

### Story 5-2: `entity_draw_polyline` and `entity_draw_line` MCP tools

**As an** AI client
**I want** to draw polylines and lines on specified layers
**So that** plot boundaries, building footprints, and setback lines can be created

**Acceptance Criteria**
- [ ] AC1: `entity_draw_polyline(points: list[tuple], layer, closed, name?)` draws a polyline — returns entity handle
- [ ] AC2: `entity_draw_line(start, end, layer, name?)` draws a line segment — returns entity handle
- [ ] AC3: Both tools validate the target layer exists before drawing (error: `LAYER_NOT_FOUND`)
- [ ] AC4: `closed=true` polylines produce geometrically closed polylines (start == end point verified)
- [ ] AC5: Both tools run on ezdxf AND COM backends
- [ ] AC6: Each tool completes within 2 seconds (NFR1)
- [ ] AC7: Write operations wrapped in snapshot/rollback

**Dependencies:** Story 5-1, Story 2-4
**Size:** M

---

### Story 5-3: `entity_draw_arc`, `entity_draw_circle` MCP tools

**As an** AI client
**I want** to draw arcs and circles
**So that** rounded building features and reference geometry can be drawn

**Acceptance Criteria**
- [ ] AC1: `entity_draw_arc(center, radius, start_angle, end_angle, layer)` draws an arc
- [ ] AC2: `entity_draw_circle(center, radius, layer)` draws a circle
- [ ] AC3: Both validate layer existence
- [ ] AC4: Both run on ezdxf AND COM backends, complete within 2 seconds (NFR1)

**Dependencies:** Story 5-2
**Size:** S

---

### Story 5-4: `entity_add_text` and `entity_insert_block` MCP tools

**As an** AI client
**I want** to add text and block references on PreDCR layers
**So that** annotations, labels, and standard block symbols are placed correctly (FR8, FR9)

**Acceptance Criteria**
- [ ] AC1: `entity_add_text(text, position, layer, height, style?)` inserts MText on the specified layer
- [ ] AC2: `entity_insert_block(block_name, position, layer, scale?, rotation?)` inserts a block reference
- [ ] AC3: Both validate layer existence
- [ ] AC4: Both run on ezdxf AND COM backends

**Dependencies:** Story 5-2
**Size:** M

---

### Story 5-5: `entity_move`, `entity_copy`, `entity_delete`, `entity_change_layer` MCP tools

**As an** AI client
**I want** to modify existing entities
**So that** the AI can correct and refine the drawing without re-drawing from scratch (FR10)

**Acceptance Criteria**
- [ ] AC1: `entity_move(handle, displacement)` translates an entity by offset vector
- [ ] AC2: `entity_copy(handle, displacement)` creates a copy at offset
- [ ] AC3: `entity_delete(handle)` removes entity from drawing
- [ ] AC4: `entity_change_layer(handle, new_layer)` moves entity to a different layer
- [ ] AC5: All tools return error `ENTITY_NOT_FOUND` if handle is invalid
- [ ] AC6: All write operations wrapped in snapshot/rollback
- [ ] AC7: All tools work on both backends, complete within 2 seconds (NFR1)

**Dependencies:** Story 5-2, Story 2-4
**Size:** M

---

### Story 5-6: `entity_query` MCP tool

**As an** AI client
**I want** to query entities by layer, type, or spatial boundary
**So that** the AI can identify and target specific entities for modification or analysis (FR12)

**Acceptance Criteria**
- [ ] AC1: `entity_query(layer?, entity_type?, bounding_box?)` returns matching entity handles with metadata
- [ ] AC2: Spatial boundary filter uses bounding box intersection
- [ ] AC3: Returns empty list (not error) when no entities match
- [ ] AC4: Works on both backends

**Dependencies:** Story 5-1
**Size:** M

---

### Story 5-7: `entity_close_polyline` MCP tool

**As an** AI client
**I want** to close an open polyline
**So that** PreDCR closure requirements are met without redrawing (FR11)

**Acceptance Criteria**
- [ ] AC1: `entity_close_polyline(handle)` sets the polyline's closed flag and connects start to end point
- [ ] AC2: Returns the closure gap distance before closing (for AI decision-making)
- [ ] AC3: Returns error if handle is not a polyline
- [ ] AC4: Works on both backends; wrapped in snapshot/rollback

**Dependencies:** Story 5-5
**Size:** S

---

## Epic 6: Verification Engine

**Goal:** A complete pre-scrutiny verification gate that checks closure, containment, naming, and entity counts, reporting every failure with a suggested correction.

**FR coverage:** FR13, FR14, FR15, FR16, FR17, FR18
**NFR coverage:** NFR14 (zero false positives)

---

### Story 6-1: Closure verification engine

**As a** developer
**I want** a closure verification engine that checks all polylines for geometric closure
**So that** non-closed polylines are caught before scrutiny (FR13)

**Acceptance Criteria**
- [ ] AC1: `verify_closure()` checks all polylines in the active drawing
- [ ] AC2: Returns `passed: bool, failures: list[{entity_handle, layer, gap_distance, suggested_action}]`
- [ ] AC3: Tolerance for closure gap is configurable (default: 0.001 drawing units)
- [ ] AC4: Zero false positives on correctly closed polylines (NFR14)
- [ ] AC5: `suggested_action` is "Use entity_close_polyline(handle)" for each failure (FR17)

**Dependencies:** Story 5-6
**Size:** M

---

### Story 6-2: Containment verification engine

**As a** developer
**I want** a containment verification engine that checks parent/child spatial relationships
**So that** entities on child layers are confirmed to lie within their parent boundaries (FR14)

**Acceptance Criteria**
- [ ] AC1: `verify_containment()` checks all entity/layer hierarchy relationships using Shapely
- [ ] AC2: Returns `passed: bool, failures: list[{child_handle, parent_handle, violation_type, suggested_action}]`
- [ ] AC3: Uses Shapely `contains` / `within` for polygon containment checks
- [ ] AC4: Handles multi-polygon parent boundaries
- [ ] AC5: Zero false positives on correctly contained entities (NFR14)

**Dependencies:** Story 5-6, Story 8-1 (Shapely setup)
**Size:** L

---

### Story 6-3: Naming validation engine

**As a** developer
**I want** a naming validation engine that checks entity names against PreDCR conventions
**So that** named entities conform to authority requirements (FR15)

**Acceptance Criteria**
- [ ] AC1: `verify_naming()` checks all named entities against PreDCR naming rules
- [ ] AC2: Returns `passed: bool, failures: list[{entity_handle, current_name, violation, suggested_name}]`
- [ ] AC3: Uses the same naming rule catalog as `layer_validate_naming` (Story 3-4)
- [ ] AC4: Zero false positives on correctly named entities (NFR14)

**Dependencies:** Story 3-4, Story 5-6
**Size:** M

---

### Story 6-4: Minimum entity count verification

**As a** developer
**I want** a minimum entity check that verifies required layers have at least one entity
**So that** drawings with empty required layers are flagged before scrutiny (FR16)

**Acceptance Criteria**
- [ ] AC1: `verify_entity_counts(building_type)` checks that each required layer has at least the minimum required entity count
- [ ] AC2: Returns `passed: bool, failures: list[{layer, required_count, actual_count, suggested_action}]`
- [ ] AC3: Minimum counts defined in the PreDCR layer catalog (Story 4-1)

**Dependencies:** Story 4-1, Story 5-6
**Size:** S

---

### Story 6-5: `verify_all` MCP tool — full verification pass

**As an** AI client
**I want** to run all verification checks in a single tool call
**So that** the AI can confirm drawing readiness before scrutiny without multiple round-trips (FR18)

**Acceptance Criteria**
- [ ] AC1: `verify_all(building_type)` runs: closure, containment, naming, entity counts — in order
- [ ] AC2: Returns aggregated result: `passed: bool, checks: { closure, containment, naming, entity_counts }` each with their failure lists
- [ ] AC3: Short-circuits after closure failures (containment cannot be valid if polylines are open) — reports this clearly
- [ ] AC4: Clean, correctly prepared drawing returns `passed: true` with empty failure lists

**Dependencies:** Story 6-1, Story 6-2, Story 6-3, Story 6-4
**Size:** M

---

## Epic 7: DCR Rule Config System

**Goal:** A config file loader that reads authority-specific DCR rules from YAML/JSON, validates them on load, tracks config version, and makes rules available to the scrutiny engine.

**FR coverage:** FR19, FR20, FR26
**NFR coverage:** NFR20, NFR23

---

### Story 7-1: DCR rule config schema and Pydantic models

**As a** developer
**I want** a documented, Pydantic-validated schema for DCR rule config files
**So that** engineers can write authority rule configs without ambiguity (FR19, NFR20)

**Acceptance Criteria**
- [ ] AC1: Schema covers: FSI limits by zone, ground coverage %, setback distances (front/side/rear), parking ratio per building type, height restrictions
- [ ] AC2: Schema is defined as Pydantic v2 models
- [ ] AC3: Schema is documented as a YAML template with inline comments
- [ ] AC4: Schema docs published in `docs/dcr-config-schema.md`
- [ ] AC5: A sample config for a generic residential authority is included as `configs/sample-residential.yaml`

**Dependencies:** Story 1-5
**Size:** M

---

### Story 7-2: `config_load` MCP tool — config file loader

**As an** AI client
**I want** to load a DCR rule config file from a custom file path
**So that** any authority's rules can be activated without code changes (FR19, FR42)

**Acceptance Criteria**
- [ ] AC1: `config_load(path)` loads and parses a YAML or JSON DCR rule config file
- [ ] AC2: `DCR_CONFIG_PATH` env var sets the default config path (FR42)
- [ ] AC3: Config is validated against the Pydantic schema on load (FR20)
- [ ] AC4: Schema validation errors are returned as structured error with field-level detail
- [ ] AC5: Config files are read-only during scrutiny execution — the engine cannot modify them (NFR23)
- [ ] AC6: Successful load returns: config version, authority name, rule count, zone count

**Dependencies:** Story 7-1
**Size:** M

---

### Story 7-3: `config_validate` and `config_get_version` MCP tools

**As an** AI client
**I want** to validate a config file without loading it and retrieve version metadata
**So that** config errors are caught before a scrutiny run begins (FR20, FR26)

**Acceptance Criteria**
- [ ] AC1: `config_validate(path)` validates schema without loading into active state — dry run
- [ ] AC2: Returns `valid: bool, errors: list[{field, message}]`
- [ ] AC3: `config_get_version()` returns version string and checksum of the currently loaded config
- [ ] AC4: Config version is recorded in every scrutiny run result (FR26)

**Dependencies:** Story 7-2
**Size:** S

---

## Epic 8: Area Computation Engine

**Goal:** Precise polygon-based area calculations using Shapely for all key DCR metrics: plot area, built-up area, carpet area, FSI, and ground coverage.

**FR coverage:** FR22
**NFR coverage:** NFR4 (10s), NFR11, NFR12

---

### Story 8-1: Shapely geometry integration and polygon extraction

**As a** developer
**I want** a geometry layer that extracts closed polylines as Shapely polygons
**So that** all area computations use accurate, floating-point-safe polygon operations (NFR11, NFR12)

**Acceptance Criteria**
- [ ] AC1: `GeometryEngine.extract_polygon(entity_handle)` returns a `shapely.Polygon` from a closed polyline
- [ ] AC2: Returns error if polyline is not closed
- [ ] AC3: Extracts polygons from both ezdxf and COM backends
- [ ] AC4: Unit tests verify area accuracy to 0.01 sqm against known test polygons (NFR11)

**Dependencies:** Story 6-1 (closure verification ensures polys are closed)
**Size:** M

---

### Story 8-2: `area_compute_plot` MCP tool

**As an** AI client
**I want** to compute the plot boundary area
**So that** the base area for all FSI and coverage calculations is established

**Acceptance Criteria**
- [ ] AC1: `area_compute_plot()` identifies the plot boundary layer and computes its polygon area
- [ ] AC2: Returns area in square meters accurate to 0.01 sqm (NFR11)
- [ ] AC3: Returns error `PLOT_BOUNDARY_NOT_FOUND` if no plot boundary entity exists
- [ ] AC4: Computation completes within 10 seconds (NFR4)

**Dependencies:** Story 8-1
**Size:** S

---

### Story 8-3: `area_compute_builtup` and `area_compute_carpet` MCP tools

**As an** AI client
**I want** to compute built-up area and carpet area
**So that** these values are available for FSI and rule checking

**Acceptance Criteria**
- [ ] AC1: `area_compute_builtup()` sums areas of all floor plate polygons across all floor layers
- [ ] AC2: `area_compute_carpet()` computes carpet area per PreDCR definition (built-up minus walls/ducts)
- [ ] AC3: Both return per-floor breakdown and total
- [ ] AC4: Area accuracy to 0.01 sqm (NFR11)

**Dependencies:** Story 8-2
**Size:** M

---

### Story 8-4: `area_compute_fsi`, `area_compute_coverage`, `area_compute_all` MCP tools

**As an** AI client
**I want** to compute FSI, ground coverage, and open space percentage
**So that** the scrutiny engine has all required area metrics

**Acceptance Criteria**
- [ ] AC1: `area_compute_fsi()` = total built-up area / plot area; accurate to 3 decimal places (NFR12)
- [ ] AC2: `area_compute_coverage()` = ground floor footprint / plot area; accurate to 3 decimal places (NFR12)
- [ ] AC3: `area_compute_all()` runs all area computations and returns a structured area table
- [ ] AC4: `area_compute_all()` completes within 10 seconds (NFR4)
- [ ] AC5: All computations are reproducible — same drawing + same config always yields identical results (NFR13)

**Dependencies:** Story 8-3
**Size:** M

---

## Epic 9: AutoDCR Scrutiny Engine

**Goal:** A complete DCR rule evaluation engine that checks every loaded rule, produces per-rule pass/fail results with computed vs. permissible values, and supports iterative correction.

**FR coverage:** FR21, FR22, FR23, FR24, FR25, FR31
**NFR coverage:** NFR3 (30s), NFR12, NFR13

---

### Story 9-1: Rule evaluation engine framework

**As a** developer
**I want** a rule evaluation framework that runs each DCR rule as a pluggable check function
**So that** new rule types can be added without modifying the engine core

**Acceptance Criteria**
- [ ] AC1: `RuleEngine` takes loaded DCR config + computed area metrics + drawing geometry
- [ ] AC2: Each rule type is a class implementing `RuleChecker.check() → RuleResult`
- [ ] AC3: `RuleResult` contains: rule_id, rule_name, status (pass/fail/deviation), computed_value, permissible_value, deviation, suggested_remediation
- [ ] AC4: Engine aggregates all rule results into a `ScrutinyReport`
- [ ] AC5: Adding a new rule checker requires only creating a new class and registering it — no core changes

**Dependencies:** Story 7-2, Story 8-4
**Size:** M

---

### Story 9-2: FSI rule checker

**As a** developer
**I want** an FSI rule checker that compares computed FSI against the permissible FSI for the zone
**So that** FSI violations are detected and reported with computed vs. permissible values (FR23)

**Acceptance Criteria**
- [ ] AC1: `FSIRuleChecker` loads FSI limits from config by zone/building_type
- [ ] AC2: Returns pass if computed FSI ≤ permissible FSI (within 3 decimal places, NFR12)
- [ ] AC3: Returns fail with computed FSI, permissible FSI, deviation (%), and remediation suggestion
- [ ] AC4: Remediation suggestion includes: "Reduce built-up area by X sqm on floor Y" (FR31)
- [ ] AC5: Matches manual calculation for FSI on 5 known test drawings

**Dependencies:** Story 9-1
**Size:** M

---

### Story 9-3: Ground coverage and setback rule checkers

**As a** developer
**I want** ground coverage and setback rule checkers
**So that** these critical DCR rules are evaluated in the scrutiny pass

**Acceptance Criteria**
- [ ] AC1: `GroundCoverageChecker` compares computed coverage against permissible coverage from config
- [ ] AC2: `SetbackChecker` measures minimum distances from plot boundary to building footprint (front/side/rear)
- [ ] AC3: SetbackChecker uses Shapely `distance()` for accurate setback measurement
- [ ] AC4: Both return pass/fail with computed and permissible values and remediation suggestion
- [ ] AC5: Setback violations include which setback line failed (front/side/rear)

**Dependencies:** Story 9-2
**Size:** M

---

### Story 9-4: Parking ratio and height restriction rule checkers

**As a** developer
**I want** parking ratio and height restriction rule checkers
**So that** all common DCR rule types are covered in the MVP scrutiny engine

**Acceptance Criteria**
- [ ] AC1: `ParkingChecker` counts parking entities on parking layer, divides by dwelling/unit count from config or drawing annotation
- [ ] AC2: `HeightChecker` reads building height entity from drawing and compares to permissible height from config
- [ ] AC3: Both return pass/fail with computed and permissible values
- [ ] AC4: Both provide remediation suggestions (FR31)

**Dependencies:** Story 9-3
**Size:** M

---

### Story 9-5: `autodcr_run_scrutiny` MCP tool — full scrutiny pass

**As an** AI client
**I want** to run a full DCR scrutiny pass in a single tool call
**So that** the AI can produce a complete compliance result without multiple rule-specific calls (FR21)

**Acceptance Criteria**
- [ ] AC1: `autodcr_run_scrutiny(config_path?, zone?, building_type?)` runs all registered rule checkers
- [ ] AC2: Returns complete `ScrutinyReport`: overall_status (compliant/non-compliant), rule_results list, area_table, config_version_used
- [ ] AC3: Full scrutiny pass completes within 30 seconds (NFR3)
- [ ] AC4: Results are fully reproducible — identical drawing + config always produces identical output (NFR13)
- [ ] AC5: Config version is recorded in the scrutiny report (FR26)
- [ ] AC6: Runs on both ezdxf and COM backends

**Dependencies:** Story 9-4
**Size:** M

---

### Story 9-6: Dry-run mode and iterative correction loop

**As an** AI client
**I want** to run scrutiny in test mode and re-run after corrections
**So that** the AI can iterate on the drawing until all rules pass without affecting the archive (FR24, FR25)

**Acceptance Criteria**
- [ ] AC1: `autodcr_run_scrutiny(dry_run=True)` runs full scrutiny without writing to the archive
- [ ] AC2: After entity modification via entity management tools, `autodcr_run_scrutiny()` re-runs correctly on the modified drawing
- [ ] AC3: Iterative loop: modify entities → re-run scrutiny → check results — repeatable without server restart
- [ ] AC4: Dry-run result is identical to non-dry-run result (only archival differs)

**Dependencies:** Story 9-5, Story 5-5
**Size:** M

---

## Epic 10: Report Generation

**Goal:** Generate human-readable, self-contained compliance reports in PDF, DOCX, and JSON formats that contain all information required for architect sign-off.

**FR coverage:** FR27, FR28, FR29, FR30, FR31
**NFR coverage:** NFR5 (30s)

---

### Story 10-1: Report data model and assembly

**As a** developer
**I want** a structured report data model that assembles all scrutiny results into a report payload
**So that** all three report formats (PDF, DOCX, JSON) share a single source of truth

**Acceptance Criteria**
- [ ] AC1: `Report` Pydantic model: project_name, date, config_version, rule_set_name, area_table, rule_results, overall_status, metadata
- [ ] AC2: `ReportAssembler.from_scrutiny(ScrutinyReport) → Report` constructs the report payload
- [ ] AC3: Report includes: project name, date, config version, rule set used, all computed values (FR30)
- [ ] AC4: Unit tests verify all fields populated correctly from a mock ScrutinyReport

**Dependencies:** Story 9-5
**Size:** S

---

### Story 10-2: `report_generate_pdf` MCP tool

**As an** AI client
**I want** to generate a PDF compliance report
**So that** the architect has a print-ready, self-contained document for review and sign-off (FR27)

**Acceptance Criteria**
- [ ] AC1: `report_generate_pdf(output_path?)` generates a PDF using ReportLab
- [ ] AC2: PDF contains: cover page (project, date, overall status), rule result table (rule name, computed, permissible, status), area summary table, objection list for failed rules
- [ ] AC3: Overall status is visually prominent (COMPLIANT = green header, NON-COMPLIANT = red header)
- [ ] AC4: PDF is readable and navigable without access to the live system (FR30)
- [ ] AC5: PDF generation completes within 30 seconds (NFR5)
- [ ] AC6: Returns output file path on success

**Dependencies:** Story 10-1
**Size:** L

---

### Story 10-3: `report_generate_docx` MCP tool

**As an** AI client
**I want** to generate a DOCX objection list
**So that** non-compliant rules are documented in an editable format for authority submission (FR28)

**Acceptance Criteria**
- [ ] AC1: `report_generate_docx(output_path?)` generates a DOCX using python-docx
- [ ] AC2: DOCX contains: objection list table (rule, computed value, permissible value, violation description) for all failed rules only
- [ ] AC3: Compliant drawings produce a DOCX with empty objection list and a "NO OBJECTIONS" statement
- [ ] AC4: Includes all metadata fields (FR30)
- [ ] AC5: DOCX generation completes within 30 seconds (NFR5)

**Dependencies:** Story 10-1
**Size:** M

---

### Story 10-4: `report_generate_json` MCP tool

**As an** AI client
**I want** to generate a JSON compliance report
**So that** scrutiny results can be consumed programmatically by other systems (FR29)

**Acceptance Criteria**
- [ ] AC1: `report_generate_json(output_path?)` serializes the `Report` Pydantic model to JSON
- [ ] AC2: JSON schema is stable — field names do not change between runs for the same config version
- [ ] AC3: JSON report includes all fields from the Report model (FR30)
- [ ] AC4: Generation completes within 30 seconds (NFR5)
- [ ] AC5: JSON is pretty-printed with 2-space indentation

**Dependencies:** Story 10-1
**Size:** S

---

## Epic 11: Workflow Orchestration & Archival

**Goal:** End-to-end pipeline coordination, SQLite archival of all scrutiny artifacts, audit trail, and archive retrieval — making every scrutiny run legally defensible and re-submittable.

**FR coverage:** FR32, FR33, FR34, FR35, FR36
**NFR coverage:** NFR8, NFR9, NFR10

---

### Story 11-1: SQLite schema and ORM setup

**As a** developer
**I want** a SQLite database schema that stores all scrutiny run artifacts
**So that** every run is archived in an ACID-compliant store (NFR9)

**Acceptance Criteria**
- [ ] AC1: Schema tables: `scrutiny_runs`, `run_artifacts`, `audit_log`
- [ ] AC2: `scrutiny_runs`: id, project_name, date, config_version, overall_status, drawing_path, report_paths
- [ ] AC3: `run_artifacts`: run_id, artifact_type (drawing/config/report), file_path, checksum
- [ ] AC4: `audit_log`: timestamp, tool_name, parameters_hash, outcome, run_id
- [ ] AC5: Schema created via SQLAlchemy ORM; migrations managed with Alembic or equivalent
- [ ] AC6: `ARCHIVE_PATH` env var controls database and artifact storage location (FR43)
- [ ] AC7: All DB writes use ACID transactions (NFR9)

**Dependencies:** Story 1-1
**Size:** M

---

### Story 11-2: Scrutiny run archival

**As a** developer
**I want** all scrutiny run artifacts archived automatically after a completed run
**So that** the system is auditable and re-submittable (FR32, NFR9)

**Acceptance Criteria**
- [ ] AC1: After `autodcr_run_scrutiny()` + `report_generate_*()`, `workflow_archive_run()` stores: drawing file, DCR config snapshot (copy), scrutiny results (JSON), all generated reports
- [ ] AC2: Archival is all-or-nothing (ACID) — a partial run is not archived (NFR9)
- [ ] AC3: Archive records config version for every run (FR26)
- [ ] AC4: Returns run_id for retrieval

**Dependencies:** Story 11-1, Story 10-4
**Size:** M

---

### Story 11-3: `workflow_retrieve_run` MCP tool — archive retrieval

**As an** AI client
**I want** to retrieve a previously archived scrutiny run
**So that** architects can access historic compliance results for re-submission or dispute resolution (FR33)

**Acceptance Criteria**
- [ ] AC1: `workflow_retrieve_run(run_id?, project_name?, date?, config_version?)` returns matching runs
- [ ] AC2: Returns list of runs with metadata when multiple matches exist
- [ ] AC3: Returns file paths for all artifacts of a specific run
- [ ] AC4: Returns error `RUN_NOT_FOUND` if no matching runs

**Dependencies:** Story 11-2
**Size:** S

---

### Story 11-4: `workflow_get_audit_trail` MCP tool

**As an** AI client
**I want** to retrieve the audit trail for a workflow session
**So that** all tool invocations and their outcomes are traceable (FR34)

**Acceptance Criteria**
- [ ] AC1: `workflow_get_audit_trail(run_id?, session_id?)` returns ordered list of tool calls with timestamps, parameters, and outcomes
- [ ] AC2: Every MCP tool call is logged to `audit_log` automatically (not just scrutiny tools)
- [ ] AC3: Audit log entries are immutable once written
- [ ] AC4: Returns error if no matching session found

**Dependencies:** Story 11-1
**Size:** M

---

### Story 11-5: `workflow_run_pipeline` MCP tool — end-to-end single call

**As an** AI client
**I want** to run the complete PreDCR → Verification → Area Computation → Scrutiny → Report pipeline in a single tool call
**So that** the AI can deliver a complete, archived, submission-ready result from a single instruction (FR36)

**Acceptance Criteria**
- [ ] AC1: `workflow_run_pipeline(drawing_path?, building_type, config_path?, output_formats: ["pdf","docx","json"])` runs the entire pipeline end-to-end
- [ ] AC2: Pipeline stages: open/create drawing → predcr_run_setup → verify_all → area_compute_all → autodcr_run_scrutiny → report_generate_* → workflow_archive_run
- [ ] AC3: Returns a pipeline summary: each stage status, overall compliance result, archived run_id, report file paths
- [ ] AC4: If any stage fails with `recoverable: false`, pipeline halts and drawing is rolled back (FR35, NFR8)
- [ ] AC5: If verify_all fails, pipeline halts before scrutiny and returns the verification failures with suggested fixes
- [ ] AC6: Pipeline can be re-run after corrections without data loss

**Dependencies:** Story 11-2, Story 9-6, Story 6-5, Story 4-4
**Size:** L

---

## Dependency Map

```
Epic 1 (Foundation)
  └─► Epic 2 (CAD Interface)
        ├─► Epic 3 (Layer Management)
        │     └─► Epic 4 (PreDCR Engine)
        ├─► Epic 5 (Entity Management)
        │     └─► Epic 6 (Verification Engine)
        └─► Epic 8 (Area Computation) ◄─────────────┐
              │                                       │
Epic 7 (DCR Config) ─────────────────────────────────┤
              │                                       │
              └─► Epic 9 (AutoDCR Scrutiny) ──────────┘
                    └─► Epic 10 (Report Generation)
                          └─► Epic 11 (Workflow Orchestration)
```

---

## Story Count Summary

| Epic | Stories | Total Size |
|---|---|---|
| E1: MCP Server Foundation | 5 | ~3 days |
| E2: CAD Interface Layer | 5 | ~4 days |
| E3: Layer Management | 4 | ~3 days |
| E4: PreDCR Engine | 5 | ~3.5 days |
| E5: Entity Management | 7 | ~4 days |
| E6: Verification Engine | 5 | ~3.5 days |
| E7: DCR Rule Config | 3 | ~2 days |
| E8: Area Computation | 4 | ~2.5 days |
| E9: AutoDCR Scrutiny | 6 | ~4.5 days |
| E10: Report Generation | 4 | ~4 days |
| E11: Workflow Orchestration | 5 | ~3 days |
| **Total** | **53 stories** | **~37 dev days** |

---

## MCP Tool Registry (Complete)

| Tool | Epic | FR |
|---|---|---|
| `cad_open_drawing` | E2 | FR1 |
| `cad_create_drawing` | E2 | FR2 |
| `cad_save_drawing` | E2 | FR3 |
| `cad_get_metadata` | E2 | FR4 |
| `cad_close_drawing` | E2 | FR1 |
| `cad_select_backend` | E2 | FR5 |
| `layer_create` | E3 | FR6 |
| `layer_delete` | E3 | — |
| `layer_get` | E3 | FR12 |
| `layer_list` | E3 | FR12 |
| `layer_set_properties` | E3 | — |
| `layer_set_state` | E3 | — |
| `layer_validate_naming` | E3 | FR6 |
| `predcr_create_layers` | E4 | FR6 |
| `predcr_get_layer_spec` | E4 | FR6 |
| `predcr_run_setup` | E4 | FR6 |
| `predcr_validate_drawing` | E4 | FR15 |
| `entity_draw_polyline` | E5 | FR7 |
| `entity_draw_line` | E5 | FR7 |
| `entity_draw_arc` | E5 | FR7 |
| `entity_draw_circle` | E5 | FR7 |
| `entity_add_text` | E5 | FR8, FR9 |
| `entity_insert_block` | E5 | FR9 |
| `entity_move` | E5 | FR10 |
| `entity_copy` | E5 | FR10 |
| `entity_delete` | E5 | FR10 |
| `entity_change_layer` | E5 | FR10 |
| `entity_query` | E5 | FR12 |
| `entity_close_polyline` | E5 | FR11 |
| `verify_closure` | E6 | FR13, FR17 |
| `verify_containment` | E6 | FR14, FR17 |
| `verify_naming` | E6 | FR15, FR17 |
| `verify_entity_counts` | E6 | FR16, FR17 |
| `verify_all` | E6 | FR18 |
| `config_load` | E7 | FR19, FR20 |
| `config_validate` | E7 | FR20 |
| `config_get_version` | E7 | FR26 |
| `area_compute_plot` | E8 | FR22 |
| `area_compute_builtup` | E8 | FR22 |
| `area_compute_carpet` | E8 | FR22 |
| `area_compute_fsi` | E8 | FR22 |
| `area_compute_coverage` | E8 | FR22 |
| `area_compute_all` | E8 | FR22 |
| `autodcr_run_scrutiny` | E9 | FR21, FR23, FR24, FR25 |
| `autodcr_get_remediation` | E9 | FR31 |
| `report_generate_pdf` | E10 | FR27, FR30 |
| `report_generate_docx` | E10 | FR28, FR30 |
| `report_generate_json` | E10 | FR29, FR30 |
| `workflow_run_pipeline` | E11 | FR36 |
| `workflow_archive_run` | E11 | FR32 |
| `workflow_retrieve_run` | E11 | FR33 |
| `workflow_get_audit_trail` | E11 | FR34 |

**Total MCP tools: 52** (within the ~60 tool target from PRD)
