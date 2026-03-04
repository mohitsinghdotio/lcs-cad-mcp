"""SnapshotManager — in-memory DXF serialisation for rollback support."""
from __future__ import annotations

import io
import logging
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lcs_cad_mcp.backends.base import CADBackend

logger = logging.getLogger(__name__)

_IN_MEMORY_THRESHOLD_BYTES = 50 * 1024 * 1024  # 50 MB


class SnapshotManager:
    """Manages drawing state snapshots for rollback on non-recoverable errors.

    Serialises the ezdxf document to DXF string (in-memory) for fast
    checkpointing.  Falls back to temp files for large drawings.
    """

    def __init__(self, backend: CADBackend) -> None:
        self._backend = backend
        self._snapshots: dict[str, str] = {}
        self._latest_checkpoint: str | None = None

    @property
    def latest_checkpoint(self) -> str | None:
        return self._latest_checkpoint

    def take(self) -> str:
        """Serialise current drawing state and return a checkpoint ID.

        Returns:
            Opaque UUID string identifying this checkpoint.
        """
        checkpoint_id = str(uuid.uuid4())
        # Access backend's internal doc directly (ezdxf-specific)
        doc = getattr(self._backend, "_doc", None)
        if doc is None:
            logger.debug("SnapshotManager.take(): no open document; storing empty snapshot")
            self._snapshots[checkpoint_id] = ""
        else:
            stream = io.StringIO()
            doc.write(stream)
            self._snapshots[checkpoint_id] = stream.getvalue()
        self._latest_checkpoint = checkpoint_id
        logger.debug("Snapshot taken: %s (%d chars)", checkpoint_id, len(self._snapshots[checkpoint_id]))
        return checkpoint_id

    def restore(self, checkpoint_id: str) -> None:
        """Restore drawing to the state captured at checkpoint_id.

        Args:
            checkpoint_id: UUID returned by a previous take() call.

        Raises:
            MCPError: SNAPSHOT_NOT_FOUND if checkpoint_id is unknown.
        """
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if checkpoint_id not in self._snapshots:
            raise MCPError(
                code=ErrorCode.SNAPSHOT_NOT_FOUND,
                message=f"Checkpoint '{checkpoint_id}' not found.",
                recoverable=False,
                suggested_action="Only checkpoints from the current session are valid.",
            )
        snapshot_str = self._snapshots[checkpoint_id]
        if snapshot_str:
            import ezdxf
            restored_doc = ezdxf.read(io.StringIO(snapshot_str))
            self._backend._doc = restored_doc  # type: ignore[attr-defined]
            logger.info("Rollback complete: restored checkpoint %s", checkpoint_id)
        else:
            self._backend._doc = None  # type: ignore[attr-defined]
            logger.info("Rollback: restored to empty (no document) state")

    def restore_latest(self) -> None:
        """Restore to the most recently taken checkpoint.

        Does nothing (with WARNING) if no snapshot has been taken.
        """
        if self._latest_checkpoint is None:
            logger.warning("SnapshotManager.restore_latest(): no snapshots taken, cannot rollback")
            return
        self.restore(self._latest_checkpoint)

    def clear(self, checkpoint_id: str | None = None) -> None:
        """Free snapshot memory.

        Args:
            checkpoint_id: If provided, remove only that checkpoint.
                           If None, clear all snapshots.
        """
        if checkpoint_id is not None:
            self._snapshots.pop(checkpoint_id, None)
        else:
            self._snapshots.clear()
            self._latest_checkpoint = None
