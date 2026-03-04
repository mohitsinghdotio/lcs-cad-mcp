# Story 9.6: Dry-Run Mode and Iterative Correction Loop

Status: ready-for-dev

## Story

As an **AI client**, I want to run scrutiny in test mode and re-run after corrections, so that the AI can iterate on the drawing until all rules pass without affecting the archive.

## Acceptance Criteria

1. **AC1:** `autodcr_run_dry_run` MCP tool calls `AutoDCRService.run_scrutiny(session_ctx, dry_run=True)`; the full scrutiny pipeline (config load, area computation, rule evaluation, report building) runs identically to `autodcr_run_scrutiny`, but `save_scrutiny_run()` is NOT called; the returned `ScrutinyReport` is identical in structure to the non-dry-run report.
2. **AC2:** `autodcr_rerun` MCP tool calls `AutoDCRService.run_scrutiny(session_ctx, dry_run=False)` after entity modifications; it is semantically identical to `autodcr_run_scrutiny` but exists as a distinct tool name to clearly signal "re-evaluation after corrections" in the AI workflow (FR24).
3. **AC3:** The iterative correction loop works as follows without requiring a server restart: (1) AI calls `autodcr_run_dry_run` → receives violations, (2) AI calls entity modification tools (e.g., `entity_move`, `entity_resize`) to correct the drawing in-session, (3) AI calls `autodcr_rerun` → receives updated `ScrutinyReport` with corrected values, (4) repeat until `overall_pass == True`, (5) AI calls `autodcr_run_scrutiny` to archive the final passing run.
4. **AC4:** Dry-run result is structurally and value-wise identical to non-dry-run result for the same drawing state: `report.rule_results`, `report.overall_pass`, `report.area_table`, `report.config_hash` are all equal; only `run_id` and `timestamp` differ (they are generated fresh each call).
5. **AC5:** `autodcr_get_violations` MCP tool returns only the failing `RuleResult` entries from the most recent scrutiny or dry-run in the session; it reads from session state (`ctx.get_state("last_scrutiny_report")`) — it does NOT re-run scrutiny.
6. **AC6:** `autodcr_get_rule_result(rule_id: str)` MCP tool returns the single `RuleResult` for the given `rule_id` from the most recent report in session state; returns `MCPError(code="RULE_NOT_FOUND", ...)` if the `rule_id` is not in the last report.
7. **AC7:** After each scrutiny call (dry-run or full), the `ScrutinyReport` is stored in session state via `ctx.set_state("last_scrutiny_report", report)` so that `autodcr_get_violations` and `autodcr_get_rule_result` can retrieve it without re-running the engine.
8. **AC8:** Unit tests verify that `dry_run=True` produces an identical report to `dry_run=False` (except `run_id` and `timestamp`), and that `save_scrutiny_run()` is NOT called when `dry_run=True`.

## Tasks / Subtasks

- [ ] Task 1: Implement `autodcr_run_dry_run` MCP tool in `src/lcs_cad_mcp/modules/autodcr/tools.py` (AC: 1, 7)
  - [ ] 1.1: Add `@mcp.tool()` decorated async function `autodcr_run_dry_run(ctx: Context)` — no parameters beyond session context
  - [ ] 1.2: Retrieve `session_ctx = ctx.get_state("drawing_session")`; if `None`, return `SESSION_NOT_STARTED` error
  - [ ] 1.3: Call `report = await AutoDCRService().run_scrutiny(session_ctx, dry_run=True)`
  - [ ] 1.4: Store in session: `ctx.set_state("last_scrutiny_report", report)` — this enables `autodcr_get_violations` to read it without re-running
  - [ ] 1.5: Return `{"success": True, "data": report.model_dump(), "error": None, "dry_run": True}`

- [ ] Task 2: Implement `autodcr_rerun` MCP tool in `src/lcs_cad_mcp/modules/autodcr/tools.py` (AC: 2, 3, 7)
  - [ ] 2.1: Add `@mcp.tool()` decorated async function `autodcr_rerun(ctx: Context)` — no parameters
  - [ ] 2.2: Retrieve `session_ctx`; check session is active
  - [ ] 2.3: Call `report = await AutoDCRService().run_scrutiny(session_ctx, dry_run=False)` — archives the result
  - [ ] 2.4: Store in session: `ctx.set_state("last_scrutiny_report", report)`
  - [ ] 2.5: Return `{"success": True, "data": report.model_dump(), "error": None, "rerun": True}`
  - [ ] 2.6: Add module-level docstring to the tool explaining its role in the iterative correction loop: `"""Re-runs the full scrutiny pass after entity modifications. Archives the result. Use autodcr_run_dry_run during iteration; call this when the drawing is ready to commit a passing result."""`

