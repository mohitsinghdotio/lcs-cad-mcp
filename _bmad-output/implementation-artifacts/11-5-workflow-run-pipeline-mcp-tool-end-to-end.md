# Story 11.5: `workflow_run_pipeline` MCP Tool — End-to-End Single Call

Status: ready-for-dev

## Story

As an **AI client**,
I want **to run the complete PreDCR → Verification → Area Computation → Scrutiny → Report pipeline in a single tool call**,
so that **the AI can deliver a complete, archived, submission-ready compliance result from a single instruction (FR36)**.

## Acceptance Criteria

1. **AC1:** `workflow_run_pipeline(drawing_path: str | None = None, building_type: str, config_path: str | None = None, output_formats: list[str] = ["pdf", "docx", "json"])` MCP tool is registered under the `workflow` module; it accepts optional `drawing_path` (opens existing) or creates a new drawing if omitted.
2. **AC2:** Pipeline stages execute in order: open/create drawing → `predcr_run_setup` → `verify_all` → `area_compute_all` → `autodcr_run_scrutiny` → `report_generate_*` (for each format in `output_formats`) → `workflow_archive_run`; each stage is called via direct Python service call (NOT via MCP tool dispatch).
3. **AC3:** Returns a pipeline summary: `{"success": True, "data": {"pipeline_summary": {"stages": [...], "overall_compliance": bool, "run_id": str, "report_paths": {...}}}}`; each stage entry in `stages` includes `{"stage": str, "status": "success"|"failed"|"skipped", "message": str | None}`.
4. **AC4:** If any stage returns a `recoverable: false` error, the pipeline halts immediately, the drawing is rolled back via `session.snapshot.restore(checkpoint)`, and the tool returns the partial pipeline summary with the failed stage status and error details — does NOT proceed to subsequent stages.
5. **AC5:** If `verify_all` returns verification failures (non-compliant result), the pipeline halts BEFORE `area_compute_all` and `autodcr_run_scrutiny`, and returns the verification failure details with suggested fixes in the response; drawing is NOT rolled back at this point (verification failure is recoverable).
6. **AC6:** The pipeline can be re-run after corrections without data loss — each run gets a new unique run_id; previous run data is NOT overwritten.
7. **AC7:** `log_tool_event()` is called at the end of the tool handler (Step 5) with `tool_name="workflow_run_pipeline"`, `outcome="success"` or `"error"`, and `params={"building_type": building_type, "config_path": config_path}`.
8. **AC8:** Integration test `tests/integration/test_full_pipeline.py` verifies the complete happy path: mock backend → predcr setup → verification pass → area compute → scrutiny → all 3 report formats → archive; asserts returned `run_id` is a non-empty string and `stages` list has 7 entries all with `status: "success"`.
9. **AC9:** Integration test verifies AC4 behavior: if `VerificationService.run_all()` raises `MCPError(recoverable=False)`, pipeline halts, drawing is rolled back, returned response includes `"success": False` and `"failed_stage": "verification"`.
10. **AC10:** Integration test verifies AC5 behavior: if `VerificationService.run_all()` returns non-compliant result (recoverable=True), pipeline halts after verify stage, returns `"overall_compliance": False` with verification failures, stages after verify show `"status": "skipped"`.

## Tasks / Subtasks

- [ ] Task 1: Define `PipelineSummary`, `StageResult`, `PipelineResult` Pydantic schemas in `modules/workflow/schemas.py` (AC: 3)
  - [ ] 1.1: Add `StageResult` model: `stage: str`, `status: Literal["success", "failed", "skipped"]`, `message: str | None = None`
  - [ ] 1.2: Add `PipelineSummary` model: `stages: list[StageResult]`, `overall_compliance: bool`, `run_id: str | None`, `report_paths: dict[str, str]`; `model_config = ConfigDict(frozen=True)`
  - [ ] 1.3: Add `PipelineResult` wrapper: `summary: PipelineSummary`, `failed_stage: str | None = None`, `verification_failures: list[dict] | None = None`
  - [ ] 1.4: Export `StageResult`, `PipelineSummary`, `PipelineResult` from `schemas.py`

