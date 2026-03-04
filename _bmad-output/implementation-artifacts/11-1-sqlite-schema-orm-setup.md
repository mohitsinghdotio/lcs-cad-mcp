# Story 11.1: SQLite Schema and ORM Setup

Status: ready-for-dev

## Story

As a **developer**,
I want **a SQLite database schema and SQLAlchemy ORM models that store all scrutiny run artifacts**,
so that **every scrutiny run is archived in an ACID-compliant persistent store that is queryable and legally defensible (NFR9)**.

## Acceptance Criteria

1. **AC1:** `src/lcs_cad_mcp/archive/engine.py` creates a SQLite engine using `sqlalchemy.create_engine()` bound to `Settings().archive_path / "archive.db"`; exposes a `sessionmaker` factory (`ArchiveSessionFactory`) for use by repository functions.
2. **AC2:** `src/lcs_cad_mcp/archive/models.py` defines all SQLAlchemy ORM models using `DeclarativeBase`: `DrawingSessionRecord`, `ScrutinyRun`, `RuleResultRecord`, `ConfigVersionRecord`, `ReportRecord`, `ToolEvent`.
3. **AC3:** `DrawingSessionRecord` table (`drawing_sessions`): `id` (UUID string PK), `project_name` (str), `drawing_path` (str), `config_path` (str), `started_at` (str ISO 8601), `ended_at` (str ISO 8601, nullable), `status` (str).
4. **AC4:** `ScrutinyRun` table (`scrutiny_runs`): `id` (UUID string PK), `session_id` (FK → `drawing_sessions.id`), `run_date` (str ISO 8601), `config_version` (str), `config_hash` (str), `rule_set_name` (str), `overall_status` (str: "COMPLIANT"/"NON_COMPLIANT"), `drawing_path` (str).
5. **AC5:** `RuleResultRecord` table (`rule_results`): `id` (UUID string PK), `run_id` (FK → `scrutiny_runs.id`), `rule_id` (str), `rule_name` (str), `status` (str: "PASS"/"FAIL"), `computed_value` (float, nullable), `permissible_value` (float, nullable), `unit` (str), `description` (str).
6. **AC6:** `ConfigVersionRecord` table (`config_versions`): `id` (UUID string PK), `run_id` (FK → `scrutiny_runs.id`), `version` (str), `config_hash` (str), `config_snapshot_json` (str — full JSON serialization of config at time of run), `recorded_at` (str ISO 8601).
7. **AC7:** `ReportRecord` table (`report_records`): `id` (UUID string PK), `run_id` (FK → `scrutiny_runs.id`), `format` (str: "pdf"/"docx"/"json"), `file_path` (str), `generated_at` (str ISO 8601).
8. **AC8:** `ToolEvent` table (`tool_events`): `id` (UUID string PK), `session_id` (FK → `drawing_sessions.id`), `tool_name` (str), `called_at` (str ISO 8601), `params_summary` (str — JSON-serialized param dict, truncated to 1000 chars), `outcome` (str: "success"/"error"), `error_code` (str, nullable).
9. **AC9:** All tables created at server startup via `Base.metadata.create_all(engine)` called from `archive/__init__.py`; no migration tool required for initial schema (schema is append-only; breaking changes require a new story).
10. **AC10:** `src/lcs_cad_mcp/archive/repository.py` exposes stub query functions: `save_scrutiny_run()`, `get_scrutiny_runs()`, `save_tool_event()`, `get_tool_events()` — stubs return `NotImplementedError` with descriptive message; full implementations in Stories 11-2 and 11-4.
11. **AC11:** `ARCHIVE_PATH` env var controls both the SQLite DB file location and artifact file storage location (FR43).
12. **AC12:** Unit tests verify: engine creation succeeds, all tables created, ORM models instantiate without error, FK relationships resolve correctly.

## Tasks / Subtasks

- [ ] Task 1: Implement `archive/engine.py` — SQLite engine and session factory (AC: 1, 11)
  - [ ] 1.1: Import `sqlalchemy.create_engine`, `sqlalchemy.orm.sessionmaker`; import `Settings` from `lcs_cad_mcp.settings`
  - [ ] 1.2: Implement `get_engine()` factory function: `engine = create_engine(f"sqlite:///{Settings().archive_path / 'archive.db'}", echo=False, future=True, connect_args={"check_same_thread": False})`; add inline comment explaining `check_same_thread=False` is safe because SQLAlchemy session management handles thread safety
  - [ ] 1.3: Implement `ArchiveSessionFactory`: `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())`; expose as module-level `SessionLocal`
  - [ ] 1.4: Ensure `ARCHIVE_PATH` directory is created if absent: `Settings().archive_path.mkdir(parents=True, exist_ok=True)` before engine creation
  - [ ] 1.5: Add `get_db_session()` context manager function: `@contextmanager def get_db_session(): session = SessionLocal(); try: yield session; session.commit(); except: session.rollback(); raise; finally: session.close()` — this is the ACID transaction wrapper for all repository operations

