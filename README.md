# LCS CAD MCP

An MCP (Model Context Protocol) server that exposes Pre-DCR and Auto-DCR building scrutiny workflows as AI-consumable tools. Designed to let AI assistants (Claude, etc.) open DXF drawings, validate layer conventions, compute areas, run regulatory rule checks, and generate compliance reports — all via natural language.

## What it does

- **PreDCR setup** — creates standardised layers (PREDCR-WALL-EXT, PREDCR-PLOT, etc.) and validates drawings against authority naming conventions
- **Entity management** — draws polylines, lines, arcs, circles, text and blocks; moves, copies, deletes and queries entities
- **Area computation** — calculates plot area, built-up area, carpet area, FSI and ground coverage using Shapely polygons
- **AutoDCR scrutiny** — evaluates FSI, ground coverage, setbacks, parking ratios and height restrictions against loaded DCR rule configs
- **Report generation** — produces PDF, DOCX and JSON compliance reports
- **Workflow archival** — stores scrutiny runs, tool events and audit trails in SQLite

## Architecture

```
src/lcs_cad_mcp/
├── modules/
│   ├── cad/          # Drawing lifecycle (open, new, save, backend selection)
│   ├── layers/       # Layer CRUD + property management
│   ├── predcr/       # PreDCR layer catalog and validation
│   ├── entities/     # Entity draw/query/edit tools
│   ├── verification/ # Closure, containment, naming and count checks
│   ├── area/         # FSI, coverage and area computation (Shapely)
│   ├── config/       # DCR rule config load and validation
│   ├── autodcr/      # Rule evaluation engine + dry-run mode
│   ├── reports/      # PDF/DOCX/JSON report generation
│   └── workflow/     # Pipeline orchestration and audit trail
├── backends/
│   ├── ezdxf_backend.py   # Cross-platform DXF backend (primary)
│   └── com_backend.py     # Windows AutoCAD COM backend (optional)
├── rule_engine/      # DCRConfig Pydantic models + RuleEvaluator
├── archive/          # SQLAlchemy ORM models + repository
└── session/          # DrawingSession context + SnapshotManager
```

Transport: **stdio** (default) and **SSE** supported via FastMCP 3.x.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

```bash
git clone <repo-url>
cd lcs-cad-mcp
uv sync
```

For development dependencies (pytest, ruff):

```bash
uv sync --extra dev
```

## Running the server

### stdio (for Claude Desktop / MCP clients)

```bash
uv run python -m lcs_cad_mcp
```

### SSE

```bash
uv run python -m lcs_cad_mcp --transport sse --port 8000
```

## Claude Desktop integration

See [`docs/claude-desktop-config.md`](docs/claude-desktop-config.md) for the full config snippet. Quick version:

```json
{
  "mcpServers": {
    "lcs-cad": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/lcs-cad-mcp", "python", "-m", "lcs_cad_mcp"]
    }
  }
}
```

## DCR Rule configs

YAML or JSON configs define the regulatory rules evaluated during scrutiny. Example:

```yaml
version: "1.0.0"
authority: "MCGM"
effective_date: "2024-01-01"
rules:
  - rule_id: "FSI_001"
    name: "Max FSI"
    rule_type: "FSI"
    threshold: 1.5
    unit: "ratio"
    zone_applicability: ["R1", "R2"]
```

Sample configs are in [`dcr_configs/`](dcr_configs/). Full schema: [`docs/dcr-config-schema.md`](docs/dcr-config-schema.md).

## Available MCP tools

| Category | Tools |
|----------|-------|
| CAD | `cad_ping`, `cad_open_drawing`, `cad_new_drawing`, `cad_save_drawing`, `cad_select_backend` |
| Layers | `layer_create`, `layer_delete`, `layer_get`, `layer_list`, `layer_set_properties`, `layer_set_state` |
| PreDCR | `predcr_run_setup`, `predcr_get_layer_spec`, `predcr_list_layer_specs`, `predcr_validate_drawing` |
| Entities | `entity_draw_polyline`, `entity_draw_line`, `entity_draw_arc`, `entity_draw_circle`, `entity_add_text`, `entity_insert_block`, `entity_move`, `entity_copy`, `entity_delete`, `entity_change_layer`, `entity_close_polyline`, `entity_query` |
| Verification | `verify_closure`, `verify_containment`, `verify_naming`, `verify_min_entity_count`, `verify_all` |
| Area | `area_compute_plot`, `area_calculate`, `area_compute_builtup`, `area_compute_carpet`, `area_compute_fsi`, `area_compute_coverage` |
| Config | `config_load`, `config_validate` |
| AutoDCR | `autodcr_run_scrutiny`, `autodcr_dry_run` |
| Reports | `report_generate_pdf`, `report_generate_docx`, `report_generate_json` |
| Workflow | `workflow_retrieve_run`, `workflow_get_audit_trail`, `workflow_run_pipeline` |

Full API reference: [`docs/tool-api-reference.md`](docs/tool-api-reference.md).

## Testing

```bash
uv run pytest
```

173 tests across unit and integration suites. Backends, services, rule engine and archive are all covered.

## Windows / AutoCAD COM backend

The COM backend enables live interaction with a running AutoCAD instance on Windows. See [`docs/windows-deployment-guide.md`](docs/windows-deployment-guide.md).
