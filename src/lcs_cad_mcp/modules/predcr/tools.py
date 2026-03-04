"""Thin MCP tool handlers for the predcr module."""
from __future__ import annotations

from lcs_cad_mcp.errors import MCPError, success_response
from lcs_cad_mcp.modules.predcr.schemas import (
    PredcrRunSetupInput,
    PredcrGetLayerSpecInput,
    PredcrValidateDrawingInput,
)


async def predcr_run_setup(inp: PredcrRunSetupInput, session) -> dict:
    from lcs_cad_mcp.modules.predcr.service import PreDCRService
    try:
        svc = PreDCRService(session)
        result = svc.run_setup(inp.project_type)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def predcr_get_layer_spec(inp: PredcrGetLayerSpecInput, session) -> dict:
    from lcs_cad_mcp.modules.predcr.service import PreDCRService
    try:
        svc = PreDCRService(session)
        result = svc.get_layer_spec(inp.layer_name)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def predcr_list_layer_specs(building_type: str | None, session) -> dict:
    from lcs_cad_mcp.modules.predcr.service import PreDCRService
    try:
        svc = PreDCRService(session)
        specs = svc.list_layer_specs(building_type)
        return success_response({"specs": specs, "count": len(specs)})
    except MCPError as exc:
        return exc.to_response()


async def predcr_validate_drawing(inp: PredcrValidateDrawingInput, session) -> dict:
    from lcs_cad_mcp.modules.predcr.service import PreDCRService
    try:
        svc = PreDCRService(session)
        result = svc.validate_drawing(inp.authority_code)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()
