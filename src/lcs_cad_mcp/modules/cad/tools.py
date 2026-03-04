"""Thin MCP tool handlers for the cad module. Business logic lives in service.py."""
from __future__ import annotations

from lcs_cad_mcp.errors import MCPError, ErrorCode, success_response
from lcs_cad_mcp.modules.cad.schemas import (
    CadOpenDrawingInput,
    CadPingInput,
    CadSelectBackendInput,
    CadSaveDrawingInput,
    CadNewDrawingInput,
)


async def cad_open_drawing(inp: CadOpenDrawingInput, session) -> dict:
    """Open a DXF/DWG drawing file."""
    from lcs_cad_mcp.modules.cad.service import CadService
    try:
        svc = CadService(session)
        result = svc.open_drawing(inp.path, inp.read_only)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def cad_select_backend(inp: CadSelectBackendInput, session) -> dict:
    """Select the CAD backend (ezdxf or com)."""
    from lcs_cad_mcp.modules.cad.service import CadService
    valid_backends = {"ezdxf", "com"}
    if inp.backend not in valid_backends:
        return MCPError(
            code=ErrorCode.BACKEND_UNAVAILABLE,
            message=f"Unknown backend '{inp.backend}'. Valid: {sorted(valid_backends)}",
            recoverable=True,
            suggested_action="Use 'ezdxf' (cross-platform) or 'com' (Windows AutoCAD only).",
        ).to_response()
    try:
        svc = CadService(session)
        result = svc.select_backend(inp.backend)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def cad_new_drawing(inp: CadNewDrawingInput, session) -> dict:
    """Create a new empty drawing."""
    from lcs_cad_mcp.modules.cad.service import CadService
    try:
        svc = CadService(session)
        result = svc.new_drawing(inp.name, inp.units)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def cad_save_drawing(inp: CadSaveDrawingInput, session) -> dict:
    """Save the active drawing to disk."""
    from lcs_cad_mcp.modules.cad.service import CadService
    try:
        svc = CadService(session)
        result = svc.save_drawing(inp.path, inp.dxf_version)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()
