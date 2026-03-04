"""Windows COM (AutoCAD) backend — full implementation.

Connects to a running AutoCAD instance via win32com, or launches one.
Only available on Windows with AutoCAD 2018+ and pywin32 installed.

AutoCAD COM API notes:
  - Points are VARIANT(VT_ARRAY|VT_R8, [x, y, z]) 3-D doubles
  - Polyline points are a flat double array [x0,y0,x1,y1,...]
  - Arc/angle parameters are in RADIANS
  - Entity.Handle returns the DXF hex handle string
  - doc.HandleToObject(handle) resolves a handle to a live COM object
  - Lineweight is stored as integer hundredths of mm (25 = 0.25 mm)
"""
from __future__ import annotations

import math
import sys
import logging

from lcs_cad_mcp.backends.base import DrawingMetadata, EntityInfo, LayerInfo

logger = logging.getLogger(__name__)

# DXF version string → AutoCAD AcSaveAsType enum value (DXF variants)
_DXF_SAVE_TYPE: dict[str, int] = {
    "R12": 9,    # acR12_DXF
    "R2000": 12, # ac2000_DXF
    "R2007": 16, # ac2007_DXF
    "R2010": 18, # ac2010_DXF
    "R2013": 20, # ac2013_DXF
    "R2018": 22, # ac2018_DXF
}

# AutoCAD ObjectName → canonical entity type string
_ACAD_TYPE_MAP: dict[str, str] = {
    "AcDbLine": "LINE",
    "AcDbPolyline": "LWPOLYLINE",
    "AcDb2dPolyline": "POLYLINE",
    "AcDbArc": "ARC",
    "AcDbCircle": "CIRCLE",
    "AcDbText": "TEXT",
    "AcDbMText": "MTEXT",
    "AcDbBlockReference": "INSERT",
}

# Reverse map for query filtering
_ENTITY_TYPE_MAP: dict[str, str] = {v: k for k, v in _ACAD_TYPE_MAP.items()}
_ENTITY_TYPE_MAP["LWPOLYLINE"] = "AcDbPolyline"


def _pt(x: float, y: float, z: float = 0.0):
    """Build a win32com VARIANT 3-D point."""
    import pythoncom
    import win32com.client
    return win32com.client.VARIANT(
        pythoncom.VT_ARRAY | pythoncom.VT_R8,
        [float(x), float(y), float(z)],
    )


def _flat_pts(points: list[tuple[float, float]]):
    """Flatten 2-D point list to VARIANT double array for AddLightWeightPolyline."""
    import pythoncom
    import win32com.client
    flat: list[float] = []
    for p in points:
        flat.extend([float(p[0]), float(p[1])])
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat)


