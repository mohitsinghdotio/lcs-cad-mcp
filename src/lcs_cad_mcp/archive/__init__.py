"""Archive package — SQLite-backed scrutiny run storage and audit trail."""
import logging

from lcs_cad_mcp.archive.engine import get_engine, SessionLocal, get_db_session
from lcs_cad_mcp.archive.models import Base

__all__ = ["init_archive", "get_engine", "SessionLocal", "get_db_session", "Base"]

logger = logging.getLogger(__name__)


def init_archive() -> None:
    """Initialize the archive database — create tables if they don't exist.

    Idempotent: calling multiple times is safe (SQLAlchemy create_all is a no-op for
    existing tables).
    """
    try:
        engine = get_engine()
        Base.metadata.create_all(engine)
        logger.info("Archive database initialized")
    except Exception as exc:
        logger.warning("Archive initialization failed (continuing without archive): %s", exc)