- [ ] Task 3: Update `autodcr_run_scrutiny` to store report in session state (AC: 7)
  - [ ] 3.1: In the existing `autodcr_run_scrutiny` tool (Story 9-5), add `ctx.set_state("last_scrutiny_report", report)` immediately after receiving the report from `AutoDCRService.run_scrutiny()`
  - [ ] 3.2: Verify this does not break the Story 9-5 integration test

- [ ] Task 4: Implement `autodcr_get_violations` MCP tool (AC: 5, 7)
  - [ ] 4.1: Add `@mcp.tool()` decorated function `autodcr_get_violations(ctx: Context)` — synchronous (reads session state only)
  - [ ] 4.2: Retrieve `report: ScrutinyReport = ctx.get_state("last_scrutiny_report")`; if `None`, return `MCPError(code="NO_SCRUTINY_RUN", message="No scrutiny run in current session. Call autodcr_run_scrutiny or autodcr_run_dry_run first.", recoverable=True)`
  - [ ] 4.3: Filter: `violations = [r for r in report.rule_results if r.status == "fail"]`
  - [ ] 4.4: Return `{"success": True, "data": {"violations": [v.model_dump() for v in violations], "violation_count": len(violations), "overall_pass": report.overall_pass}, "error": None}`

- [ ] Task 5: Implement `autodcr_get_rule_result` MCP tool (AC: 6, 7)
  - [ ] 5.1: Add `@mcp.tool()` decorated function `autodcr_get_rule_result(rule_id: str, ctx: Context)` — `rule_id` is a tool parameter
  - [ ] 5.2: Retrieve `report = ctx.get_state("last_scrutiny_report")`; if `None`, return `NO_SCRUTINY_RUN` error
  - [ ] 5.3: Find: `result = next((r for r in report.rule_results if r.rule_id == rule_id), None)`
  - [ ] 5.4: If `result is None`, return `MCPError(code="RULE_NOT_FOUND", message=f"Rule '{rule_id}' not found in last scrutiny report.", recoverable=True).to_response()`
  - [ ] 5.5: Return `{"success": True, "data": result.model_dump(), "error": None}`

- [ ] Task 6: Write unit tests for dry-run parity and session state (AC: 8)
  - [ ] 6.1: Write `test_dry_run_identical_to_full_run`: mock `save_scrutiny_run` with `MagicMock`; call `run_scrutiny(dry_run=True)` and `run_scrutiny(dry_run=False)` on identical inputs; assert `rule_results`, `overall_pass`, `area_table`, `config_hash` are equal; assert `save_scrutiny_run` was called exactly once (only by the non-dry-run call)
  - [ ] 6.2: Write `test_dry_run_does_not_archive`: mock `save_scrutiny_run`; call `run_scrutiny(dry_run=True)`; assert `save_scrutiny_run.called == False`
  - [ ] 6.3: Write `test_get_violations_returns_only_failures`: set up `last_scrutiny_report` in mock session state with 2 passing and 1 failing rule; call `autodcr_get_violations`; assert `violation_count == 1`
  - [ ] 6.4: Write `test_get_violations_no_report_returns_error`: session state has no `last_scrutiny_report`; assert `MCPError` with `NO_SCRUTINY_RUN` code
  - [ ] 6.5: Write `test_get_rule_result_found`: set up session state; call `autodcr_get_rule_result("fsi-limit")`; assert `result.rule_id == "fsi-limit"`
  - [ ] 6.6: Write `test_get_rule_result_not_found`: call `autodcr_get_rule_result("nonexistent")`; assert `RULE_NOT_FOUND` error

- [ ] Task 7: Write integration test for the iterative correction loop (AC: 3)
  - [ ] 7.1: In `tests/integration/test_iterative_correction.py`, set up a mock drawing where FSI initially fails
  - [ ] 7.2: Call `autodcr_run_dry_run` → assert `overall_pass == False`
  - [ ] 7.3: Modify `computed_areas["fsi"]` in mock to a passing value (simulating entity modification by `EntityService`)
  - [ ] 7.4: Call `autodcr_rerun` → assert `overall_pass == True`
  - [ ] 7.5: Assert the two reports have different `run_id` values (each call generates a fresh UUID)
  - [ ] 7.6: Assert `save_scrutiny_run` was called exactly once (only by `autodcr_rerun`, not by dry-run)

## Dev Notes

### Critical Architecture Constraints

