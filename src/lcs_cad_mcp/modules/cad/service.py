"""Business logic for CAD drawing lifecycle and backend selection."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lcs_cad_mcp.backends.base import BackendFactory

if TYPE_CHECKING:
    from lcs_cad_mcp.session.context import DrawingSession

logger = logging.getLogger(__name__)


class CadService:
    """Implements CAD drawing lifecycle operations for the cad module."""

    def __init__(self, session: DrawingSession) -> None:
        self._session = session

    def select_backend(self, backend_name: str) -> dict:
        """Switch the active session's backend.

        Args:
            backend_name: "ezdxf" or "com".

        Returns:
            Dict with backend name, availability, and optional warning.

        Raises:
            MCPError: BACKEND_UNAVAILABLE if backend not registered or not available.
        """
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        from lcs_cad_mcp.session.snapshot import SnapshotManager

        try:
            new_backend = BackendFactory.get(backend_name)
        except MCPError:
            raise

        if not new_backend.is_available():
            raise MCPError(
                code=ErrorCode.BACKEND_UNAVAILABLE,
                message=f"Backend '{backend_name}' is not available on this system.",
                recoverable=True,
                suggested_action="Use 'ezdxf' backend or ensure AutoCAD is running on Windows.",
            )

        warning = None
        if self._session.is_drawing_open:
            self._session.close_drawing()
            warning = "Active drawing closed during backend switch. Unsaved changes are lost."

        self._session.backend = new_backend
        self._session.snapshots = SnapshotManager(backend=new_backend)
        logger.info("Backend switched to '%s'", backend_name)
        return {"backend": backend_name, "available": True, "warning": warning}

    def open_drawing(self, path: str, read_only: bool = False) -> dict:
        """Open a DXF drawing and mark session as active."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._session.backend is None:
            raise MCPError(
                code=ErrorCode.BACKEND_UNAVAILABLE,
                message="No backend configured for this session.",
                recoverable=True,
            )
        metadata = self._session.backend.open_drawing(path)
        self._session.is_drawing_open = True
        return {
            "path": metadata.file_path,
            "dxf_version": metadata.dxf_version,
            "layer_count": metadata.layer_count,
            "entity_count": metadata.entity_count,
            "read_only": read_only,
        }

    def new_drawing(self, name: str = "Untitled", units: str = "metric") -> dict:
        """Create a new blank drawing."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._session.backend is None:
            raise MCPError(
                code=ErrorCode.BACKEND_UNAVAILABLE,
                message="No backend configured.",
                recoverable=True,
            )
        metadata = self._session.backend.new_drawing(name=name, units=units)
        self._session.is_drawing_open = True
        return {
            "name": name,
            "units": metadata.units,
            "dxf_version": metadata.dxf_version,
            "layer_count": metadata.layer_count,
        }

    def save_drawing(self, path: str, dxf_version: str = "R2018") -> dict:
        """Save the active drawing to disk."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if not self._session.is_drawing_open:
            raise MCPError(
                code=ErrorCode.SESSION_DRAWING_NOT_OPEN,
                message="No drawing is open. Call cad_open_drawing or cad_new_drawing first.",
                recoverable=True,
            )
        self._session.backend.save_drawing(path, dxf_version=dxf_version)
        return {"path": path, "dxf_version": dxf_version}

    def get_metadata(self) -> dict:
        """Return metadata about the active drawing."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if not self._session.is_drawing_open:
            raise MCPError(
                code=ErrorCode.SESSION_DRAWING_NOT_OPEN,
                message="No drawing is open.",
                recoverable=True,
            )
        meta = self._session.backend.get_drawing_metadata()
        return meta.model_dump()
