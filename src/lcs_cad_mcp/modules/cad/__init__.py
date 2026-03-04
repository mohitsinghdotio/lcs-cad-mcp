"""CAD module — register(mcp) wires all CAD tools into the FastMCP instance."""
from fastmcp import FastMCP

from lcs_cad_mcp.modules.cad.schemas import CadOpenDrawingInput, CadPingInput, CadSelectBackendInput
from lcs_cad_mcp.modules.cad.tools import cad_open_drawing, cad_select_backend
from lcs_cad_mcp.errors import success_response


def register(mcp: FastMCP) -> None:
    """Register all CAD tools. Called once by __main__.py at startup."""

    @mcp.tool()
    async def cad_ping(inp: CadPingInput) -> dict:
        """Health check tool — returns pong."""
        return success_response({"pong": True})

    @mcp.tool()
    async def cad_open_drawing_tool(inp: CadOpenDrawingInput) -> dict:
        """Open a DXF/DWG drawing file and start a session."""
        return await cad_open_drawing(inp)

    @mcp.tool()
    async def cad_select_backend_tool(inp: CadSelectBackendInput) -> dict:
        """Select the CAD backend (ezdxf or com) for this session."""
        return await cad_select_backend(inp)
