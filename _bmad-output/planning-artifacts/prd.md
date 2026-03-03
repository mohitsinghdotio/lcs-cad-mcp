---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - AutoDCR_PreDCR_MCP_Server_Architecture.docx
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: govtech
  complexity: high
  projectContext: greenfield
  keyInsight: 'Full automation with architect review gate before submission. Architect trust in output is the core UX problem.'
---

# Product Requirements Document — lcs-cad-mcp

**Author:** Mohit.singh2
**Date:** 2026-03-04

## Executive Summary

**lcs-cad-mcp** is a custom Model Context Protocol (MCP) server that replicates and extends the full functionality of PreDCR (Drawing Pre-Formatting Utility) and AutoDCR (Automated Building Plan Scrutiny System) as AI-consumable tools. Any MCP-compatible AI client — Claude, Cursor, VS Code Copilot — drives the entire building plan preparation and regulatory scrutiny workflow through natural language, without requiring the architect to operate CAD software.

**Target user:** An architect or drafter whose firm uses an MCP-compatible AI assistant. Their workflow shifts from manually operating proprietary desktop utilities, mastering layer conventions, and running verification commands — to issuing natural language instructions and receiving a fully prepared, scrutinized, submission-ready drawing for review and sign-off.

**Problem being solved:** The current PreDCR/AutoDCR desktop workflow is error-prone, training-intensive, and siloed. Architects manually install proprietary utilities, master layer naming conventions, draw entities on correct layers, execute verification commands, and interpret compliance outputs. This creates friction, training overhead, and submission errors. The MCP server eliminates this by making the AI the operator of the workflow.

**What makes this special:**

- **Full automation with a human trust gate.** The AI executes 100% of the CAD workflow — layer creation, entity drawing, naming, closure verification, area computation, DCR rule checking, and report generation. The architect receives a finished, regulation-checked drawing and scrutiny report, reviews, and signs off. No CAD tool interaction required before that review gate.
- **Complete feature parity as the baseline.** 60+ MCP tools across 10 modules replicate every PreDCR and AutoDCR capability: CAD Interface, PreDCR Engine, Layer Management, Entity Management, Verification, AutoDCR Scrutiny, DCR Rule Configuration, Area Computation, Report Generation, and Workflow Orchestration.
- **Universal authority support.** DCR rules are externalized as engineer-maintained YAML/JSON config files — deployable for any Indian municipal authority without code changes.
- **Dual-mode CAD backend.** Live AutoCAD control (COM/pywin32) and headless DXF processing (ezdxf) exposed through a unified abstraction — the same tools work with or without AutoCAD installed.

**Classification:**

| Field | Value |
|---|---|
| **Project Type** | Developer Tool — MCP server exposing 60+ tools via JSON-RPC/stdio/SSE, consumed by AI clients |
| **Domain** | GovTech — Indian municipal building permit compliance (Development Control Regulations) |
| **Complexity** | High — CAD automation, dual backends, geometry engine, regulatory rule engine, consequence-bearing compliance outputs |
| **Project Context** | Greenfield — internal MVP for firm use |

## Success Criteria

### User Success

An architect provides a natural language building description to an MCP-compatible AI client. The system returns a fully prepared, scrutinized, submission-ready DWG/DXF file and compliance report (PDF/DOCX/JSON). The architect reviews, signs off, and submits — without touching any CAD tool or desktop utility. Success is measured by the architect's ability to make a confident sign-off decision from the system's output alone.

### Business Success

| Milestone | Target |
|---|---|
| First complete pipeline run (PreDCR → AutoDCR → Report) | Month 1–2 post-deployment |
| First real permit submission package prepared via system | Month 3 |
| Old PreDCR/AutoDCR desktop workflow retired as firm default | Month 6 |

### Technical Success

- End-to-end pipeline executes without drawing data loss or file corruption
- Scrutiny outputs are 100% accurate against any valid DCR rule config loaded from a custom file path
- Both COM and ezdxf backends operational and tested at launch
- Reports (PDF, DOCX, JSON) are readable and navigable enough for architect sign-off
- System recovers gracefully from partial failures without leaving drawings in a corrupted state

### Measurable Outcomes

- Zero manual CAD tool interactions required before the architect review gate
- DCR rule config loadable from any custom file path without code changes
- Reports contain: compliant/non-compliant rule list, objection list, area tables, FSI/ground coverage results

## User Journeys

