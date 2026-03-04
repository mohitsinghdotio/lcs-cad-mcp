"""Entity management business logic."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lcs_cad_mcp.session.context import DrawingSession

logger = logging.getLogger(__name__)


class EntityService:
    """Manages CAD entity operations — draw, query, move, copy, delete."""

    def __init__(self, session: DrawingSession) -> None:
        self._session = session

    def _require_open(self) -> None:
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        if not self._session.is_drawing_open:
            raise MCPError(
                code=ErrorCode.SESSION_DRAWING_NOT_OPEN,
                message="No drawing is open. Call cad_open_drawing or cad_new_drawing first.",
                recoverable=True,
            )

    def draw_polyline(self, points: list[list[float]], layer: str, closed: bool = False) -> dict:
        self._require_open()
        pts = [tuple(p[:2]) for p in points]
        info = self._session.backend.draw_polyline(pts, layer=layer, closed=closed)
        return info.model_dump()

    def draw_line(self, start: list[float], end: list[float], layer: str) -> dict:
        self._require_open()
        info = self._session.backend.draw_line(
            tuple(start[:2]), tuple(end[:2]), layer=layer
        )
        return info.model_dump()

    def draw_arc(self, center: list[float], radius: float, start_angle: float,
                 end_angle: float, layer: str) -> dict:
        self._require_open()
        info = self._session.backend.draw_arc(
            tuple(center[:2]), radius, start_angle, end_angle, layer=layer
        )
        return info.model_dump()

    def draw_circle(self, center: list[float], radius: float, layer: str) -> dict:
        self._require_open()
        info = self._session.backend.draw_circle(tuple(center[:2]), radius, layer=layer)
        return info.model_dump()

    def add_text(self, text: str, position: list[float], height: float, layer: str) -> dict:
        self._require_open()
        info = self._session.backend.add_text(text, tuple(position[:2]), height, layer=layer)
        return info.model_dump()

    def insert_block(self, block_name: str, position: list[float], scale: float, layer: str) -> dict:
        self._require_open()
        info = self._session.backend.insert_block(block_name, tuple(position[:2]), scale, layer=layer)
        return info.model_dump()

    def move_entity(self, handle: str, displacement: list[float]) -> dict:
        self._require_open()
        info = self._session.backend.move_entity(handle, tuple(displacement[:2]))
        return info.model_dump()

    def copy_entity(self, handle: str, displacement: list[float]) -> dict:
        self._require_open()
        info = self._session.backend.copy_entity(handle, tuple(displacement[:2]))
        return info.model_dump()

    def delete_entity(self, handle: str) -> bool:
        self._require_open()
        return self._session.backend.delete_entity(handle)

    def change_layer(self, handle: str, target_layer: str) -> dict:
        """Move an entity to a different layer (ezdxf-specific)."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        from lcs_cad_mcp.backends.base import EntityInfo

        self._require_open()
        backend = self._session.backend
        if hasattr(backend, "_doc") and backend._doc is not None:
            entity = backend._doc.entitydb.get(handle)
            if entity is None:
                raise MCPError(
                    code=ErrorCode.ENTITY_NOT_FOUND,
                    message=f"Entity handle '{handle}' not found.",
                    recoverable=True,
                )
            entity.dxf.layer = target_layer
            return EntityInfo(
                handle=handle,
                entity_type=entity.dxftype(),
                layer=target_layer,
                geometry={},
            ).model_dump()
        raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No document.", recoverable=True)

    def close_polyline(self, handle: str) -> dict:
        """Close an LWPOLYLINE entity."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        from lcs_cad_mcp.backends.base import EntityInfo

        self._require_open()
        backend = self._session.backend
        if hasattr(backend, "_doc") and backend._doc is not None:
            entity = backend._doc.entitydb.get(handle)
            if entity is None:
                raise MCPError(code=ErrorCode.ENTITY_NOT_FOUND, message=f"Handle '{handle}' not found.", recoverable=True)
            if entity.dxftype() != "LWPOLYLINE":
                raise MCPError(code=ErrorCode.ENTITY_INVALID, message=f"Entity {handle} is not an LWPOLYLINE.", recoverable=True)
            entity.close(True)
            return EntityInfo(
                handle=handle,
                entity_type="LWPOLYLINE",
                layer=entity.dxf.layer,
                geometry={"closed": True},
            ).model_dump()
        raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No document.", recoverable=True)

    def query_entities(self, layer: str | None = None, entity_type: str | None = None) -> list[dict]:
        self._require_open()
        entities = self._session.backend.query_entities(layer=layer, entity_type=entity_type)
        return [e.model_dump() for e in entities]
