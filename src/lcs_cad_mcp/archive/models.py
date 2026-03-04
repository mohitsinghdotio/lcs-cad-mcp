"""SQLAlchemy ORM models for the archive database."""
from __future__ import annotations

import uuid
from sqlalchemy import String, Float, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DrawingSessionRecord(Base):
    __tablename__ = "drawing_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_name: Mapped[str] = mapped_column(String, default="")
    drawing_path: Mapped[str] = mapped_column(String, default="")
    config_path: Mapped[str] = mapped_column(String, default="")
    started_at: Mapped[str] = mapped_column(String, default="")
    ended_at: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String, default="active")

    scrutiny_runs: Mapped[list["ScrutinyRun"]] = relationship(
        "ScrutinyRun", back_populates="drawing_session", cascade="all, delete-orphan"
    )
    tool_events: Mapped[list["ToolEvent"]] = relationship(
        "ToolEvent", back_populates="drawing_session", cascade="all, delete-orphan"
    )


class ScrutinyRun(Base):
    __tablename__ = "scrutiny_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("drawing_sessions.id"))
    run_date: Mapped[str] = mapped_column(String, default="")
    config_version: Mapped[str] = mapped_column(String, default="")
    config_hash: Mapped[str] = mapped_column(String, default="")
    rule_set_name: Mapped[str] = mapped_column(String, default="")
    overall_status: Mapped[str] = mapped_column(String, default="NON_COMPLIANT")
    drawing_path: Mapped[str] = mapped_column(String, default="")

    drawing_session: Mapped["DrawingSessionRecord"] = relationship(
        "DrawingSessionRecord", back_populates="scrutiny_runs"
    )
    rule_results: Mapped[list["RuleResultRecord"]] = relationship(
        "RuleResultRecord", back_populates="scrutiny_run", cascade="all, delete-orphan"
    )
    config_versions: Mapped[list["ConfigVersionRecord"]] = relationship(
        "ConfigVersionRecord", back_populates="scrutiny_run", cascade="all, delete-orphan"
    )
    report_records: Mapped[list["ReportRecord"]] = relationship(
        "ReportRecord", back_populates="scrutiny_run", cascade="all, delete-orphan"
    )


class RuleResultRecord(Base):
    __tablename__ = "rule_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("scrutiny_runs.id"))
    rule_id: Mapped[str] = mapped_column(String, default="")
    rule_name: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="FAIL")
    computed_value: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    permissible_value: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    unit: Mapped[str] = mapped_column(String, default="")
    description: Mapped[str] = mapped_column(Text, default="")

    scrutiny_run: Mapped["ScrutinyRun"] = relationship("ScrutinyRun", back_populates="rule_results")


class ConfigVersionRecord(Base):
    __tablename__ = "config_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("scrutiny_runs.id"))
    version: Mapped[str] = mapped_column(String, default="")
    config_hash: Mapped[str] = mapped_column(String, default="")
    config_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    recorded_at: Mapped[str] = mapped_column(String, default="")

    scrutiny_run: Mapped["ScrutinyRun"] = relationship("ScrutinyRun", back_populates="config_versions")


class ReportRecord(Base):
    __tablename__ = "report_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("scrutiny_runs.id"))
    format: Mapped[str] = mapped_column(String, default="json")  # "pdf", "docx", "json"
    file_path: Mapped[str] = mapped_column(String, default="")
    generated_at: Mapped[str] = mapped_column(String, default="")

    scrutiny_run: Mapped["ScrutinyRun"] = relationship("ScrutinyRun", back_populates="report_records")


class ToolEvent(Base):
    __tablename__ = "tool_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("drawing_sessions.id"))
    tool_name: Mapped[str] = mapped_column(String, default="")
    called_at: Mapped[str] = mapped_column(String, default="")
    params_summary: Mapped[str] = mapped_column(Text, default="{}")  # Truncated to 1000 chars
    outcome: Mapped[str] = mapped_column(String, default="success")  # "success" or "error"
    error_code: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    drawing_session: Mapped["DrawingSessionRecord"] = relationship(
        "DrawingSessionRecord", back_populates="tool_events"
    )
