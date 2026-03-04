"""Workflow service — run pipeline, retrieve runs, get audit trail."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lcs_cad_mcp.session.context import DrawingSession

logger = logging.getLogger(__name__)


class WorkflowService:
    """Orchestrates multi-step scrutiny pipeline and archive operations."""

    def retrieve_run(self, run_id: str) -> dict:
        """Retrieve a scrutiny run from the archive by run_id."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        try:
            from lcs_cad_mcp.archive.engine import get_db_session
            from lcs_cad_mcp.archive.repository import get_scrutiny_run_by_id
        except Exception as exc:
            raise MCPError(
                code=ErrorCode.ARCHIVE_WRITE_FAILED,
                message=f"Archive not initialized: {exc}",
                recoverable=True,
            )

        with get_db_session() as db:
            run = get_scrutiny_run_by_id(db, run_id)

        if run is None:
            raise MCPError(
                code=ErrorCode.RUN_NOT_FOUND,
                message=f"Scrutiny run '{run_id}' not found in archive.",
                recoverable=True,
            )

        return {
            "run_id": run.id,
            "run_date": run.run_date,
            "config_version": run.config_version,
            "config_hash": run.config_hash,
            "rule_set_name": run.rule_set_name,
            "overall_status": run.overall_status,
            "drawing_path": run.drawing_path,
            "rule_results": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "status": r.status,
                    "computed_value": r.computed_value,
                    "permissible_value": r.permissible_value,
                    "unit": r.unit,
                    "description": r.description,
                }
                for r in (run.rule_results or [])
            ],
        }

    def get_audit_trail(self, run_id: str | None = None, limit: int = 100) -> list[dict]:
        """Get tool call audit trail, optionally filtered by run_id."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        try:
            from lcs_cad_mcp.archive.engine import get_db_session
            from lcs_cad_mcp.archive.repository import get_tool_events
        except Exception as exc:
            raise MCPError(
                code=ErrorCode.ARCHIVE_WRITE_FAILED,
                message=f"Archive not initialized: {exc}",
                recoverable=True,
            )

        with get_db_session() as db:
            events = get_tool_events(db, session_id=run_id, limit=limit)

        return [
            {
                "tool_name": e.tool_name,
                "called_at": e.called_at,
                "outcome": e.outcome,
                "error_code": e.error_code,
                "params_summary": e.params_summary,
            }
            for e in events
        ]

    def run_pipeline(self, session: DrawingSession, authority_code: str,
                     output_dir: str, dry_run: bool = False) -> dict:
        """Run the full AutoDCR scrutiny pipeline end-to-end.

        Steps: load config → compute areas → run scrutiny → generate reports → archive
        """
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        results = {
            "authority_code": authority_code,
            "dry_run": dry_run,
            "steps": [],
        }

        # Get active config from session
        config = getattr(session, "_active_config", None)
        if config is None:
            results["steps"].append({"step": "config_check", "status": "error",
                                     "message": "No active config. Call config_load first."})
            results["overall_status"] = "FAILED"
            return results

        # Run scrutiny
        try:
            from lcs_cad_mcp.modules.autodcr.service import AutoDCRService
            svc = AutoDCRService()
            report = svc.run_scrutiny(session, config, dry_run=dry_run)
            results["steps"].append({
                "step": "scrutiny",
                "status": "ok",
                "overall_pass": report.overall_pass,
                "run_id": report.run_id,
            })
        except Exception as exc:
            results["steps"].append({"step": "scrutiny", "status": "error", "message": str(exc)})
            results["overall_status"] = "FAILED"
            return results

        # Generate reports (unless dry_run)
        if not dry_run:
            from pathlib import Path
            from lcs_cad_mcp.modules.reports.service import ReportService
            report_svc = ReportService()
            output = Path(output_dir)
            output.mkdir(parents=True, exist_ok=True)

            try:
                json_path = report_svc.generate_json(report, str(output / f"{report.run_id}.json"))
                results["steps"].append({"step": "report_json", "status": "ok", "path": json_path})
            except Exception as exc:
                results["steps"].append({"step": "report_json", "status": "error", "message": str(exc)})

        results["overall_status"] = "COMPLIANT" if (hasattr(report, "overall_pass") and report.overall_pass) else "NON_COMPLIANT"
        results["run_id"] = getattr(report, "run_id", "")
        return results
