"""Unit tests for PreDCRService."""
import pytest
from unittest.mock import MagicMock
from lcs_cad_mcp.modules.predcr.service import PreDCRService
from lcs_cad_mcp.backends.base import LayerInfo
from lcs_cad_mcp.errors import MCPError


def _make_mock_session(layers=None):
    session = MagicMock()
    session.is_drawing_open = True
    layers = layers or [LayerInfo(name="0", color=7, linetype="Continuous")]
    session.backend.list_layers.return_value = layers
    session.backend.create_layer.side_effect = lambda name, color, linetype, **kw: LayerInfo(
        name=name, color=color, linetype=linetype
    )
    return session


def test_create_layers_residential():
    session = _make_mock_session()
    svc = PreDCRService(session)
    result = svc.create_layers("residential")
    assert result["building_type"] == "residential"
    assert result["created_count"] > 0
    assert len(result["created"]) > 0


def test_create_layers_unknown_type():
    session = _make_mock_session()
    svc = PreDCRService(session)
    with pytest.raises(MCPError) as exc_info:
        svc.create_layers("spaceship")
    assert exc_info.value.code == "LAYER_INVALID"


def test_create_layers_skips_existing():
    from lcs_cad_mcp.modules.predcr.layer_registry import get_layers_for_building_type
    specs = get_layers_for_building_type("residential")
    existing = [LayerInfo(name=s.name, color=s.color_index, linetype=s.linetype) for s in specs]
    session = _make_mock_session(layers=existing)
    svc = PreDCRService(session)
    result = svc.create_layers("residential")
    assert result["created_count"] == 0
    assert result["skipped_count"] == len(specs)


def test_get_layer_spec_found():
    session = _make_mock_session()
    svc = PreDCRService(session)
    spec = svc.get_layer_spec("PREDCR-WALL-EXT")
    assert spec["name"] == "PREDCR-WALL-EXT"
    assert spec["color_index"] == 7


def test_get_layer_spec_not_found():
    session = _make_mock_session()
    svc = PreDCRService(session)
    with pytest.raises(MCPError) as exc_info:
        svc.get_layer_spec("NONEXISTENT-LAYER")
    assert exc_info.value.code == "LAYER_NOT_FOUND"


def test_list_layer_specs_all():
    session = _make_mock_session()
    svc = PreDCRService(session)
    specs = svc.list_layer_specs()
    assert len(specs) >= 40


def test_list_layer_specs_filtered():
    session = _make_mock_session()
    svc = PreDCRService(session)
    specs = svc.list_layer_specs("commercial")
    assert len(specs) >= 30
    for s in specs:
        assert "commercial" in s["required_for"]


def test_validate_drawing_no_predcr_layers():
    session = _make_mock_session()
    svc = PreDCRService(session)
    result = svc.validate_drawing("TEST_AUTH")
    assert result["passed"] is False  # Missing layers
    assert len(result["missing_layers"]) > 0


def test_validate_drawing_not_open():
    session = _make_mock_session()
    session.is_drawing_open = False
    svc = PreDCRService(session)
    with pytest.raises(MCPError) as exc_info:
        svc.validate_drawing("TEST")
    assert exc_info.value.code == "SESSION_DRAWING_NOT_OPEN"
