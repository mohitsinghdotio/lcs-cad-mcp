"""Unit tests for DCR rule engine Pydantic models."""
import pytest
from pydantic import ValidationError
from lcs_cad_mcp.rule_engine.models import DCRRule, DCRConfig, RuleResult, RuleType


def make_rule(**kwargs) -> dict:
    defaults = {
        "rule_id": "TEST-FSI",
        "name": "Test FSI",
        "rule_type": "FSI",
        "threshold": 1.0,
        "unit": "ratio",
        "zone_applicability": ["R1"],
    }
    defaults.update(kwargs)
    return defaults


class TestDCRRule:
    def test_valid_rule(self):
        rule = DCRRule(**make_rule())
        assert rule.rule_id == "TEST-FSI"
        assert rule.threshold == 1.0

    def test_threshold_negative_raises(self):
        with pytest.raises(ValidationError):
            DCRRule(**make_rule(threshold=-0.1))

    def test_empty_zone_applicability_raises(self):
        with pytest.raises(ValidationError):
            DCRRule(**make_rule(zone_applicability=[]))

    def test_frozen_model(self):
        rule = DCRRule(**make_rule())
        with pytest.raises(Exception):
            rule.threshold = 2.0  # type: ignore

    def test_all_rule_types(self):
        for rt in RuleType:
            rule = DCRRule(**make_rule(rule_id=f"TEST-{rt}", rule_type=rt.value))
            assert rule.rule_type == rt


class TestDCRConfig:
    def make_config(self, **kwargs) -> dict:
        defaults = {
            "version": "1.0.0",
            "authority": "Test Authority",
            "effective_date": "2024-01-01",
            "rules": [DCRRule(**make_rule())],
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_config(self):
        cfg = DCRConfig(**self.make_config())
        assert cfg.authority == "Test Authority"
        assert cfg.rule_count == 1

    def test_empty_rules_raises(self):
        with pytest.raises(ValidationError):
            DCRConfig(**self.make_config(rules=[]))

    def test_duplicate_rule_ids_raises(self):
        r1 = DCRRule(**make_rule(rule_id="DUP"))
        r2 = DCRRule(**make_rule(rule_id="DUP"))
        with pytest.raises(ValidationError):
            DCRConfig(**self.make_config(rules=[r1, r2]))

    def test_zone_set(self):
        r1 = DCRRule(**make_rule(zone_applicability=["R1", "R2"]))
        r2 = DCRRule(**make_rule(rule_id="GC", rule_type="GROUND_COVERAGE", zone_applicability=["C1"]))
        cfg = DCRConfig(**self.make_config(rules=[r1, r2]))
        assert cfg.zone_set == {"R1", "R2", "C1"}


class TestRuleResult:
    def test_pass_result(self):
        result = RuleResult(
            rule_id="FSI-R1",
            rule_name="FSI",
            passed=True,
            computed_value=0.8,
            permissible_value=1.0,
            deviation=-0.2,
        )
        assert result.status == "pass"
        assert result.deviation_percent == pytest.approx(20.0)

    def test_fail_result(self):
        result = RuleResult(
            rule_id="FSI-R1",
            rule_name="FSI",
            passed=False,
            computed_value=1.5,
            permissible_value=1.0,
            deviation=0.5,
        )
        assert result.status == "fail"

    def test_deviation_status(self):
        result = RuleResult(
            rule_id="FSI-R1",
            rule_name="FSI",
            passed=False,
            computed_value=1.05,
            permissible_value=1.0,
            deviation=0.05,
            tolerance=0.1,
        )
        assert result.status == "deviation"

    def test_deviation_percent_zero_permissible(self):
        result = RuleResult(
            rule_id="FSI-R1",
            rule_name="FSI",
            passed=True,
            computed_value=0.0,
            permissible_value=0.0,
            deviation=0.0,
        )
        assert result.deviation_percent == 0.0
