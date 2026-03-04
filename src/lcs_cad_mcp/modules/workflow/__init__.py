"""Workflow module — register(mcp) wires all workflow tools into the FastMCP instance."""
from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all workflow tools. Called once by __main__.py at startup."""
    from lcs_cad_mcp.modules.workflow.tools import (
        workflow_retrieve_run, workflow_get_audit_trail, workflow_run_pipeline,
    )
    from lcs_cad_mcp.modules.workflow.schemas import (
        WorkflowRetrieveRunInput, WorkflowGetAuditTrailInput, WorkflowRunPipelineInput,
    )
    from lcs_cad_mcp.errors import validate_input

    @mcp.tool(name="workflow_retrieve_run")
    async def _workflow_retrieve_run(ctx, run_id: str) -> dict:
        inp, err = validate_input(WorkflowRetrieveRunInput, {"run_id": run_id})
        if err:
            return err
        return await workflow_retrieve_run(inp)

    @mcp.tool(name="workflow_get_audit_trail")
    async def _workflow_get_audit_trail(ctx, run_id: str | None = None, limit: int = 100) -> dict:
        inp, err = validate_input(WorkflowGetAuditTrailInput, {"run_id": run_id, "limit": limit})
        if err:
            return err
        return await workflow_get_audit_trail(inp)

    @mcp.tool(name="workflow_run_pipeline")
    async def _workflow_run_pipeline(ctx, drawing_path: str, authority_code: str, output_dir: str, dry_run: bool = False) -> dict:
        inp, err = validate_input(WorkflowRunPipelineInput, {
            "drawing_path": drawing_path, "authority_code": authority_code,
            "output_dir": output_dir, "dry_run": dry_run
        })
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await workflow_run_pipeline(inp, session)
