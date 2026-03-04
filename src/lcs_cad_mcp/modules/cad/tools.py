"""Thin MCP tool handlers for the cad module. Business logic lives in service.py."""
from lcs_cad_mcp.errors import MCPError, ErrorCode, success_response
from lcs_cad_mcp.modules.cad.schemas import CadOpenDrawingInput, CadSelectBackendInput


async def cad_open_drawing(inp: CadOpenDrawingInput) -> dict:
    """Open a DXF/DWG drawing file and start a session. (Stub — full impl in Epic 2.)"""
    # Steps 2-6 implemented in Epic 2 stories
    return success_response({"path": inp.path, "read_only": inp.read_only, "status": "stub — not yet implemented"})


async def cad_select_backend(inp: CadSelectBackendInput) -> dict:
    """Select the CAD backend to use for this session. (Stub — full impl in Story 2-6.)"""
    valid_backends = {"ezdxf", "com"}
    if inp.backend not in valid_backends:
        return MCPError(
            code=ErrorCode.BACKEND_UNAVAILABLE,
            message=f"Unknown backend '{inp.backend}'. Valid options: {sorted(valid_backends)}",
            recoverable=True,
            suggested_action="Use 'ezdxf' (cross-platform) or 'com' (Windows AutoCAD only).",
        ).to_response()
    return success_response({"backend": inp.backend, "status": "stub — not yet implemented"})
