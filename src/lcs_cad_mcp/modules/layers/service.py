"""Layer management business logic — LayerRegistry and LayerService."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lcs_cad_mcp.backends.base import CADBackend
    from lcs_cad_mcp.session.context import DrawingSession

logger = logging.getLogger(__name__)


class LayerRegistry:
    """In-process cache of layer records, synced from the CAD backend.

    Keys are lower-cased names for case-insensitive lookup.
    """

    def __init__(self) -> None:
        self._layers: dict[str, dict] = {}

    def sync_from_backend(self, backend: CADBackend) -> None:
        """Populate registry from the live backend.  Clears existing data."""
        self._layers.clear()
        for layer_info in backend.list_layers():
            key = layer_info.name.lower()
            self._layers[key] = layer_info.model_dump()

    def get(self, name: str) -> dict | None:
        return self._layers.get(name.lower())

    def all(self) -> list[dict]:
        return sorted(self._layers.values(), key=lambda l: l["name"])

    def contains(self, name: str) -> bool:
        return name.lower() in self._layers

    def add(self, layer_dict: dict) -> None:
        key = layer_dict["name"].lower()
        self._layers[key] = layer_dict

    def remove(self, name: str) -> None:
        key = name.lower()
        if key not in self._layers:
            raise KeyError(f"Layer '{name}' not in registry")
        del self._layers[key]

    def count(self) -> int:
        return len(self._layers)

    def __repr__(self) -> str:
        return f"LayerRegistry({list(self._layers.keys())})"


class LayerService:
    """Implements layer CRUD operations for the layers module."""

    def __init__(self, session: DrawingSession) -> None:
        self._session = session
        self.registry = LayerRegistry()

    def ensure_synced(self) -> None:
        """Sync registry from backend if a drawing is open."""
        if self._session.backend is not None and self._session.is_drawing_open:
            self.registry.sync_from_backend(self._session.backend)

    def create_layer(self, name: str, color: int = 7, linetype: str = "CONTINUOUS") -> dict:
        """Create a new layer in the active drawing."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        self._require_open()
        try:
            layer_info = self._session.backend.create_layer(name, color=color, linetype=linetype)
        except MCPError:
            raise
        record = layer_info.model_dump()
        self.registry.add(record)
        return record

    def delete_layer(self, name: str, force: bool = False) -> bool:
        """Delete a layer from the drawing."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        self._require_open()
        self._session.backend.delete_layer(name)
        if self.registry.contains(name):
            self.registry.remove(name)
        return True

    def list_layers(self) -> list[dict]:
        """Return all layers in the drawing."""
        self._require_open()
        self.ensure_synced()
        return self.registry.all()

    def get_layer(self, name: str) -> dict:
        """Return a single layer's properties."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        self._require_open()
        layer_info = self._session.backend.get_layer(name)
        return layer_info.model_dump()

    def set_layer_properties(self, name: str, **props) -> dict:
        """Update one or more layer properties."""
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        self._require_open()
        # Retrieve current state
        layer_info = self._session.backend.get_layer(name)
        current = layer_info.model_dump()
        # Apply only non-None props
        updated = {**current, **{k: v for k, v in props.items() if v is not None}}
        # Re-create the layer with updated props (delete and recreate if name unchanged)
        # For now, use create_layer with new properties (backend-specific)
        # Note: In a real implementation, this would use backend.set_layer_properties()
        # For the ezdxf backend, we update directly
        backend = self._session.backend
        if hasattr(backend, "_doc") and backend._doc is not None:
            layer = backend._doc.layers.get(name)
            if layer is not None:
                if "color" in props and props["color"] is not None:
                    layer.color = props["color"]
                if "linetype" in props and props["linetype"] is not None:
                    layer.linetype = props["linetype"]
                if "is_on" in props and props["is_on"] is not None:
                    if props["is_on"]:
                        layer.on()
                    else:
                        layer.off()
                if "is_frozen" in props and props["is_frozen"] is not None:
                    if props["is_frozen"]:
                        layer.freeze()
                    else:
                        layer.thaw()
        # Return updated record
        return updated

    def _require_open(self) -> None:
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if not self._session.is_drawing_open:
            raise MCPError(
                code=ErrorCode.SESSION_DRAWING_NOT_OPEN,
                message="No drawing is open. Open or create a drawing first.",
                recoverable=True,
                suggested_action="Call cad_open_drawing or cad_new_drawing first.",
            )
