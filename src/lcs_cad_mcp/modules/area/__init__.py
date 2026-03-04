"""Area module — register(mcp) wires all area tools into the FastMCP instance."""
from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all area tools. Called once by __main__.py at startup."""
    from lcs_cad_mcp.modules.area.tools import (
        area_compute_plot, area_calculate, area_compute_builtup,
        area_compute_carpet, area_compute_fsi, area_compute_coverage,
    )
    from lcs_cad_mcp.modules.area.schemas import (
        AreaComputePlotInput, AreaCalculateInput, AreaComputeBuiltupInput,
        AreaComputeCarpetInput, AreaComputeFsiInput, AreaComputeCoverageInput,
    )
    from lcs_cad_mcp.errors import validate_input

    @mcp.tool(name="area_compute_plot")
    async def _area_compute_plot(ctx, plot_layer: str, unit: str = "sqm") -> dict:
        inp, err = validate_input(AreaComputePlotInput, {"plot_layer": plot_layer, "unit": unit})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await area_compute_plot(inp, session)

    @mcp.tool(name="area_calculate")
    async def _area_calculate(ctx, layer: str, unit: str = "sqm") -> dict:
        inp, err = validate_input(AreaCalculateInput, {"layer": layer, "unit": unit})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await area_calculate(inp, session)

    @mcp.tool(name="area_compute_builtup")
    async def _area_compute_builtup(ctx, floor_layers: list, unit: str = "sqm") -> dict:
        inp, err = validate_input(AreaComputeBuiltupInput, {"floor_layers": floor_layers, "unit": unit})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await area_compute_builtup(inp, session)

    @mcp.tool(name="area_compute_carpet")
    async def _area_compute_carpet(ctx, carpet_layer: str, unit: str = "sqm") -> dict:
        inp, err = validate_input(AreaComputeCarpetInput, {"carpet_layer": carpet_layer, "unit": unit})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await area_compute_carpet(inp, session)

    @mcp.tool(name="area_compute_fsi")
    async def _area_compute_fsi(ctx, plot_layer: str, floor_layers: list, unit: str = "sqm") -> dict:
        inp, err = validate_input(AreaComputeFsiInput, {"plot_layer": plot_layer, "floor_layers": floor_layers, "unit": unit})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await area_compute_fsi(inp, session)

    @mcp.tool(name="area_compute_coverage")
    async def _area_compute_coverage(ctx, plot_layer: str, footprint_layer: str) -> dict:
        inp, err = validate_input(AreaComputeCoverageInput, {"plot_layer": plot_layer, "footprint_layer": footprint_layer})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await area_compute_coverage(inp, session)
