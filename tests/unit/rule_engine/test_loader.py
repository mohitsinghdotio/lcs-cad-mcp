"""Unit tests for rule_engine loader."""
import json
import pytest
import tempfile
from pathlib import Path
from lcs_cad_mcp.rule_engine.loader import load_config
from lcs_cad_mcp.errors import MCPError


VALID_YAML_CONTENT = """
version: "1.0.0"
authority: "TEST"
effective_date: "2024-01-01"
rules:
  - rule_id: "FSI_001"
    name: "Max FSI"
    rule_type: "FSI"
    threshold: 1.5
    unit: "ratio"
    zone_applicability: ["R1"]
"""


def test_load_config_from_yaml():
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(VALID_YAML_CONTENT)
        tmp_path = f.name
    config = load_config(tmp_path)
    assert config.version == "1.0.0"
    assert config.authority == "TEST"
    assert config.rule_count == 1


def test_load_config_from_json():
    data = {
        "version": "2.0.0", "authority": "JSON_AUTH", "effective_date": "2024-01-01",
        "rules": [{"rule_id": "GC_001", "name": "Coverage", "rule_type": "GROUND_COVERAGE",
                   "threshold": 40.0, "unit": "%", "zone_applicability": ["R1"]}]
    }
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(data, f)
        tmp_path = f.name
    config = load_config(tmp_path)
    assert config.authority == "JSON_AUTH"


def test_load_config_file_not_found():
    with pytest.raises(MCPError) as exc_info:
        load_config("/nonexistent/config.yaml")
    assert exc_info.value.code == "FILE_NOT_FOUND"


def test_load_config_unsupported_extension():
    with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as f:
        f.write("test = 1")
        tmp_path = f.name
    with pytest.raises(MCPError) as exc_info:
        load_config(tmp_path)
    assert exc_info.value.code == "CONFIG_INVALID"


def test_load_config_invalid_yaml():
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write("version: '1.0'\nrules: []\n")  # Empty rules
        tmp_path = f.name
    with pytest.raises(MCPError) as exc_info:
        load_config(tmp_path)
    assert exc_info.value.code == "CONFIG_INVALID"
