"""Unit tests for archive SQLAlchemy ORM models and schema."""
import pytest
import uuid
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from lcs_cad_mcp.archive.models import (
    Base, DrawingSessionRecord, ScrutinyRun, RuleResultRecord,
    ConfigVersionRecord, ReportRecord, ToolEvent,
)


@pytest.fixture
def tmp_engine():
    """In-memory SQLite engine for test isolation."""
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(tmp_engine):
    Session = sessionmaker(bind=tmp_engine)
    session = Session()
    yield session
    session.close()


def test_all_tables_created(tmp_engine):
    table_names = inspect(tmp_engine).get_table_names()
    assert "drawing_sessions" in table_names
    assert "scrutiny_runs" in table_names
    assert "rule_results" in table_names
    assert "config_versions" in table_names
    assert "report_records" in table_names
    assert "tool_events" in table_names


def test_drawing_session_record_persists(db_session):
    session_id = str(uuid.uuid4())
    rec = DrawingSessionRecord(
        id=session_id,
        project_name="TestProject",
        drawing_path="/tmp/test.dxf",
        status="active",
        started_at="2024-01-01T00:00:00+00:00",
    )
    db_session.add(rec)
    db_session.commit()

    fetched = db_session.query(DrawingSessionRecord).filter_by(id=session_id).first()
    assert fetched is not None
    assert fetched.project_name == "TestProject"
    assert fetched.drawing_path == "/tmp/test.dxf"


def test_scrutiny_run_fk_resolves(db_session):
    session_id = str(uuid.uuid4())
    ds = DrawingSessionRecord(id=session_id, started_at="2024-01-01T00:00:00+00:00")
    db_session.add(ds)
    db_session.commit()

    run_id = str(uuid.uuid4())
    run = ScrutinyRun(
        id=run_id,
        session_id=session_id,
        run_date="2024-01-01T00:00:00+00:00",
        overall_status="COMPLIANT",
    )
    db_session.add(run)
    db_session.commit()

    fetched = db_session.query(ScrutinyRun).filter_by(id=run_id).first()
    assert fetched is not None
    assert fetched.session_id == session_id


def test_rule_result_nullable_floats(db_session):
    session_id = str(uuid.uuid4())
    ds = DrawingSessionRecord(id=session_id, started_at="2024-01-01T00:00:00+00:00")
    db_session.add(ds)

    run_id = str(uuid.uuid4())
    run = ScrutinyRun(id=run_id, session_id=session_id)
    db_session.add(run)
    db_session.commit()

    result_id = str(uuid.uuid4())
    rr = RuleResultRecord(
        id=result_id,
        run_id=run_id,
        rule_id="test_rule",
        computed_value=None,
        permissible_value=None,
    )
    db_session.add(rr)
    db_session.commit()

    fetched = db_session.query(RuleResultRecord).filter_by(id=result_id).first()
    assert fetched is not None
    assert fetched.computed_value is None
    assert fetched.permissible_value is None


def test_tool_event_persists(db_session):
    session_id = str(uuid.uuid4())
    ds = DrawingSessionRecord(id=session_id, started_at="2024-01-01T00:00:00+00:00")
    db_session.add(ds)
    db_session.commit()

    event = ToolEvent(
        session_id=session_id,
        tool_name="cad_new_drawing",
        called_at="2024-01-01T00:00:00+00:00",
        params_summary='{"name": "test"}',
        outcome="success",
    )
    db_session.add(event)
    db_session.commit()

    fetched = db_session.query(ToolEvent).filter_by(session_id=session_id).first()
    assert fetched is not None
    assert fetched.tool_name == "cad_new_drawing"
    assert fetched.outcome == "success"


def test_create_all_idempotent(tmp_engine):
    """Calling create_all twice should not raise."""
    Base.metadata.create_all(tmp_engine)
    Base.metadata.create_all(tmp_engine)
    table_names = inspect(tmp_engine).get_table_names()
    assert len(table_names) >= 6
