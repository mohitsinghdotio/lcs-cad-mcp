"""ezdxf-based CAD backend implementation.

import ezdxf is ONLY permitted in this file — see architecture enforcement rules.
All other modules receive DrawingMetadata, LayerInfo, EntityInfo Pydantic objects.
"""
from __future__ import annotations

import logging
import math

import ezdxf  # ezdxf import allowed ONLY in backends/ — see architecture enforcement rules

from lcs_cad_mcp.backends.base import DrawingMetadata, EntityInfo, LayerInfo

logger = logging.getLogger(__name__)


class EzdxfBackend:
    """Headless ezdxf-based CAD backend.  No AutoCAD required."""

    def __init__(self) -> None:
        self._doc: ezdxf.document.Drawing | None = None
        self._current_path: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Always True — ezdxf is pure Python with no system dependencies."""
        return True

    def open_drawing(self, path: str) -> DrawingMetadata:
        """Open an existing DXF file.

        DWG files are attempted via ezdxf but may fail without ODA converter.

        Args:
            path: Absolute or relative path to a DXF (or DWG) file.
        Returns:
            DrawingMetadata for the opened drawing.
        Raises:
            MCPError: DRAWING_OPEN_FAILED if file is missing or corrupt.
        """
        if path.lower().endswith(".dwg"):
            logger.warning(
                "DWG format detected for %s. ezdxf requires ODA File Converter for native DWG. "
                "Attempting readfile() anyway.",
                path,
            )
        try:
            self._doc = ezdxf.readfile(path)
            self._current_path = path
            return self.get_drawing_metadata()
        except (FileNotFoundError, ezdxf.DXFError, IOError) as exc:
            from lcs_cad_mcp.errors import MCPError, ErrorCode
            raise MCPError(
                code=ErrorCode.DRAWING_OPEN_FAILED,
                message=str(exc),
                recoverable=False,
                suggested_action="Verify the file path exists and is a valid DXF file.",
            )

    def new_drawing(self, name: str = "Untitled", units: str = "metric") -> DrawingMetadata:
        """Create a blank DXF R2018 drawing.

        Args:
            name: Display name (stored as comment, not a DXF header field).
            units: 'metric' (mm) or 'imperial' (inches).
        Returns:
            DrawingMetadata for the new empty drawing.
        """
        self._doc = ezdxf.new(dxfversion="R2018")
        # Set drawing units in header
        units_map = {"metric": 4, "imperial": 1}
        insunits = units_map.get(units)
        if insunits is None:
            logger.warning("Unrecognised unit string '%s'; defaulting to metric (mm).", units)
            insunits = 4
        self._doc.header["$INSUNITS"] = insunits
        self._current_path = None
        return DrawingMetadata(
            file_path=None,
            dxf_version="R2018",
            units=units if units in units_map else "metric",
            entity_count=0,
            layer_count=1,  # ezdxf always creates layer "0"
        )

    def save_drawing(self, path: str, dxf_version: str = "R2018") -> bool:
        """Save the active drawing to disk.

        Args:
            path: Target file path.
            dxf_version: Output DXF version (default R2018).
        Returns:
            True on success.
        Raises:
            MCPError: DRAWING_OPEN_FAILED if no drawing is open or save fails.
        """
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(
                code=ErrorCode.DRAWING_OPEN_FAILED,
                message="No drawing is currently open.",
                recoverable=True,
                suggested_action="Call new_drawing() or open_drawing() first.",
            )
        try:
            self._doc.saveas(path)
            self._current_path = path
        except OSError as exc:
            raise MCPError(
                code=ErrorCode.DRAWING_SAVE_FAILED,
                message=str(exc),
                recoverable=True,
                suggested_action="Check the output path is writable.",
            )
        # Post-save audit — log warnings but don't fail
        try:
            auditor = self._doc.audit()
            errors = auditor.errors
            if errors:
                logger.warning("ezdxf audit: %d error(s) after saving %s", len(errors), path)
                for err in errors[:5]:
                    logger.warning("  audit: %s", err)
        except Exception as audit_exc:
            logger.warning("ezdxf audit failed: %s", audit_exc)
        return True

    # ------------------------------------------------------------------
    # Layer operations
    # ------------------------------------------------------------------

    def create_layer(
        self,
        name: str,
        color: int = 7,
        linetype: str = "Continuous",
        lineweight: float = 0.25,
    ) -> LayerInfo:
        """Create a new layer in the active drawing."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        layers = self._doc.layers
        if name in layers:
            raise MCPError(
                code=ErrorCode.LAYER_ALREADY_EXISTS,
                message=f"Layer '{name}' already exists.",
                recoverable=True,
                suggested_action="Use a different name or call delete_layer first.",
            )
        layer = layers.new(name=name)
        layer.color = color
        layer.linetype = linetype
        return LayerInfo(name=name, color=color, linetype=linetype, lineweight=lineweight)

    def delete_layer(self, name: str) -> bool:
        """Delete a layer from the active drawing."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        if name not in self._doc.layers:
            raise MCPError(
                code=ErrorCode.LAYER_NOT_FOUND,
                message=f"Layer '{name}' not found.",
                recoverable=True,
                suggested_action="Call list_layers() to see available layers.",
            )
        self._doc.layers.remove(name)
        return True

    def list_layers(self) -> list[LayerInfo]:
        """Return all layers in the active drawing."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        result = []
        for layer in self._doc.layers:
            result.append(LayerInfo(
                name=layer.dxf.name,
                color=abs(layer.color),
                linetype=layer.dxf.get("linetype", "Continuous"),
                is_on=layer.is_on(),
                is_frozen=layer.is_frozen(),
                is_locked=layer.is_locked(),
            ))
        return result

    def get_layer(self, name: str) -> LayerInfo:
        """Return properties of a single layer."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        if name not in self._doc.layers:
            raise MCPError(
                code=ErrorCode.LAYER_NOT_FOUND,
                message=f"Layer '{name}' not found.",
                recoverable=True,
                suggested_action="Call list_layers() to see available layers.",
            )
        layer = self._doc.layers.get(name)
        return LayerInfo(
            name=layer.dxf.name,
            color=abs(layer.color),
            linetype=layer.dxf.get("linetype", "Continuous"),
            is_on=layer.is_on(),
            is_frozen=layer.is_frozen(),
            is_locked=layer.is_locked(),
        )

    # ------------------------------------------------------------------
    # Entity drawing
    # ------------------------------------------------------------------

    def _msp(self):
        """Return the model space layout."""
        return self._doc.modelspace()

    def draw_polyline(
        self,
        points: list[tuple[float, float]],
        layer: str,
        closed: bool = False,
    ) -> EntityInfo:
        """Add a LWPOLYLINE to the drawing."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        msp = self._msp()
        entity = msp.add_lwpolyline(points, dxfattribs={"layer": layer, "closed": closed})
        return EntityInfo(
            handle=entity.dxf.handle,
            entity_type="LWPOLYLINE",
            layer=layer,
            geometry={"points": [list(p) for p in points], "closed": closed},
        )

    def draw_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        layer: str,
    ) -> EntityInfo:
        """Add a LINE entity."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        msp = self._msp()
        entity = msp.add_line(start, end, dxfattribs={"layer": layer})
        return EntityInfo(
            handle=entity.dxf.handle,
            entity_type="LINE",
            layer=layer,
            geometry={"start": list(start), "end": list(end)},
        )

    def draw_arc(
        self,
        center: tuple[float, float],
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str,
    ) -> EntityInfo:
        """Add an ARC entity."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        msp = self._msp()
        entity = msp.add_arc(
            center=center,
            radius=radius,
            start_angle=start_angle,
            end_angle=end_angle,
            dxfattribs={"layer": layer},
        )
        return EntityInfo(
            handle=entity.dxf.handle,
            entity_type="ARC",
            layer=layer,
            geometry={"center": list(center), "radius": radius,
                      "start_angle": start_angle, "end_angle": end_angle},
        )

    def draw_circle(
        self,
        center: tuple[float, float],
        radius: float,
        layer: str,
    ) -> EntityInfo:
        """Add a CIRCLE entity."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        msp = self._msp()
        entity = msp.add_circle(center=center, radius=radius, dxfattribs={"layer": layer})
        return EntityInfo(
            handle=entity.dxf.handle,
            entity_type="CIRCLE",
            layer=layer,
            geometry={"center": list(center), "radius": radius},
        )

    def add_text(
        self,
        text: str,
        position: tuple[float, float],
        height: float,
        layer: str,
    ) -> EntityInfo:
        """Add a TEXT entity."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        msp = self._msp()
        entity = msp.add_text(
            text,
            dxfattribs={"layer": layer, "insert": position, "height": height},
        )
        return EntityInfo(
            handle=entity.dxf.handle,
            entity_type="TEXT",
            layer=layer,
            geometry={"text": text, "position": list(position), "height": height},
        )

    def insert_block(
        self,
        name: str,
        position: tuple[float, float],
        scale: float,
        layer: str,
    ) -> EntityInfo:
        """Insert a block reference (INSERT)."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        if name not in self._doc.blocks:
            raise MCPError(
                code=ErrorCode.ENTITY_INVALID,
                message=f"Block '{name}' not defined in this drawing.",
                recoverable=True,
                suggested_action="Define the block first with the appropriate tool.",
            )
        msp = self._msp()
        entity = msp.add_blockref(
            name,
            insert=position,
            dxfattribs={"layer": layer, "xscale": scale, "yscale": scale},
        )
        return EntityInfo(
            handle=entity.dxf.handle,
            entity_type="INSERT",
            layer=layer,
            geometry={"block_name": name, "position": list(position), "scale": scale},
        )

    def move_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo:
        """Move an entity by a displacement vector."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        entity = self._doc.entitydb.get(handle)
        if entity is None:
            raise MCPError(
                code=ErrorCode.ENTITY_NOT_FOUND,
                message=f"Entity handle '{handle}' not found.",
                recoverable=True,
            )
        entity.translate(delta[0], delta[1], 0)
        return EntityInfo(
            handle=handle,
            entity_type=entity.dxftype(),
            layer=entity.dxf.layer,
            geometry={"delta": list(delta)},
        )

    def copy_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo:
        """Copy an entity with a displacement offset."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        import copy

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        entity = self._doc.entitydb.get(handle)
        if entity is None:
            raise MCPError(
                code=ErrorCode.ENTITY_NOT_FOUND,
                message=f"Entity handle '{handle}' not found.",
                recoverable=True,
            )
        msp = self._msp()
        # Use ezdxf copy mechanism
        new_entity = entity.copy()
        msp.add_entity(new_entity)
        new_entity.translate(delta[0], delta[1], 0)
        return EntityInfo(
            handle=new_entity.dxf.handle,
            entity_type=new_entity.dxftype(),
            layer=new_entity.dxf.layer,
            geometry={"copied_from": handle, "delta": list(delta)},
        )

    def delete_entity(self, handle: str) -> bool:
        """Delete an entity from the drawing."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        entity = self._doc.entitydb.get(handle)
        if entity is None:
            raise MCPError(
                code=ErrorCode.ENTITY_NOT_FOUND,
                message=f"Entity handle '{handle}' not found.",
                recoverable=True,
            )
        entity.destroy()
        return True

    def query_entities(
        self,
        layer: str | None = None,
        entity_type: str | None = None,
        bounds: tuple[float, float, float, float] | None = None,
    ) -> list[EntityInfo]:
        """Query entities with optional filters."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        msp = self._msp()
        results = []
        for entity in msp:
            if layer is not None and entity.dxf.get("layer", "0") != layer:
                continue
            if entity_type is not None and entity.dxftype() != entity_type.upper():
                continue
            results.append(EntityInfo(
                handle=entity.dxf.handle,
                entity_type=entity.dxftype(),
                layer=entity.dxf.get("layer", "0"),
                geometry={},
            ))
        return results

    def get_drawing_metadata(self) -> DrawingMetadata:
        """Return metadata about the active drawing."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._doc is None:
            raise MCPError(code=ErrorCode.SESSION_NOT_STARTED, message="No drawing open.", recoverable=True)
        msp = self._msp()
        entity_count = len(list(msp))
        layer_count = len(list(self._doc.layers))
        # Try to get extents
        extents_min = (0.0, 0.0)
        extents_max = (0.0, 0.0)
        try:
            ext_min = self._doc.header.get("$EXTMIN", (0, 0, 0))
            ext_max = self._doc.header.get("$EXTMAX", (0, 0, 0))
            extents_min = (float(ext_min[0]), float(ext_min[1]))
            extents_max = (float(ext_max[0]), float(ext_max[1]))
        except Exception:
            pass
        insunits = self._doc.header.get("$INSUNITS", 4)
        units = "imperial" if insunits == 1 else "metric"
        return DrawingMetadata(
            file_path=self._current_path,
            dxf_version=self._doc.dxfversion,
            units=units,
            extents_min=extents_min,
            extents_max=extents_max,
            entity_count=entity_count,
            layer_count=layer_count,
        )