- [ ] Task 2: Implement `WorkflowService.run_full_pipeline()` in `modules/workflow/service.py` (AC: 2, 4, 5, 6)
  - [ ] 2.1: Add method signature: `async def run_full_pipeline(self, drawing_path: str | None, building_type: str, config_path: str | None, output_formats: list[str]) -> PipelineResult`
  - [ ] 2.2: Take snapshot checkpoint at start: `checkpoint = self.session.snapshot.take()` — this is the rollback point for unrecoverable failures
  - [ ] 2.3: **Stage 1 — Open/Create Drawing:** if `drawing_path` is provided, call `self.session.backend.open_drawing(drawing_path)`; else call `self.session.backend.new_drawing(name=building_type)`; append `StageResult(stage="open_drawing", status="success")` to `stages`
  - [ ] 2.4: **Stage 2 — PreDCR Setup:** call `PreDCRService(self.session).setup(building_type=building_type)`; on `MCPError` with `recoverable=False`, call `self.session.snapshot.restore(checkpoint)`, append `StageResult(stage="predcr_setup", status="failed", message=str(e))`, return early `PipelineResult(summary=..., failed_stage="predcr_setup")`
  - [ ] 2.5: **Stage 3 — Verify All:** call `VerificationService(self.session).run_all()`; if result is non-compliant AND recoverable, append failed stage, mark remaining stages as skipped, return `PipelineResult(summary=..., verification_failures=result.failures)`; if `MCPError(recoverable=False)`, restore checkpoint and return as in 2.4
  - [ ] 2.6: **Stage 4 — Area Compute All:** call `AreaService(self.session).compute_all()`; handle `MCPError(recoverable=False)` with snapshot restore and early return
  - [ ] 2.7: **Stage 5 — AutoDCR Scrutiny:** call `AutoDCRService(self.session).run_scrutiny(config_path=config_path)`; capture `scrutiny_result`; handle `MCPError(recoverable=False)` similarly
  - [ ] 2.8: **Stage 6 — Report Generation:** for each format in `output_formats`, call the corresponding `ReportService(self.session).generate_{format}(scrutiny_result=scrutiny_result)`; collect report file paths; if any report fails, log warning but continue (report generation failure is non-critical to compliance result)
  - [ ] 2.9: **Stage 7 — Archive Run:** call `repository.save_session(self.session)` with all artifacts; capture `run_id`; append `StageResult(stage="archive_run", status="success")`
  - [ ] 2.10: Return `PipelineResult(summary=PipelineSummary(stages=stages, overall_compliance=scrutiny_result.is_compliant, run_id=run_id, report_paths=report_paths))`

- [ ] Task 3: Implement `workflow_run_pipeline` MCP tool handler in `tools.py` (AC: 1, 3, 7)
  - [ ] 3.1: Define `@mcp.tool()` decorated async function `workflow_run_pipeline(ctx: Context, building_type: str, drawing_path: str | None = None, config_path: str | None = None, output_formats: list[str] | None = None) -> dict`
  - [ ] 3.2: Step 1 — retrieve session: `session = ctx.get_state("session")`; if `session is None`, return `MCPError(code=ErrorCode.NO_ACTIVE_SESSION, message="Call workflow_start first").to_response()`
  - [ ] 3.3: Step 2 — validate params: ensure `building_type` is non-empty string; set `output_formats = output_formats or ["pdf", "docx", "json"]`; validate each format in `output_formats` is one of `["pdf", "docx", "json"]`; on invalid format return `MCPError(code=ErrorCode.INVALID_PARAMETER, ...).to_response()`
  - [ ] 3.4: Step 3 — call service: `result = await WorkflowService(session).run_full_pipeline(drawing_path=drawing_path, building_type=building_type, config_path=config_path, output_formats=output_formats)`
  - [ ] 3.5: Step 4 — determine success/failure: if `result.failed_stage is not None` → success=False; elif `result.verification_failures` → success=False with compliance info; else success=True
  - [ ] 3.6: Step 5 — log event: `session.event_log.append({"tool": "workflow_run_pipeline", ...})`; call `log_tool_event(session_id=session.id, tool_name="workflow_run_pipeline", params={"building_type": building_type, "config_path": config_path}, outcome=outcome)`
  - [ ] 3.7: Step 6 — return response: `{"success": success, "data": {"pipeline_summary": result.summary.model_dump(), "failed_stage": result.failed_stage, "verification_failures": result.verification_failures}}`
  - [ ] 3.8: Add `workflow_run_pipeline` to `register(mcp)` in the module's `__init__.py`

