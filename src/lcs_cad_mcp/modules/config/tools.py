"""Thin MCP tool handlers for the config module."""
from __future__ import annotations

from lcs_cad_mcp.errors import MCPError, success_response
from lcs_cad_mcp.modules.config.schemas import ConfigLoadInput, ConfigValidateInput


async def config_load(inp: ConfigLoadInput) -> dict:
    from lcs_cad_mcp.modules.config.service import ConfigService
    try:
        svc = ConfigService()
        result = svc.load_config(inp.config_path)
        # Strip internal _config key from MCP response
        response_data = {k: v for k, v in result.items() if not k.startswith("_")}
        return success_response(response_data)
    except MCPError as exc:
        return exc.to_response()


async def config_validate(inp: ConfigValidateInput) -> dict:
    from lcs_cad_mcp.modules.config.service import ConfigService
    try:
        svc = ConfigService()
        result = svc.validate_config(inp.config_path)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()
