"""Entities module — register(mcp) wires all entity tools into the FastMCP instance."""
from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all entity tools. Called once by __main__.py at startup."""
    from lcs_cad_mcp.modules.entities.tools import (
        entity_draw_polyline, entity_draw_line, entity_draw_arc, entity_draw_circle,
        entity_add_text, entity_insert_block, entity_move, entity_copy,
        entity_delete, entity_change_layer, entity_close_polyline, entity_query,
    )
    from lcs_cad_mcp.modules.entities.schemas import (
        EntityDrawPolylineInput, EntityDrawLineInput, EntityDrawArcInput, EntityDrawCircleInput,
        EntityAddTextInput, EntityInsertBlockInput, EntityMoveInput, EntityCopyInput,
        EntityDeleteInput, EntityChangeLayerInput, EntityClosePolylineInput, EntityQueryInput,
    )
    from lcs_cad_mcp.errors import validate_input

    @mcp.tool(name="entity_draw_polyline")
    async def _entity_draw_polyline(ctx, points: list, layer: str, closed: bool = False) -> dict:
        inp, err = validate_input(EntityDrawPolylineInput, {"points": points, "layer": layer, "closed": closed})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_draw_polyline(inp, session)

    @mcp.tool(name="entity_draw_line")
    async def _entity_draw_line(ctx, start: list, end: list, layer: str) -> dict:
        inp, err = validate_input(EntityDrawLineInput, {"start": start, "end": end, "layer": layer})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_draw_line(inp, session)

    @mcp.tool(name="entity_draw_arc")
    async def _entity_draw_arc(ctx, center: list, radius: float, start_angle: float, end_angle: float, layer: str) -> dict:
        inp, err = validate_input(EntityDrawArcInput, {"center": center, "radius": radius, "start_angle": start_angle, "end_angle": end_angle, "layer": layer})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_draw_arc(inp, session)

    @mcp.tool(name="entity_draw_circle")
    async def _entity_draw_circle(ctx, center: list, radius: float, layer: str) -> dict:
        inp, err = validate_input(EntityDrawCircleInput, {"center": center, "radius": radius, "layer": layer})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_draw_circle(inp, session)

    @mcp.tool(name="entity_add_text")
    async def _entity_add_text(ctx, text: str, position: list, height: float, layer: str) -> dict:
        inp, err = validate_input(EntityAddTextInput, {"text": text, "position": position, "height": height, "layer": layer})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_add_text(inp, session)

    @mcp.tool(name="entity_insert_block")
    async def _entity_insert_block(ctx, block_name: str, position: list, scale: float, layer: str) -> dict:
        inp, err = validate_input(EntityInsertBlockInput, {"block_name": block_name, "position": position, "scale": scale, "layer": layer})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_insert_block(inp, session)

    @mcp.tool(name="entity_move")
    async def _entity_move(ctx, entity_handle: str, displacement: list) -> dict:
        inp, err = validate_input(EntityMoveInput, {"entity_handle": entity_handle, "displacement": displacement})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_move(inp, session)

    @mcp.tool(name="entity_copy")
    async def _entity_copy(ctx, entity_handle: str, displacement: list) -> dict:
        inp, err = validate_input(EntityCopyInput, {"entity_handle": entity_handle, "displacement": displacement})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_copy(inp, session)

    @mcp.tool(name="entity_delete")
    async def _entity_delete(ctx, entity_handle: str) -> dict:
        inp, err = validate_input(EntityDeleteInput, {"entity_handle": entity_handle})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_delete(inp, session)

    @mcp.tool(name="entity_change_layer")
    async def _entity_change_layer(ctx, entity_handle: str, target_layer: str) -> dict:
        inp, err = validate_input(EntityChangeLayerInput, {"entity_handle": entity_handle, "target_layer": target_layer})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_change_layer(inp, session)

    @mcp.tool(name="entity_close_polyline")
    async def _entity_close_polyline(ctx, entity_handle: str) -> dict:
        inp, err = validate_input(EntityClosePolylineInput, {"entity_handle": entity_handle})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_close_polyline(inp, session)

    @mcp.tool(name="entity_query")
    async def _entity_query(ctx, layer: str | None = None, entity_type: str | None = None) -> dict:
        inp, err = validate_input(EntityQueryInput, {"layer": layer, "entity_type": entity_type})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await entity_query(inp, session)
