"""Shared pytest fixtures for all tests."""
from __future__ import annotations

import pytest

from lcs_cad_mcp.backends.base import (
    CADBackend,
    DrawingMetadata,
    EntityInfo,
    LayerInfo,
)
from lcs_cad_mcp.session.context import DrawingSession


class MockCADBackend:
    """In-memory stub that satisfies the CADBackend Protocol.

    Every method returns a sensible stub value.  Tests can override return
    values by monkey-patching individual methods.
    """

    def __init__(self) -> None:
        self._layers: dict[str, LayerInfo] = {
            "0": LayerInfo(name="0", color=7, linetype="Continuous")
        }
        self._entities: dict[str, EntityInfo] = {}
        self._handle_counter = 1
        self._metadata = DrawingMetadata(file_path=None, layer_count=1)

    def _next_handle(self) -> str:
        h = f"MOCK{self._handle_counter:04d}"
        self._handle_counter += 1
        return h

    def is_available(self) -> bool:
        return True

    def open_drawing(self, path: str) -> DrawingMetadata:
        self._metadata = DrawingMetadata(file_path=path, layer_count=len(self._layers))
        return self._metadata

    def new_drawing(self, name: str = "Untitled", units: str = "metric") -> DrawingMetadata:
        self._metadata = DrawingMetadata(file_path=None, units=units)
        return self._metadata

    def save_drawing(self, path: str, dxf_version: str = "R2018") -> bool:
        self._metadata = DrawingMetadata(file_path=path)
        return True

    def create_layer(
        self,
        name: str,
        color: int = 7,
        linetype: str = "Continuous",
        lineweight: float = 0.25,
    ) -> LayerInfo:
        info = LayerInfo(name=name, color=color, linetype=linetype, lineweight=lineweight)
        self._layers[name] = info
        return info

    def delete_layer(self, name: str) -> bool:
        self._layers.pop(name, None)
        return True

    def list_layers(self) -> list[LayerInfo]:
        return list(self._layers.values())

    def get_layer(self, name: str) -> LayerInfo:
        if name not in self._layers:
            from lcs_cad_mcp.errors import MCPError, ErrorCode
            raise MCPError(code=ErrorCode.LAYER_NOT_FOUND, message=f"Layer '{name}' not found.")
        return self._layers[name]

    def draw_polyline(
        self,
        points: list[tuple[float, float]],
        layer: str,
        closed: bool = False,
    ) -> EntityInfo:
        h = self._next_handle()
        info = EntityInfo(handle=h, entity_type="LWPOLYLINE", layer=layer,
                          geometry={"points": [list(p) for p in points], "closed": closed})
        self._entities[h] = info
        return info

    def draw_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        layer: str,
    ) -> EntityInfo:
        h = self._next_handle()
        info = EntityInfo(handle=h, entity_type="LINE", layer=layer,
                          geometry={"start": list(start), "end": list(end)})
        self._entities[h] = info
        return info

    def draw_arc(
        self,
        center: tuple[float, float],
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str,
    ) -> EntityInfo:
        h = self._next_handle()
        info = EntityInfo(handle=h, entity_type="ARC", layer=layer,
                          geometry={"center": list(center), "radius": radius,
                                    "start_angle": start_angle, "end_angle": end_angle})
        self._entities[h] = info
        return info

    def draw_circle(
        self,
        center: tuple[float, float],
        radius: float,
        layer: str,
    ) -> EntityInfo:
        h = self._next_handle()
        info = EntityInfo(handle=h, entity_type="CIRCLE", layer=layer,
                          geometry={"center": list(center), "radius": radius})
        self._entities[h] = info
        return info

    def add_text(
        self,
        text: str,
        position: tuple[float, float],
        height: float,
        layer: str,
    ) -> EntityInfo:
        h = self._next_handle()
        info = EntityInfo(handle=h, entity_type="TEXT", layer=layer,
                          geometry={"text": text, "position": list(position), "height": height})
        self._entities[h] = info
        return info

    def insert_block(
        self,
        name: str,
        position: tuple[float, float],
        scale: float,
        layer: str,
    ) -> EntityInfo:
        h = self._next_handle()
        info = EntityInfo(handle=h, entity_type="INSERT", layer=layer,
                          geometry={"block_name": name, "position": list(position), "scale": scale})
        self._entities[h] = info
        return info

    def move_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo:
        if handle not in self._entities:
            from lcs_cad_mcp.errors import MCPError, ErrorCode
            raise MCPError(code=ErrorCode.ENTITY_NOT_FOUND, message=f"Handle '{handle}' not found.")
        entity = self._entities[handle]
        return EntityInfo(handle=handle, entity_type=entity.entity_type, layer=entity.layer,
                          geometry={**entity.geometry, "delta": list(delta)})

    def copy_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo:
        if handle not in self._entities:
            from lcs_cad_mcp.errors import MCPError, ErrorCode
            raise MCPError(code=ErrorCode.ENTITY_NOT_FOUND, message=f"Handle '{handle}' not found.")
        src = self._entities[handle]
        new_h = self._next_handle()
        info = EntityInfo(handle=new_h, entity_type=src.entity_type, layer=src.layer,
                          geometry={**src.geometry, "copied_from": handle, "delta": list(delta)})
        self._entities[new_h] = info
        return info

    def delete_entity(self, handle: str) -> bool:
        self._entities.pop(handle, None)
        return True

    def query_entities(
        self,
        layer: str | None = None,
        entity_type: str | None = None,
        bounds: tuple[float, float, float, float] | None = None,
    ) -> list[EntityInfo]:
        results = []
        for entity in self._entities.values():
            if layer is not None and entity.layer != layer:
                continue
            if entity_type is not None and entity.entity_type != entity_type.upper():
                continue
            results.append(entity)
        return results

    def get_drawing_metadata(self) -> DrawingMetadata:
        return DrawingMetadata(
            file_path=self._metadata.file_path,
            entity_count=len(self._entities),
            layer_count=len(self._layers),
        )


@pytest.fixture
def mock_backend() -> MockCADBackend:
    """Return a fresh MockCADBackend instance."""
    return MockCADBackend()


@pytest.fixture
def mock_session(mock_backend: MockCADBackend) -> DrawingSession:
    """Return a DrawingSession with a MockCADBackend attached."""
    session = DrawingSession(session_id="test-session-001", backend=mock_backend)
    return session
