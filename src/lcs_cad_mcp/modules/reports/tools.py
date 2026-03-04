"""Thin MCP tool handlers for the reports module."""
from __future__ import annotations

from lcs_cad_mcp.errors import MCPError, success_response
from lcs_cad_mcp.modules.reports.schemas import (
    ReportGeneratePdfInput, ReportGenerateDocxInput, ReportGenerateJsonInput,
)
from lcs_cad_mcp.modules.reports.service import ReportGenerationError


def _get_report(ctx) -> object | None:
    return ctx.get_state("last_scrutiny_report") if hasattr(ctx, "get_state") else None


async def report_generate_pdf(inp: ReportGeneratePdfInput, report) -> dict:
    from lcs_cad_mcp.modules.reports.service import ReportService
    try:
        if report is None:
            return MCPError(
                code="NO_SCRUTINY_REPORT",
                message="No scrutiny report available. Run autodcr_run_scrutiny first.",
                recoverable=True,
            ).to_response()
        svc = ReportService()
        path = svc.generate_pdf(report, inp.output_path, run_id=inp.run_id)
        return success_response({"output_path": path, "format": "pdf"})
    except ReportGenerationError as exc:
        return {"success": False, "data": None, "error": {"code": exc.code, "message": exc.message}}
    except MCPError as exc:
        return exc.to_response()


async def report_generate_docx(inp: ReportGenerateDocxInput, report) -> dict:
    from lcs_cad_mcp.modules.reports.service import ReportService
    try:
        if report is None:
            return MCPError(
                code="NO_SCRUTINY_REPORT",
                message="No scrutiny report available. Run autodcr_run_scrutiny first.",
                recoverable=True,
            ).to_response()
        svc = ReportService()
        path = svc.generate_docx(report, inp.output_path, run_id=inp.run_id)
        return success_response({"output_path": path, "format": "docx"})
    except ReportGenerationError as exc:
        return {"success": False, "data": None, "error": {"code": exc.code, "message": exc.message}}
    except MCPError as exc:
        return exc.to_response()


async def report_generate_json(inp: ReportGenerateJsonInput, report) -> dict:
    from lcs_cad_mcp.modules.reports.service import ReportService
    try:
        if report is None:
            return MCPError(
                code="NO_SCRUTINY_REPORT",
                message="No scrutiny report available. Run autodcr_run_scrutiny first.",
                recoverable=True,
            ).to_response()
        svc = ReportService()
        path = svc.generate_json(report, inp.output_path, run_id=inp.run_id)
        return success_response({"output_path": path, "format": "json"})
    except ReportGenerationError as exc:
        return {"success": False, "data": None, "error": {"code": exc.code, "message": exc.message}}
    except MCPError as exc:
        return exc.to_response()
