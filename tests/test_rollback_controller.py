"""Tests for Automated Rollback Controller."""

import pytest
from src.rollback_controller import RollbackController


@pytest.fixture
def controller():
    return RollbackController()


def test_register_service(controller):
    result = controller.register_service(
        "order-engine", {"version": "1.0", "replicas": 3, "memory": "4Gi"}
    )
    assert result["registered"] == "order-engine"
    assert "version" in result["config_keys"]


def test_register_duplicate_raises(controller):
    controller.register_service("dup", {"v": "1.0"})
    with pytest.raises(ValueError, match="already registered"):
        controller.register_service("dup", {"v": "2.0"})


def test_snapshot_and_rollback(controller):
    controller.register_service("svc", {"version": "1.0", "replicas": 2})
    snap = controller.snapshot_state("svc", label="pre-deploy")
    assert snap["service"] == "svc"

    # Change state
    controller.update_state("svc", {"version": "2.0", "replicas": 5})
    current = controller.get_current_state("svc")
    assert current["version"] == "2.0"

    # Rollback
    result = controller.rollback_to_snapshot(snap["snapshot_id"])
    assert result["snapshot_label"] == "pre-deploy"

    restored = controller.get_current_state("svc")
    assert restored["version"] == "1.0"
    assert restored["replicas"] == 2


def test_rollback_not_found_raises(controller):
    with pytest.raises(KeyError, match="not found"):
        controller.rollback_to_snapshot("snap-nonexistent")


def test_validate_rollback_passes(controller):
    controller.register_service("svc", {"a": 1, "b": 2, "c": 3})
    result = controller.validate_rollback("svc", expected_keys=["a", "b", "c"])
    assert result["valid"] is True
    assert result["missing_keys"] == []


def test_validate_rollback_fails_missing_keys(controller):
    controller.register_service("svc", {"a": 1})
    result = controller.validate_rollback("svc", expected_keys=["a", "b"])
    assert result["valid"] is False
    assert "b" in result["missing_keys"]


def test_audit_log(controller):
    controller.register_service("svc", {"v": "1.0"})
    controller.snapshot_state("svc")
    controller.update_state("svc", {"v": "2.0"})
    log = controller.get_audit_log(service_name="svc")
    assert len(log) == 3  # REGISTER + SNAPSHOT + UPDATE
    events = [e["event"] for e in log]
    assert "REGISTER" in events
    assert "SNAPSHOT" in events
    assert "UPDATE" in events


def test_list_snapshots(controller):
    controller.register_service("svc", {"v": "1.0"})
    controller.snapshot_state("svc", label="s1")
    controller.snapshot_state("svc", label="s2")
    snaps = controller.list_snapshots(service_name="svc")
    assert len(snaps) == 2
    labels = {s["label"] for s in snaps}
    assert labels == {"s1", "s2"}
