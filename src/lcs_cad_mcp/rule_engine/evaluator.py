"""DCR rule evaluator — applies DCRConfig rules against drawing metrics."""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lcs_cad_mcp.rule_engine.models import DCRConfig, RuleResult, ScrutinyReport

logger = logging.getLogger(__name__)


class RuleEvaluator:
    """Evaluates a DCRConfig's rules against drawing-derived metrics."""

    def __init__(self, config: DCRConfig) -> None:
        self._config = config

    def evaluate(self, metrics: dict) -> ScrutinyReport:
        """Evaluate all rules in the loaded config against the given metrics.

        Args:
            metrics: Dict mapping rule_type strings to computed float values.
                     e.g. {"FSI": 1.25, "GROUND_COVERAGE": 42.0, "SETBACK_FRONT": 3.5}

        Returns:
            ScrutinyReport with per-rule results and overall pass/fail.
        """
        from lcs_cad_mcp.rule_engine.models import RuleResult, ScrutinyReport

        results: list[RuleResult] = []
        for rule in self._config.rules:
            computed = float(metrics.get(rule.rule_type.value, 0.0))
            # For setbacks and heights, lower is BAD (computed < threshold = violation)
            # For FSI, coverage, parking — higher is BAD (computed > threshold = violation)
            if rule.rule_type in (
                "SETBACK_FRONT", "SETBACK_SIDE", "SETBACK_REAR", "HEIGHT_RESTRICTION"
            ):
                # For setbacks and heights: computed must be >= threshold (minimum requirement)
                deviation = computed - rule.threshold  # negative = violation
                passed = deviation >= -rule.tolerance
            else:
                # For FSI, coverage, parking, etc.: computed must be <= threshold (maximum limit)
                deviation = computed - rule.threshold  # positive = violation
                passed = deviation <= rule.tolerance

            suggested = ""
            if not passed:
                if rule.rule_type.value.startswith("SETBACK") or rule.rule_type.value == "HEIGHT_RESTRICTION":
                    suggested = f"Increase {rule.name} to at least {rule.threshold} {rule.unit}."
                else:
                    suggested = f"Reduce {rule.name} to at most {rule.threshold} {rule.unit}."

            results.append(RuleResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                passed=passed,
                computed_value=computed,
                permissible_value=rule.threshold,
                deviation=deviation,
                suggested_action=suggested,
                tolerance=rule.tolerance,
            ))

        passed_count = sum(1 for r in results if r.passed)
        return ScrutinyReport(
            run_id=str(uuid.uuid4()),
            drawing_path="",
            authority=self._config.authority,
            results=results,
            overall_pass=all(r.passed for r in results),
            total_rules=len(results),
            passed_rules=passed_count,
            failed_rules=len(results) - passed_count,
        )
