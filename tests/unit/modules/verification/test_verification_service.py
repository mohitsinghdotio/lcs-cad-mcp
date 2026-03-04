"""Unit tests for VerificationService."""
import pytest
from unittest.mock import MagicMock
from lcs_cad_mcp.modules.verification.service import VerificationService
from lcs_cad_mcp.backends.base import EntityInfo, LayerInfo
from lcs_cad_mcp.errors import MCPError, ErrorCode


def _make_mock_session(entities_by_layer=None, layers=None):
    session = MagicMock()
    session.is_drawing_open = True
    entities_by_layer = entities_by_layer or {}
    layers = layers or [LayerInfo(name="0", color=7, linetype="Continuous")]

    def query_entities(layer=None, entity_type=None, bounds=None):
        return entities_by_layer.get(layer, [])

    session.backend.query_entities.side_effect = query_entities
    session.backend.list_layers.return_value = layers
    return session


def _polyline_entity(pts, closed=True, layer="TEST", handle="H001"):
    return EntityInfo(
        handle=handle,
        entity_type="LWPOLYLINE",
        layer=layer,
        geometry={"points": pts, "closed": closed},
    )


def test_verify_closure_all_closed():
    svc = VerificationService(_make_mock_session())
    # Closed square
    pts = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    entity = _polyline_entity(pts, closed=False, layer="WALLS")
    session = _make_mock_session({"WALLS": [entity]})
    svc = VerificationService(session)
    result = svc.verify_closure("WALLS", tolerance=0.001)
    assert result["passed"] is True
    assert result["checked"] == 1


def test_verify_closure_open_polyline():
    pts = [[0, 0], [10, 0], [10, 10], [0, 10]]  # Not closed
    entity = _polyline_entity(pts, closed=False, layer="WALLS", handle="H001")
    session = _make_mock_session({"WALLS": [entity]})
    svc = VerificationService(session)
    result = svc.verify_closure("WALLS", tolerance=0.001)
    assert result["passed"] is False
    assert len(result["failures"]) == 1


def test_verify_closure_no_drawing_open():
    session = _make_mock_session()
    session.is_drawing_open = False
    svc = VerificationService(session)
    with pytest.raises(MCPError) as exc_info:
        svc.verify_closure("TEST")
    assert exc_info.value.code == ErrorCode.SESSION_DRAWING_NOT_OPEN


def test_verify_naming_passes():
    layers = [
        LayerInfo(name="PREDCR-WALL-EXT", color=7, linetype="Continuous"),
        LayerInfo(name="0", color=7, linetype="Continuous"),
    ]
    session = _make_mock_session(layers=layers)
    svc = VerificationService(session)
    result = svc.verify_naming("TEST_AUTH")
    assert result["passed"] is True
    assert result["checked"] == 2


def test_verify_min_entity_count_passes():
    entity = _polyline_entity([[0, 0], [10, 0]], layer="TEST")
    session = _make_mock_session({"TEST": [entity]})
    svc = VerificationService(session)
    result = svc.verify_min_entity_count("TEST", min_count=1)
    assert result["passed"] is True
    assert result["count"] == 1


def test_verify_min_entity_count_fails():
    session = _make_mock_session({})
    svc = VerificationService(session)
    result = svc.verify_min_entity_count("EMPTY", min_count=1)
    assert result["passed"] is False
    assert result["count"] == 0


def test_verify_all_empty_drawing_passes():
    session = _make_mock_session()
    svc = VerificationService(session)
    result = svc.verify_all("TEST_AUTH")
    assert "passed" in result
    assert "layers_checked" in result
