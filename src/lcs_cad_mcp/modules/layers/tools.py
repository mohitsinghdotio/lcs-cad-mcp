"""Thin MCP tool handlers for the layers module."""
from __future__ import annotations

from lcs_cad_mcp.errors import MCPError, ErrorCode, success_response
from lcs_cad_mcp.modules.layers.schemas import (
    LayerCreateInput,
    LayerDeleteInput,
    LayerGetInput,
    LayerSetPropertiesInput,
)


async def layer_create(inp: LayerCreateInput, session) -> dict:
    """Create a new layer in the active drawing."""
    from lcs_cad_mcp.modules.layers.service import LayerService

    try:
        service = LayerService(session)
        record = service.create_layer(inp.name, color=inp.color, linetype=inp.linetype)
        return success_response(record)
    except MCPError as exc:
        return exc.to_response()


async def layer_delete(inp: LayerDeleteInput, session) -> dict:
    """Delete a layer from the drawing."""
    from lcs_cad_mcp.modules.layers.service import LayerService

    try:
        service = LayerService(session)
        service.delete_layer(inp.name, force=inp.force)
        return success_response({"deleted": inp.name})
    except MCPError as exc:
        return exc.to_response()


async def layer_list(session) -> dict:
    """List all layers in the active drawing."""
    from lcs_cad_mcp.modules.layers.service import LayerService

    try:
        service = LayerService(session)
        layers = service.list_layers()
        return success_response({"layers": layers, "count": len(layers)})
    except MCPError as exc:
        return exc.to_response()


async def layer_get(inp: LayerGetInput, session) -> dict:
    """Get properties of a single layer."""
    from lcs_cad_mcp.modules.layers.service import LayerService

    try:
        service = LayerService(session)
        layer = service.get_layer(inp.name)
        return success_response(layer)
    except MCPError as exc:
        return exc.to_response()


async def layer_set_properties(inp: LayerSetPropertiesInput, session) -> dict:
    """Update layer properties."""
    from lcs_cad_mcp.modules.layers.service import LayerService

    try:
        service = LayerService(session)
        updated = service.set_layer_properties(
            inp.name,
            color=inp.color,
            linetype=inp.linetype,
            is_on=inp.visible,
            is_frozen=inp.frozen,
            is_locked=inp.locked,
        )
        return success_response(updated)
    except MCPError as exc:
        return exc.to_response()
