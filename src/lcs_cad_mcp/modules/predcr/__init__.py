"""PreDCR module — register(mcp) wires all PreDCR tools into the FastMCP instance."""
from fastmcp import FastMCP
from lcs_cad_mcp.modules.predcr.layer_registry import (
    LayerSpec, PREDCR_LAYERS,
    get_layers_for_building_type, get_layer_by_name, get_all_building_types,
)

__all__ = [
    "register", "LayerSpec", "PREDCR_LAYERS",
    "get_layers_for_building_type", "get_layer_by_name", "get_all_building_types",
]


def register(mcp: FastMCP) -> None:
    """Register all PreDCR tools. Called once by __main__.py at startup."""
    from lcs_cad_mcp.modules.predcr.tools import (
        predcr_run_setup, predcr_get_layer_spec,
        predcr_list_layer_specs, predcr_validate_drawing,
    )
    from lcs_cad_mcp.modules.predcr.schemas import (
        PredcrRunSetupInput, PredcrGetLayerSpecInput, PredcrValidateDrawingInput,
    )
    from lcs_cad_mcp.errors import validate_input

    @mcp.tool(name="predcr_run_setup")
    async def _predcr_run_setup(ctx, project_type: str = "residential", authority_code: str = "") -> dict:
        inp, err = validate_input(PredcrRunSetupInput, {"authority_code": authority_code, "project_type": project_type})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await predcr_run_setup(inp, session)

    @mcp.tool(name="predcr_get_layer_spec")
    async def _predcr_get_layer_spec(ctx, authority_code: str, layer_name: str) -> dict:
        inp, err = validate_input(PredcrGetLayerSpecInput, {"authority_code": authority_code, "layer_name": layer_name})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await predcr_get_layer_spec(inp, session)

    @mcp.tool(name="predcr_list_layer_specs")
    async def _predcr_list_layer_specs(ctx, building_type: str | None = None) -> dict:
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await predcr_list_layer_specs(building_type, session)

    @mcp.tool(name="predcr_validate_drawing")
    async def _predcr_validate_drawing(ctx, authority_code: str) -> dict:
        inp, err = validate_input(PredcrValidateDrawingInput, {"authority_code": authority_code})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await predcr_validate_drawing(inp, session)
