"""Thin MCP tool handlers for the area module."""
from __future__ import annotations

from lcs_cad_mcp.errors import MCPError, success_response
from lcs_cad_mcp.modules.area.schemas import (
    AreaComputePlotInput, AreaComputeBuiltupInput,
    AreaComputeCarpetInput, AreaComputeFsiInput, AreaComputeCoverageInput,
    AreaCalculateInput,
)
from lcs_cad_mcp.modules.area.service import AreaComputationError, format_area


async def area_compute_plot(inp: AreaComputePlotInput, session) -> dict:
    from lcs_cad_mcp.modules.area.service import AreaService
    try:
        svc = AreaService()
        area = svc.compute_plot_area(session)
        return success_response({
            "area_sqm": area,
            "area_sqm_str": format_area(area),
            "layer": inp.plot_layer,
        })
    except AreaComputationError as exc:
        return {"success": False, "data": None, "error": {"code": exc.code, "message": exc.message}}
    except MCPError as exc:
        return exc.to_response()


async def area_calculate(inp: AreaCalculateInput, session) -> dict:
    from lcs_cad_mcp.modules.area.service import AreaService
    try:
        svc = AreaService()
        area = svc.compute_layer_area(session, inp.layer, inp.unit)
        return success_response({
            "area": area,
            "area_str": format_area(area),
            "layer": inp.layer,
            "unit": inp.unit,
        })
    except AreaComputationError as exc:
        return {"success": False, "data": None, "error": {"code": exc.code, "message": exc.message}}
    except MCPError as exc:
        return exc.to_response()


async def area_compute_builtup(inp: AreaComputeBuiltupInput, session) -> dict:
    from lcs_cad_mcp.modules.area.service import AreaService
    try:
        svc = AreaService()
        result = svc.compute_builtup_area(session, list(inp.floor_layers), inp.unit)
        return success_response(result)
    except AreaComputationError as exc:
        return {"success": False, "data": None, "error": {"code": exc.code, "message": exc.message}}
    except MCPError as exc:
        return exc.to_response()


async def area_compute_carpet(inp: AreaComputeCarpetInput, session) -> dict:
    from lcs_cad_mcp.modules.area.service import AreaService
    try:
        svc = AreaService()
        area = svc.compute_carpet_area(session, inp.carpet_layer, inp.unit)
        return success_response({"area": area, "area_str": format_area(area), "unit": inp.unit})
    except AreaComputationError as exc:
        return {"success": False, "data": None, "error": {"code": exc.code, "message": exc.message}}
    except MCPError as exc:
        return exc.to_response()


async def area_compute_fsi(inp: AreaComputeFsiInput, session) -> dict:
    from lcs_cad_mcp.modules.area.service import AreaService
    try:
        svc = AreaService()
        result = svc.compute_fsi(session, inp.plot_layer, list(inp.floor_layers), inp.unit)
        return success_response(result)
    except AreaComputationError as exc:
        return {"success": False, "data": None, "error": {"code": exc.code, "message": exc.message}}
    except MCPError as exc:
        return exc.to_response()


async def area_compute_coverage(inp: AreaComputeCoverageInput, session) -> dict:
    from lcs_cad_mcp.modules.area.service import AreaService
    try:
        svc = AreaService()
        result = svc.compute_coverage(session, inp.plot_layer, inp.footprint_layer)
        return success_response(result)
    except AreaComputationError as exc:
        return {"success": False, "data": None, "error": {"code": exc.code, "message": exc.message}}
    except MCPError as exc:
        return exc.to_response()
