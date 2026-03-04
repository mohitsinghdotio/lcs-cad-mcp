"""Tests for cad module tool handlers."""
import pytest
from unittest.mock import MagicMock
from lcs_cad_mcp.backends.base import DrawingMetadata
from lcs_cad_mcp.modules.cad.schemas import (
    CadOpenDrawingInput, CadNewDrawingInput, CadSaveDrawingInput, CadSelectBackendInput,
)
from lcs_cad_mcp.modules.cad.tools import (
    cad_open_drawing, cad_new_drawing, cad_save_drawing, cad_select_backend,
)


def _make_session(is_open=False):
    session = MagicMock()
    session.is_drawing_open = is_open
    session.backend.is_available.return_value = True
    session.backend.open_drawing.return_value = DrawingMetadata(
        file_path="/tmp/test.dxf", layer_count=1, entity_count=0
    )
    session.backend.new_drawing.return_value = DrawingMetadata(
        file_path=None, units="metric", layer_count=1
    )
    session.backend.save_drawing.return_value = True
    return session


@pytest.mark.asyncio
async def test_cad_open_drawing_returns_success():
    session = _make_session()
    inp = CadOpenDrawingInput(path="/tmp/test.dxf")
    result = await cad_open_drawing(inp, session)
    assert result["success"] is True
    assert result["data"]["path"] == "/tmp/test.dxf"
    assert result["data"]["read_only"] is False


@pytest.mark.asyncio
async def test_cad_open_drawing_read_only_flag():
    session = _make_session()
    inp = CadOpenDrawingInput(path="/tmp/test.dxf", read_only=True)
    result = await cad_open_drawing(inp, session)
    assert result["success"] is True
    assert result["data"]["read_only"] is True


@pytest.mark.asyncio
async def test_cad_new_drawing_returns_success():
    session = _make_session()
    inp = CadNewDrawingInput(name="MyDrawing", units="metric")
    result = await cad_new_drawing(inp, session)
    assert result["success"] is True
    assert result["data"]["name"] == "MyDrawing"


@pytest.mark.asyncio
async def test_cad_save_drawing_requires_open_drawing():
    session = _make_session(is_open=False)
    inp = CadSaveDrawingInput(path="/tmp/out.dxf")
    result = await cad_save_drawing(inp, session)
    assert result["success"] is False
    assert result["error"]["code"] == "SESSION_DRAWING_NOT_OPEN"


@pytest.mark.asyncio
async def test_cad_save_drawing_saves_successfully():
    session = _make_session(is_open=True)
    inp = CadSaveDrawingInput(path="/tmp/out.dxf", dxf_version="R2018")
    result = await cad_save_drawing(inp, session)
    assert result["success"] is True
    assert result["data"]["path"] == "/tmp/out.dxf"


@pytest.mark.asyncio
async def test_cad_select_backend_invalid():
    session = _make_session()
    inp = CadSelectBackendInput(backend="autocad_bad")
    result = await cad_select_backend(inp, session)
    assert result["success"] is False
    assert result["error"]["code"] == "BACKEND_UNAVAILABLE"
