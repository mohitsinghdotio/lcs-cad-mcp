"""Thin MCP tool handlers for the workflow module."""
from __future__ import annotations

from lcs_cad_mcp.errors import MCPError, success_response
from lcs_cad_mcp.modules.workflow.schemas import (
    WorkflowRetrieveRunInput, WorkflowGetAuditTrailInput, WorkflowRunPipelineInput,
)


async def workflow_retrieve_run(inp: WorkflowRetrieveRunInput) -> dict:
    from lcs_cad_mcp.modules.workflow.service import WorkflowService
    try:
        svc = WorkflowService()
        result = svc.retrieve_run(inp.run_id)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def workflow_get_audit_trail(inp: WorkflowGetAuditTrailInput) -> dict:
    from lcs_cad_mcp.modules.workflow.service import WorkflowService
    try:
        svc = WorkflowService()
        events = svc.get_audit_trail(run_id=inp.run_id, limit=inp.limit)
        return success_response({"events": events, "count": len(events)})
    except MCPError as exc:
        return exc.to_response()


async def workflow_run_pipeline(inp: WorkflowRunPipelineInput, session) -> dict:
    from lcs_cad_mcp.modules.workflow.service import WorkflowService
    try:
        svc = WorkflowService()
        result = svc.run_pipeline(session, inp.authority_code, inp.output_dir, dry_run=inp.dry_run)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()