- [ ] Task 4: Write integration tests in `tests/integration/test_full_pipeline.py` (AC: 8, 9, 10)
  - [ ] 4.1: Create `tests/integration/test_full_pipeline.py` with `pytest.mark.integration` marker
  - [ ] 4.2: **Happy path test:** set up mock session with `MockCADBackend`; mock all service calls to return success; call `WorkflowService(session).run_full_pipeline(...)`; assert `result.summary.overall_compliance is True`; assert `len(result.summary.stages) == 7`; assert all stage statuses are `"success"`; assert `result.summary.run_id` is a non-empty string
  - [ ] 4.3: **Unrecoverable failure test (AC9):** mock `VerificationService.run_all()` to raise `MCPError(recoverable=False)`; call `run_full_pipeline()`; assert `result.failed_stage == "verification"`; assert snapshot restore was called (use `mock_session.snapshot.restore.assert_called_once()`)
  - [ ] 4.4: **Recoverable verification failure test (AC10):** mock `VerificationService.run_all()` to return a non-compliant result with `recoverable=True`; call `run_full_pipeline()`; assert `result.verification_failures` is a non-empty list; assert stages after verify all have `status="skipped"`; assert snapshot restore was NOT called
  - [ ] 4.5: **Output format validation test:** call the MCP tool handler directly with `output_formats=["invalid"]`; assert response has `"success": False` with `ErrorCode.INVALID_PARAMETER`
  - [ ] 4.6: **No active session test:** call tool with no session in `ctx`; assert `ErrorCode.NO_ACTIVE_SESSION` response
  - [ ] 4.7: Run `pytest tests/integration/test_full_pipeline.py -v` and confirm all tests pass

- [ ] Task 5: Verify pipeline stage method signatures align with actual service APIs (AC: 2)
  - [ ] 5.1: Cross-check `PreDCRService(session).setup()` call signature against `modules/predcr/service.py` (from Story 4-4); align method name and params
  - [ ] 5.2: Cross-check `VerificationService(session).run_all()` return schema against `modules/verification/service.py` (from Story 6-5); ensure `is_compliant` and `failures` fields exist on result
  - [ ] 5.3: Cross-check `AreaService(session).compute_all()` against Story 8-4's implementation
  - [ ] 5.4: Cross-check `AutoDCRService(session).run_scrutiny()` against Story 9-5's implementation; confirm `is_compliant` field on return value
  - [ ] 5.5: Cross-check `ReportService(session).generate_pdf()`, `generate_docx()`, `generate_json()` against Story 10-4's implementation; confirm file path returned
  - [ ] 5.6: Cross-check `repository.save_session()` against Story 11-2's implementation; confirm it returns a `run_id` string

## Dev Notes

### Critical Architecture Constraints

1. **Modules call each other via direct Python service calls — NEVER via MCP tool dispatch.** The pipeline MUST call `PreDCRService().setup()`, not `predcr_run_setup` MCP tool. Calling tools from within tools creates protocol overhead and circular dispatch risk. This is an explicitly forbidden anti-pattern per architecture spec.
2. **`workflow_run_pipeline` requires an active session.** The AI client MUST call `workflow_start()` before `workflow_run_pipeline`. The tool handler checks `ctx.get_state("session")` at Step 1 and returns `NO_ACTIVE_SESSION` error if no session exists.
3. **Snapshot/rollback only for `recoverable: false` failures.** The snapshot taken at pipeline start is ONLY restored if a stage raises `MCPError(recoverable=False)`. Verification non-compliance is `recoverable: True` — no rollback. Architecture spec says rollback is for catastrophic drawing corruption, not business rule failures.
4. **Report generation failures are non-blocking.** If `report_generate_pdf()` fails, log a warning and continue; do not fail the pipeline. The scrutiny result is the legally significant artifact — reports are a convenience output.
5. **FORBIDDEN: Do not call other MCP tools inside this handler.** No `await mcp.call_tool("predcr_run_setup", ...)` patterns. Direct service instantiation only.
6. **This is the FINAL story in the project.** Ensure all upstream service APIs are confirmed (Task 5) before writing the service orchestration code. If upstream API signatures differ from what's expected, update the call sites to match — do NOT change upstream service signatures just for this story.

### Module/Component Notes

**Pipeline orchestration flow (from architecture spec):**

