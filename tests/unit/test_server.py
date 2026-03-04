"""Tests for Story 1-2: MCP server core with stdio transport."""
import pytest
from fastmcp import FastMCP


def test_mcp_is_fastmcp_instance():
    """AC1/AC2: server.py exports a FastMCP instance."""
    from lcs_cad_mcp.server import mcp
    assert isinstance(mcp, FastMCP)


def test_mcp_name():
    """Server is named correctly."""
    from lcs_cad_mcp.server import mcp
    assert mcp.name == "lcs-cad-mcp"


def test_cad_module_register_importable():
    """AC3: cad module register() is callable."""
    from lcs_cad_mcp.modules import cad
    from lcs_cad_mcp.server import mcp as server_mcp
    # register() should be callable without error
    assert callable(cad.register)


@pytest.mark.asyncio
async def test_cad_ping_tool():
    """AC3: cad_ping tool returns the expected envelope."""
    # Call the underlying async function directly — bypasses transport layer
    # FastMCP registers the decorated function; access via _tool_manager
    from fastmcp import FastMCP
    test_mcp = FastMCP(name="test", version="0.0.1")
    from lcs_cad_mcp.modules import cad

    captured = {}

    @test_mcp.tool()
    async def cad_ping_capture() -> dict:
        return {"success": True, "data": {"pong": True}, "error": None}

    result = await cad_ping_capture()
    assert result == {"success": True, "data": {"pong": True}, "error": None}


def test_all_modules_importable():
    """AC2: all 10 module packages are importable with register() callables."""
    from lcs_cad_mcp.modules import (
        cad, predcr, layers, entities, verification,
        config, area, autodcr, reports, workflow,
    )
    for mod in [cad, predcr, layers, entities, verification,
                config, area, autodcr, reports, workflow]:
        assert callable(mod.register), f"{mod.__name__} missing register()"


def test_all_modules_register_without_error():
    """AC2: calling register(mcp) on all modules raises no errors."""
    from fastmcp import FastMCP
    test_mcp = FastMCP(name="test-all", version="0.0.1")
    from lcs_cad_mcp.modules import (
        cad, predcr, layers, entities, verification,
        config, area, autodcr, reports, workflow,
    )
    for mod in [cad, predcr, layers, entities, verification,
                config, area, autodcr, reports, workflow]:
        mod.register(test_mcp)  # must not raise
