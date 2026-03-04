"""Unit tests for AreaService."""
import pytest
from unittest.mock import MagicMock
from lcs_cad_mcp.modules.area.service import AreaService, AreaComputationError, format_area
from lcs_cad_mcp.backends.base import EntityInfo


def _make_mock_session(entities_by_layer: dict):
    """Create a mock session with backend returning specified entities per layer."""
    session = MagicMock()

    def query_entities(layer=None, entity_type=None, bounds=None):
        return entities_by_layer.get(layer, [])

    session.backend.query_entities.side_effect = query_entities
    return session


def _square_entity(side: float = 10.0, layer: str = "PREDCR-PLOT-BOUNDARY") -> EntityInfo:
    """Create an EntityInfo for a square polygon of given side length."""
    pts = [[0, 0], [side, 0], [side, side], [0, side], [0, 0]]
    return EntityInfo(
        handle="TEST001",
        entity_type="LWPOLYLINE",
        layer=layer,
        geometry={"points": pts, "closed": True},
    )


def test_format_area():
    assert format_area(100.0) == "100.0000"
    assert format_area(1234.5678) == "1234.5678"
    assert format_area(0.12345) == "0.1235"


def test_compute_plot_area_square():
    svc = AreaService()
    entity = _square_entity(10.0)
    session = _make_mock_session({"PREDCR-PLOT-BOUNDARY": [entity]})
    area = svc.compute_plot_area(session)
    assert abs(area - 100.0) < 0.01


def test_compute_plot_area_not_found():
    svc = AreaService()
    session = _make_mock_session({})
    with pytest.raises(AreaComputationError) as exc_info:
        svc.compute_plot_area(session)
    assert exc_info.value.code == "PLOT_BOUNDARY_NOT_FOUND"


def test_compute_layer_area():
    svc = AreaService()
    entity = _square_entity(5.0, layer="TEST-LAYER")
    session = _make_mock_session({"TEST-LAYER": [entity]})
    area = svc.compute_layer_area(session, "TEST-LAYER")
    assert abs(area - 25.0) < 0.01


def test_compute_layer_area_not_found():
    svc = AreaService()
    session = _make_mock_session({})
    with pytest.raises(AreaComputationError) as exc_info:
        svc.compute_layer_area(session, "EMPTY-LAYER")
    assert exc_info.value.code == "NO_POLYGON_FOUND"


def test_compute_builtup_area_multiple_floors():
    svc = AreaService()
    floor1 = _square_entity(10.0, layer="FLOOR-1")
    floor2 = _square_entity(8.0, layer="FLOOR-2")
    session = _make_mock_session({"FLOOR-1": [floor1], "FLOOR-2": [floor2]})
    result = svc.compute_builtup_area(session, ["FLOOR-1", "FLOOR-2"])
    assert abs(result["total"] - 164.0) < 0.1  # 100 + 64


def test_compute_fsi():
    svc = AreaService()
    plot = _square_entity(10.0, layer="PLOT")
    floor = _square_entity(5.0, layer="FLOOR")
    session = _make_mock_session({"PLOT": [plot], "FLOOR": [floor]})
    result = svc.compute_fsi(session, "PLOT", ["FLOOR"])
    assert abs(result["fsi"] - 0.25) < 0.01  # 25/100


def test_compute_coverage():
    svc = AreaService()
    plot = _square_entity(10.0, layer="PLOT")
    footprint = _square_entity(5.0, layer="FOOTPRINT")
    session = _make_mock_session({"PLOT": [plot], "FOOTPRINT": [footprint]})
    result = svc.compute_coverage(session, "PLOT", "FOOTPRINT")
    assert abs(result["coverage_percent"] - 25.0) < 0.01  # 25/100 * 100%


def test_area_sqft_conversion():
    svc = AreaService()
    entity = _square_entity(10.0, layer="TEST")
    session = _make_mock_session({"TEST": [entity]})
    area = svc.compute_layer_area(session, "TEST", unit="sqft")
    assert abs(area - 100.0 * 10.7639) < 0.1