### Journey 1: Architect — Happy Path (Full Pipeline)

**Persona:** Rahul, an architect at the firm. Technically comfortable, uses Cursor daily, assigned to a new residential project submission.

**Opening Scene:** Rahul has a building brief — plot dimensions, FSI limits, proposed floors, parking requirements. The old workflow: 2–3 hours of manual PreDCR setup, 40+ layers, entity drawing, verification, scrutiny. Today he opens Cursor.

**Rising Action:** Rahul types: *"Create a new residential building drawing. Plot area 500 sqm, ground + 3 floors, FSI 2.0, two covered parking spaces."* The MCP server opens a new DXF file, creates all required PreDCR layers with correct naming, draws the plot boundary, building footprint, parking entities, and setback lines on their respective layers. The AI reports: *"Drawing prepared. 43 layers created. All entities placed. Running verification."* Closure checks pass. Containment checks pass. Naming validation passes.

**Climax:** AutoDCR scrutiny runs against the loaded DCR rule config. FSI: compliant. Ground coverage: compliant. Setbacks: compliant. Parking ratio: compliant. PDF and JSON reports generated. Rahul opens the PDF — a clean checklist, every rule checked, every value computed, every result green.

**Resolution:** Rahul signs the drawings digitally and packages the report for submission. Total time: 25 minutes vs. 3 hours. The old desktop workflow is already irrelevant.

---

### Journey 2: Architect — Failed Scrutiny Recovery (Edge Case)

**Opening Scene:** Commercial building, tighter plot, aggressive FSI. PreDCR pipeline completes. Scrutiny runs.

**Rising Action:** FSI violation. Proposed built-up area exceeds permissible by 8%. System generates a red-flagged report on rule R-14 with computed vs. permissible values and a DOCX objection list. AI presents: *"FSI violation: computed 2.18, permissible 2.0. Suggested remediation: reduce floor plate on level 3 by ~90 sqm."*

**Climax:** Rahul instructs: *"Reduce the third floor footprint by 95 sqm and re-run scrutiny."* MCP server modifies entities, recalculates areas, re-runs the full scrutiny pipeline.

**Resolution:** Second run — all rules pass. Updated report generated. Correction loop completed entirely within the AI conversation — no manual CAD editing, no desktop tools.

---

### Journey 3: Engineer — DCR Rule Config Setup (Admin/Ops)

**Persona:** Dev, a developer at the firm who deployed the MCP server. New project requires an authority whose DCR rules aren't yet configured.

**Opening Scene:** Dev receives the authority's DCR handbook as a PDF and must translate relevant rules into YAML config format.

**Rising Action:** Dev reads the config schema, creates a YAML file at the custom config path defining FSI limits by zone, ground coverage percentages, setback distances, parking ratios, and height restrictions. He points the MCP server to the new config path and triggers a test scrutiny run on a sample drawing.

**Resolution:** Rule engine loads config, parses all rules without errors, produces a test scrutiny report matching manual calculations from the DCR handbook. New authority's rules are live.

---

### Journey 4: Architect — Headless Mode (No AutoCAD Installed)

**Opening Scene:** Rahul working from home. AutoCAD workstation is at the office. He needs a quick drawing check.

**Rising Action:** MCP server runs in headless mode — ezdxf backend, no AutoCAD required. Same PreDCR pipeline initiated via Cursor on his laptop.

**Resolution:** Full pipeline completes — layers created, entities drawn, verification passed, scrutiny run, report generated — without AutoCAD. Workflow is not blocked by location or software installation.

## Domain-Specific Requirements

### Compliance & Regulatory

- **DCR rule accuracy is a legal requirement.** Scrutiny outputs support building permit applications — legal submissions with financial and safety consequences. Incorrect outputs causing permit rejection or non-compliant construction are firm-level liability events.
- **Rule config versioning required.** Every scrutiny run records which DCR rule config version was used, enabling re-submission, dispute resolution, and audit of historic decisions.
- **PreDCR layer naming conventions are standardized.** Layer names, entity types, and drawing conventions must conform to the PreDCR specification exactly — deviations result in authority rejection.
- **CAD format compatibility.** DXF/DWG output defaults to AutoCAD 2018 / DXF R2018 format. Verification against specific authority portal requirements is required before first live submission; output format version is configurable.

### Technical Constraints

