"""Unit tests for CADBackend Protocol and BackendFactory."""
import pytest
from lcs_cad_mcp.backends.base import CADBackend, BackendFactory, DrawingMetadata, LayerInfo, EntityInfo
from lcs_cad_mcp.errors import MCPError, ErrorCode


class MinimalBackend:
    """Minimal class satisfying CADBackend Protocol."""
    def is_available(self): return True
    def open_drawing(self, path): return DrawingMetadata()
    def new_drawing(self, name="Untitled", units="metric"): return DrawingMetadata()
    def save_drawing(self, path, dxf_version="R2018"): return True
    def create_layer(self, name, color=7, linetype="Continuous", lineweight=0.25): return LayerInfo(name=name)
    def delete_layer(self, name): return True
    def list_layers(self): return []
    def get_layer(self, name): return LayerInfo(name=name)
    def draw_polyline(self, points, layer, closed=False): return EntityInfo(handle="h1", entity_type="LWPOLYLINE", layer=layer, geometry={})
    def draw_line(self, start, end, layer): return EntityInfo(handle="h2", entity_type="LINE", layer=layer, geometry={})
    def draw_arc(self, center, radius, start_angle, end_angle, layer): return EntityInfo(handle="h3", entity_type="ARC", layer=layer, geometry={})
    def draw_circle(self, center, radius, layer): return EntityInfo(handle="h4", entity_type="CIRCLE", layer=layer, geometry={})
    def add_text(self, text, position, height, layer): return EntityInfo(handle="h5", entity_type="TEXT", layer=layer, geometry={})
    def insert_block(self, name, position, scale, layer): return EntityInfo(handle="h6", entity_type="INSERT", layer=layer, geometry={})
    def move_entity(self, handle, delta): return EntityInfo(handle=handle, entity_type="LINE", layer="0", geometry={})
    def copy_entity(self, handle, delta): return EntityInfo(handle="h_copy", entity_type="LINE", layer="0", geometry={})
    def delete_entity(self, handle): return True
    def query_entities(self, layer=None, entity_type=None, bounds=None): return []
    def get_drawing_metadata(self): return DrawingMetadata()


class IncompleteBackend:
    """Missing several required methods — should fail Protocol check."""
    def is_available(self): return True
    def open_drawing(self, path): return DrawingMetadata()


def test_minimal_backend_satisfies_protocol():
    assert isinstance(MinimalBackend(), CADBackend)


def test_incomplete_backend_fails_protocol_check():
    assert not isinstance(IncompleteBackend(), CADBackend)


def test_mock_backend_satisfies_protocol(mock_backend):
    assert isinstance(mock_backend, CADBackend)


def test_backend_factory_get_ezdxf():
    backend = BackendFactory.get("ezdxf")
    assert backend is not None
    assert backend.is_available() is True


def test_backend_factory_get_unknown_raises():
    with pytest.raises(MCPError) as exc_info:
        BackendFactory.get("unknown_backend_xyz")
    assert exc_info.value.code == ErrorCode.BACKEND_UNAVAILABLE


def test_backend_factory_register_and_get():
    BackendFactory.register("minimal_test", MinimalBackend)
    backend = BackendFactory.get("minimal_test")
    assert isinstance(backend, MinimalBackend)
    # Cleanup
    del BackendFactory._registry["minimal_test"]
