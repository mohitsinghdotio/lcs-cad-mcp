"""Thin MCP tool handlers for the autodcr module."""
from __future__ import annotations

from lcs_cad_mcp.errors import MCPError, success_response
from lcs_cad_mcp.modules.autodcr.schemas import AutodcrRunScrutinyInput, AutodcrDryRunInput


async def autodcr_run_scrutiny(inp: AutodcrRunScrutinyInput, session, config) -> dict:
    from lcs_cad_mcp.modules.autodcr.service import AutoDCRService
    try:
        if config is None:
            return MCPError(
                code="CONFIG_NOT_LOADED",
                message="No DCR config loaded. Call config_load first.",
                recoverable=True,
                suggested_action="Use config_load to load a DCR config file.",
            ).to_response()
        svc = AutoDCRService()
        report = svc.run_scrutiny(session, config, dry_run=inp.dry_run)
        return success_response({
            "run_id": report.run_id,
            "authority": report.authority,
            "overall_pass": report.overall_pass,
            "total_rules": report.total_rules,
            "passed_rules": report.passed_rules,
            "failed_rules": report.failed_rules,
            "results": [r.model_dump() for r in report.results],
        })
    except MCPError as exc:
        return exc.to_response()


async def autodcr_dry_run(inp: AutodcrDryRunInput, session, config) -> dict:
    from lcs_cad_mcp.modules.autodcr.service import AutoDCRService
    try:
        if config is None:
            return MCPError(
                code="CONFIG_NOT_LOADED",
                message="No DCR config loaded. Call config_load first.",
                recoverable=True,
            ).to_response()
        svc = AutoDCRService()
        reports = svc.dry_run(session, config, max_iterations=inp.max_iterations)
        return success_response({
            "iterations": len(reports),
            "final_pass": reports[-1].overall_pass if reports else False,
            "reports": [
                {
                    "iteration": i + 1,
                    "overall_pass": r.overall_pass,
                    "passed_rules": r.passed_rules,
                    "failed_rules": r.failed_rules,
                }
                for i, r in enumerate(reports)
            ],
        })
    except MCPError as exc:
        return exc.to_response()
