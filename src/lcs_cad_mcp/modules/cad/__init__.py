"""CAD module — register(mcp) wires all CAD tools into the FastMCP instance."""
from fastmcp import FastMCP

from lcs_cad_mcp.modules.cad.schemas import (
    CadOpenDrawingInput, CadPingInput, CadSelectBackendInput,
    CadNewDrawingInput, CadSaveDrawingInput,
)
from lcs_cad_mcp.modules.cad.tools import (
    cad_open_drawing, cad_select_backend, cad_new_drawing, cad_save_drawing,
)
from lcs_cad_mcp.errors import success_response, validate_input


def register(mcp: FastMCP) -> None:
    """Register all CAD tools. Called once by __main__.py at startup."""

    @mcp.tool()
    async def cad_ping(inp: CadPingInput) -> dict:
        """Health check tool — returns pong."""
        return success_response({"pong": True})

    @mcp.tool(name="cad_open_drawing")
    async def _cad_open_drawing(ctx, path: str, read_only: bool = False) -> dict:
        """Open a DXF/DWG drawing file and start a session."""
        inp, err = validate_input(CadOpenDrawingInput, {"path": path, "read_only": read_only})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await cad_open_drawing(inp, session)

    @mcp.tool(name="cad_new_drawing")
    async def _cad_new_drawing(ctx, name: str = "Untitled", units: str = "metric") -> dict:
        """Create a new empty DXF drawing."""
        inp, err = validate_input(CadNewDrawingInput, {"name": name, "units": units})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await cad_new_drawing(inp, session)

    @mcp.tool(name="cad_save_drawing")
    async def _cad_save_drawing(ctx, path: str, dxf_version: str = "R2018") -> dict:
        """Save the active drawing to disk."""
        inp, err = validate_input(CadSaveDrawingInput, {"path": path, "dxf_version": dxf_version})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await cad_save_drawing(inp, session)

    @mcp.tool(name="cad_select_backend")
    async def _cad_select_backend(ctx, backend: str) -> dict:
        """Select the CAD backend (ezdxf or com) for this session."""
        inp, err = validate_input(CadSelectBackendInput, {"backend": backend})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await cad_select_backend(inp, session)