- [ ] Task 2: Implement `archive/models.py` — all SQLAlchemy ORM models (AC: 2, 3, 4, 5, 6, 7, 8)
  - [ ] 2.1: Import `sqlalchemy` column types and ORM base: `from sqlalchemy import String, Float, ForeignKey, Text`; `from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship`; define `class Base(DeclarativeBase): pass`
  - [ ] 2.2: Implement `DrawingSessionRecord` ORM model with `__tablename__ = "drawing_sessions"` and all fields per AC3; use `Mapped[str]` for non-nullable string fields, `Mapped[str | None]` for nullable; default `id` to `default=lambda: str(uuid.uuid4())`
  - [ ] 2.3: Implement `ScrutinyRun` ORM model with `__tablename__ = "scrutiny_runs"` and all fields per AC4; add FK: `session_id: Mapped[str] = mapped_column(ForeignKey("drawing_sessions.id"))`; add `relationship("DrawingSessionRecord", back_populates="scrutiny_runs")`
  - [ ] 2.4: Implement `RuleResultRecord` ORM model with `__tablename__ = "rule_results"` and all fields per AC5; `computed_value` and `permissible_value` as `Mapped[float | None]`; FK to `scrutiny_runs.id`
  - [ ] 2.5: Implement `ConfigVersionRecord` ORM model with `__tablename__ = "config_versions"` and all fields per AC6; `config_snapshot_json: Mapped[str] = mapped_column(Text)` for storing full JSON
  - [ ] 2.6: Implement `ReportRecord` ORM model with `__tablename__ = "report_records"` and all fields per AC7; `format` constrained to `"pdf"`, `"docx"`, `"json"` by application logic (not DB constraint)
  - [ ] 2.7: Implement `ToolEvent` ORM model with `__tablename__ = "tool_events"` and all fields per AC8; `params_summary: Mapped[str] = mapped_column(Text)` truncated to 1000 chars at write time; `error_code: Mapped[str | None]`
  - [ ] 2.8: Add `back_populates` relationships on `DrawingSessionRecord` to enable `session.scrutiny_runs` and `session.tool_events` navigation; add `cascade="all, delete-orphan"` on child relationships

- [ ] Task 3: Implement `archive/repository.py` — stub query functions (AC: 10)
  - [ ] 3.1: Create `save_scrutiny_run(db_session, scrutiny_run_data: dict) -> str` stub — raises `NotImplementedError("Implemented in Story 11-2")`
  - [ ] 3.2: Create `get_scrutiny_runs(db_session, project_name: str | None = None, run_date: str | None = None, config_version: str | None = None) -> list` stub
  - [ ] 3.3: Create `save_tool_event(db_session, event_data: dict) -> None` stub — raises `NotImplementedError("Implemented in Story 11-4")`
  - [ ] 3.4: Create `get_tool_events(db_session, session_id: str | None = None) -> list` stub
  - [ ] 3.5: Document each stub with a docstring describing the expected signature and return type for Stories 11-2 and 11-4 to implement

- [ ] Task 4: Implement `archive/__init__.py` — initialization and `create_all` (AC: 9)
  - [ ] 4.1: In `archive/__init__.py`, implement `init_archive() -> None`: calls `Settings().archive_path.mkdir(parents=True, exist_ok=True)`, then `Base.metadata.create_all(get_engine())`; add log message: `logger.info("Archive database initialized at %s", ...)`
  - [ ] 4.2: Call `init_archive()` from server startup in `server.py` or `__main__.py` — it must run before any MCP tool can be called
  - [ ] 4.3: Ensure `init_archive()` is idempotent: calling it multiple times does NOT drop or recreate existing tables (SQLAlchemy `create_all()` is safe to call repeatedly)
  - [ ] 4.4: Export `init_archive`, `get_engine`, `SessionLocal`, `get_db_session`, `Base` from `archive/__init__.py`

- [ ] Task 5: Write unit tests for schema and ORM (AC: 12)
  - [ ] 5.1: Create `tests/unit/archive/__init__.py` and `test_schema.py`
  - [ ] 5.2: Add `tmp_archive_engine` pytest fixture: creates in-memory SQLite engine (`create_engine("sqlite:///:memory:")`) with `Base.metadata.create_all(engine)` for test isolation
  - [ ] 5.3: Test all tables exist after `create_all`: use `inspect(engine).get_table_names()` and assert all 6 table names present
  - [ ] 5.4: Test `DrawingSessionRecord` instantiation: create instance with required fields, add to session, commit, query back; assert all fields persisted correctly
  - [ ] 5.5: Test `ScrutinyRun` FK relationship: create `DrawingSessionRecord`, then `ScrutinyRun(session_id=session.id, ...)`, commit, query `ScrutinyRun` — assert `session_id` resolves
  - [ ] 5.6: Test `ToolEvent` FK relationship: create `DrawingSessionRecord`, then `ToolEvent(session_id=session.id, ...)`, commit, query back; assert `called_at` is ISO 8601 string (not a datetime object)
  - [ ] 5.7: Test `RuleResultRecord` nullable floats: insert with `computed_value=None` and `permissible_value=None`; assert persisted and retrieved as `None`
  - [ ] 5.8: Test `init_archive()` idempotency: call twice; assert no exception and tables still exist after second call

