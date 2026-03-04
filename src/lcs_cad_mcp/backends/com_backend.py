"""Windows COM (AutoCAD) backend stub.

This backend is only available on Windows with AutoCAD installed.
It satisfies the CADBackend Protocol structurally.
"""
from __future__ import annotations

import sys
import logging

from lcs_cad_mcp.backends.base import DrawingMetadata, EntityInfo, LayerInfo

logger = logging.getLogger(__name__)


class COMBackend:
    """AutoCAD COM automation backend (Windows only)."""

    def __init__(self) -> None:
        self._app = None
        self._doc = None
        self._current_path: str | None = None

    def is_available(self) -> bool:
        """Return True only on Windows with win32com installed."""
        if sys.platform != "win32":
            return False
        try:
            import win32com.client  # noqa: F401
            return True
        except ImportError:
            return False

    def _require_available(self) -> None:
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        if not self.is_available():
            raise MCPError(
                code=ErrorCode.BACKEND_UNAVAILABLE,
                message="COM backend requires Windows with AutoCAD and win32com installed.",
                recoverable=False,
                suggested_action="Use 'ezdxf' backend on non-Windows platforms.",
            )

    def open_drawing(self, path: str) -> DrawingMetadata:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(
            code=ErrorCode.BACKEND_UNAVAILABLE,
            message="COM backend open_drawing not yet implemented.",
            recoverable=False,
        )

    def new_drawing(self, name: str = "Untitled", units: str = "metric") -> DrawingMetadata:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(
            code=ErrorCode.BACKEND_UNAVAILABLE,
            message="COM backend new_drawing not yet implemented.",
            recoverable=False,
        )

    def save_drawing(self, path: str, dxf_version: str = "R2018") -> bool:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(
            code=ErrorCode.BACKEND_UNAVAILABLE,
            message="COM backend save_drawing not yet implemented.",
            recoverable=False,
        )

    def create_layer(self, name: str, color: int = 7, linetype: str = "Continuous", lineweight: float = 0.25) -> LayerInfo:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def delete_layer(self, name: str) -> bool:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def list_layers(self) -> list[LayerInfo]:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def get_layer(self, name: str) -> LayerInfo:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def draw_polyline(self, points: list[tuple[float, float]], layer: str, closed: bool = False) -> EntityInfo:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def draw_line(self, start: tuple[float, float], end: tuple[float, float], layer: str) -> EntityInfo:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def draw_arc(self, center: tuple[float, float], radius: float, start_angle: float, end_angle: float, layer: str) -> EntityInfo:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def draw_circle(self, center: tuple[float, float], radius: float, layer: str) -> EntityInfo:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def add_text(self, text: str, position: tuple[float, float], height: float, layer: str) -> EntityInfo:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def insert_block(self, name: str, position: tuple[float, float], scale: float, layer: str) -> EntityInfo:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def move_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def copy_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def delete_entity(self, handle: str) -> bool:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def query_entities(self, layer: str | None = None, entity_type: str | None = None, bounds: tuple[float, float, float, float] | None = None) -> list[EntityInfo]:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)

    def get_drawing_metadata(self) -> DrawingMetadata:
        self._require_available()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        raise MCPError(code=ErrorCode.BACKEND_UNAVAILABLE, message="Not implemented.", recoverable=False)
