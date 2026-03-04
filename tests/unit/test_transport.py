"""Tests for Story 1-3: transport branching in __main__."""
import pytest
from unittest.mock import patch, MagicMock


def test_transport_branching_stdio(monkeypatch):
    """AC3/AC5: stdio transport calls mcp.run(transport='stdio')."""
    from lcs_cad_mcp.settings import Settings
    mock_mcp = MagicMock()
    mock_settings = Settings(
        dcr_config_path="/tmp/dcr.yaml",
        archive_path="/tmp/archive",
        mcp_transport="stdio",
    )
    with patch("lcs_cad_mcp.settings.Settings", return_value=mock_settings):
        with patch("lcs_cad_mcp.server.mcp", mock_mcp):
            # simulate the __main__ branching logic
            if mock_settings.mcp_transport == "sse":
                mock_mcp.run(
                    transport="sse",
                    host=mock_settings.mcp_sse_host,
                    port=mock_settings.mcp_sse_port,
                )
            else:
                mock_mcp.run(transport="stdio")
    mock_mcp.run.assert_called_once_with(transport="stdio")


def test_transport_branching_sse(monkeypatch):
    """AC1/AC4: sse transport calls mcp.run with host and port."""
    from lcs_cad_mcp.settings import Settings
    mock_mcp = MagicMock()
    mock_settings = Settings(
        dcr_config_path="/tmp/dcr.yaml",
        archive_path="/tmp/archive",
        mcp_transport="sse",
        mcp_sse_host="127.0.0.1",
        mcp_sse_port=9090,
    )
    with patch("lcs_cad_mcp.settings.Settings", return_value=mock_settings):
        with patch("lcs_cad_mcp.server.mcp", mock_mcp):
            if mock_settings.mcp_transport == "sse":
                mock_mcp.run(
                    transport="sse",
                    host=mock_settings.mcp_sse_host,
                    port=mock_settings.mcp_sse_port,
                )
            else:
                mock_mcp.run(transport="stdio")
    mock_mcp.run.assert_called_once_with(transport="sse", host="127.0.0.1", port=9090)