class COMBackend:
    """AutoCAD COM automation backend (Windows only)."""

    def __init__(self) -> None:
        self._app = None   # AutoCAD.Application COM object
        self._doc = None   # AcadDocument COM object
        self._current_path: str | None = None
        self._com_initialized = False

    # ------------------------------------------------------------------
    # Availability & connection helpers
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True only on Windows with pywin32 installed."""
        if sys.platform != "win32":
            return False
        try:
            import win32com.client  # noqa: F401
            import pythoncom        # noqa: F401
            return True
        except ImportError:
            return False

    def _require_available(self) -> None:
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        if not self.is_available():
            raise MCPError(
                code=ErrorCode.BACKEND_UNAVAILABLE,
                message="COM backend requires Windows with AutoCAD and pywin32 installed.",
                recoverable=False,
                suggested_action="Install pywin32: uv run pip install pywin32",
            )

    def _connect(self) -> None:
        """Attach to a running AutoCAD instance, or launch one."""
        import pythoncom
        import win32com.client

        if not self._com_initialized:
            pythoncom.CoInitialize()
            self._com_initialized = True

        if self._app is not None:
            return  # already connected

        # Try attaching to a running instance first
        try:
            self._app = win32com.client.GetActiveObject("AutoCAD.Application")
            logger.info("COM backend: attached to running AutoCAD instance.")
            return
        except Exception:
            pass

        # Fall back to launching AutoCAD
        try:
            self._app = win32com.client.Dispatch("AutoCAD.Application")
            self._app.Visible = True
            logger.info("COM backend: launched new AutoCAD instance.")
        except Exception as exc:
            from lcs_cad_mcp.errors import MCPError, ErrorCode
            raise MCPError(
                code=ErrorCode.BACKEND_UNAVAILABLE,
                message=f"Could not connect to AutoCAD: {exc}",
                recoverable=False,
                suggested_action=(
                    "Ensure AutoCAD 2018+ is installed, licensed, and not blocking COM access."
                ),
            )

    def _require_doc(self) -> None:
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        if self._doc is None:
            raise MCPError(
                code=ErrorCode.SESSION_NOT_STARTED,
                message="No drawing is open.",
                recoverable=True,
                suggested_action="Call open_drawing() or new_drawing() first.",
            )

    def _entity_by_handle(self, handle: str):
        """Resolve a DXF handle string to a live AutoCAD COM entity object."""
        self._require_doc()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        try:
            return self._doc.HandleToObject(handle)
        except Exception:
            raise MCPError(
                code=ErrorCode.ENTITY_NOT_FOUND,
                message=f"Entity handle '{handle}' not found in active drawing.",
                recoverable=True,
            )

    def _to_entity_info(self, entity, geometry: dict | None = None) -> EntityInfo:
        """Convert an AutoCAD COM entity to an EntityInfo Pydantic model."""
        acad_name = entity.ObjectName
        entity_type = _ACAD_TYPE_MAP.get(acad_name, acad_name)
        return EntityInfo(
            handle=entity.Handle,
            entity_type=entity_type,
            layer=entity.Layer,
            geometry=geometry or {},
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open_drawing(self, path: str) -> DrawingMetadata:
        self._require_available()
        self._connect()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        try:
            self._doc = self._app.Documents.Open(path)
            self._current_path = path
            logger.info("COM backend: opened '%s'.", path)
            return self.get_drawing_metadata()
        except MCPError:
            raise
        except Exception as exc:
            raise MCPError(
                code=ErrorCode.DRAWING_OPEN_FAILED,
                message=f"AutoCAD could not open '{path}': {exc}",
                recoverable=False,
                suggested_action="Verify the file exists and is a valid DWG/DXF file.",
            )

    def new_drawing(self, name: str = "Untitled", units: str = "metric") -> DrawingMetadata:
        self._require_available()
        self._connect()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        try:
            self._doc = self._app.Documents.Add()
            # INSUNITS: 4 = millimetres (metric), 1 = inches (imperial)
            insunits = 4 if units == "metric" else 1
            self._doc.SetVariable("INSUNITS", insunits)
            self._current_path = None
            logger.info("COM backend: new drawing created (units=%s).", units)
            return DrawingMetadata(
                file_path=None,
                dxf_version="R2018",
                units=units,
                entity_count=0,
                layer_count=self._doc.Layers.Count,
            )
        except MCPError:
            raise
        except Exception as exc:
            raise MCPError(
                code=ErrorCode.DRAWING_OPEN_FAILED,
                message=f"Could not create new AutoCAD drawing: {exc}",
                recoverable=False,
            )

    def save_drawing(self, path: str, dxf_version: str = "R2018") -> bool:
        self._require_available()
        self._require_doc()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        try:
            if path.lower().endswith(".dxf"):
                file_type = _DXF_SAVE_TYPE.get(dxf_version, 22)
            else:
                file_type = 1  # acNative — current DWG format
            self._doc.SaveAs(path, file_type)
            self._current_path = path
            logger.info("COM backend: saved drawing to '%s' (type=%d).", path, file_type)
            return True
        except MCPError:
            raise
        except Exception as exc:
            raise MCPError(
                code=ErrorCode.DRAWING_SAVE_FAILED,
                message=f"AutoCAD save failed for '{path}': {exc}",
                recoverable=True,
                suggested_action="Check the output path is writable and not locked by another process.",
            )

    # ------------------------------------------------------------------
    # Layer operations
    # ------------------------------------------------------------------

    def _get_com_layer(self, name: str):
        """Return COM layer object by name, or None if not found."""
        layers = self._doc.Layers
        for i in range(layers.Count):
            lyr = layers.Item(i)
            if lyr.Name.upper() == name.upper():
                return lyr
        return None

    def create_layer(
        self,
        name: str,
        color: int = 7,
        linetype: str = "Continuous",
        lineweight: float = 0.25,
    ) -> LayerInfo:
        self._require_available()
        self._require_doc()
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if self._get_com_layer(name) is not None:
            raise MCPError(
                code=ErrorCode.LAYER_ALREADY_EXISTS,
                message=f"Layer '{name}' already exists.",
                recoverable=True,
                suggested_action="Use a different name or delete the existing layer first.",
            )
        try:
            layer = self._doc.Layers.Add(name)
            layer.Color = int(color)
            # Load linetype if not already loaded
            if linetype.upper() != "CONTINUOUS":
                try:
                    self._doc.Linetypes.Load(linetype, "acad.lin")
                except Exception:
                    pass  # Already loaded or linetype file not found — skip silently
            try:
                layer.Linetype = linetype
            except Exception:
                logger.warning("COM: could not set linetype '%s' on layer '%s'.", linetype, name)
                layer.Linetype = "Continuous"
            # Lineweight is integer hundredths of mm (25 = 0.25 mm)
            try:
                layer.Lineweight = int(round(lineweight * 100))
            except Exception:
                pass  # Non-standard lineweight value — AutoCAD will use default
            return LayerInfo(name=name, color=color, linetype=linetype, lineweight=lineweight)
        except MCPError:
            raise
        except Exception as exc:
            raise MCPError(
                code=ErrorCode.LAYER_INVALID,
                message=f"Could not create layer '{name}': {exc}",
                recoverable=True,
            )

    def delete_layer(self, name: str) -> bool:
        self._require_available()
        self._require_doc()
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        layer = self._get_com_layer(name)
        if layer is None:
            raise MCPError(
                code=ErrorCode.LAYER_NOT_FOUND,
                message=f"Layer '{name}' not found.",
                recoverable=True,
            )
        try:
            layer.Delete()
            return True
        except Exception as exc:
            raise MCPError(
                code=ErrorCode.LAYER_INVALID,
                message=f"Could not delete layer '{name}': {exc}",
                recoverable=True,
                suggested_action=(
                    "Layer may be current, contain entities, or be locked. "
                    "Move all entities off it first."
                ),
            )

    def list_layers(self) -> list[LayerInfo]:
        self._require_available()
        self._require_doc()
        result: list[LayerInfo] = []
        layers = self._doc.Layers
        for i in range(layers.Count):
            lyr = layers.Item(i)
            result.append(self._layer_to_info(lyr))
        return result

    def get_layer(self, name: str) -> LayerInfo:
        self._require_available()
        self._require_doc()
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        layer = self._get_com_layer(name)
        if layer is None:
            raise MCPError(
                code=ErrorCode.LAYER_NOT_FOUND,
                message=f"Layer '{name}' not found.",
                recoverable=True,
            )
        return self._layer_to_info(layer)

    def _layer_to_info(self, lyr) -> LayerInfo:
        """Convert a COM layer object to LayerInfo."""
        try:
            is_on = bool(lyr.LayerOn)
        except Exception:
            is_on = True
        try:
            is_frozen = bool(lyr.Freeze)
        except Exception:
            is_frozen = False
        try:
            is_locked = bool(lyr.Lock)
        except Exception:
            is_locked = False
        try:
            lw_raw = int(lyr.Lineweight)
            lineweight = lw_raw / 100.0 if lw_raw > 0 else 0.25
        except Exception:
            lineweight = 0.25
        return LayerInfo(
            name=lyr.Name,
            color=abs(int(lyr.Color)),
            linetype=lyr.Linetype,
            lineweight=lineweight,
            is_on=is_on,
            is_frozen=is_frozen,
            is_locked=is_locked,
        )

    # ------------------------------------------------------------------
    # Entity drawing
    # ------------------------------------------------------------------

    def draw_polyline(
        self,
        points: list[tuple[float, float]],
        layer: str,
        closed: bool = False,
    ) -> EntityInfo:
        self._require_available()
        self._require_doc()
        msp = self._doc.ModelSpace
        pline = msp.AddLightWeightPolyline(_flat_pts(points))
        pline.Layer = layer
        pline.Closed = closed
        pline.Update()
        return EntityInfo(
            handle=pline.Handle,
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
        self._require_available()
        self._require_doc()
        msp = self._doc.ModelSpace
        line = msp.AddLine(_pt(*start), _pt(*end))
        line.Layer = layer
        line.Update()
        return EntityInfo(
            handle=line.Handle,
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
        self._require_available()
        self._require_doc()
        # AutoCAD COM AddArc takes angles in RADIANS
        msp = self._doc.ModelSpace
        arc = msp.AddArc(
            _pt(*center),
            float(radius),
            math.radians(start_angle),
            math.radians(end_angle),
        )
        arc.Layer = layer
        arc.Update()
        return EntityInfo(
            handle=arc.Handle,
            entity_type="ARC",
            layer=layer,
            geometry={
                "center": list(center),
                "radius": radius,
                "start_angle": start_angle,
                "end_angle": end_angle,
            },
        )

    def draw_circle(
        self,
        center: tuple[float, float],
        radius: float,
        layer: str,
    ) -> EntityInfo:
        self._require_available()
        self._require_doc()
        msp = self._doc.ModelSpace
        circle = msp.AddCircle(_pt(*center), float(radius))
        circle.Layer = layer
        circle.Update()
        return EntityInfo(
            handle=circle.Handle,
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
        self._require_available()
        self._require_doc()
        msp = self._doc.ModelSpace
        txt = msp.AddText(str(text), _pt(*position), float(height))
        txt.Layer = layer
        txt.Update()
        return EntityInfo(
            handle=txt.Handle,
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
        self._require_available()
        self._require_doc()
        from lcs_cad_mcp.errors import MCPError, ErrorCode
        try:
            msp = self._doc.ModelSpace
            # InsertBlock(InsertionPoint, Name, Xscale, Yscale, Zscale, Rotation)
            ref = msp.InsertBlock(
                _pt(*position),
                str(name),
                float(scale),
                float(scale),
                float(scale),
                0.0,
            )
            ref.Layer = layer
            ref.Update()
            return EntityInfo(
                handle=ref.Handle,
                entity_type="INSERT",
                layer=layer,
                geometry={"block_name": name, "position": list(position), "scale": scale},
            )
        except MCPError:
            raise
        except Exception as exc:
            raise MCPError(
                code=ErrorCode.ENTITY_INVALID,
                message=f"Block '{name}' insert failed: {exc}",
                recoverable=True,
                suggested_action=(
                    "Ensure the block is defined in the drawing or an attached xref."
                ),
            )

    # ------------------------------------------------------------------
    # Entity operations
    # ------------------------------------------------------------------

    def move_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo:
        self._require_available()
        entity = self._entity_by_handle(handle)
        # Move(FromPoint, ToPoint) — displacement from origin by delta
        entity.Move(_pt(0.0, 0.0), _pt(delta[0], delta[1]))
        entity.Update()
        return self._to_entity_info(entity, geometry={"delta": list(delta)})

    def copy_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo:
        self._require_available()
        entity = self._entity_by_handle(handle)
        new_entity = entity.Copy()
        new_entity.Move(_pt(0.0, 0.0), _pt(delta[0], delta[1]))
        new_entity.Update()
        return self._to_entity_info(
            new_entity,
            geometry={"copied_from": handle, "delta": list(delta)},
        )

    def delete_entity(self, handle: str) -> bool:
        self._require_available()
        entity = self._entity_by_handle(handle)
        entity.Delete()
        return True

    def query_entities(
        self,
        layer: str | None = None,
        entity_type: str | None = None,
        bounds: tuple[float, float, float, float] | None = None,
    ) -> list[EntityInfo]:
        self._require_available()
        self._require_doc()

        # Map our canonical type name to AutoCAD ObjectName
        acad_name_filter: str | None = None
        if entity_type is not None:
            acad_name_filter = _ENTITY_TYPE_MAP.get(entity_type.upper(), entity_type)

        msp = self._doc.ModelSpace
        results: list[EntityInfo] = []
        for i in range(msp.Count):
            try:
                entity = msp.Item(i)
            except Exception:
                continue

            if layer is not None and entity.Layer.upper() != layer.upper():
                continue
            if acad_name_filter is not None and entity.ObjectName != acad_name_filter:
                continue

            # Optional bounding-box filter
            if bounds is not None:
                try:
                    min_pt, max_pt = entity.GetBoundingBox()
                    ex_min_x, ex_min_y = float(min_pt[0]), float(min_pt[1])
                    ex_max_x, ex_max_y = float(max_pt[0]), float(max_pt[1])
                    xmin, ymin, xmax, ymax = bounds
                    if ex_max_x < xmin or ex_min_x > xmax or ex_max_y < ymin or ex_min_y > ymax:
                        continue
                except Exception:
                    pass  # Skip bounding box filter if not supported for this entity type

            results.append(self._to_entity_info(entity))
        return results

    # ------------------------------------------------------------------
    # Drawing metadata
    # ------------------------------------------------------------------

    def get_drawing_metadata(self) -> DrawingMetadata:
        self._require_available()
        self._require_doc()

        msp = self._doc.ModelSpace
        entity_count = msp.Count
        layer_count = self._doc.Layers.Count

        extents_min = (0.0, 0.0)
        extents_max = (0.0, 0.0)
        try:
            ext_min = self._doc.GetVariable("EXTMIN")
            ext_max = self._doc.GetVariable("EXTMAX")
            extents_min = (float(ext_min[0]), float(ext_min[1]))
            extents_max = (float(ext_max[0]), float(ext_max[1]))
        except Exception:
            pass

        units = "metric"
        try:
            insunits = int(self._doc.GetVariable("INSUNITS"))
            units = "imperial" if insunits == 1 else "metric"
        except Exception:
            pass

        # AutoCAD reports its own DXF version via ACADVER sysvar
        dxf_version = "R2018"
        try:
            acadver = str(self._doc.GetVariable("ACADVER")).strip()
            # Map "AC1032" etc. to human-readable
            _ver_map = {
                "AC1009": "R12", "AC1015": "R2000",
                "AC1021": "R2007", "AC1024": "R2010",
                "AC1027": "R2013", "AC1032": "R2018",
            }
            dxf_version = _ver_map.get(acadver, dxf_version)
        except Exception:
            pass

        return DrawingMetadata(
            file_path=self._current_path,
            dxf_version=dxf_version,
            units=units,
            extents_min=extents_min,
            extents_max=extents_max,
            entity_count=entity_count,
            layer_count=layer_count,
        )
