"""Config service — DCR config loading and validation."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigService:
    """Stateless service for loading and validating DCR config files."""

    def load_config(self, path: str | Path) -> dict:
        """Load and validate a DCR config file.

        Returns summary dict with version, authority, rule_count, zone_count, config_hash.
        Raises MCPError on file-not-found or validation failure.
        """
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        from lcs_cad_mcp.rule_engine.loader import load_config
        from pydantic import ValidationError

        resolved = Path(path)
        if not resolved.exists():
            raise MCPError(
                code=ErrorCode.FILE_NOT_FOUND,
                message=f"Config file not found: {path}",
                recoverable=True,
                suggested_action="Verify the file path or set DCR_CONFIG_PATH env var.",
            )

        # Compute hash before parse
        content_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()

        try:
            config = load_config(str(resolved))
        except MCPError:
            raise

        return {
            "version": config.version,
            "authority": config.authority,
            "rule_count": config.rule_count,
            "zone_count": len(config.zone_set),
            "config_hash": content_hash,
            "_config": config,  # internal, stripped before returning to MCP
        }

    def validate_config(self, path: str | Path) -> dict:
        """Validate a DCR config and return a validation report."""
        from lcs_cad_mcp.rule_engine.validator import validate_config
        return validate_config(str(path))
