# Story 5.4: `entity_draw_text` and `entity_insert_block` MCP Tools

Status: ready-for-dev

## Story

As an **AI client**,
I want **to add text annotations and insert block references on PreDCR-compliant layers**,
so that **labels, dimensions, titles, and standard CAD block symbols (e.g., north arrows, scale bars, door/window blocks) are placed correctly per FR8 and FR9**.

## Acceptance Criteria

1. **AC1:** `entity_draw_text(position: tuple[float, float], text: str, layer: str, height: float = 2.5, style: str = "Standard")` MCP tool inserts MText (MTEXT entity type) on the specified layer and returns `{"success": true, "data": {"entity_id": "<handle>", "entity_type": "MTEXT", "layer": "<layer>"}}`
2. **AC2:** `entity_insert_block(name: str, position: tuple[float, float], layer: str, scale: float = 1.0, rotation: float = 0.0)` MCP tool inserts a block reference (INSERT entity type) and returns `{"success": true, "data": {"entity_id": "<handle>", "entity_type": "INSERT", "layer": "<layer>"}}`
3. **AC3:** Both tools validate layer existence before drawing; non-existent layer returns `LAYER_NOT_FOUND` error
4. **AC4:** `entity_draw_text` validates `text` is non-empty and `height > 0`; violations return `INVALID_PARAMS` error
5. **AC5:** `entity_insert_block` validates `scale > 0` and that the named block definition exists in the drawing's block table; if block definition is absent, returns `ENTITY_NOT_FOUND` error with message indicating the block name
6. **AC6:** Both tools execute against both `EzdxfBackend` and `COMBackend`
7. **AC7:** Both tools complete within 2 seconds (NFR1)
8. **AC8:** Both tools take a snapshot BEFORE mutating the drawing

## Tasks / Subtasks

- [ ] Task 1: Implement `EntityService.draw_text` and `EntityService.insert_block` in `service.py` (AC: 1, 2, 5, 6)
  - [ ] 1.1: Replace `draw_text` stub: call `self._backend.add_mtext(layer=layer, position=position, text=text, height=height, style=style)` — returns entity handle string
  - [ ] 1.2: Replace `insert_block` stub: call `self._backend.insert_block(layer=layer, block_name=name, position=position, scale=scale, rotation=rotation)` — returns entity handle string
  - [ ] 1.3: For `draw_text`, populate and return `TextEntityRecord` with `entity_id`, `entity_type=EntityType.MTEXT`, `layer`, `position`, `text_content`, `height`, `style`, and computed `bounding_box`
  - [ ] 1.4: For `insert_block`, populate and return `BlockRefEntityRecord` with `entity_id`, `entity_type=EntityType.INSERT`, `layer`, `block_name`, `position`, `scale`, `rotation`; `bounding_box` may be `None` for block references (block extents depend on block definition geometry)
  - [ ] 1.5: Add private `_compute_text_bbox(position, text, height) -> BoundingBox` helper — approximate bbox: `BoundingBox(min_x=x, min_y=y, max_x=x + len(text) * height * 0.6, max_y=y + height)` (rough estimation; exact bbox requires font metrics not available at this layer)
  - [ ] 1.6: Add `_block_exists(block_name: str) -> bool` helper using `self._backend.block_exists(block_name)`

- [ ] Task 2: Implement MCP tool handlers in `tools.py` following the 6-step pattern (AC: 1, 2, 3, 4, 5, 8)
  - [ ] 2.1: Add async `entity_draw_text(ctx, position, text, layer, height=2.5, style="Standard") -> dict`
  - [ ] 2.2: Add async `entity_insert_block(ctx, name, position, layer, scale=1.0, rotation=0.0) -> dict`
  - [ ] 2.3: Step 1 — Session: `session = ctx.get_state("drawing_session")`; `SESSION_NOT_STARTED` if None
  - [ ] 2.4: Step 2 (text) — Validate `text.strip()` is non-empty and `height > 0`; return `INVALID_PARAMS` for either violation
  - [ ] 2.5: Step 2 (block) — Validate `scale > 0`; return `INVALID_PARAMS` if not; check `session.backend.block_exists(name)`, return `ENTITY_NOT_FOUND` with `suggested_action="Check block definitions with cad_list_blocks"` if block absent
  - [ ] 2.6: Step 3 — Layer existence: `session.backend.layer_exists(layer)`; return `LAYER_NOT_FOUND` if False
  - [ ] 2.7: Step 4 — Snapshot: `snapshot_id = await session.snapshot.take()`
  - [ ] 2.8: Step 5 — Delegate to `EntityService(session).draw_text(...)` or `insert_block(...)`
  - [ ] 2.9: Step 6 — Append event_log entry; return structured response

