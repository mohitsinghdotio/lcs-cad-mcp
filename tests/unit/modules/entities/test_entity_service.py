"""Unit tests for EntityService."""
import pytest
from lcs_cad_mcp.modules.entities.service import EntityService
from lcs_cad_mcp.errors import MCPError, ErrorCode


@pytest.fixture
def open_session(mock_session):
    """mock_session with is_drawing_open = True."""
    mock_session.is_drawing_open = True
    mock_session.backend.new_drawing()
    return mock_session


def test_draw_polyline(open_session):
    svc = EntityService(open_session)
    result = svc.draw_polyline([[0, 0], [10, 0], [10, 10], [0, 0]], layer="0")
    assert result["entity_type"] == "LWPOLYLINE"
    assert result["layer"] == "0"
    assert "handle" in result


def test_draw_line(open_session):
    svc = EntityService(open_session)
    result = svc.draw_line([0, 0], [10, 0], layer="0")
    assert result["entity_type"] == "LINE"


def test_draw_arc(open_session):
    svc = EntityService(open_session)
    result = svc.draw_arc([5, 5], radius=3.0, start_angle=0.0, end_angle=90.0, layer="0")
    assert result["entity_type"] == "ARC"


def test_draw_circle(open_session):
    svc = EntityService(open_session)
    result = svc.draw_circle([5, 5], radius=3.0, layer="0")
    assert result["entity_type"] == "CIRCLE"


def test_add_text(open_session):
    svc = EntityService(open_session)
    result = svc.add_text("Hello", [0, 0], height=2.5, layer="0")
    assert result["entity_type"] == "TEXT"


def test_query_entities_empty(open_session):
    svc = EntityService(open_session)
    results = svc.query_entities(layer="NONEXISTENT")
    assert results == []


def test_query_entities_by_layer(open_session):
    svc = EntityService(open_session)
    svc.draw_line([0, 0], [10, 0], layer="0")
    svc.draw_line([0, 1], [10, 1], layer="0")
    results = svc.query_entities(layer="0")
    assert len(results) == 2


def test_delete_entity(open_session):
    svc = EntityService(open_session)
    entity = svc.draw_line([0, 0], [10, 0], layer="0")
    handle = entity["handle"]
    result = svc.delete_entity(handle)
    assert result is True


def test_move_entity(open_session):
    svc = EntityService(open_session)
    entity = svc.draw_line([0, 0], [10, 0], layer="0")
    handle = entity["handle"]
    result = svc.move_entity(handle, [5, 5])
    assert result["handle"] == handle


def test_entity_requires_open_drawing():
    """Should raise if no drawing open."""
    from unittest.mock import MagicMock
    session = MagicMock()
    session.is_drawing_open = False
    svc = EntityService(session)
    with pytest.raises(MCPError) as exc_info:
        svc.draw_line([0, 0], [10, 0], layer="0")
    assert exc_info.value.code == ErrorCode.SESSION_DRAWING_NOT_OPEN
