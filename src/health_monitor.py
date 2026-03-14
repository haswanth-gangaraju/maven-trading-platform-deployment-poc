"""
Trading System Health Monitor.

Monitors service health, manages circuit breakers, and tracks service
dependency graphs for a low-latency trading platform.
"""

from datetime import datetime, timezone


class HealthMonitor:
    """Monitors health of trading platform services."""

    VALID_STATUSES = {"healthy", "degraded", "unhealthy", "unknown"}

    def __init__(self):
        self._services = {}       # service_name -> service info
        self._circuit_breakers = {}  # service_name -> circuit breaker state
        self._dependencies = {}   # service_name -> list of dependency names

    def register_service(
        self,
        name: str,
        endpoint: str,
        critical: bool = False,
        dependencies: list | None = None,
    ) -> dict:
        """Register a service for health monitoring.

        Args:
            name: Unique service name.
            endpoint: Health check endpoint URL.
            critical: Whether the service is critical to trading operations.
            dependencies: List of service names this service depends on.

        Returns:
            Service registration dict.

        Raises:
            ValueError: If the service is already registered.
        """
        if name in self._services:
            raise ValueError(f"Service '{name}' already registered")

        service = {
            "name": name,
            "endpoint": endpoint,
            "critical": critical,
            "status": "unknown",
            "last_check": None,
            "consecutive_failures": 0,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        self._services[name] = service
        self._dependencies[name] = dependencies or []
        self._circuit_breakers[name] = {
            "state": "closed",  # closed = normal, open = blocked, half-open = testing
            "failure_threshold": 3,
            "failures": 0,
        }
        return service

    def health_check(self, name: str, is_healthy: bool = True) -> dict:
        """Record a health check result for a service.

        Args:
            name: Service name.
            is_healthy: Whether the check passed.

        Returns:
            Updated service status dict.

        Raises:
            KeyError: If the service is not registered.
        """
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")

        service = self._services[name]
        service["last_check"] = datetime.now(timezone.utc).isoformat()

        if is_healthy:
            service["status"] = "healthy"
            service["consecutive_failures"] = 0
            self._circuit_breakers[name]["failures"] = 0
            if self._circuit_breakers[name]["state"] == "half-open":
                self._circuit_breakers[name]["state"] = "closed"
        else:
            service["consecutive_failures"] += 1
            cb = self._circuit_breakers[name]
            cb["failures"] += 1

            if service["consecutive_failures"] >= 3:
                service["status"] = "unhealthy"
            else:
                service["status"] = "degraded"

            if cb["failures"] >= cb["failure_threshold"]:
                cb["state"] = "open"

        return {
            "name": name,
            "status": service["status"],
            "consecutive_failures": service["consecutive_failures"],
            "circuit_breaker": self._circuit_breakers[name]["state"],
        }

    def get_circuit_breaker_state(self, name: str) -> dict:
        """Get the circuit breaker state for a service.

        Raises:
            KeyError: If the service is not registered.
        """
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")

        cb = self._circuit_breakers[name]
        return {
            "service": name,
            "state": cb["state"],
            "failures": cb["failures"],
            "threshold": cb["failure_threshold"],
        }

    def reset_circuit_breaker(self, name: str) -> dict:
        """Reset the circuit breaker to half-open for testing.

        Raises:
            KeyError: If the service is not registered.
        """
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")

        cb = self._circuit_breakers[name]
        old_state = cb["state"]
        cb["state"] = "half-open"
        cb["failures"] = 0
        return {
            "service": name,
            "old_state": old_state,
            "new_state": "half-open",
        }

    def get_dependency_graph(self, name: str) -> dict:
        """Get the dependency graph for a service.

        Returns:
            Dict with direct dependencies and their statuses.

        Raises:
            KeyError: If the service is not registered.
        """
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered")

        deps = self._dependencies.get(name, [])
        dep_statuses = []
        for dep in deps:
            if dep in self._services:
                dep_statuses.append({
                    "name": dep,
                    "status": self._services[dep]["status"],
                    "critical": self._services[dep]["critical"],
                })
            else:
                dep_statuses.append({
                    "name": dep,
                    "status": "unregistered",
                    "critical": False,
                })

        return {
            "service": name,
            "dependencies": dep_statuses,
            "dependency_count": len(deps),
        }

    def get_system_status(self) -> dict:
        """Get overall system health status.

        Returns:
            Dict with overall status and per-service summaries.
        """
        services = []
        all_healthy = True
        critical_healthy = True

        for svc in self._services.values():
            healthy = svc["status"] == "healthy"
            services.append({
                "name": svc["name"],
                "status": svc["status"],
                "critical": svc["critical"],
            })
            if not healthy:
                all_healthy = False
                if svc["critical"]:
                    critical_healthy = False

        if all_healthy:
            overall = "healthy"
        elif critical_healthy:
            overall = "degraded"
        else:
            overall = "critical"

        return {
            "overall": overall,
            "service_count": len(services),
            "services": services,
        }

    def list_services(self) -> list:
        """List all registered services."""
        return [
            {
                "name": s["name"],
                "status": s["status"],
                "critical": s["critical"],
            }
            for s in self._services.values()
        ]