- **Drawing file integrity is non-negotiable.** DXF/DWG files are legal artifacts. All write operations are atomic or transactional; partial failure triggers rollback to the last valid state.
- **COM backend is Windows-only.** Live AutoCAD control via pywin32 requires Windows OS with a supported CAD application (AutoCAD, ZWCAD, BricsCAD, or GstarCAD). This is a deployment constraint, not a product limitation.
- **ezdxf backend is cross-platform** and functions as a full fallback for all PreDCR and AutoDCR operations when no live CAD session is available.
- **Geometry correctness.** Area computations and FSI calculations use Shapely for all polygon operations. Floating-point errors that produce incorrect FSI results or false compliance flags are unacceptable.

### Data Retention & Archival

- **All scrutiny artifacts are archived.** For every completed run: input drawing file, DCR rule config snapshot (or version reference), computed values (areas, FSI, ground coverage), rule-by-rule pass/fail results, and generated reports (PDF, DOCX, JSON).
- **Archive is indexed and retrievable** by project, date, and config version. SQLite is the designated store.
- **Reports are self-contained.** Generated PDF/DOCX reports include sufficient metadata (project name, date, config version, rule set, computed values) to be interpretable without access to the live system.

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. AI as CAD Operator — A New Compliance Paradigm**
Every existing building compliance tool — including SoftTech's AutoDCR/PreDCR and CivitPERMIT — positions the human as the operator. This product inverts the model: the AI client *operates* the CAD workflow; the human reviews and signs off. Compliance expertise moves from the architect's hands into the system's rule engine; the AI becomes the skilled operator.

**2. Compliance-as-Protocol (MCP-Native)**
DCR rule checking, area computation, PreDCR preparation, and scrutiny are exposed as MCP tools — making building compliance a callable service invocable by any AI client via natural language. No existing Indian building compliance tool exposes its functionality as an open protocol. The closest analogs are code linters and CI/CD pipelines — applied to building regulations for the first time.

**3. Dual-Mode Output Architecture**
- **DXF/DWG Output Mode:** Produces regulation-compliant drawing files for municipal submission
- **Pure Data Pipeline Mode:** Headless compliance engine returning structured JSON — no CAD file output; for programmatic consumption, future portal integrations, or batch processing

The same system serves today's submission requirements (DXF files) and tomorrow's direct portal integrations (data APIs) without architectural changes.

**4. Configurable Rule Engine vs. Bundled Rules**
SoftTech bundles DCR rules into proprietary releases — rule updates require a software update from the vendor. This system externalizes rules as engineer-maintained config files, enabling authority-specific deployments and rapid rule updates without vendor dependency.

### Competitive Landscape

| Dimension | SoftTech AutoDCR/CivitPERMIT | lcs-cad-mcp |
|---|---|---|
| Interaction model | Human operates desktop utility | AI client operates via natural language |
| Deployment | Proprietary desktop installation | MCP server, configurable deployment |
| Rule management | Vendor-bundled, update via software release | Engineer-maintained config files |
| Output | DXF/DWG files only | DXF/DWG files + pure JSON data pipeline |
| Integration | Standalone desktop tool | Protocol-native, any MCP client |
| Automation level | Semi-automated (human drives each step) | Fully automated (AI drives end-to-end) |

### Validation Approach

- Validate scrutiny outputs against manually computed DCR results for known test drawings before first live submission
- Verify DXF output mode and data pipeline mode produce identical compliance results for the same input
- Test rule config loading with multiple authority rule sets to validate authority-agnostic operation
- Maintain a regression suite of test drawings with known pass/fail outcomes per rule; run against every config change

## Technical Platform Requirements

lcs-cad-mcp is a Python-based MCP server. Consumers are AI clients invoking tools via the Model Context Protocol over JSON-RPC. The server communicates via stdio or SSE transport.

### Language & Runtime

| Component | Specification |
|---|---|
| Language | Python 3.11+ |
| MCP Framework | `mcp` (official SDK) or FastMCP |
| Package Manager | uv (primary), pip (fallback) |
| CAD Backend 1 | pywin32 + COM (Windows, live AutoCAD) |
| CAD Backend 2 | ezdxf (cross-platform, headless) |
| Geometry Engine | Shapely + scipy |
| Validation | Pydantic v2 (all tool parameters and data models) |
| Database | SQLite + SQLAlchemy |
| Report Generation | ReportLab (PDF), python-docx (DOCX) |
| Testing | pytest + hypothesis |

