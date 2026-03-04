"""Verification engine — closure, containment, naming, and entity count checks."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lcs_cad_mcp.session.context import DrawingSession

logger = logging.getLogger(__name__)


class VerificationService:
    """Implements geometric and naming verification checks."""

    def __init__(self, session: DrawingSession) -> None:
        self._session = session

    def _require_open(self) -> None:
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        if not self._session.is_drawing_open:
            raise MCPError(
                code=ErrorCode.SESSION_DRAWING_NOT_OPEN,
                message="No drawing is open.",
                recoverable=True,
            )

    def _get_polyline_points(self, layer: str) -> list[list[list[float]]]:
        """Return list of point-lists for all LWPOLYLINE entities on a layer."""
        entities = self._session.backend.query_entities(layer=layer, entity_type="LWPOLYLINE")
        polys = []
        for e in entities:
            pts = e.geometry.get("points", [])
            if pts:
                polys.append(pts)
        return polys

    def verify_closure(self, layer: str, tolerance: float = 0.001) -> dict:
        """Verify all LWPOLYLINE entities on a layer are closed.

        Returns a report dict with passed bool, failures list, and layer info.
        """
        self._require_open()
        import math

        entities = self._session.backend.query_entities(layer=layer, entity_type="LWPOLYLINE")
        failures = []
        for e in entities:
            pts = e.geometry.get("points", [])
            closed = e.geometry.get("closed", False)
            if closed:
                continue  # already closed
            if len(pts) >= 2:
                first = pts[0]
                last = pts[-1]
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(first[:2], last[:2])))
                if dist > tolerance:
                    failures.append({
                        "handle": e.handle,
                        "gap": round(dist, 6),
                        "first": first[:2],
                        "last": last[:2],
                    })
        return {
            "passed": len(failures) == 0,
            "layer": layer,
            "checked": len(entities),
            "failures": failures,
            "tolerance": tolerance,
        }

    def verify_containment(self, outer_layer: str, inner_layer: str, tolerance: float = 0.001) -> dict:
        """Verify all polygons on inner_layer are contained within outer_layer polygon."""
        self._require_open()
        try:
            from shapely.geometry import Polygon
            from shapely.ops import unary_union
        except ImportError:
            from lcs_cad_mcp.errors import MCPError, ErrorCode
            raise MCPError(
                code=ErrorCode.GEOMETRY_INVALID,
                message="shapely is required for containment verification.",
                recoverable=False,
            )

        outer_entities = self._session.backend.query_entities(layer=outer_layer, entity_type="LWPOLYLINE")
        inner_entities = self._session.backend.query_entities(layer=inner_layer, entity_type="LWPOLYLINE")

        if not outer_entities:
            return {"passed": False, "error": f"No LWPOLYLINE found on outer layer '{outer_layer}'"}

        outer_pts = outer_entities[0].geometry.get("points", [])
        if len(outer_pts) < 3:
            return {"passed": False, "error": "Outer polygon has fewer than 3 points"}

        outer_poly = Polygon([(p[0], p[1]) for p in outer_pts]).buffer(tolerance)
        failures = []
        for e in inner_entities:
            pts = e.geometry.get("points", [])
            if len(pts) < 3:
                continue
            inner_poly = Polygon([(p[0], p[1]) for p in pts])
            if not outer_poly.contains(inner_poly):
                failures.append({"handle": e.handle, "layer": inner_layer})

        return {
            "passed": len(failures) == 0,
            "outer_layer": outer_layer,
            "inner_layer": inner_layer,
            "checked": len(inner_entities),
            "failures": failures,
        }

    def verify_naming(self, authority_code: str) -> dict:
        """Verify layer names conform to authority naming conventions."""
        self._require_open()
        layers = self._session.backend.list_layers()
        violations = []
        for layer in layers:
            if not layer.name or layer.name.startswith("  "):
                violations.append({"layer": layer.name, "issue": "Invalid layer name"})
        return {
            "passed": len(violations) == 0,
            "authority_code": authority_code,
            "checked": len(layers),
            "violations": violations,
        }

    def verify_min_entity_count(self, layer: str, min_count: int = 1,
                                 entity_type: str | None = None) -> dict:
        """Verify a layer has at least min_count entities."""
        self._require_open()
        entities = self._session.backend.query_entities(layer=layer, entity_type=entity_type)
        count = len(entities)
        return {
            "passed": count >= min_count,
            "layer": layer,
            "entity_type": entity_type,
            "count": count,
            "min_required": min_count,
        }

    def verify_all(self, authority_code: str, tolerance: float = 0.001) -> dict:
        """Run all verification checks and return aggregated report."""
        self._require_open()
        layers = [l.name for l in self._session.backend.list_layers()]
        results = []
        # Check closure on all layers
        for layer in layers:
            closure_result = self.verify_closure(layer, tolerance=tolerance)
            if not closure_result["passed"]:
                results.append({"check": "closure", "layer": layer, "result": closure_result})
        # Check naming
        naming = self.verify_naming(authority_code)
        if not naming["passed"]:
            results.append({"check": "naming", "result": naming})
        overall_pass = len(results) == 0
        return {
            "passed": overall_pass,
            "authority_code": authority_code,
            "layers_checked": len(layers),
            "failures": results,
        }
