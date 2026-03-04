"""DrawingSession — holds the active backend, snapshot manager, and event log."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lcs_cad_mcp.session.event_log import EventLog
from lcs_cad_mcp.session.snapshot import SnapshotManager

if TYPE_CHECKING:
    from lcs_cad_mcp.backends.base import CADBackend

logger = logging.getLogger(__name__)


class DrawingSession:
    """Active drawing session.  One instance per connected client session."""

    def __init__(self, backend: CADBackend | None = None, session_id: str = "") -> None:
        self.session_id = session_id
        self.backend = backend
        self.snapshots: SnapshotManager | None = (
            SnapshotManager(backend=backend) if backend is not None else None
        )
        self.event_log: EventLog = EventLog()
        self.is_drawing_open: bool = False

    def close_drawing(self) -> None:
        """Close the active drawing, releasing resources."""
        self.is_drawing_open = False
        if self.snapshots is not None:
            self.snapshots.clear()
        logger.info("Drawing closed for session %s", self.session_id)

    def rollback(self) -> None:
        """Revert drawing to last snapshot.  Called on non-recoverable errors."""
        logger.info("Rollback triggered for session=%s", self.session_id)
        if self.snapshots is not None:
            self.snapshots.restore_latest()
