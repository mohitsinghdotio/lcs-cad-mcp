"""AutoDCR module — register(mcp) wires all AutoDCR tools into the FastMCP instance."""
from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all AutoDCR tools. Called once by __main__.py at startup."""
    from lcs_cad_mcp.modules.autodcr.tools import autodcr_run_scrutiny, autodcr_dry_run
    from lcs_cad_mcp.modules.autodcr.schemas import AutodcrRunScrutinyInput, AutodcrDryRunInput
    from lcs_cad_mcp.errors import validate_input

    @mcp.tool(name="autodcr_run_scrutiny")
    async def _autodcr_run_scrutiny(ctx, authority_code: str, dry_run: bool = False) -> dict:
        inp, err = validate_input(AutodcrRunScrutinyInput, {"authority_code": authority_code, "dry_run": dry_run})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        config = ctx.get_state("active_dcr_config") if hasattr(ctx, "get_state") else None
        return await autodcr_run_scrutiny(inp, session, config)

    @mcp.tool(name="autodcr_dry_run")
    async def _autodcr_dry_run(ctx, authority_code: str, max_iterations: int = 10) -> dict:
        inp, err = validate_input(AutodcrDryRunInput, {"authority_code": authority_code, "max_iterations": max_iterations})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        config = ctx.get_state("active_dcr_config") if hasattr(ctx, "get_state") else None
        return await autodcr_dry_run(inp, session, config)
