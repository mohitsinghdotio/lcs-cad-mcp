"""Config module — register(mcp) wires all config tools into the FastMCP instance."""
from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all config tools. Called once by __main__.py at startup."""
    from lcs_cad_mcp.modules.config.tools import config_load, config_validate
    from lcs_cad_mcp.modules.config.schemas import ConfigLoadInput, ConfigValidateInput
    from lcs_cad_mcp.errors import validate_input

    @mcp.tool(name="config_load")
    async def _config_load(ctx, config_path: str) -> dict:
        inp, err = validate_input(ConfigLoadInput, {"config_path": config_path})
        if err:
            return err
        return await config_load(inp)

    @mcp.tool(name="config_validate")
    async def _config_validate(ctx, config_path: str) -> dict:
        inp, err = validate_input(ConfigValidateInput, {"config_path": config_path})
        if err:
            return err
        return await config_validate(inp)
