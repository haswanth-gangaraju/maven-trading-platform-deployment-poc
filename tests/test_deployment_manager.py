"""Tests for Kubernetes Deployment Manager."""

import pytest
from src.deployment_manager import DeploymentManager


@pytest.fixture
def manager():
    return DeploymentManager()


def test_deploy_service(manager):
    dep = manager.deploy(
        "order-service", "trading/order-svc:1.0.0",
        replicas=3, strategy="rolling",
    )
    assert dep["name"] == "order-service"
    assert dep["image"] == "trading/order-svc:1.0.0"
    assert dep["replicas"] == 3
    assert dep["status"] == "RUNNING"
    assert dep["version"] == 1


def test_deploy_duplicate_raises(manager):
    manager.deploy("dup", "img:1.0")
    with pytest.raises(ValueError, match="already exists"):
        manager.deploy("dup", "img:2.0")


def test_deploy_invalid_strategy_raises(manager):
    with pytest.raises(ValueError, match="Invalid strategy"):
        manager.deploy("bad", "img:1.0", strategy="yolo")


def test_update_deployment(manager):
    manager.deploy("svc", "img:1.0")
    updated = manager.update_deployment("svc", "img:2.0", replicas=5)
    assert updated["image"] == "img:2.0"
    assert updated["replicas"] == 5
    assert updated["version"] == 2


def test_rollback_to_previous(manager):
    manager.deploy("svc", "img:1.0")
    manager.update_deployment("svc", "img:2.0")
    result = manager.rollback("svc")
    assert result["rolled_back_to_image"] == "img:1.0"
    assert result["new_version"] == 3


def test_rollback_to_specific_version(manager):
    manager.deploy("svc", "img:1.0")
    manager.update_deployment("svc", "img:2.0")
    manager.update_deployment("svc", "img:3.0")
    result = manager.rollback("svc", target_version=1)
    assert result["rolled_back_to_image"] == "img:1.0"


def test_rollback_no_history_raises(manager):
    manager.deploy("fresh", "img:1.0")
    with pytest.raises(ValueError, match="No previous versions"):
        manager.rollback("fresh")


def test_canary_release(manager):
    manager.deploy("svc", "img:1.0")
    canary = manager.canary_release("svc", "img:2.0", canary_percent=20)
    assert canary["stable_image"] == "img:1.0"
    assert canary["canary_image"] == "img:2.0"
    assert canary["canary_percent"] == 20
    assert canary["stable_percent"] == 80


def test_canary_invalid_percent_raises(manager):
    manager.deploy("svc", "img:1.0")
    with pytest.raises(ValueError, match="canary_percent"):
        manager.canary_release("svc", "img:2.0", canary_percent=75)


def test_blue_green_switch(manager):
    manager.deploy("svc", "img:1.0")
    result = manager.blue_green_switch("svc", "img:2.0")
    assert result["blue_image"] == "img:1.0"
    assert result["green_image"] == "img:2.0"
    assert result["active"] == "green"


def test_list_deployments(manager):
    manager.deploy("a", "img:1.0")
    manager.deploy("b", "img:2.0")
    deps = manager.list_deployments()
    assert len(deps) == 2
    names = {d["name"] for d in deps}
    assert names == {"a", "b"}


def test_delete_deployment(manager):
    manager.deploy("temp", "img:1.0")
    result = manager.delete_deployment("temp")
    assert result["deleted"] == "temp"
    assert manager.list_deployments() == []