- [ ] Task 3: Extend `CADBackend` Protocol and implement in backends (AC: 6)
  - [ ] 3.1: Add `add_mtext(layer: str, position: tuple[float, float], text: str, height: float, style: str) -> str` to Protocol
  - [ ] 3.2: Add `insert_block(layer: str, block_name: str, position: tuple[float, float], scale: float, rotation: float) -> str` to Protocol
  - [ ] 3.3: Add `block_exists(block_name: str) -> bool` to Protocol — checks the drawing's block table
  - [ ] 3.4: Implement `EzdxfBackend.add_mtext`: `msp.add_mtext(position, height, text, dxfattribs={"layer": layer, "style": style})`; handle ezdxf's `MText` API; return entity handle
  - [ ] 3.5: Implement `EzdxfBackend.insert_block`: `msp.add_blockref(block_name, position, dxfattribs={"layer": layer, "xscale": scale, "yscale": scale, "zscale": scale, "rotation": rotation})`; return entity handle
  - [ ] 3.6: Implement `EzdxfBackend.block_exists`: `return block_name in self._doc.blocks`
  - [ ] 3.7: Add `COMBackend` stubs for `add_mtext`, `insert_block`, `block_exists` raising `NotImplementedError("COM backend text/block: Story 5-4")`

- [ ] Task 4: Register new tools in `entities/__init__.py` (AC: 1, 2)
  - [ ] 4.1: Update `register(mcp)` to call `_register_text_block_tools(mcp)` from `tools.py`
  - [ ] 4.2: Verify that `entity_draw_text` and `entity_insert_block` appear correctly in MCP tool registry
  - [ ] 4.3: Ensure all previously registered entity tools (5-2, 5-3) are still registered

- [ ] Task 5: Write unit tests (AC: 1, 2, 3, 4, 5, 7, 8)
  - [ ] 5.1: Create `tests/unit/modules/entities/test_text_block_tools.py`
  - [ ] 5.2: Extend `MockCADBackend` to support `add_mtext`, `insert_block`, `block_exists`; `block_exists` returns True for a pre-configured set of test block names
  - [ ] 5.3: Test `entity_draw_text` happy path: valid position, text, layer, default height → returns `entity_id`, `MTEXT` type
  - [ ] 5.4: Test `entity_draw_text` with empty string `text=""` → `INVALID_PARAMS` error
  - [ ] 5.5: Test `entity_draw_text` with `height=0` → `INVALID_PARAMS` error
  - [ ] 5.6: Test `entity_draw_text` with `height=-1.0` → `INVALID_PARAMS` error
  - [ ] 5.7: Test `entity_insert_block` happy path: known block name, valid position, layer → returns `entity_id`, `INSERT` type
  - [ ] 5.8: Test `entity_insert_block` with unknown block name → `ENTITY_NOT_FOUND` error, no snapshot taken
  - [ ] 5.9: Test `entity_insert_block` with `scale=0` → `INVALID_PARAMS` error
  - [ ] 5.10: Test both tools with non-existent layer → `LAYER_NOT_FOUND`, no snapshot, no backend mutation
  - [ ] 5.11: Test snapshot is taken exactly once per successful call
  - [ ] 5.12: Test text bounding box approximation: position `(0,0)`, text `"Hello"` (5 chars), height `2.5` → bbox `min_x=0, min_y=0, max_x=7.5, max_y=2.5`

- [ ] Task 6: PreDCR-specific text validation rules (AC: 4)
  - [ ] 6.1: Document in `draw_text` tool docstring which layers are typical text annotation layers in PreDCR (e.g., `ANNO-TEXT`, `TITLE-TEXT`) — text tools do NOT enforce this; it is the AI client's responsibility to choose the correct layer
  - [ ] 6.2: Add a note in `draw_text` that `style` parameter defaults to `"Standard"` — if the drawing does not have this text style defined, ezdxf will use its fallback; do NOT raise an error for missing styles
  - [ ] 6.3: Verify via test that style name is passed through to backend without modification (no backend-level style validation in this story)

## Dev Notes

### Critical Architecture Constraints