### MCP Transport & Protocol

- **Primary transport:** `stdio` — local Claude Desktop, Cursor, VS Code Copilot integration
- **Secondary transport:** `SSE` — remote/server deployments and future portal integrations
- **Protocol:** JSON-RPC 2.0 over MCP standard
- All 60+ tools registered at server startup; tool list exposed via standard MCP `tools/list` endpoint

### MCP Tool API Surface

**Naming convention:** `{module}_{action}` — e.g., `cad_open_drawing`, `predcr_create_layers`, `autodcr_run_scrutiny`, `report_generate_pdf`

| Module | Tool Prefix | Approx. Count |
|---|---|---|
| CAD Interface Layer | `cad_` | ~7 |
| PreDCR Engine | `predcr_` | ~10 |
| Layer Management | `layer_` | ~8 |
| Entity Management | `entity_` | ~10 |
| Verification Engine | `verify_` | ~6 |
| AutoDCR Scrutiny | `autodcr_` | ~8 |
| DCR Rule Config | `config_` | ~4 |
| Area Computation | `area_` | ~6 |
| Report Generation | `report_` | ~5 |
| Workflow Orchestration | `workflow_` | ~4 |

### Error Handling Contract

Every MCP tool returns:

```json
{
  "success": true | false,
  "data": {},
  "error": {
    "code": "LAYER_NOT_FOUND | CLOSURE_FAILED | DCR_VIOLATION | ...",
    "message": "Human-readable description",
    "recoverable": true | false,
    "suggested_action": "Optional remediation hint for AI client"
  }
}
```

- `recoverable: true` — AI client retries or remediates automatically
- `recoverable: false` — AI client surfaces to architect for decision; drawing rollback triggered automatically

### Installation

```bash
uv pip install lcs-cad-mcp
```

**Claude Desktop configuration:**

```json
{
  "mcpServers": {
    "lcs-cad-mcp": {
      "command": "python",
      "args": ["-m", "lcs_cad_mcp"],
      "env": {
        "DCR_CONFIG_PATH": "/path/to/dcr-rules.yaml",
        "ARCHIVE_PATH": "/path/to/archive",
        "CAD_BACKEND": "ezdxf"
      }
    }
  }
}
```

### Migration from Legacy PreDCR Drawings

Existing DWG/DXF files created with legacy PreDCR can be opened via `cad_open_drawing` and run through AutoDCR scrutiny without redrawing from scratch:

1. `cad_open_drawing(path)` — open existing drawing
2. `verify_all()` — assess current conformance state
3. Fix non-conformant layers/entities via MCP tools
4. `autodcr_run_scrutiny(config_path)` — run scrutiny
5. `report_generate_pdf()` — generate report

## Project Scoping & Phased Development

### MVP Strategy

**Approach:** Complete Replacement MVP. The product delivers value only when the full PreDCR → AutoDCR → Report pipeline is operational. Partial delivery does not retire the incumbent desktop tools and does not achieve the Month 6 workflow retirement target. All 10 modules are therefore MVP scope.

**Build order** (recommended, dependency-driven): CAD Interface → PreDCR Engine → Verification → Area Computation → DCR Rule Engine → AutoDCR Scrutiny → Report Generation → Workflow Orchestration.

**Resource:** Single developer (Python + CAD automation expertise). Build and test each module independently with mock interfaces before integration.

### MVP Scope (Phase 1)

All 4 user journeys supported. Must-have capabilities:

| Capability | Rationale |
|---|---|
| CAD Interface Layer (COM + ezdxf dual backend) | Foundation for all operations |
| PreDCR Engine — all layer/entity/naming operations | Core automation; pipeline entry point |
| Layer Management System — complete layer registry | PreDCR correctness requires exact layer spec compliance |
| Entity Management & Spatial Hierarchy | Required for containment, area, and scrutiny |
| Verification Engine — closure, containment, naming | Gate before scrutiny; prevents false compliance |
| AutoDCR Scrutiny Engine — full DCR rule checking | The compliance output; enables workflow retirement |
| DCR Rule Config System — custom file path loading | Authority-agnostic rule management |
| Area Computation Engine — FSI, coverage, carpet area | Core DCR calculations |
| Report Generation — PDF, DOCX, JSON | Architect's review artifact; required for sign-off |
| Workflow Orchestration & API | End-to-end coordination; audit trail; archival |
| SQLite archival — drawings, configs, results, reports | Legal defensibility and re-submission capability |
| Structured error handling with drawing rollback | File integrity; non-negotiable for production use |

