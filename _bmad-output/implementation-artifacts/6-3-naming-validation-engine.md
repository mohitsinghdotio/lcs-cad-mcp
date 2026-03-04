# Story 6.3: Naming Validation Engine

Status: ready-for-dev

## Story

As a **developer**,
I want **a naming validation engine that checks entity names against PreDCR conventions**,
so that **named entities conform to authority naming requirements and are flagged before scrutiny (FR15)**.

## Acceptance Criteria

1. **AC1:** `VerificationService.check_naming()` inspects all named entities in the active drawing — specifically TEXT, MTEXT, and ATTRIB entities — and validates each name against the PreDCR naming rules defined in `layer_registry.py`.
2. **AC2:** Returns `list[VerificationFailure]` where each failure carries `entity_id`, `failure_type="NAMING"`, `layer`, `description` (current name + specific rule violated), and `suggested_correction` (the correctly formatted name).
3. **AC3:** Uses the same naming rule catalog as `layer_validate_naming` (Story 3-4) — the `LayerValidator` class from the layers module — to avoid duplicating rule definitions.
4. **AC4:** Zero false positives on correctly named entities (NFR14) — entities whose names conform to all PreDCR naming conventions return no failures.
5. **AC5:** The `verify_naming` MCP tool wraps `check_naming()`, follows the 6-step handler pattern (session → validate → NO snapshot → service call → event_log → return), and returns `passed: bool` and `failures: list`.
6. **AC6:** Unit tests cover: correct name passes, wrong prefix fails with suggested correction, empty name fails, name on wrong layer fails, and Hypothesis property-based test on valid names.

## Tasks / Subtasks

- [ ] Task 1: Extend `schemas.py` with naming result type (AC: 2)
  - [ ] 1.1: Add `NamingCheckResult` Pydantic model with fields: `passed: bool`, `failures: list[VerificationFailure]`, `checked_entity_count: int`
  - [ ] 1.2: Export `NamingCheckResult` from `schemas.py`
  - [ ] 1.3: Confirm `VerificationFailure.failure_type` literal already includes `"NAMING"` — no schema change needed for the failure model itself

- [ ] Task 2: Understand and reuse the `LayerValidator` naming interface from Story 3-4 (AC: 3)
  - [ ] 2.1: Review `src/lcs_cad_mcp/modules/layers/` for `LayerValidator` class — specifically its `validate_entity_name(name: str, layer: str) -> tuple[bool, str | None]` method signature (adapt if the actual method name differs)
  - [ ] 2.2: Review `src/lcs_cad_mcp/modules/predcr/layer_registry.py` for naming convention definitions — identify the data structure (e.g., `LayerDefinition.naming_pattern: str | re.Pattern`) used to express valid names
  - [ ] 2.3: Document the `LayerValidator` interface contract in a comment at the top of `service.py` (import path, method signature, return semantics) so the naming check is self-documenting
  - [ ] 2.4: If `LayerValidator` does not yet exist (Story 3-4 not complete), create a stub interface in `VerificationService` with a `TODO` comment linking to Story 3-4 — do NOT duplicate the naming rules

- [ ] Task 3: Implement `VerificationService.check_naming()` in `service.py` (AC: 1, 2, 3, 4)
  - [ ] 3.1: Retrieve all named entities: call `EntityService.list_entities(entity_type="TEXT")`, `EntityService.list_entities(entity_type="MTEXT")`, and `EntityService.list_entities(entity_type="ATTRIB")` — concatenate results
  - [ ] 3.2: For each entity, extract `entity.name` (or `entity.text` depending on EntityService schema) and `entity.layer`
  - [ ] 3.3: Instantiate `LayerValidator()` (from `src/lcs_cad_mcp/modules/layers/`) and call `validator.validate_entity_name(name=entity.name, layer=entity.layer)` — this returns `(is_valid: bool, suggested_name: str | None)`
  - [ ] 3.4: If `not is_valid`, construct `VerificationFailure(entity_id=entity.handle, failure_type="NAMING", layer=entity.layer, description=f"Name '{entity.name}' violates PreDCR naming convention for layer '{entity.layer}'", suggested_correction=f"Rename to '{suggested_name}'" if suggested_name else "Refer to PreDCR naming guide")`
  - [ ] 3.5: Also check for entities with empty or whitespace-only names — always a naming failure: `description="Entity has no name"`, `suggested_correction="Assign a name conforming to PreDCR conventions for layer '{entity.layer}'"`
  - [ ] 3.6: Return `failures` list

