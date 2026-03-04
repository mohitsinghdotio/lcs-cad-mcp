"""Unit tests for the RuleEvaluator."""
import pytest
from lcs_cad_mcp.rule_engine.models import DCRConfig, DCRRule, RuleType
from lcs_cad_mcp.rule_engine.evaluator import RuleEvaluator


def _make_config(rules=None):
    if rules is None:
        rules = [
            DCRRule(
                rule_id="FSI_001",
                name="Max FSI",
                rule_type=RuleType.FSI,
                threshold=1.5,
                unit="ratio",
                zone_applicability=["R1"],
            )
        ]
    return DCRConfig(
        version="1.0.0",
        authority="TEST",
        effective_date="2024-01-01",
        rules=rules,
    )


def test_evaluator_returns_results_for_each_rule():
    config = _make_config()
    evaluator = RuleEvaluator(config)
    report = evaluator.evaluate({"FSI": 1.2})
    assert report.total_rules == 1
    assert len(report.results) == 1


def test_evaluator_pass_under_threshold():
    config = _make_config()
    evaluator = RuleEvaluator(config)
    report = evaluator.evaluate({"FSI": 1.0})  # 1.0 <= 1.5
    assert report.results[0].passed is True
    assert report.overall_pass is True


def test_evaluator_fail_over_threshold():
    config = _make_config()
    evaluator = RuleEvaluator(config)
    report = evaluator.evaluate({"FSI": 2.0})  # 2.0 > 1.5
    assert report.results[0].passed is False
    assert report.overall_pass is False


def test_evaluator_setback_pass_above_minimum():
    rule = DCRRule(
        rule_id="SB_001",
        name="Front Setback",
        rule_type=RuleType.SETBACK_FRONT,
        threshold=3.0,
        unit="m",
        zone_applicability=["R1"],
    )
    config = _make_config(rules=[rule])
    evaluator = RuleEvaluator(config)
    report = evaluator.evaluate({"SETBACK_FRONT": 4.0})  # 4.0 >= 3.0
    assert report.results[0].passed is True


def test_evaluator_setback_fail_below_minimum():
    rule = DCRRule(
        rule_id="SB_001",
        name="Front Setback",
        rule_type=RuleType.SETBACK_FRONT,
        threshold=3.0,
        unit="m",
        zone_applicability=["R1"],
    )
    config = _make_config(rules=[rule])
    evaluator = RuleEvaluator(config)
    report = evaluator.evaluate({"SETBACK_FRONT": 2.0})  # 2.0 < 3.0
    assert report.results[0].passed is False


def test_evaluator_multiple_rules_preserves_order():
    rules = [
        DCRRule(rule_id=f"R_{i}", name=f"Rule {i}", rule_type=RuleType.FSI,
                threshold=1.5, unit="ratio", zone_applicability=["R1"])
        for i in range(5)
    ]
    config = _make_config(rules=rules)
    evaluator = RuleEvaluator(config)
    report = evaluator.evaluate({"FSI": 1.0})
    result_ids = [r.rule_id for r in report.results]
    assert result_ids == [f"R_{i}" for i in range(5)]


def test_evaluator_reproducibility():
    """Same inputs always produce same output (NFR13)."""
    config = _make_config()
    evaluator = RuleEvaluator(config)
    metrics = {"FSI": 1.2}
    report1 = evaluator.evaluate(metrics)
    report2 = evaluator.evaluate(metrics)
    assert report1.results[0].passed == report2.results[0].passed
    assert report1.results[0].deviation == report2.results[0].deviation
    assert report1.overall_pass == report2.overall_pass


def test_scrutiny_report_has_run_id():
    config = _make_config()
    evaluator = RuleEvaluator(config)
    report = evaluator.evaluate({"FSI": 1.0})
    assert report.run_id is not None
    assert len(report.run_id) > 0
