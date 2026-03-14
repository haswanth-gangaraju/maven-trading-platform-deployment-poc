"""Tests for Trading System Health Monitor."""

import pytest
from src.health_monitor import HealthMonitor


@pytest.fixture
def monitor():
    return HealthMonitor()


def test_register_service(monitor):
    svc = monitor.register_service(
        "order-gateway", "http://order-gw:8080/health", critical=True
    )
    assert svc["name"] == "order-gateway"
    assert svc["critical"] is True
    assert svc["status"] == "unknown"


def test_register_duplicate_raises(monitor):
    monitor.register_service("dup", "/health")
    with pytest.raises(ValueError, match="already registered"):
        monitor.register_service("dup", "/health")


def test_health_check_healthy(monitor):
    monitor.register_service("svc", "/health")
    result = monitor.health_check("svc", is_healthy=True)
    assert result["status"] == "healthy"
    assert result["consecutive_failures"] == 0
    assert result["circuit_breaker"] == "closed"


def test_health_check_degraded(monitor):
    monitor.register_service("svc", "/health")
    monitor.health_check("svc", is_healthy=False)
    result = monitor.health_check("svc", is_healthy=False)
    assert result["status"] == "degraded"
    assert result["consecutive_failures"] == 2


def test_health_check_unhealthy_opens_circuit_breaker(monitor):
    monitor.register_service("svc", "/health")
    for _ in range(3):
        result = monitor.health_check("svc", is_healthy=False)
    assert result["status"] == "unhealthy"
    assert result["circuit_breaker"] == "open"


def test_circuit_breaker_reset(monitor):
    monitor.register_service("svc", "/health")
    for _ in range(3):
        monitor.health_check("svc", is_healthy=False)
    result = monitor.reset_circuit_breaker("svc")
    assert result["old_state"] == "open"
    assert result["new_state"] == "half-open"


def test_circuit_breaker_closes_after_healthy(monitor):
    monitor.register_service("svc", "/health")
    for _ in range(3):
        monitor.health_check("svc", is_healthy=False)
    monitor.reset_circuit_breaker("svc")
    result = monitor.health_check("svc", is_healthy=True)
    assert result["circuit_breaker"] == "closed"


def test_dependency_graph(monitor):
    monitor.register_service("db", "/health", critical=True)
    monitor.register_service("api", "/health", dependencies=["db"])
    monitor.health_check("db", is_healthy=True)
    graph = monitor.get_dependency_graph("api")
    assert graph["dependency_count"] == 1
    assert graph["dependencies"][0]["name"] == "db"
    assert graph["dependencies"][0]["status"] == "healthy"


def test_system_status_all_healthy(monitor):
    monitor.register_service("a", "/health")
    monitor.register_service("b", "/health")
    monitor.health_check("a", is_healthy=True)
    monitor.health_check("b", is_healthy=True)
    status = monitor.get_system_status()
    assert status["overall"] == "healthy"


def test_system_status_critical_unhealthy(monitor):
    monitor.register_service("critical-svc", "/health", critical=True)
    monitor.health_check("critical-svc", is_healthy=True)
    for _ in range(3):
        monitor.health_check("critical-svc", is_healthy=False)
    status = monitor.get_system_status()
    assert status["overall"] == "critical"


def test_list_services(monitor):
    monitor.register_service("a", "/health")
    monitor.register_service("b", "/health", critical=True)
    services = monitor.list_services()
    assert len(services) == 2
