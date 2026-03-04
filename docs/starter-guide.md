# LCS CAD MCP — Starter Guide

This guide shows you how to use the LCS CAD MCP tools from Claude Desktop chat using plain English prompts. No coding required.

---

## Prerequisites

- Claude Desktop installed and running
- LCS CAD MCP server connected (green indicator in Claude Desktop)
- A DXF drawing file, or let Claude create one from scratch

To verify the server is connected, ask Claude:
> "Ping the CAD server"

Claude will call `cad_ping` and respond with `pong: true`.

---

## Quick Reference — What Can You Ask?

| Goal | Example prompt |
|------|----------------|
| Create a new drawing | "Create a new CAD drawing called Site Plan" |
| Open an existing file | "Open the drawing at /tmp/myplot.dxf" |
| Set up PreDCR layers | "Set up PreDCR layers for a residential building" |
| Draw the plot boundary | "Draw the plot boundary as a polyline on layer PREDCR-PLOT" |
| Compute plot area | "Calculate the plot area from the PREDCR-PLOT layer" |
| Load DCR rules | "Load the DCR config from /path/to/sample-residential.yaml" |
| Run AutoDCR scrutiny | "Run AutoDCR scrutiny with authority code MCGM" |
| Generate a report | "Generate a PDF compliance report and save to /tmp/report.pdf" |
| Run the full pipeline | "Run the full DCR pipeline on /tmp/site.dxf for authority MCGM" |

---

## Workflow 1 — Create a Drawing from Scratch

### Step 1: Create a new drawing

> "Create a new metric drawing called 'Residential Site Plan'"

Claude calls `cad_new_drawing` → drawing is ready.

---

### Step 2: Set up PreDCR layers

> "Set up PreDCR layers for a residential building"

Claude calls `predcr_run_setup` with `building_type=residential`. This creates 40+ standard layers like:
- `PREDCR-PLOT` — plot boundary
- `PREDCR-WALL-EXT` — external walls
- `PREDCR-SETBACK-FRONT` — front setback line
- `PREDCR-PARKING` — parking areas
- …and more

---

### Step 3: Draw the plot boundary

> "Draw the plot boundary as a closed polyline with corners at (0,0), (20,0), (20,30), (0,30) on layer PREDCR-PLOT"

Claude calls `entity_draw_polyline` with `closed=true`.

---

### Step 4: Draw the building footprint

> "Draw the building footprint on layer PREDCR-BLD-FOOTPRINT with points (4.5, 4.5), (15.5, 4.5), (15.5, 25.5), (4.5, 25.5)"

---

### Step 5: Verify the drawing

> "Verify the drawing — check that all polylines are closed and there are no missing PreDCR layers"

Claude calls `verify_all` which runs closure, containment, naming, and entity-count checks.

---

### Step 6: Save the drawing

> "Save the drawing to /tmp/site-plan.dxf"

Claude calls `cad_save_drawing`.

---

## Workflow 2 — Open and Scrutinise an Existing Drawing

### Step 1: Open a drawing

> "Open the drawing at /Users/me/projects/site.dxf"

---

### Step 2: Load DCR rules

> "Load the DCR rules from /Users/me/lcs-cad-mcp/dcr_configs/sample-residential.yaml"

Claude calls `config_load`. You'll get back the version, authority name, and rule count.

---

### Step 3: Compute areas

> "Calculate the FSI — use PREDCR-PLOT as the plot layer and PREDCR-FLOOR-01, PREDCR-FLOOR-02 as floor layers"

Claude calls `area_compute_fsi` → returns FSI ratio, plot area, and total built-up area.

> "Calculate the ground coverage percentage"

Claude calls `area_compute_coverage`.

---

### Step 4: Run AutoDCR scrutiny

> "Run AutoDCR scrutiny with authority code MCGM"

Claude calls `autodcr_run_scrutiny`. You get a pass/fail result for each rule:

