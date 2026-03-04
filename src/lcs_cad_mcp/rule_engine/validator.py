"""DCR config validator — validates config files against schema and semantic rules."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lcs_cad_mcp.rule_engine.models import DCRConfig

logger = logging.getLogger(__name__)


def validate_config(config_path: str) -> dict:
    """Validate a DCR config file and return a validation report.

    Args:
        config_path: Path to the config file to validate.

    Returns:
        Dict with fields: valid (bool), errors (list[str]), warnings (list[str]),
        rule_count (int), authority (str), version (str).
    """
    from lcs_cad_mcp.rule_engine.loader import load_config
    from lcs_cad_mcp.errors import MCPError

    errors: list[str] = []
    warnings: list[str] = []

    try:
        config = load_config(config_path)
    except MCPError as exc:
        return {
            "valid": False,
            "errors": [exc.message],
            "warnings": [],
            "rule_count": 0,
            "authority": "",
            "version": "",
        }

    # Semantic checks
    if not config.authority.strip():
        errors.append("authority field is blank")
    if not config.version.strip():
        errors.append("version field is blank")

    # Check for rules without descriptions
    for rule in config.rules:
        if not rule.description.strip():
            warnings.append(f"Rule '{rule.rule_id}' has no description")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "rule_count": config.rule_count,
        "authority": config.authority,
        "version": config.version,
    }
