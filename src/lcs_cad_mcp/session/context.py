"""DrawingSession context — stub with rollback hook (Story 1-4); full impl in Story 2-1+."""
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class DrawingSession:
    """Active drawing session. Holds backend reference, snapshot, event log."""
    session_id: str = ""
    backend: object = None  # CADBackend; typed properly in Story 2-1
    snapshot: object = None  # SnapshotManager; typed properly in Story 2-4
    event_log: list = field(default_factory=list)

    def rollback(self) -> None:
        """Revert drawing to last snapshot. Called on non-recoverable errors."""
        logger.info("rollback triggered for session=%s", self.session_id)
        if self.snapshot is not None:
            # Real impl uses session.snapshot.restore(); stub logs only
            logger.info("snapshot.restore() would be called here")