**Out of MVP scope:** Web-based review UI, pre-bundled authority rule sets, multi-user concurrent processing, municipal portal integration, drawing diff/revision tracking.

### Post-MVP Roadmap

**Phase 2 — Growth:**
- Pre-bundled DCR rule sets for major Indian authorities (MCGM, PMRDA, BBMP, HMDA)
- Batch processing — multiple drawings in a single pipeline run
- Drawing revision tracking — diff between scrutiny runs
- Extended MCP client testing (additional IDEs and AI clients)

**Phase 3 — Expansion:**
- Web-based architect review and sign-off interface
- Direct integration with municipal e-submission portals
- Authority-managed rule set publishing and versioning
- Pure data pipeline mode as standalone API service
- Multi-firm / SaaS deployment model

### Risk Register

| Risk Type | Risk | Mitigation |
|---|---|---|
| Technical | COM automation fragility on Windows | Build ezdxf backend to full parity first; COM is enhancement, not foundation |
| Technical | Geometry precision errors in area computation | Use Shapely for all polygon ops; regression suite with known area test cases |
| Technical | Module interdependency delays end-to-end testing | Build and test each module independently with mock interfaces; integrate progressively |
| Technical | CAD format incompatible with authority portal | Configurable output format version; deployment checklist before first submission |
| Market | Architect distrust of AI-generated scrutiny output | Parallel validation: same drawing through legacy AutoDCR + MCP server, compare outputs |
| Market | DCR rule config errors producing false compliance | Mandatory test scrutiny run before first live submission; config validation on load |
| Resource | Single developer, 10 modules | Build in critical path order; prioritize CAD → PreDCR → Verification → Area → Scrutiny → Report |
| Data | Archived data loss | SQLite database backed up alongside drawing archive; storage path configurable |

## Functional Requirements

### Drawing Management

- **FR1:** AI Client can open an existing DWG or DXF file for processing
- **FR2:** AI Client can create a new blank drawing
- **FR3:** AI Client can save a drawing in DWG or DXF format
- **FR4:** AI Client can retrieve metadata about the current drawing (units, extents, entity count, layer count)
- **FR5:** AI Client can select between COM (live AutoCAD) and ezdxf (headless) backends for all drawing operations

### PreDCR Drawing Preparation

- **FR6:** AI Client can create all required PreDCR layers with correct naming conventions for a specified building type
- **FR7:** AI Client can draw polylines, lines, arcs, circles, and text entities on specified layers
- **FR8:** AI Client can assign names to entities according to PreDCR naming conventions
- **FR9:** AI Client can insert block references and MText on correct PreDCR layers
- **FR10:** AI Client can modify existing entities (move, copy, delete, change layer)
- **FR11:** AI Client can close open polylines to meet PreDCR closure requirements
- **FR12:** AI Client can query entities by layer, type, or spatial boundary

### Verification

- **FR13:** AI Client can run closure verification on all polylines in the drawing
- **FR14:** AI Client can run containment verification (child entities within parent boundaries)
- **FR15:** AI Client can run naming validation against PreDCR conventions
- **FR16:** AI Client can run minimum entity checks per required layer type
- **FR17:** System reports each verification failure with the specific entity, failure type, and suggested correction
- **FR18:** AI Client can run a complete verification pass covering all checks in a single call

### DCR Compliance Scrutiny

- **FR19:** Engineer can define DCR rules in a YAML or JSON config file and load them via a custom file path
- **FR20:** System validates a DCR rule config file on load and reports schema errors before scrutiny begins
- **FR21:** AI Client can run a full DCR scrutiny pass against the loaded rule config
- **FR22:** System computes all required areas (plot area, built-up area, carpet area, FSI, ground coverage, open space percentage) from drawing geometry
- **FR23:** System checks each DCR rule and records pass, fail, or deviation with computed and permissible values
- **FR24:** AI Client can run scrutiny in test/dry-run mode against a sample drawing without affecting the archive
- **FR25:** AI Client can modify drawing entities and re-run scrutiny in an iterative correction loop
- **FR26:** System records which DCR rule config version was used for each scrutiny run

### Report Generation