1. **6-step handler pattern** — identical to Stories 5-2 and 5-3. Deviation from this pattern is an architecture violation.
2. **MText vs Text:** The architecture specifies entity type `MTEXT` (multi-line text) for the `entity_draw_text` tool. Do NOT use ezdxf's older single-line `TEXT` entity — always use `MTEXT` for forward compatibility and richer text support. The `TextEntityRecord` schema allows both `TEXT` and `MTEXT` via its Literal type, but the draw_text tool always creates MTEXT.
3. **Block definition must pre-exist:** `entity_insert_block` inserts a *reference* to an existing block definition. It does NOT create block definitions. The block definition must already exist in the drawing's block table (created outside this system, or via a future `cad_define_block` tool not in scope for Epic 5).
4. **Snapshot before mutation** — `session.snapshot.take()` must precede any backend call. The block_exists check (step 2) must occur before the snapshot (step 4) to avoid taking an unnecessary snapshot when the block is missing.
5. **No direct ezdxf in entities module** — `EzdxfBackend` handles all ezdxf-specific MText and BlockRef APIs.

### Module/Component Notes

**Tool parameter definitions for MCP clients:**

`entity_draw_text`:
- `position: tuple[float, float]` — `(x, y)` insertion point of the text
- `text: str` — text content; must be non-empty after stripping whitespace
- `layer: str` — target layer name (must exist)
- `height: float = 2.5` — text height in drawing units; must be > 0
- `style: str = "Standard"` — text style name (must exist in drawing; no validation performed)

`entity_insert_block`:
- `name: str` — name of the block definition to insert; must exist in block table
- `position: tuple[float, float]` — `(x, y)` insertion point
- `layer: str` — target layer name (must exist)
- `scale: float = 1.0` — uniform scale factor; must be > 0
- `rotation: float = 0.0` — rotation in degrees CCW from positive X axis

**Response schema:**
```python
# entity_draw_text
{
    "success": True,
    "data": {
        "entity_id": "4D9E",
        "entity_type": "MTEXT",
        "layer": "ANNO-TEXT",
        "position": [10.0, 20.0],
        "text_content": "Plot Area: 500 sqm",
        "height": 2.5,
        "bounding_box": {"min_x": 10.0, "min_y": 20.0, "max_x": 37.0, "max_y": 22.5}
    }
}

# entity_insert_block
{
    "success": True,
    "data": {
        "entity_id": "5E0F",
        "entity_type": "INSERT",
        "layer": "SYMBOL-LAYER",
        "block_name": "NORTH-ARROW",
        "position": [150.0, 200.0],
        "scale": 1.0,
        "rotation": 0.0,
        "bounding_box": None  # block extents not computed at this layer
    }
}
```

**EzdxfBackend MText implementation notes:**
```python
# ezdxf MText API (v1.x)
mtext = msp.add_mtext(
    text,
    dxfattribs={
        "layer": layer,
        "char_height": height,
        "style": style,
    }
)
mtext.set_location(position)
return mtext.dxf.handle
```

**EzdxfBackend block reference implementation notes:**
```python
# ezdxf block reference insertion
blockref = msp.add_blockref(
    block_name,
    insert=position,
    dxfattribs={
        "layer": layer,
        "xscale": scale,
        "yscale": scale,
        "zscale": scale,
        "rotation": rotation,
    }
)
return blockref.dxf.handle
```

### Project Structure Notes

Files modified by this story:
```
src/lcs_cad_mcp/
├── backends/
│   ├── base.py              # add_mtext, insert_block, block_exists to Protocol
│   ├── ezdxf_backend.py     # implement add_mtext, insert_block, block_exists
│   └── com_backend.py       # stub add_mtext, insert_block, block_exists
└── modules/entities/
    ├── __init__.py           # register() includes text/block tools
    ├── service.py            # draw_text, insert_block implemented
    └── tools.py              # entity_draw_text, entity_insert_block handlers

tests/unit/modules/entities/
└── test_text_block_tools.py  # new
```

### Dependencies

- **Story 5-2 (draw_polyline / draw_line):** Establishes the 6-step handler pattern, `layer_exists()`, session snapshot integration — all reused here
- **Story 5-1 (Entity Data Models):** `TextEntityRecord`, `BlockRefEntityRecord`, `EntityService` skeleton
- **Story 2-x (EzdxfBackend):** MText and block reference creation via ezdxf API

### References

- FR8 (text placement): [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Functional Requirements"]
- FR9 (block insertion): [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Functional Requirements"]
- Entity tool naming: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "MCP Tool Naming Conventions"]
- 6-step tool handler: [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]
- Story requirements: [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 5, Story 5-4]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/backends/base.py`
- `src/lcs_cad_mcp/backends/ezdxf_backend.py`
- `src/lcs_cad_mcp/backends/com_backend.py`
- `src/lcs_cad_mcp/modules/entities/__init__.py`
- `src/lcs_cad_mcp/modules/entities/service.py`
- `src/lcs_cad_mcp/modules/entities/tools.py`
- `tests/unit/modules/entities/test_text_block_tools.py`
