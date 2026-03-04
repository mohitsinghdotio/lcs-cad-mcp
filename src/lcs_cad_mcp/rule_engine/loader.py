"""DCR config loader — reads YAML/JSON config files and validates against schema."""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> "DCRConfig":
    """Load and validate a DCR config file (YAML or JSON).

    Args:
        config_path: Path to a .yaml, .yml, or .json file.

    Returns:
        Validated DCRConfig instance.

    Raises:
        MCPError: CONFIG_INVALID if the file is invalid, CONFIG_NOT_LOADED if missing.
    """
    from lcs_cad_mcp.errors import MCPError, ErrorCode
    from lcs_cad_mcp.rule_engine.models import DCRConfig
    from pydantic import ValidationError

    path = Path(config_path)
    if not path.exists():
        raise MCPError(
            code=ErrorCode.FILE_NOT_FOUND,
            message=f"Config file not found: {config_path}",
            recoverable=True,
            suggested_action="Verify the file path or set DCR_CONFIG_PATH env var.",
        )

    try:
        if path.suffix.lower() in (".yaml", ".yml"):
            import yaml
            with open(path) as f:
                raw = yaml.safe_load(f)
        elif path.suffix.lower() == ".json":
            with open(path) as f:
                raw = json.load(f)
        else:
            raise MCPError(
                code=ErrorCode.CONFIG_INVALID,
                message=f"Unsupported config format: {path.suffix}. Use .yaml or .json.",
                recoverable=True,
            )
    except (OSError, Exception) as exc:
        if isinstance(exc, MCPError):
            raise
        raise MCPError(
            code=ErrorCode.CONFIG_INVALID,
            message=f"Failed to parse config file: {exc}",
            recoverable=True,
        )

    try:
        config = DCRConfig.model_validate(raw)
    except ValidationError as exc:
        raise MCPError(
            code=ErrorCode.CONFIG_INVALID,
            message=f"Config validation failed: {exc}",
            recoverable=True,
            suggested_action="Check the config file structure against docs/dcr-config-schema.md.",
        )

    logger.info("Loaded DCR config: authority=%s version=%s rules=%d",
                config.authority, config.version, config.rule_count)
    return config
