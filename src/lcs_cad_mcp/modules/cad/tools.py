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


async def cad_open_drawing(inp: CadOpenDrawingInput) -> dict:
    """Open a DXF/DWG drawing file. (Session context injected by caller.)"""
    return success_response({"path": inp.path, "read_only": inp.read_only, "status": "stub — backend wiring in progress"})


async def cad_select_backend(inp: CadSelectBackendInput) -> dict:
    """Select the CAD backend (ezdxf or com)."""
    valid_backends = {"ezdxf", "com"}
    if inp.backend not in valid_backends:
        return MCPError(
            code=ErrorCode.BACKEND_UNAVAILABLE,
            message=f"Unknown backend '{inp.backend}'. Valid: {sorted(valid_backends)}",
            recoverable=True,
            suggested_action="Use 'ezdxf' (cross-platform) or 'com' (Windows AutoCAD only).",
        ).to_response()
    return success_response({"backend": inp.backend, "status": "stub — session wiring in progress"})


async def cad_new_drawing(inp: CadNewDrawingInput) -> dict:
    """Create a new empty drawing."""
    return success_response({"name": inp.name, "units": inp.units, "status": "stub"})


async def cad_save_drawing(inp: CadSaveDrawingInput) -> dict:
    """Save the active drawing to disk."""
    return success_response({"path": inp.path, "dxf_version": inp.dxf_version, "status": "stub"})
