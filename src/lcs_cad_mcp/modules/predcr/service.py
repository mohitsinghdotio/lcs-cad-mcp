"""PreDCR service — layer setup, spec queries, and drawing validation."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lcs_cad_mcp.session.context import DrawingSession

logger = logging.getLogger(__name__)


class PreDCRService:
    """Manages PreDCR layer setup and drawing validation against the layer catalog."""

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

    def create_layers(self, building_type: str) -> dict:
        """Create all required PreDCR layers for the given building type."""
        self._require_open()
        from lcs_cad_mcp.modules.predcr.layer_registry import get_layers_for_building_type
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        try:
            specs = get_layers_for_building_type(building_type)
        except ValueError as exc:
            raise MCPError(
                code=ErrorCode.LAYER_INVALID,
                message=str(exc),
                recoverable=True,
                suggested_action="Use 'residential', 'commercial', or 'industrial'.",
            )

        created = []
        skipped = []
        existing_layers = {l.name.upper() for l in self._session.backend.list_layers()}

        for spec in specs:
            if spec.name.upper() in existing_layers:
                skipped.append(spec.name)
                continue
            self._session.backend.create_layer(
                name=spec.name,
                color=spec.color_index,
                linetype=spec.linetype,
            )
            created.append(spec.name)

        return {
            "building_type": building_type,
            "created_count": len(created),
            "skipped_count": len(skipped),
            "created": created,
            "skipped": skipped,
        }

    def get_layer_spec(self, layer_name: str) -> dict:
        """Return the specification for a named PreDCR layer."""
        from lcs_cad_mcp.modules.predcr.layer_registry import get_layer_by_name
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        spec = get_layer_by_name(layer_name)
        if spec is None:
            raise MCPError(
                code=ErrorCode.LAYER_NOT_FOUND,
                message=f"No PreDCR layer spec found for '{layer_name}'.",
                recoverable=True,
                suggested_action="Use predcr_list_layer_specs to see available layers.",
            )
        return spec.model_dump()

    def list_layer_specs(self, building_type: str | None = None) -> list[dict]:
        """List all PreDCR layer specs, optionally filtered by building type."""
        from lcs_cad_mcp.modules.predcr.layer_registry import PREDCR_LAYERS, get_layers_for_building_type
        from lcs_cad_mcp.errors import MCPError, ErrorCode

        if building_type is not None:
            try:
                specs = get_layers_for_building_type(building_type)
            except ValueError as exc:
                raise MCPError(
                    code=ErrorCode.LAYER_INVALID,
                    message=str(exc),
                    recoverable=True,
                )
        else:
            specs = PREDCR_LAYERS
        return [s.model_dump() for s in specs]

    def run_setup(self, building_type: str) -> dict:
        """Run full PreDCR setup: create all required layers."""
        return self.create_layers(building_type)

    def validate_drawing(self, authority_code: str) -> dict:
        """Validate drawing layer structure against PreDCR requirements."""
        self._require_open()
        from lcs_cad_mcp.modules.predcr.layer_registry import PREDCR_LAYERS

        existing_layers = {l.name.upper() for l in self._session.backend.list_layers()}
        missing = []
        for spec in PREDCR_LAYERS:
            if spec.name.upper() not in existing_layers:
                missing.append(spec.name)

        # Check that all existing layers with PREDCR- prefix are valid
        invalid = []
        valid_names = {s.name.upper() for s in PREDCR_LAYERS}
        for layer_name in existing_layers:
            if layer_name.startswith("PREDCR-") and layer_name not in valid_names:
                invalid.append(layer_name)

        passed = len(missing) == 0 and len(invalid) == 0
        return {
            "passed": passed,
            "authority_code": authority_code,
            "missing_layers": missing,
            "invalid_layers": invalid,
            "checked_layers": len(existing_layers),
        }