1. **`dry_run` is a thin flag — not a separate code path**: The ONLY difference between `autodcr_run_dry_run` and `autodcr_run_scrutiny` is the `dry_run=True` argument passed to `AutoDCRService.run_scrutiny()`. Inside the service, the only branch is `if not dry_run: save_scrutiny_run(...)`. This ensures AC4 (identical reports).
2. **Session state stores the full report**: `ctx.set_state("last_scrutiny_report", report)` stores the `ScrutinyReport` Pydantic object (not a dict). Downstream tools (`get_violations`, `get_rule_result`) retrieve it and filter in-memory — no re-evaluation. This is efficient and correct.
3. **`autodcr_rerun` archives by default**: It calls `dry_run=False`. This is intentional — `rerun` is used when the AI is confident the correction is final. The AI uses `dry_run` for intermediate iterations and `rerun` for the final commit.
4. **FastMCP 3.x `ctx.set_state` / `ctx.get_state`**: These are connection-scoped (per MCP client session). Each AI client has its own state scope. This means `last_scrutiny_report` is isolated per client — concurrent clients do not interfere.
5. **No re-evaluation in `get_violations`**: `autodcr_get_violations` reads from session state ONLY. It must NOT call `AreaService` or `DCRRuleEvaluator`. This is both for performance and for consistency — the client wants the violations from the LAST run, not a fresh re-evaluation.
6. **Iterative loop requires no server restart**: The session state persists across multiple tool calls within the same MCP connection. Entity modifications via `EntityService` modify the in-memory drawing state, and a subsequent `autodcr_rerun` picks up the modified drawing from the session.

### Module/Component Notes

- All 5 tools for this story are registered in `src/lcs_cad_mcp/modules/autodcr/tools.py`:
  - `autodcr_run_scrutiny` (Story 9-5, updated in Task 3)
  - `autodcr_run_dry_run` (NEW)
  - `autodcr_rerun` (NEW)
  - `autodcr_get_violations` (NEW)
  - `autodcr_get_rule_result` (NEW)
- Session state key convention: `"last_scrutiny_report"` — document this in `session/context.py` as a known state key constant
- `AutoDCRService.run_scrutiny()` signature from Story 9-5: `async def run_scrutiny(self, session_ctx, dry_run: bool = False) -> ScrutinyReport` — the `dry_run` parameter was already specified there

### MCP Tool API Summary

```
autodcr_run_dry_run()
  → ScrutinyReport (no archival)

autodcr_rerun()
  → ScrutinyReport (archived)

autodcr_get_violations()
  → {"violations": list[RuleResult], "violation_count": int, "overall_pass": bool}

autodcr_get_rule_result(rule_id: str)
  → RuleResult

Iterative correction workflow:
  autodcr_run_dry_run()          # see violations
  → entity_move() / entity_resize()  # fix drawing (Epic 5 tools)
  → autodcr_run_dry_run()        # check again (optional)
  → autodcr_rerun()              # commit final passing result to archive
```

### Project Structure Notes

```
src/lcs_cad_mcp/
└── modules/
    └── autodcr/
        └── tools.py    # updated: 5 tools total after this story

tests/
├── unit/
│   └── modules/
│       └── autodcr/
│           └── test_autodcr_tools.py  # NEW: dry-run + get_violations + get_rule_result tests
└── integration/
    └── test_iterative_correction.py   # NEW
```

### Dependencies

- Story 9-5: `AutoDCRService.run_scrutiny()` with `dry_run` parameter; `autodcr_run_scrutiny` tool already implemented; `archive/repository.py` `save_scrutiny_run()` already implemented
- Epic 5 (Story 5-5): Entity modification tools (`entity_move`, `entity_resize`, etc.) — used by AI in the iterative loop but NOT called by this story's code; just needs to be available in the session
- FastMCP 3.x: `ctx.set_state()` / `ctx.get_state()` — connection-scoped session state (this is why FastMCP 3.x was chosen)

### References

- Story 9-5: `_bmad-output/implementation-artifacts/9-5-autodcr-run-scrutiny-mcp-tool-full.md`
- FR24 (iterative correction without server restart): `_bmad-output/planning-artifacts/epics-and-stories.md`
- FR25 (dry-run mode): `_bmad-output/planning-artifacts/epics-and-stories.md`
- NFR13 (reproducibility — dry-run vs full-run parity): `_bmad-output/planning-artifacts/epics-and-stories.md`
- Epic 9 stories: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 9, Story 9-6
- FastMCP 3.x session state docs: architecture doc section "Session Architecture"

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/autodcr/tools.py` (updated: 5 tools total)
- `src/lcs_cad_mcp/modules/autodcr/service.py` (no changes needed if dry_run param already in place from 9-5)
- `tests/unit/modules/autodcr/test_autodcr_tools.py`
- `tests/integration/test_iterative_correction.py`
