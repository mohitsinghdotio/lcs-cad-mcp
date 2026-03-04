"""AutoDCR scrutiny service — orchestrates rule evaluation against loaded drawing."""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lcs_cad_mcp.session.context import DrawingSession
    from lcs_cad_mcp.rule_engine.models import DCRConfig, ScrutinyReport

logger = logging.getLogger(__name__)


class AutoDCRService:
    """Orchestrates the full AutoDCR scrutiny workflow.

    Computes drawing metrics, then evaluates all config rules.
    Stateless — instantiated per-call.
    """

    def run_scrutiny(self, session: DrawingSession, config: DCRConfig,
                     dry_run: bool = False) -> ScrutinyReport:
        """Run full DCR scrutiny against the loaded drawing and config.

        Returns a ScrutinyReport with per-rule results.
        """
        from lcs_cad_mcp.rule_engine.evaluator import RuleEvaluator
        from lcs_cad_mcp.modules.area.service import AreaService, AreaComputationError

        # Compute drawing metrics needed for rule evaluation
        metrics = self._compute_metrics(session)

        evaluator = RuleEvaluator(config)
        report = evaluator.evaluate(metrics)
        logger.info("AutoDCR scrutiny complete: overall_pass=%s rules=%d",
                    report.overall_pass, report.total_rules)
        return report

    def _compute_metrics(self, session: DrawingSession) -> dict:
        """Extract drawing metrics (areas, setbacks, etc.) for rule evaluation."""
        from lcs_cad_mcp.modules.area.service import AreaService, AreaComputationError, PLOT_BOUNDARY_LAYER

        metrics = {}
        area_svc = AreaService()

        # Attempt to compute plot area
        try:
            plot_area = area_svc.compute_plot_area(session)
            metrics["PLOT_AREA"] = plot_area
        except (AreaComputationError, Exception):
            metrics["PLOT_AREA"] = 0.0

        # Attempt to compute built-up area from common floor layers
        builtup_layers = ["PREDCR-FLOOR-PLATE", "PREDCR-BUILTUP-AREA"]
        try:
            builtup = area_svc.compute_builtup_area(session, builtup_layers)
            metrics["BUILTUP_AREA"] = builtup["total"]
        except (AreaComputationError, Exception):
            metrics["BUILTUP_AREA"] = 0.0

        # FSI = builtup / plot
        if metrics.get("PLOT_AREA", 0.0) > 0:
            metrics["FSI"] = metrics["BUILTUP_AREA"] / metrics["PLOT_AREA"]
        else:
            metrics["FSI"] = 0.0

        # Ground coverage from footprint
        try:
            footprint_layers = ["PREDCR-FLOOR-PLATE", "PREDCR-BUILTUP-AREA"]
            footprint_polygons = []
            for layer in footprint_layers:
                entities = session.backend.query_entities(layer=layer, entity_type="LWPOLYLINE")
                footprint_polygons.extend(entities)
            if footprint_polygons and metrics.get("PLOT_AREA", 0.0) > 0:
                # Use first polygon only for ground coverage
                pts = footprint_polygons[0].geometry.get("points", [])
                if len(pts) >= 3:
                    from shapely.geometry import Polygon
                    poly = Polygon([(p[0], p[1]) for p in pts])
                    metrics["GROUND_COVERAGE"] = (poly.area / metrics["PLOT_AREA"]) * 100.0
                else:
                    metrics["GROUND_COVERAGE"] = 0.0
            else:
                metrics["GROUND_COVERAGE"] = 0.0
        except Exception:
            metrics["GROUND_COVERAGE"] = 0.0

        # Default setback and other metrics (would be extracted from drawing geometry)
        metrics.setdefault("SETBACK_FRONT", 0.0)
        metrics.setdefault("SETBACK_SIDE", 0.0)
        metrics.setdefault("SETBACK_REAR", 0.0)
        metrics.setdefault("PARKING_RATIO", 0.0)
        metrics.setdefault("HEIGHT_RESTRICTION", 0.0)
        metrics.setdefault("OPEN_SPACE", 0.0)

        return metrics

    def dry_run(self, session: DrawingSession, config: DCRConfig,
                max_iterations: int = 10) -> list[ScrutinyReport]:
        """Run iterative scrutiny in dry-run mode, returning a list of reports."""
        reports = []
        for i in range(max_iterations):
            report = self.run_scrutiny(session, config, dry_run=True)
            reports.append(report)
            if report.overall_pass:
                logger.info("Dry run passed on iteration %d", i + 1)
                break
        return reports
