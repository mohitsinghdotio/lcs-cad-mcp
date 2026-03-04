"""Unit tests for EzdxfBackend drawing lifecycle."""
import pytest
import ezdxf
from lcs_cad_mcp.backends.ezdxf_backend import EzdxfBackend
from lcs_cad_mcp.errors import MCPError, ErrorCode


@pytest.fixture
def backend():
    return EzdxfBackend()


def test_is_available(backend):
    assert backend.is_available() is True


def test_new_drawing_returns_metadata(backend):
    meta = backend.new_drawing("TestDraw", "metric")
    assert meta.layer_count == 1  # layer "0" always created
    assert meta.entity_count == 0
    assert meta.units == "metric"
    assert meta.file_path is None


def test_new_drawing_imperial(backend):
    meta = backend.new_drawing("TestDraw", "imperial")
    assert meta.units == "imperial"


def test_open_drawing_missing_file_raises(backend):
    with pytest.raises(MCPError) as exc_info:
        backend.open_drawing("/nonexistent/path/test.dxf")
    assert exc_info.value.code == ErrorCode.DRAWING_OPEN_FAILED


def test_open_drawing_existing_file(tmp_path, backend):
    dxf_path = tmp_path / "test.dxf"
    doc = ezdxf.new()
    doc.saveas(str(dxf_path))
    meta = backend.open_drawing(str(dxf_path))
    assert meta.file_path == str(dxf_path)
    assert meta.layer_count >= 1


def test_save_drawing_creates_file(tmp_path, backend):
    backend.new_drawing()
    out_path = str(tmp_path / "out.dxf")
    result = backend.save_drawing(out_path)
    assert result is True
    assert (tmp_path / "out.dxf").exists()
    assert (tmp_path / "out.dxf").stat().st_size > 0


def test_save_drawing_no_open_raises(backend):
    with pytest.raises(MCPError) as exc_info:
        backend.save_drawing("/tmp/should_fail.dxf")
    assert exc_info.value.recoverable is True


def test_save_drawing_audit_passes(tmp_path, backend):
    backend.new_drawing()
    out_path = str(tmp_path / "audited.dxf")
    backend.save_drawing(out_path)
    # Re-open and audit
    doc = ezdxf.readfile(out_path)
    auditor = doc.audit()
    critical = [e for e in auditor.errors if e.code >= 10]  # high-severity errors
    assert len(critical) == 0


def test_create_layer(backend):
    backend.new_drawing()
    layer = backend.create_layer("walls", color=3, linetype="DASHED")
    assert layer.name == "walls"
    assert layer.color == 3


def test_list_layers(backend):
    backend.new_drawing()
    backend.create_layer("walls")
    layers = backend.list_layers()
    names = [l.name for l in layers]
    assert "walls" in names
    assert "0" in names


def test_draw_polyline(backend):
    backend.new_drawing()
    backend.create_layer("boundary")
    pts = [(0, 0), (10, 0), (10, 10), (0, 10)]
    entity = backend.draw_polyline(pts, layer="boundary", closed=True)
    assert entity.entity_type == "LWPOLYLINE"
    assert entity.layer == "boundary"
    assert entity.handle is not None


def test_draw_line(backend):
    backend.new_drawing()
    backend.create_layer("walls")
    entity = backend.draw_line((0, 0), (5, 5), layer="walls")
    assert entity.entity_type == "LINE"
    assert entity.handle is not None


def test_draw_circle(backend):
    backend.new_drawing()
    backend.create_layer("column")
    entity = backend.draw_circle((5, 5), 2.0, layer="column")
    assert entity.entity_type == "CIRCLE"


def test_query_entities_by_layer(backend):
    backend.new_drawing()
    backend.create_layer("walls")
    backend.create_layer("columns")
    backend.draw_line((0, 0), (10, 0), layer="walls")
    backend.draw_circle((5, 5), 1.0, layer="columns")
    walls = backend.query_entities(layer="walls")
    assert all(e.layer == "walls" for e in walls)
    assert len(walls) == 1


def test_get_drawing_metadata_after_ops(backend):
    backend.new_drawing()
    backend.create_layer("test")
    backend.draw_line((0, 0), (10, 0), layer="test")
    meta = backend.get_drawing_metadata()
    assert meta.entity_count >= 1
    assert meta.layer_count >= 2