- [ ] Task 6: Integrate `init_archive()` into server startup (AC: 9, 11)
  - [ ] 6.1: In `src/lcs_cad_mcp/server.py` or `__main__.py`, call `from lcs_cad_mcp.archive import init_archive; init_archive()` before `mcp.run()`
  - [ ] 6.2: Verify server starts cleanly with `ARCHIVE_PATH` set in `.env` — confirm `archive.db` file created at the expected location
  - [ ] 6.3: Confirm no import-time DB operations — `init_archive()` must be called explicitly, never triggered by module import

## Dev Notes

### Critical Architecture Constraints

1. **SQLite only — no PostgreSQL, MySQL, or other backends.** The system is a local MCP server; SQLite provides sufficient ACID guarantees and zero-config deployment. `check_same_thread=False` is required for FastMCP's async handlers to share the engine.
2. **All date/time fields stored as ISO 8601 strings — never `datetime` Python objects or Unix timestamps.** SQLAlchemy `String` column type is correct for these fields. SQLite natively stores dates as TEXT when the column type is `String`.
3. **Area `computed_value` stored at full float precision in `RuleResultRecord`.** SQLAlchemy `Float` maps to SQLite `REAL` (8-byte IEEE 754 double). Never round values at the DB layer.
4. **UUIDs as string PKs.** All `id` fields are `str` type, defaulting to `str(uuid.uuid4())`. Do NOT use SQLite auto-increment integers — UUIDs ensure global uniqueness across archive merge/import scenarios.
5. **`create_all()` is the schema management strategy.** No Alembic migrations for v1. Schema changes in future stories require a new migration story. Append-only schema evolution is the convention.
6. **Repository functions use the `get_db_session()` context manager.** Callers never manage transactions manually. The context manager handles commit-on-success and rollback-on-exception automatically (NFR9 ACID requirement).

### Module/Component Notes

**`engine.py` complete implementation:**

```python
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lcs_cad_mcp.settings import Settings


def get_engine():
    settings = Settings()
    settings.archive_path.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{settings.archive_path / 'archive.db'}"
    return create_engine(
        db_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},  # safe: SQLAlchemy session manages thread safety
    )


_engine = None


def _get_or_create_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


SessionLocal = sessionmaker(autocommit=False, autoflush=False)


@contextmanager
def get_db_session():
    engine = _get_or_create_engine()
    SessionLocal.configure(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**`models.py` key patterns:**

```python
import uuid
from sqlalchemy import String, Float, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DrawingSessionRecord(Base):
    __tablename__ = "drawing_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_name: Mapped[str] = mapped_column(String, nullable=False)
    drawing_path: Mapped[str] = mapped_column(String, nullable=False)
    config_path: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[str] = mapped_column(String, nullable=False)  # ISO 8601
    ended_at: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")

    scrutiny_runs: Mapped[list["ScrutinyRun"]] = relationship(
        "ScrutinyRun", back_populates="session", cascade="all, delete-orphan"
    )
    tool_events: Mapped[list["ToolEvent"]] = relationship(
        "ToolEvent", back_populates="session", cascade="all, delete-orphan"
    )
```

### Project Structure Notes

Files to create or modify for this story:

```
src/lcs_cad_mcp/archive/
├── __init__.py        # init_archive(), exports
├── engine.py          # get_engine(), get_db_session(), SessionLocal
├── models.py          # All ORM models (DrawingSessionRecord, ScrutinyRun, ...)
└── repository.py      # Stub query functions

src/lcs_cad_mcp/
└── server.py          # MODIFY: call init_archive() at startup

tests/unit/archive/
├── __init__.py        # NEW
└── test_schema.py     # NEW
```

### Dependencies

- **Story 1-1** (pyproject.toml with `sqlalchemy` declared — already present from scaffold)
- **Story 1-2** (server.py / `__main__.py` — integration point for `init_archive()` call)
- **Story 1-5** (`Settings` class with `archive_path: Path` attribute)
- No other stories are prerequisites — this story can be developed in parallel with Epics 2–10

### References

- NFR9: ACID transactions — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 11 NFR coverage]
- FR43: ARCHIVE_PATH env var — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 11, Story 11-1, AC6]
- SQLAlchemy ORM models — [Source: Architecture mandatory context — EPIC 11 SPECIFIC CONTEXT, 11-1]
- ISO 8601 date storage rule — [Source: Architecture mandatory context — DATES section]
- Area full precision storage — [Source: Architecture mandatory context — AREAS section]
- UUID string PK pattern — [Source: Architecture mandatory context — EPIC 11 SPECIFIC CONTEXT]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/archive/__init__.py`
- `src/lcs_cad_mcp/archive/engine.py`
- `src/lcs_cad_mcp/archive/models.py`
- `src/lcs_cad_mcp/archive/repository.py`
- `src/lcs_cad_mcp/server.py` (modified — `init_archive()` call added)
- `tests/unit/archive/__init__.py`
- `tests/unit/archive/test_schema.py`