- [ ] Task 4: Implement `verify_naming` MCP tool handler in `tools.py` (AC: 5)
  - [ ] 4.1: Define `@mcp.tool()` decorated async function `verify_naming(ctx: Context) -> dict`
  - [ ] 4.2: Step 1 — retrieve session: `session = ctx.get_state("drawing_session")`; if missing, return `MCPError(SESSION_NOT_STARTED).to_response()`
  - [ ] 4.3: Step 2 — validate: confirm active session; no additional input parameters for this tool
  - [ ] 4.4: Step 3 — NO snapshot (read-only tool)
  - [ ] 4.5: Step 4 — call `VerificationService(session).check_naming()`; collect `failures`
  - [ ] 4.6: Step 5 — append to event log: `{"tool": "verify_naming", "failure_count": len(failures)}`
  - [ ] 4.7: Step 6 — return `{"success": True, "data": {"passed": len(failures) == 0, "failures": [f.model_dump() for f in failures], "checked_entity_count": <total entities checked>}}`

- [ ] Task 5: Register `verify_naming` tool and update `__init__.py` (AC: 5)
  - [ ] 5.1: Add `verify_naming` to the `register(mcp)` call chain in `tools.py`
  - [ ] 5.2: Confirm `modules/verification/__init__.py` `register()` function picks up `verify_closure`, `verify_containment`, and `verify_naming`

- [ ] Task 6: Write unit tests for naming validation (AC: 4, 6)
  - [ ] 6.1: Create `tests/unit/modules/verification/test_naming.py`
  - [ ] 6.2: Build `MockCADBackend` fixture providing: TEXT entity with a valid PreDCR-conforming name on correct layer, TEXT entity with wrong prefix, MTEXT entity with empty name string, ATTRIB entity with valid name
  - [ ] 6.3: Test `check_naming()` returns zero failures for valid-named entities
  - [ ] 6.4: Test `check_naming()` returns one failure per invalid entity with correct `suggested_correction` populated
  - [ ] 6.5: Test empty name triggers failure with appropriate description
  - [ ] 6.6: Write Hypothesis property-based test: generate entity names that conform to naming regex → `check_naming()` always returns zero failures (NFR14 property)
  - [ ] 6.7: Mock `LayerValidator` to control naming rule output independently of Story 3-4 implementation state

- [ ] Task 7: Handle naming rule edge cases (AC: 1, 4)
  - [ ] 7.1: Entities on layers with no defined naming rule in `layer_registry.py` — skip naming validation for those entities (do NOT treat absence of a rule as a failure)
  - [ ] 7.2: Handle case sensitivity in naming rules — PreDCR conventions may require uppercase layer codes; ensure the validator comparison is case-aware per layer definition
  - [ ] 7.3: Entities with names containing only numeric characters — evaluate against naming pattern; do not assume numeric-only names are valid or invalid without checking the layer rule

## Dev Notes

### Critical Architecture Constraints

1. **READ-ONLY tool — no snapshot.** `verify_naming` never mutates drawing state. Skip Step 3 (snapshot) of the 6-step handler pattern entirely.
2. **Do NOT duplicate naming rules.** The naming rule catalog lives exclusively in `layer_registry.py` (owned by Story 4-1) and is consumed via `LayerValidator` (owned by Story 3-4). `VerificationService.check_naming()` is a consumer of those rules — it never defines its own naming patterns.
3. **VerificationService calls LayerValidator as plain Python** — never call `layer_validate_naming` as an MCP tool from within the service. Instantiate `LayerValidator()` directly.
4. **`suggested_correction` must be a concrete, actionable string** — if `LayerValidator` returns a suggested name, format it as `f"Rename to '{suggested_name}'"`. If no suggestion is available, provide guidance pointing to the PreDCR naming guide.

