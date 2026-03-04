"""Tests for cad module tool handlers."""
import pytest
from lcs_cad_mcp.modules.cad.schemas import CadOpenDrawingInput
from lcs_cad_mcp.modules.cad.tools import cad_open_drawing


@pytest.mark.asyncio
async def test_cad_open_drawing_stub_returns_success():
    inp = CadOpenDrawingInput(path="/tmp/test.dxf")
    result = await cad_open_drawing(inp)
    assert result["success"] is True
    assert result["data"]["path"] == "/tmp/test.dxf"
    assert result["data"]["read_only"] is False


@pytest.mark.asyncio
async def test_cad_open_drawing_read_only_flag():
    inp = CadOpenDrawingInput(path="/tmp/test.dxf", read_only=True)
    result = await cad_open_drawing(inp)
    assert result["success"] is True
    assert result["data"]["read_only"] is True
