"""Tests for Story 1-3: Settings transport fields."""
import pytest
from unittest.mock import patch
import os


def test_settings_defaults_to_stdio():
    """AC3/AC5: MCP_TRANSPORT defaults to 'stdio' when env var not set."""
    with patch.dict(os.environ, {
        "DCR_CONFIG_PATH": "/tmp/dcr.yaml",
        "ARCHIVE_PATH": "/tmp/archive",
    }, clear=False):
        from importlib import reload
        import lcs_cad_mcp.settings as settings_mod
        # Avoid env file interference
        from lcs_cad_mcp.settings import Settings
        s = Settings(dcr_config_path="/tmp/dcr.yaml", archive_path="/tmp/archive")
        assert s.mcp_transport == "stdio"


def test_settings_accepts_sse_transport():
    """AC3: Settings accepts mcp_transport='sse'."""
    from lcs_cad_mcp.settings import Settings
    s = Settings(
        dcr_config_path="/tmp/dcr.yaml",
        archive_path="/tmp/archive",
        mcp_transport="sse",
        mcp_sse_port=9000,
    )
    assert s.mcp_transport == "sse"
    assert s.mcp_sse_port == 9000


def test_settings_default_sse_host():
    """AC5 security: SSE host defaults to 127.0.0.1 not 0.0.0.0."""
    from lcs_cad_mcp.settings import Settings
    s = Settings(dcr_config_path="/tmp/dcr.yaml", archive_path="/tmp/archive")
    assert s.mcp_sse_host == "127.0.0.1"


def test_settings_parametrized_transports():
    """AC3: both 'stdio' and 'sse' are valid values."""
    from lcs_cad_mcp.settings import Settings
    for transport in ["stdio", "sse"]:
        s = Settings(
            dcr_config_path="/tmp/dcr.yaml",
            archive_path="/tmp/archive",
            mcp_transport=transport,
        )
        assert s.mcp_transport == transport


def test_settings_invalid_transport_raises():
    """AC3: invalid transport value raises ValidationError."""
    from lcs_cad_mcp.settings import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(
            dcr_config_path="/tmp/dcr.yaml",
            archive_path="/tmp/archive",
            mcp_transport="websocket",  # invalid
        )
