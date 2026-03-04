"""Unit tests for config module."""
import pytest
import tempfile
from pathlib import Path
from lcs_cad_mcp.modules.config.service import ConfigService
from lcs_cad_mcp.errors import MCPError


VALID_YAML = """
version: "1.0.0"
authority: "MCGM"
effective_date: "2024-01-01"
rules:
  - rule_id: "FSI_001"
    name: "Maximum FSI"
    rule_type: "FSI"
    threshold: 1.5
    unit: "ratio"
    zone_applicability: ["R1", "R2"]
"""


def test_config_service_load_valid_yaml():
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(VALID_YAML)
        tmp_path = f.name

    svc = ConfigService()
    result = svc.load_config(tmp_path)
    assert result["version"] == "1.0.0"
    assert result["authority"] == "MCGM"
    assert result["rule_count"] == 1
    assert "config_hash" in result
    assert len(result["config_hash"]) == 64  # SHA-256 hex


def test_config_service_load_file_not_found():
    svc = ConfigService()
    with pytest.raises(MCPError) as exc_info:
        svc.load_config("/nonexistent/path/config.yaml")
    assert exc_info.value.code == "FILE_NOT_FOUND"


def test_config_service_validate_yaml():
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(VALID_YAML)
        tmp_path = f.name

    svc = ConfigService()
    result = svc.validate_config(tmp_path)
    assert result["valid"] is True
    assert result["rule_count"] == 1
    assert result["authority"] == "MCGM"


def test_config_service_load_json():
    import json

    data = {
        "version": "1.0.0",
        "authority": "HMDA",
        "effective_date": "2024-01-01",
        "rules": [
            {
                "rule_id": "GC_001",
                "name": "Ground Coverage",
                "rule_type": "GROUND_COVERAGE",
                "threshold": 40.0,
                "unit": "%",
                "zone_applicability": ["R1"],
            }
        ]
    }

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(data, f)
        tmp_path = f.name

    svc = ConfigService()
    result = svc.load_config(tmp_path)
    assert result["authority"] == "HMDA"
    assert result["rule_count"] == 1
