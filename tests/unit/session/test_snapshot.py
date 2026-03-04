"""Unit tests for SnapshotManager."""
import hashlib
import io
import pytest
import ezdxf
from lcs_cad_mcp.backends.ezdxf_backend import EzdxfBackend
from lcs_cad_mcp.session.snapshot import SnapshotManager
from lcs_cad_mcp.errors import MCPError, ErrorCode


@pytest.fixture
def backend_with_drawing():
    """EzdxfBackend with a fresh empty drawing open."""
    backend = EzdxfBackend()
    backend.new_drawing()
    return backend


@pytest.fixture
def mgr(backend_with_drawing):
    return SnapshotManager(backend=backend_with_drawing)


def test_take_returns_non_empty_id(mgr):
    cid = mgr.take()
    assert cid
    assert len(cid) == 36  # UUID format


def test_two_takes_return_distinct_ids(mgr):
    a = mgr.take()
    b = mgr.take()
    assert a != b


def test_latest_checkpoint_tracks_most_recent(mgr):
    a = mgr.take()
    b = mgr.take()
    assert mgr.latest_checkpoint == b


def test_restore_invalid_id_raises(mgr):
    mgr.take()
    with pytest.raises(MCPError) as exc_info:
        mgr.restore("nonexistent-id-xyz")
    assert exc_info.value.code == ErrorCode.SNAPSHOT_NOT_FOUND


def test_take_restore_removes_added_entity(backend_with_drawing, mgr):
    """Take snapshot, add entity, restore — entity should be gone."""
    cid = mgr.take()
    backend_with_drawing.create_layer("test_layer")
    backend_with_drawing.draw_line((0, 0), (10, 0), layer="test_layer")
    assert backend_with_drawing.get_drawing_metadata().entity_count == 1
    mgr.restore(cid)
    assert backend_with_drawing.get_drawing_metadata().entity_count == 0


def test_restore_functionally_identical_to_snapshot(backend_with_drawing, mgr):
    """After restore, drawing has same layer count as before mutation."""
    layers_before = len(backend_with_drawing.list_layers())
    cid = mgr.take()
    backend_with_drawing.create_layer("tmp_mutated_layer")
    assert len(backend_with_drawing.list_layers()) > layers_before
    mgr.restore(cid)
    assert len(backend_with_drawing.list_layers()) == layers_before


def test_restore_latest_no_snapshot_does_not_raise(mgr):
    """restore_latest with no prior take should log WARNING but not raise."""
    mgr.restore_latest()  # should not raise


def test_clear_specific_checkpoint(mgr):
    a = mgr.take()
    b = mgr.take()
    mgr.clear(a)
    with pytest.raises(MCPError):
        mgr.restore(a)
    # b still accessible
    mgr.restore(b)


def test_clear_all(mgr):
    a = mgr.take()
    b = mgr.take()
    mgr.clear()
    with pytest.raises(MCPError):
        mgr.restore(a)
    assert mgr.latest_checkpoint is None


def test_rollback_then_tool_call_succeeds(backend_with_drawing, mgr):
    """After rollback, backend is still usable."""
    cid = mgr.take()
    backend_with_drawing.create_layer("temp_layer")
    mgr.restore(cid)
    # Should be able to create layer again after rollback
    layer = backend_with_drawing.create_layer("temp_layer")
    assert layer.name == "temp_layer"