### Module/Component Notes

**`service.py` — check_naming() skeleton:**

```python
from lcs_cad_mcp.modules.layers.service import LayerValidator  # adjust import if needed


def check_naming(self) -> list[VerificationFailure]:
    failures: list[VerificationFailure] = []
    validator = LayerValidator()

    entity_types = ["TEXT", "MTEXT", "ATTRIB"]
    all_entities = []
    for etype in entity_types:
        all_entities.extend(self._entity_svc.list_entities(entity_type=etype))

    for entity in all_entities:
        name = getattr(entity, "name", None) or getattr(entity, "text", None) or ""
        name = name.strip()

        if not name:
            failures.append(VerificationFailure(
                entity_id=entity.handle,
                failure_type="NAMING",
                layer=entity.layer,
                description=f"Entity on layer '{entity.layer}' has no name or an empty name",
                suggested_correction=f"Assign a name conforming to PreDCR conventions for layer '{entity.layer}'",
            ))
            continue

        is_valid, suggested = validator.validate_entity_name(name=name, layer=entity.layer)
        if not is_valid:
            correction = f"Rename to '{suggested}'" if suggested else "Refer to PreDCR naming guide"
            failures.append(VerificationFailure(
                entity_id=entity.handle,
                failure_type="NAMING",
                layer=entity.layer,
                description=f"Name '{name}' violates PreDCR naming convention for layer '{entity.layer}'",
                suggested_correction=correction,
            ))

    return failures
```

**NamingCheckResult schema addition to `schemas.py`:**

```python
class NamingCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    failures: list[VerificationFailure]
    checked_entity_count: int
```

**`LayerValidator` expected interface (from Story 3-4):**

```python
# Expected signature — confirm with Story 3-4 implementation
class LayerValidator:
    def validate_entity_name(
        self,
        name: str,
        layer: str,
    ) -> tuple[bool, str | None]:
        """
        Returns (is_valid, suggested_name).
        suggested_name is None if no suggestion is available.
        If the layer has no naming rule, returns (True, None) — skip validation.
        """
        ...
```

### Project Structure Notes

Files modified or created for this story:

```
src/lcs_cad_mcp/modules/verification/
├── __init__.py       # updated: register() includes verify_naming
├── schemas.py        # updated: add NamingCheckResult
├── service.py        # updated: add check_naming()
└── tools.py          # updated: add verify_naming handler

tests/unit/modules/verification/
├── __init__.py       # already exists from Story 6-1
└── test_naming.py    # NEW
```

### Dependencies

- **Story 6-1** (`VerificationFailure` model in `schemas.py`; `VerificationService` class skeleton in `service.py`)
- **Story 3-4** (Layer naming validation — `LayerValidator` class with `validate_entity_name()` method; must be complete and importable)
- **Story 4-1** (PreDCR layer catalog — `layer_registry.py` must contain `naming_pattern` or equivalent field per layer definition)
- **Story 5-6** (Entity listing — `EntityService.list_entities(entity_type=...)` must support TEXT, MTEXT, ATTRIB entity types)
- **Story 2-1** (CAD Backend — `DrawingSession` accessible via `ctx.get_state()`)

### References

- FR15: Naming check requirement — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 6, Story 6-3]
- NFR14: Zero false positives — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 6 NFR coverage]
- LayerValidator interface — [Source: `_bmad-output/planning-artifacts/epics-and-stories.md` — Epic 3, Story 3-4]
- layer_registry.py naming conventions — [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Layer Registry"]
- 6-step tool handler pattern — [Source: `_bmad-output/planning-artifacts/architecture.md` — Section "Tool Handler Pattern"]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None — story not yet implemented_

### Completion Notes List

_None — story not yet implemented_

### File List

_Files to be populated by dev agent after implementation:_

- `src/lcs_cad_mcp/modules/verification/__init__.py`
- `src/lcs_cad_mcp/modules/verification/schemas.py`
- `src/lcs_cad_mcp/modules/verification/service.py`
- `src/lcs_cad_mcp/modules/verification/tools.py`
- `tests/unit/modules/verification/test_naming.py`
