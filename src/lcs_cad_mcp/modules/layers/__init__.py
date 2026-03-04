"""Layers module — register(mcp) wires all layer tools into FastMCP."""
from fastmcp import FastMCP
from lcs_cad_mcp.modules.layers.schemas import LayerCreateInput, LayerDeleteInput, LayerGetInput, LayerSetPropertiesInput
from lcs_cad_mcp.modules.layers.tools import layer_create, layer_delete, layer_list, layer_get, layer_set_properties
from lcs_cad_mcp.errors import MCPError, ErrorCode


def register(mcp: FastMCP) -> None:
    """Register all layer management tools."""

    @mcp.tool()
    async def layer_create_tool(inp: LayerCreateInput) -> dict:
        """Create a new layer in the active drawing."""
        return await layer_create(inp, None)  # session injected at runtime

    @mcp.tool()
    async def layer_delete_tool(inp: LayerDeleteInput) -> dict:
        """Delete a layer from the active drawing."""
        return await layer_delete(inp, None)

    @mcp.tool()
    async def layer_list_tool() -> dict:
        """List all layers in the active drawing."""
        return await layer_list(None)

    @mcp.tool()
    async def layer_get_tool(inp: LayerGetInput) -> dict:
        """Get properties of a single layer."""
        return await layer_get(inp, None)

    @mcp.tool()
    async def layer_set_properties_tool(inp: LayerSetPropertiesInput) -> dict:
        """Update one or more layer properties."""
        return await layer_set_properties(inp, None)