```python
WorkflowService.run_full_pipeline()
  → PreDCRService.setup()
  → VerificationService.run_all()
  → AreaService.compute_all()
  → AutoDCRService.run_scrutiny()
  → ReportService.generate_all()
  → archive/repository.save_session()
```

**`WorkflowService.run_full_pipeline()` skeleton:**

```python
from lcs_cad_mcp.modules.predcr.service import PreDCRService
from lcs_cad_mcp.modules.verification.service import VerificationService
from lcs_cad_mcp.modules.area.service import AreaService
from lcs_cad_mcp.modules.autodcr.service import AutoDCRService
from lcs_cad_mcp.modules.reports.service import ReportService
from lcs_cad_mcp.archive import repository
from lcs_cad_mcp.archive.engine import get_db_session
from lcs_cad_mcp.errors import MCPError
from .schemas import PipelineResult, PipelineSummary, StageResult


async def run_full_pipeline(
    self,
    drawing_path: str | None,
    building_type: str,
    config_path: str | None,
    output_formats: list[str],
) -> PipelineResult:
    stages: list[StageResult] = []
    report_paths: dict[str, str] = {}
    run_id: str | None = None

    # Snapshot for rollback on unrecoverable failures only
    checkpoint = self.session.snapshot.take()

    def _fail_unrecoverable(stage_name: str, error: MCPError) -> PipelineResult:
        self.session.snapshot.restore(checkpoint)
        stages.append(StageResult(stage=stage_name, status="failed", message=error.message))
        # Mark remaining stages as skipped
        all_stages = ["open_drawing", "predcr_setup", "verification",
                      "area_compute", "autodcr_scrutiny", "report_generation", "archive_run"]
        for s in all_stages[len(stages):]:
            stages.append(StageResult(stage=s, status="skipped"))
        return PipelineResult(
            summary=PipelineSummary(
                stages=stages,
                overall_compliance=False,
                run_id=None,
                report_paths={},
            ),
            failed_stage=stage_name,
        )

    # Stage 1: Open or create drawing
    try:
        if drawing_path:
            self.session.backend.open_drawing(drawing_path)
        else:
            self.session.backend.new_drawing(name=building_type)
        stages.append(StageResult(stage="open_drawing", status="success"))
    except MCPError as e:
        if not e.recoverable:
            return _fail_unrecoverable("open_drawing", e)
        stages.append(StageResult(stage="open_drawing", status="failed", message=e.message))
        return PipelineResult(summary=PipelineSummary(stages=stages, overall_compliance=False, run_id=None, report_paths={}), failed_stage="open_drawing")

    # Stage 2: PreDCR setup
    try:
        PreDCRService(self.session).setup(building_type=building_type)
        stages.append(StageResult(stage="predcr_setup", status="success"))
    except MCPError as e:
        if not e.recoverable:
            return _fail_unrecoverable("predcr_setup", e)
        # ...

    # Stage 3: Verify all
    try:
        verification_result = VerificationService(self.session).run_all()
        if not verification_result.is_compliant:
            # Recoverable — halt but do NOT roll back
            stages.append(StageResult(stage="verification", status="failed",
                                      message="Drawing has verification failures"))
            for s in ["area_compute", "autodcr_scrutiny", "report_generation", "archive_run"]:
                stages.append(StageResult(stage=s, status="skipped"))
            return PipelineResult(
                summary=PipelineSummary(stages=stages, overall_compliance=False, run_id=None, report_paths={}),
                verification_failures=[f.model_dump() for f in verification_result.failures],
            )
        stages.append(StageResult(stage="verification", status="success"))
    except MCPError as e:
        if not e.recoverable:
            return _fail_unrecoverable("verification", e)

    # Stage 4–7: area, scrutiny, reports, archive (follow same pattern)
    # ...
```

**`workflow_run_pipeline` tool handler (Step 5 — log_tool_event integration):**

```python
from lcs_cad_mcp.archive.event_logger import log_tool_event

# Step 5: Event log
outcome = "success" if success else "error"
error_code = result.failed_stage  # or None
session.event_log.append({
    "tool": "workflow_run_pipeline",
    "building_type": building_type,
    "overall_compliance": result.summary.overall_compliance if success else False,
})
log_tool_event(
    session_id=session.id,
    tool_name="workflow_run_pipeline",
    params={"building_type": building_type, "config_path": config_path},
    outcome=outcome,
    error_code=error_code,
)
```