```
FSI-R1:          PASS  (computed: 0.92, limit: 1.0)
GC-R1:           PASS  (computed: 36%, limit: 40%)
SETBACK-FRONT-R1: FAIL (computed: 3.1m, minimum: 4.5m)
```

---

### Step 5: Try dry-run mode for iterative correction

> "Run a dry-run scrutiny with 3 iterations to suggest corrections"

Claude calls `autodcr_dry_run` with `max_iterations=3`. Each iteration reports which rules still fail.

---

### Step 6: Generate reports

> "Generate a PDF report and save it to /tmp/scrutiny-report.pdf"

> "Also generate a Word document version at /tmp/scrutiny-report.docx"

> "And a JSON report for the records at /tmp/scrutiny-report.json"

Claude calls `report_generate_pdf`, `report_generate_docx`, and `report_generate_json`.

---

## Workflow 3 — Full Automated Pipeline

Run everything in a single prompt:

> "Run the full DCR scrutiny pipeline on /tmp/site.dxf for authority MCGM and save all reports to /tmp/output"

Claude calls `workflow_run_pipeline` which:
1. Opens the drawing
2. Loads the configured DCR rules
3. Computes all areas
4. Runs all verifications
5. Runs AutoDCR scrutiny
6. Generates PDF, DOCX and JSON reports
7. Archives the run in the database

---

## Workflow 4 — Layer Management

### List all layers

> "List all layers in the current drawing"

### Create a custom layer

> "Create a layer called CUSTOM-SETBACK with color 3 and dashed linetype"

### Check a PreDCR layer specification

> "What are the required properties for the PREDCR-WALL-EXT layer?"

Claude calls `predcr_get_layer_spec` and returns color, linetype, and which building types require it.

### List all available PreDCR layers for commercial buildings

> "Show me all PreDCR layer specs required for commercial buildings"

---

## Workflow 5 — Entity Operations

### Query what's on a layer

> "What entities are on the PREDCR-PLOT layer?"

### Move an entity

> "Move entity with handle A1F3 by 2 metres in the X direction"

### Copy an entity

> "Copy entity A1F3 and place it 5 metres to the right"

### Delete an entity

> "Delete the entity with handle B2C4"

### Change an entity's layer

> "Move entity A1F3 to layer PREDCR-WALL-EXT"

### Add a text label

> "Add the text 'PLOT AREA: 600 sqm' at position (1, 28) with height 0.5 on layer PREDCR-DIMS"

---

## Workflow 6 — Audit Trail & History

### Retrieve a past scrutiny run

> "Retrieve scrutiny run abc-123-def-456"

### View the audit trail

> "Show me the last 20 tool events from the audit trail"

> "Show the audit trail for run abc-123-def-456"

---

## Tips

**Coordinates** are always in metres (metric drawings) or inches (imperial). Specify them as lists: `[x, y]`.

**Layer names** are case-sensitive. PreDCR layers always start with `PREDCR-`.

**File paths** must be absolute paths on the machine running the server (the Docker container or local machine).

**Backend** defaults to `ezdxf` (works everywhere). If you have AutoCAD on Windows, ask:
> "Switch the CAD backend to COM"

**Session state** — the server keeps one drawing open per session. Open a new drawing to start fresh.

---

## Common Questions

**Q: Can I draw arcs and circles?**
> "Draw a circle at centre (10, 15) with radius 3 on layer PREDCR-DIMS"
> "Draw an arc centred at (5, 5) with radius 2, from 0° to 90° on layer 0"

**Q: Can I insert blocks?**
> "Insert block TREE at position (5, 10) with scale 1.0 on layer PREDCR-LANDSCAPE"

**Q: How do I validate the config file before scrutiny?**
> "Validate the DCR config at /tmp/rules.yaml"

**Q: Can I check just one verification type?**
> "Check only closure verification on the current drawing"
> "Check only naming convention on the current drawing"
