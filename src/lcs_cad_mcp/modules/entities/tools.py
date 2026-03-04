"""Thin MCP tool handlers for the entities module."""
from __future__ import annotations

from lcs_cad_mcp.errors import MCPError, success_response
from lcs_cad_mcp.modules.entities.schemas import (
    EntityQueryInput, EntityDrawPolylineInput, EntityDrawLineInput,
    EntityDrawArcInput, EntityDrawCircleInput, EntityAddTextInput,
    EntityInsertBlockInput, EntityMoveInput, EntityCopyInput,
    EntityDeleteInput, EntityChangeLayerInput, EntityClosePolylineInput,
)


async def entity_draw_polyline(inp: EntityDrawPolylineInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        result = svc.draw_polyline(inp.points, layer=inp.layer, closed=inp.closed)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def entity_draw_line(inp: EntityDrawLineInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        result = svc.draw_line(inp.start, inp.end, layer=inp.layer)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def entity_draw_arc(inp: EntityDrawArcInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        result = svc.draw_arc(inp.center, inp.radius, inp.start_angle, inp.end_angle, layer=inp.layer)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def entity_draw_circle(inp: EntityDrawCircleInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        result = svc.draw_circle(inp.center, inp.radius, layer=inp.layer)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def entity_add_text(inp: EntityAddTextInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        result = svc.add_text(inp.text, inp.position, inp.height, layer=inp.layer)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def entity_insert_block(inp: EntityInsertBlockInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        result = svc.insert_block(inp.block_name, inp.position, inp.scale, layer=inp.layer)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def entity_move(inp: EntityMoveInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        result = svc.move_entity(inp.entity_handle, inp.displacement)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def entity_copy(inp: EntityCopyInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        result = svc.copy_entity(inp.entity_handle, inp.displacement)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def entity_delete(inp: EntityDeleteInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        svc.delete_entity(inp.entity_handle)
        return success_response({"deleted": inp.entity_handle})
    except MCPError as exc:
        return exc.to_response()


async def entity_change_layer(inp: EntityChangeLayerInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        result = svc.change_layer(inp.entity_handle, inp.target_layer)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def entity_close_polyline(inp: EntityClosePolylineInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        result = svc.close_polyline(inp.entity_handle)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def entity_query(inp: EntityQueryInput, session) -> dict:
    from lcs_cad_mcp.modules.entities.service import EntityService
    try:
        svc = EntityService(session)
        entities = svc.query_entities(layer=inp.layer, entity_type=inp.entity_type)
        return success_response({"entities": entities, "count": len(entities)})
    except MCPError as exc:
        return exc.to_response()
