"""Thin MCP tool handlers for the verification module."""
from __future__ import annotations

from lcs_cad_mcp.errors import MCPError, success_response
from lcs_cad_mcp.modules.verification.schemas import (
    VerifyClosureInput,
    VerifyContainmentInput,
    VerifyNamingInput,
    VerifyMinEntityCountInput,
    VerifyAllInput,
)


async def verify_closure(inp: VerifyClosureInput, session) -> dict:
    from lcs_cad_mcp.modules.verification.service import VerificationService
    try:
        svc = VerificationService(session)
        result = svc.verify_closure(inp.layer, tolerance=inp.tolerance)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def verify_containment(inp: VerifyContainmentInput, session) -> dict:
    from lcs_cad_mcp.modules.verification.service import VerificationService
    try:
        svc = VerificationService(session)
        result = svc.verify_containment(inp.outer_layer, inp.inner_layer, tolerance=inp.tolerance)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def verify_naming(inp: VerifyNamingInput, session) -> dict:
    from lcs_cad_mcp.modules.verification.service import VerificationService
    try:
        svc = VerificationService(session)
        result = svc.verify_naming(inp.authority_code)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def verify_min_entity_count(inp: VerifyMinEntityCountInput, session) -> dict:
    from lcs_cad_mcp.modules.verification.service import VerificationService
    try:
        svc = VerificationService(session)
        result = svc.verify_min_entity_count(inp.layer, inp.min_count, inp.entity_type)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()


async def verify_all(inp: VerifyAllInput, session) -> dict:
    from lcs_cad_mcp.modules.verification.service import VerificationService
    try:
        svc = VerificationService(session)
        result = svc.verify_all(inp.authority_code, tolerance=inp.tolerance)
        return success_response(result)
    except MCPError as exc:
        return exc.to_response()