**`PipelineSummary` response shape (AC3):**

```json
{
  "success": true,
  "data": {
    "pipeline_summary": {
      "stages": [
        {"stage": "open_drawing", "status": "success", "message": null},
        {"stage": "predcr_setup", "status": "success", "message": null},
        {"stage": "verification", "status": "success", "message": null},
        {"stage": "area_compute", "status": "success", "message": null},
        {"stage": "autodcr_scrutiny", "status": "success", "message": null},
        {"stage": "report_generation", "status": "success", "message": null},
        {"stage": "archive_run", "status": "success", "message": null}
      ],
      "overall_compliance": true,
      "run_id": "a1b2c3d4-...",
      "report_paths": {
        "pdf": "/path/to/report.pdf",
        "docx": "/path/to/report.docx",
        "json": "/path/to/report.json"
      }
    },
    "failed_stage": null,
    "verification_failures": null
  }
}
```

### Project Structure Notes

Files to create or modify for this story:

```
src/lcs_cad_mcp/modules/workflow/
├── schemas.py             # MODIFY: add StageResult, PipelineSummary, PipelineResult
├── service.py             # MODIFY: add run_full_pipeline() method to WorkflowService
├── tools.py               # MODIFY: add workflow_run_pipeline handler
└── __init__.py            # MODIFY: register workflow_run_pipeline in register(mcp)

tests/integration/
└── test_full_pipeline.py  # CREATE: full pipeline integration tests (Stories 11-5)
```

No new files are created outside the `workflow/` module — all other module service classes are consumed via direct import, not modified.

### Dependencies

- **Story 4-4** (`predcr_run_setup_mcp_tool_full`): `PreDCRService.setup(building_type)` must be implemented and testable.
- **Story 6-5** (`verify_all_mcp_tool_full_verification`): `VerificationService.run_all()` must return a result with `is_compliant: bool` and `failures: list[...]`.
- **Story 8-4** (`area_compute_fsi_coverage_all_tools`): `AreaService.compute_all()` must be callable from service layer.
- **Story 9-5** (`autodcr_run_scrutiny_mcp_tool_full`): `AutoDCRService.run_scrutiny(config_path)` must return `scrutiny_result` with `is_compliant`.
- **Story 9-6** (`dry_run_mode_iterative_correction_loop`): Correction loop is a separate flow — `workflow_run_pipeline` is for single-pass pipeline execution; refer to Story 9-6 for iterative mode.
- **Story 10-2 / 10-3 / 10-4** (report generation tools): `ReportService.generate_pdf/docx/json()` must accept scrutiny result and return file path.
- **Story 11-2** (`scrutiny_run_archival`): `repository.save_session()` or `workflow_archive_run()` must accept all artifacts and return `run_id`.
- **Story 11-4** (`workflow_get_audit_trail`): `log_tool_event()` from `archive/event_logger.py` must be available.

### References

- Pipeline flow diagram: [Source: `_bmad-output/planning-artifacts/architecture.md` — "Pipeline path (workflow_run_pipeline)" section]
- FR36 (end-to-end single call): [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 11, Story 11-5]
- Anti-pattern: calling MCP tools from tools: [Source: `_bmad-output/planning-artifacts/architecture.md` — "Inter-Module Communication" section]
- Snapshot/rollback pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — "Snapshot Pattern (write tools only)" section]
- Session access pattern: [Source: `_bmad-output/planning-artifacts/architecture.md` — "Session Access" section]
- `log_tool_event()` integration: [Source: `_bmad-output/implementation-artifacts/11-4-workflow-get-audit-trail-mcp-tool.md` — Task 6]
- 6-step tool handler anatomy: [Source: `_bmad-output/planning-artifacts/architecture.md` — "Enforcement Guidelines"]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/workflow/schemas.py` (modified — `StageResult`, `PipelineSummary`, `PipelineResult` added)
- `src/lcs_cad_mcp/modules/workflow/service.py` (modified — `run_full_pipeline()` method added)
- `src/lcs_cad_mcp/modules/workflow/tools.py` (modified — `workflow_run_pipeline` handler added)
- `src/lcs_cad_mcp/modules/workflow/__init__.py` (modified — `workflow_run_pipeline` registered)
- `tests/integration/test_full_pipeline.py` (created)
