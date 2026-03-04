"""Reports module — register(mcp) wires all report tools into the FastMCP instance."""
from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all report tools. Called once by __main__.py at startup."""
    from lcs_cad_mcp.modules.reports.tools import (
        report_generate_pdf, report_generate_docx, report_generate_json,
    )
    from lcs_cad_mcp.modules.reports.schemas import (
        ReportGeneratePdfInput, ReportGenerateDocxInput, ReportGenerateJsonInput,
    )
    from lcs_cad_mcp.errors import validate_input

    @mcp.tool(name="report_generate_pdf")
    async def _report_generate_pdf(ctx, output_path: str, run_id: str | None = None) -> dict:
        inp, err = validate_input(ReportGeneratePdfInput, {"output_path": output_path, "run_id": run_id})
        if err:
            return err
        report = ctx.get_state("last_scrutiny_report") if hasattr(ctx, "get_state") else None
        return await report_generate_pdf(inp, report)

    @mcp.tool(name="report_generate_docx")
    async def _report_generate_docx(ctx, output_path: str, run_id: str | None = None) -> dict:
        inp, err = validate_input(ReportGenerateDocxInput, {"output_path": output_path, "run_id": run_id})
        if err:
            return err
        report = ctx.get_state("last_scrutiny_report") if hasattr(ctx, "get_state") else None
        return await report_generate_docx(inp, report)

    @mcp.tool(name="report_generate_json")
    async def _report_generate_json(ctx, output_path: str, run_id: str | None = None) -> dict:
        inp, err = validate_input(ReportGenerateJsonInput, {"output_path": output_path, "run_id": run_id})
        if err:
            return err
        report = ctx.get_state("last_scrutiny_report") if hasattr(ctx, "get_state") else None
        return await report_generate_json(inp, report)
