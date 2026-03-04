"""Verification module — register(mcp) wires all verification tools into the FastMCP instance."""
from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register all verification tools. Called once by __main__.py at startup."""
    from lcs_cad_mcp.modules.verification.tools import (
        verify_closure, verify_containment, verify_naming,
        verify_min_entity_count, verify_all,
    )
    from lcs_cad_mcp.modules.verification.schemas import (
        VerifyClosureInput, VerifyContainmentInput, VerifyNamingInput,
        VerifyMinEntityCountInput, VerifyAllInput,
    )
    from lcs_cad_mcp.errors import validate_input

    @mcp.tool(name="verify_closure")
    async def _verify_closure(ctx, layer: str, tolerance: float = 0.001) -> dict:
        inp, err = validate_input(VerifyClosureInput, {"layer": layer, "tolerance": tolerance})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await verify_closure(inp, session)

    @mcp.tool(name="verify_containment")
    async def _verify_containment(ctx, outer_layer: str, inner_layer: str, tolerance: float = 0.001) -> dict:
        inp, err = validate_input(VerifyContainmentInput, {"outer_layer": outer_layer, "inner_layer": inner_layer, "tolerance": tolerance})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await verify_containment(inp, session)

    @mcp.tool(name="verify_naming")
    async def _verify_naming(ctx, authority_code: str) -> dict:
        inp, err = validate_input(VerifyNamingInput, {"authority_code": authority_code})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await verify_naming(inp, session)

    @mcp.tool(name="verify_min_entity_count")
    async def _verify_min_entity_count(ctx, layer: str, min_count: int = 1, entity_type: str | None = None) -> dict:
        inp, err = validate_input(VerifyMinEntityCountInput, {"layer": layer, "min_count": min_count, "entity_type": entity_type})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await verify_min_entity_count(inp, session)

    @mcp.tool(name="verify_all")
    async def _verify_all(ctx, authority_code: str, tolerance: float = 0.001) -> dict:
        inp, err = validate_input(VerifyAllInput, {"authority_code": authority_code, "tolerance": tolerance})
        if err:
            return err
        session = ctx.get_state("session") if hasattr(ctx, "get_state") else None
        return await verify_all(inp, session)