- **FR27:** System generates a compliance report in PDF format containing rule results, area tables, computed values, and pass/fail status per rule
- **FR28:** System generates a compliance report in DOCX format containing an objection list for all non-compliant rules
- **FR29:** System generates a compliance report in JSON format containing all scrutiny results as structured data
- **FR30:** All generated reports include metadata: project name, date, config version, rule set used, and computed values
- **FR31:** AI Client can retrieve remediation suggestions for each failed DCR rule

### Workflow Orchestration & Audit

- **FR32:** System archives the input drawing file, DCR rule config snapshot, computed values, and all generated reports for each completed scrutiny run
- **FR33:** Architect can retrieve a previously archived scrutiny run by project name, date, or config version
- **FR34:** System maintains an audit trail of all tool invocations and outcomes for each workflow session
- **FR35:** System rolls back all drawing modifications to the last valid state when a non-recoverable error occurs
- **FR36:** AI Client can invoke a complete end-to-end pipeline (PreDCR → Verification → Area Computation → Scrutiny → Report) in a single workflow call

### MCP Protocol & Integration

- **FR37:** System exposes all capabilities as MCP tools via stdio transport for local AI client integration
- **FR38:** System exposes all capabilities as MCP tools via SSE transport for remote/server deployment
- **FR39:** System validates all MCP tool input parameters against defined schemas before execution
- **FR40:** System returns a structured error response including error code, human-readable message, recoverability flag, and suggested remediation action for every tool failure
- **FR41:** AI Client can discover all available MCP tools and their parameter schemas via standard MCP protocol

### System Configuration

- **FR42:** Engineer can configure the active DCR rule config file path without code changes
- **FR43:** Engineer can configure the archive storage path without code changes
- **FR44:** Engineer can select the active CAD backend (COM or ezdxf) without code changes
- **FR45:** System operates fully in headless mode without requiring AutoCAD or any CAD software installation

## Non-Functional Requirements

### Performance

- **NFR1:** Individual single-entity MCP tool calls (draw, move, query) complete within 2 seconds
- **NFR2:** Full PreDCR pipeline (all layers + entities for a typical building) completes within 60 seconds
- **NFR3:** Full AutoDCR scrutiny pass (all DCR rules against a complete drawing) completes within 30 seconds
- **NFR4:** Area computation for a complete drawing completes within 10 seconds
- **NFR5:** Report generation (PDF, DOCX, and JSON) completes within 30 seconds
- **NFR6:** MCP server starts and exposes all tools within 10 seconds of process launch

### Data Integrity

- **NFR7:** All drawing write operations are atomic — either fully applied or fully rolled back; no partial writes are persisted
- **NFR8:** On any non-recoverable tool failure that modifies drawing state, the system restores the drawing to its last valid state automatically
- **NFR9:** SQLite archive operations use ACID transactions — a scrutiny run is either fully archived or not archived
- **NFR10:** System restarts after a drawing corruption event without manual file repair or database intervention

### Correctness & Accuracy

- **NFR11:** Area computations (plot area, built-up area, FSI, ground coverage) accurate to within 0.01 sqm
- **NFR12:** FSI and coverage ratio computations accurate to 3 decimal places
- **NFR13:** Scrutiny results are fully reproducible — identical drawing + identical DCR rule config always produces identical pass/fail results
- **NFR14:** Verification checks (closure, containment, naming) produce zero false positives against correctly prepared PreDCR drawings

### Reliability

- **NFR15:** A failed MCP tool call does not leave the server in an unusable state — subsequent tool calls succeed normally
- **NFR16:** COM backend connection loss is detected and reported without crashing the server; ezdxf backend remains available as fallback
- **NFR17:** Malformed or missing tool parameters return structured validation error responses, not unhandled exceptions

### Integration & Compatibility

- **NFR18:** All MCP tools are compatible with Claude Desktop, Cursor, and VS Code Copilot MCP client implementations
- **NFR19:** DXF output files are compatible with AutoCAD 2018 format or later by default; output format version is configurable
- **NFR20:** DCR rule config files conform to a documented YAML/JSON schema validated via Pydantic on load
- **NFR21:** ezdxf backend produces DXF files that open without errors in AutoCAD, ZWCAD, and BricsCAD

### Security

- **NFR22:** Drawing files and scrutiny archives are stored locally; no data is transmitted to external services
- **NFR23:** DCR rule config files are read-only during scrutiny execution — the rule engine cannot modify config files
- **NFR24:** No authentication mechanism required for MVP (local/trusted internal network deployment)
