"""Area computation service — uses Shapely for all polygon area calculations."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lcs_cad_mcp.session.context import DrawingSession

logger = logging.getLogger(__name__)

PLOT_BOUNDARY_LAYER = "PREDCR-PLOT-BOUNDARY"  # Must match PreDCR layer registry (Story 4-1)


class AreaComputationError(Exception):
    """Raised when an area computation fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def format_area(area_float: float, decimals: int = 4) -> str:
    return f"{area_float:.{decimals}f}"


class AreaService:
    """Stateless computation service for polygon area calculations using Shapely."""

    def _require_shapely(self):
        try:
            from shapely.geometry import Polygon  # noqa: F401
        except ImportError:
            raise AreaComputationError(
                code="SHAPELY_NOT_AVAILABLE",
                message="shapely is required for area computation. Install it with: pip install shapely",
            )

    def _entities_to_polygon(self, vertices: list):
        """Convert a vertex list to a Shapely Polygon.

        Raises AreaComputationError if polygon is invalid.
        """
        from shapely.geometry import Polygon

        if len(vertices) < 3:
            raise AreaComputationError(
                code="POLYGON_TOO_FEW_VERTICES",
                message=f"Polygon requires at least 3 vertices, got {len(vertices)}",
            )

        # Support both {x, y} dicts and [x, y] lists
        points = []
        for v in vertices:
            if isinstance(v, dict):
                points.append((float(v.get("x", v.get(0, 0))), float(v.get("y", v.get(1, 0)))))
            else:
                points.append((float(v[0]), float(v[1])))

        poly = Polygon(points)
        if not poly.is_valid:
            raise AreaComputationError(
                code="POLYGON_SELF_INTERSECTING",
                message="Polygon is self-intersecting and cannot be used for area computation.",
            )
        # Check closure: first and last point should be same (or close)
        if len(points) >= 2:
            first, last = points[0], points[-1]
            dist = ((first[0] - last[0]) ** 2 + (first[1] - last[1]) ** 2) ** 0.5
            if dist > 0.001:
                raise AreaComputationError(
                    code="POLYGON_NOT_CLOSED",
                    message=f"Polygon is not closed (gap={dist:.6f}). Close the polyline first.",
                )
        return poly

    def _get_layer_polygons(self, session: DrawingSession, layer: str) -> list:
        """Get all LWPOLYLINE entities from a layer and convert to Shapely polygons."""
        entities = session.backend.query_entities(layer=layer, entity_type="LWPOLYLINE")
        if not entities:
            return []

        polygons = []
        for entity in entities:
            pts = entity.geometry.get("points", [])
            if len(pts) >= 3:
                try:
                    poly = self._entities_to_polygon(pts)
                    polygons.append(poly)
                except AreaComputationError:
                    pass
        return polygons

    def compute_plot_area(self, session: DrawingSession) -> float:
        """Compute plot boundary area using Shapely polygon."""
        self._require_shapely()
        entities = session.backend.query_entities(layer=PLOT_BOUNDARY_LAYER, entity_type="LWPOLYLINE")
        if not entities:
            raise AreaComputationError(
                code="PLOT_BOUNDARY_NOT_FOUND",
                message=f"No entity found on layer '{PLOT_BOUNDARY_LAYER}'. "
                        "Ensure plot boundary polyline is drawn on the correct layer.",
            )
        pts = entities[0].geometry.get("points", [])
        polygon = self._entities_to_polygon(pts)
        return polygon.area  # shapely polygon.area — NFR11 compliance

    def compute_layer_area(self, session: DrawingSession, layer: str, unit: str = "sqm") -> float:
        """Compute total area of all closed polygons on a layer."""
        self._require_shapely()
        polygons = self._get_layer_polygons(session, layer)
        if not polygons:
            raise AreaComputationError(
                code="NO_POLYGON_FOUND",
                message=f"No closed LWPOLYLINE entities found on layer '{layer}'.",
            )
        total = sum(p.area for p in polygons)
        if unit == "sqft":
            total *= 10.7639  # 1 sqm = 10.7639 sqft
        return total

    def compute_builtup_area(self, session: DrawingSession, floor_layers: list[str], unit: str = "sqm") -> dict:
        """Compute total built-up area across all floor layers."""
        self._require_shapely()
        floor_areas = {}
        total = 0.0
        for layer in floor_layers:
            try:
                area = self.compute_layer_area(session, layer, unit)
                floor_areas[layer] = area
                total += area
            except AreaComputationError:
                floor_areas[layer] = 0.0
        return {"total": total, "by_floor": floor_areas, "unit": unit}

    def compute_carpet_area(self, session: DrawingSession, carpet_layer: str, unit: str = "sqm") -> float:
        """Compute carpet area from the specified layer."""
        self._require_shapely()
        return self.compute_layer_area(session, carpet_layer, unit)

    def compute_fsi(self, session: DrawingSession, plot_layer: str, floor_layers: list[str], unit: str = "sqm") -> dict:
        """Compute Floor Space Index = total built-up / plot area."""
        self._require_shapely()
        # Compute plot area
        entities = session.backend.query_entities(layer=plot_layer, entity_type="LWPOLYLINE")
        if not entities:
            raise AreaComputationError(
                code="PLOT_BOUNDARY_NOT_FOUND",
                message=f"No entity found on plot layer '{plot_layer}'.",
            )
        pts = entities[0].geometry.get("points", [])
        plot_poly = self._entities_to_polygon(pts)
        plot_area = plot_poly.area

        if plot_area == 0:
            raise AreaComputationError(code="PLOT_AREA_ZERO", message="Plot area is zero.")

        builtup = self.compute_builtup_area(session, floor_layers, unit)
        fsi = builtup["total"] / plot_area
        return {
            "fsi": round(fsi, 4),
            "plot_area": round(plot_area, 4),
            "total_builtup": round(builtup["total"], 4),
            "unit": unit,
        }

    def compute_coverage(self, session: DrawingSession, plot_layer: str, footprint_layer: str) -> dict:
        """Compute ground coverage ratio = footprint area / plot area."""
        self._require_shapely()
        entities = session.backend.query_entities(layer=plot_layer, entity_type="LWPOLYLINE")
        if not entities:
            raise AreaComputationError(
                code="PLOT_BOUNDARY_NOT_FOUND",
                message=f"No entity found on plot layer '{plot_layer}'.",
            )
        pts = entities[0].geometry.get("points", [])
        plot_poly = self._entities_to_polygon(pts)
        plot_area = plot_poly.area
        if plot_area == 0:
            raise AreaComputationError(code="PLOT_AREA_ZERO", message="Plot area is zero.")

        footprint_polygons = self._get_layer_polygons(session, footprint_layer)
        if not footprint_polygons:
            raise AreaComputationError(
                code="FOOTPRINT_NOT_FOUND",
                message=f"No LWPOLYLINE found on footprint layer '{footprint_layer}'.",
            )
        footprint_area = sum(p.area for p in footprint_polygons)
        coverage_pct = (footprint_area / plot_area) * 100.0
        return {
            "coverage_percent": round(coverage_pct, 4),
            "footprint_area": round(footprint_area, 4),
            "plot_area": round(plot_area, 4),
        }
