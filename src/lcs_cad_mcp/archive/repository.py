"""Archive repository — query and persistence functions for scrutiny run artifacts."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_scrutiny_run(db_session, scrutiny_run_data: dict) -> str:
    """Persist a scrutiny run and its rule results to the archive.

    Args:
        db_session: SQLAlchemy session
        scrutiny_run_data: Dict with keys: session_id, run_id, config_version, config_hash,
                           rule_set_name, overall_status, drawing_path, results (list of dicts)

    Returns:
        run_id (str UUID)
    """
    from lcs_cad_mcp.archive.models import ScrutinyRun, RuleResultRecord

    run_id = scrutiny_run_data.get("run_id") or str(uuid.uuid4())
    run = ScrutinyRun(
        id=run_id,
        session_id=scrutiny_run_data.get("session_id", ""),
        run_date=_now_iso(),
        config_version=scrutiny_run_data.get("config_version", ""),
        config_hash=scrutiny_run_data.get("config_hash", ""),
        rule_set_name=scrutiny_run_data.get("rule_set_name", ""),
        overall_status="COMPLIANT" if scrutiny_run_data.get("overall_pass") else "NON_COMPLIANT",
        drawing_path=scrutiny_run_data.get("drawing_path", ""),
    )
    db_session.add(run)

    for r in scrutiny_run_data.get("results", []):
        record = RuleResultRecord(
            run_id=run_id,
            rule_id=r.get("rule_id", ""),
            rule_name=r.get("rule_name", ""),
            status="PASS" if r.get("passed") else "FAIL",
            computed_value=r.get("computed_value"),
            permissible_value=r.get("permissible_value"),
            unit=r.get("unit", ""),
            description=r.get("suggested_action", ""),
        )
        db_session.add(record)

    return run_id


def get_scrutiny_runs(db_session, project_name: str | None = None,
                      run_date: str | None = None,
                      config_version: str | None = None) -> list:
    """Query archived scrutiny runs with optional filters.

    Returns:
        List of ScrutinyRun ORM objects
    """
    from lcs_cad_mcp.archive.models import ScrutinyRun

    query = db_session.query(ScrutinyRun)
    if config_version:
        query = query.filter(ScrutinyRun.config_version == config_version)
    if run_date:
        query = query.filter(ScrutinyRun.run_date.startswith(run_date))
    return query.all()


def get_scrutiny_run_by_id(db_session, run_id: str):
    """Get a single scrutiny run by ID."""
    from lcs_cad_mcp.archive.models import ScrutinyRun
    return db_session.query(ScrutinyRun).filter(ScrutinyRun.id == run_id).first()


def save_tool_event(db_session, event_data: dict) -> None:
    """Persist a tool call event to the audit trail.

    Args:
        db_session: SQLAlchemy session
        event_data: Dict with keys: session_id, tool_name, params_summary, outcome, error_code
    """
    from lcs_cad_mcp.archive.models import ToolEvent

    params_str = json.dumps(event_data.get("params", {}))[:1000]  # Truncate to 1000 chars
    event = ToolEvent(
        session_id=event_data.get("session_id", ""),
        tool_name=event_data.get("tool_name", ""),
        called_at=_now_iso(),
        params_summary=params_str,
        outcome=event_data.get("outcome", "success"),
        error_code=event_data.get("error_code"),
    )
    db_session.add(event)


def get_tool_events(db_session, session_id: str | None = None, limit: int = 100) -> list:
    """Query tool events with optional session_id filter.

    Returns:
        List of ToolEvent ORM objects
    """
    from lcs_cad_mcp.archive.models import ToolEvent

    query = db_session.query(ToolEvent)
    if session_id:
        query = query.filter(ToolEvent.session_id == session_id)
    return query.order_by(ToolEvent.called_at.desc()).limit(limit).all()
