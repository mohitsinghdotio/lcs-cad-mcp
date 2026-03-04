"""
CAD Backend Abstraction Layer.

Uses typing.Protocol (structural subtyping / duck typing) so that
EzdxfBackend and COMBackend do NOT need to explicitly inherit from
CADBackend.  Any class that implements the full method set satisfies the
Protocol at runtime when @runtime_checkable is applied.

No ezdxf or win32com types may appear in any signature here.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class DrawingMetadata(BaseModel):
    """Metadata about an open or newly-created DXF drawing."""
    file_path: str | None = None
    dxf_version: str = "R2018"
    units: str = "metric"
    extents_min: tuple[float, float] = (0.0, 0.0)
    extents_max: tuple[float, float] = (0.0, 0.0)
    entity_count: int = 0
    layer_count: int = 0


class LayerInfo(BaseModel):
    """Properties of a single CAD layer."""
    name: str
    color: int = 7
    linetype: str = "Continuous"
    lineweight: float = 0.25
    is_on: bool = True
    is_frozen: bool = False
    is_locked: bool = False


class EntityInfo(BaseModel):
    """Description of a single CAD entity."""
    handle: str
    entity_type: str
    layer: str
    geometry: dict


@runtime_checkable
class CADBackend(Protocol):
    """Duck-typed interface every CAD backend must satisfy."""

    def is_available(self) -> bool:
        """Return True if this backend can operate in the current environment."""
        ...

    def open_drawing(self, path: str) -> DrawingMetadata:
        """Open an existing DXF/DWG file.

        Args:
            path: Absolute or relative file path.
        Returns:
            DrawingMetadata for the opened drawing.
        Raises:
            MCPError: DRAWING_OPEN_FAILED if the file cannot be opened.
        """
        ...

    def new_drawing(self, name: str = "Untitled", units: str = "metric") -> DrawingMetadata:
        """Create a new empty drawing in memory.

        Args:
            name: Display name for the drawing.
            units: Unit system — "metric" or "imperial".
        Returns:
            DrawingMetadata for the new drawing.
        """
        ...

    def save_drawing(self, path: str, dxf_version: str = "R2018") -> bool:
        """Save the current drawing to disk.

        Args:
            path: Target file path.
            dxf_version: DXF format version string.
        Returns:
            True on success.
        Raises:
            MCPError: DRAWING_SAVE_FAILED on I/O error.
        """
        ...

    def create_layer(
        self,
        name: str,
        color: int = 7,
        linetype: str = "Continuous",
        lineweight: float = 0.25,
    ) -> LayerInfo:
        """Create a new layer in the active drawing.

        Args:
            name: Unique layer name.
            color: ACI colour index (1-255).
            linetype: Linetype name.
            lineweight: Line weight in mm.
        Returns:
            LayerInfo for the newly created layer.
        Raises:
            MCPError: LAYER_ALREADY_EXISTS if the name is taken.
        """
        ...

    def delete_layer(self, name: str) -> bool:
        """Delete a layer from the drawing.

        Args:
            name: Layer name to delete.
        Returns:
            True on success.
        Raises:
            MCPError: LAYER_NOT_FOUND if the layer does not exist.
        """
        ...

    def list_layers(self) -> list[LayerInfo]:
        """Return all layers in the active drawing."""
        ...

    def get_layer(self, name: str) -> LayerInfo:
        """Return properties of a single layer.

        Args:
            name: Layer name.
        Returns:
            LayerInfo for the requested layer.
        Raises:
            MCPError: LAYER_NOT_FOUND if the layer does not exist.
        """
        ...

    def draw_polyline(
        self,
        points: list[tuple[float, float]],
        layer: str,
        closed: bool = False,
    ) -> EntityInfo:
        """Add a polyline (LWPOLYLINE) to the drawing.

        Args:
            points: Ordered list of (x, y) vertex coordinates.
            layer: Target layer name.
            closed: If True, connect the last vertex to the first.
        Returns:
            EntityInfo for the created polyline.
        """
        ...

    def draw_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        layer: str,
    ) -> EntityInfo:
        """Add a LINE entity to the drawing.

        Args:
            start: Start point (x, y).
            end: End point (x, y).
            layer: Target layer name.
        Returns:
            EntityInfo for the created line.
        """
        ...

    def draw_arc(
        self,
        center: tuple[float, float],
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str,
    ) -> EntityInfo:
        """Add an ARC entity to the drawing.

        Args:
            center: Centre point (x, y).
            radius: Arc radius.
            start_angle: Start angle in degrees (0=east, CCW).
            end_angle: End angle in degrees.
            layer: Target layer name.
        Returns:
            EntityInfo for the created arc.
        """
        ...

    def draw_circle(
        self,
        center: tuple[float, float],
        radius: float,
        layer: str,
    ) -> EntityInfo:
        """Add a CIRCLE entity to the drawing.

        Args:
            center: Centre point (x, y).
            radius: Circle radius.
            layer: Target layer name.
        Returns:
            EntityInfo for the created circle.
        """
        ...

    def add_text(
        self,
        text: str,
        position: tuple[float, float],
        height: float,
        layer: str,
    ) -> EntityInfo:
        """Add a TEXT entity to the drawing.

        Args:
            text: Text string content.
            position: Insertion point (x, y).
            height: Text height in drawing units.
            layer: Target layer name.
        Returns:
            EntityInfo for the created text entity.
        """
        ...

    def insert_block(
        self,
        name: str,
        position: tuple[float, float],
        scale: float,
        layer: str,
    ) -> EntityInfo:
        """Insert a block reference (INSERT) into the drawing.

        Args:
            name: Block definition name.
            position: Insertion point (x, y).
            scale: Uniform scale factor.
            layer: Target layer name.
        Returns:
            EntityInfo for the created block reference.
        Raises:
            MCPError: ENTITY_INVALID if the block definition does not exist.
        """
        ...

    def move_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo:
        """Move an entity by a displacement vector.

        Args:
            handle: DXF entity handle string.
            delta: (dx, dy) displacement.
        Returns:
            Updated EntityInfo after move.
        Raises:
            MCPError: ENTITY_NOT_FOUND if handle is invalid.
        """
        ...

    def copy_entity(self, handle: str, delta: tuple[float, float]) -> EntityInfo:
        """Copy an entity with a displacement offset.

        Args:
            handle: DXF entity handle string.
            delta: (dx, dy) displacement for the copy.
        Returns:
            EntityInfo for the new copy.
        Raises:
            MCPError: ENTITY_NOT_FOUND if handle is invalid.
        """
        ...

    def delete_entity(self, handle: str) -> bool:
        """Delete an entity from the drawing.

        Args:
            handle: DXF entity handle string.
        Returns:
            True on success.
        Raises:
            MCPError: ENTITY_NOT_FOUND if handle is invalid.
        """
        ...

    def query_entities(
        self,
        layer: str | None = None,
        entity_type: str | None = None,
        bounds: tuple[float, float, float, float] | None = None,
    ) -> list[EntityInfo]:
        """Query entities with optional filters.

        Args:
            layer: Filter by layer name.  None returns all layers.
            entity_type: Filter by DXF entity type (e.g. "LINE", "LWPOLYLINE").
            bounds: Bounding box filter (xmin, ymin, xmax, ymax).
        Returns:
            Filtered list of EntityInfo objects.
        """
        ...

    def get_drawing_metadata(self) -> DrawingMetadata:
        """Return metadata about the active drawing.

        Returns:
            DrawingMetadata for the currently open drawing.
        Raises:
            MCPError: SESSION_NOT_STARTED if no drawing is open.
        """
        ...


class BackendFactory:
    """Registry-based factory for CAD backend implementations.

    Backends self-register via BackendFactory.register(name, cls) at
    module-import time (called from backends/__init__.py).  Lazy imports
    prevent circular dependencies.
    """

    _registry: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, backend_cls: type) -> None:
        """Register a backend implementation class.

        Args:
            name: Short identifier, e.g. "ezdxf" or "com".
            backend_cls: The implementation class (not an instance).
        """
        cls._registry[name] = backend_cls

    @classmethod
    def get(cls, backend_name: str | None = None) -> CADBackend:
        """Return a fresh backend instance for the requested name.

        Args:
            backend_name: "ezdxf" or "com".  If None, reads Settings().cad_backend.
        Returns:
            A new CADBackend-compliant instance.
        Raises:
            MCPError: BACKEND_UNAVAILABLE if the name is not registered.
        """
        if backend_name is None:
            try:
                from lcs_cad_mcp.settings import Settings
                backend_name = Settings().cad_backend
            except Exception:
                backend_name = "ezdxf"

        if backend_name not in cls._registry:
            from lcs_cad_mcp.errors import MCPError, ErrorCode
            raise MCPError(
                code=ErrorCode.BACKEND_UNAVAILABLE,
                message=f"Backend '{backend_name}' is not registered or not available on this platform.",
                recoverable=False,
                suggested_action="Use 'ezdxf' (cross-platform) or 'com' (Windows only).",
            )
        return cls._registry[backend_name]()
