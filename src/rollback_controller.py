"""
Automated Rollback Controller.

Manages state snapshots, rollback operations, validation checks, and
audit logging for safe deployment changes in a trading platform.
"""

import uuid
from copy import deepcopy
from datetime import datetime, timezone


class RollbackController:
    """Controls automated rollback operations with state snapshotting and audit logs."""

    def __init__(self):
        self._snapshots = {}     # snapshot_id -> snapshot data
        self._current_state = {} # service_name -> current config
        self._audit_log = []     # list of audit entries

    def register_service(self, name: str, config: dict) -> dict:
        """Register a service with its current configuration.

        Args:
            name: Service name.
            config: Current configuration dict.

        Returns:
            Registration confirmation.

        Raises:
            ValueError: If the service is already registered.
        """
        if name in self._current_state:
            raise ValueError(f"Service '{name}' already registered")

        self._current_state[name] = deepcopy(config)
        self._log_event("REGISTER", name, detail=f"Registered with config keys: {list(config.keys())}")
        return {"registered": name, "config_keys": list(config.keys())}

    def snapshot_state(self, name: str, label: str = "") -> dict:
        """Take a snapshot of a service's current state.

        Args:
            name: Service name.
            label: Optional human-readable label for the snapshot.

        Returns:
            Snapshot metadata dict.

        Raises:
            KeyError: If the service is not registered.
        """
        if name not in self._current_state:
            raise KeyError(f"Service '{name}' not registered")

        snapshot_id = f"snap-{str(uuid.uuid4())[:8]}"
        snapshot = {
            "id": snapshot_id,
            "service": name,
            "label": label,
            "state": deepcopy(self._current_state[name]),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._snapshots[snapshot_id] = snapshot
        self._log_event("SNAPSHOT", name, detail=f"Created snapshot {snapshot_id}")
        return {
            "snapshot_id": snapshot_id,
            "service": name,
            "label": label,
            "created_at": snapshot["created_at"],
        }

    def update_state(self, name: str, config: dict) -> dict:
        """Update a service's current configuration.

        Args:
            name: Service name.
            config: New configuration (merged with existing).

        Returns:
            Updated configuration summary.

        Raises:
            KeyError: If the service is not registered.
        """
        if name not in self._current_state:
            raise KeyError(f"Service '{name}' not registered")

        self._current_state[name].update(config)
        self._log_event("UPDATE", name, detail=f"Updated keys: {list(config.keys())}")
        return {
            "service": name,
            "updated_keys": list(config.keys()),
            "total_keys": len(self._current_state[name]),
        }

    def rollback_to_snapshot(self, snapshot_id: str) -> dict:
        """Rollback a service to a previously captured snapshot.

        Args:
            snapshot_id: The snapshot to restore.

        Returns:
            Rollback result dict.

        Raises:
            KeyError: If the snapshot does not exist.
        """
        if snapshot_id not in self._snapshots:
            raise KeyError(f"Snapshot '{snapshot_id}' not found")

        snapshot = self._snapshots[snapshot_id]
        name = snapshot["service"]

        old_state = deepcopy(self._current_state.get(name, {}))
        self._current_state[name] = deepcopy(snapshot["state"])

        self._log_event(
            "ROLLBACK", name,
            detail=f"Rolled back to snapshot {snapshot_id} (label: {snapshot['label']})"
        )

        return {
            "service": name,
            "snapshot_id": snapshot_id,
            "snapshot_label": snapshot["label"],
            "restored_keys": list(snapshot["state"].keys()),
        }

    def validate_rollback(self, name: str, expected_keys: list) -> dict:
        """Validate that a rollback restored the expected configuration keys.

        Args:
            name: Service name.
            expected_keys: Keys that should be present in the current config.

        Returns:
            Validation result dict.

        Raises:
            KeyError: If the service is not registered.
        """
        if name not in self._current_state:
            raise KeyError(f"Service '{name}' not registered")

        current_keys = set(self._current_state[name].keys())
        expected_set = set(expected_keys)
        missing = expected_set - current_keys
        extra = current_keys - expected_set

        valid = len(missing) == 0
        self._log_event(
            "VALIDATE", name,
            detail=f"Validation {'PASSED' if valid else 'FAILED'}: missing={list(missing)}"
        )

        return {
            "service": name,
            "valid": valid,
            "missing_keys": list(missing),
            "extra_keys": list(extra),
        }

    def get_audit_log(self, service_name: str | None = None) -> list:
        """Retrieve the audit log, optionally filtered by service.

        Args:
            service_name: Filter by service name (optional).

        Returns:
            List of audit log entries.
        """
        if service_name:
            return [e for e in self._audit_log if e["service"] == service_name]
        return list(self._audit_log)

    def list_snapshots(self, service_name: str | None = None) -> list:
        """List all snapshots, optionally filtered by service.

        Returns:
            List of snapshot summaries.
        """
        snapshots = self._snapshots.values()
        if service_name:
            snapshots = [s for s in snapshots if s["service"] == service_name]
        return [
            {
                "snapshot_id": s["id"],
                "service": s["service"],
                "label": s["label"],
                "created_at": s["created_at"],
            }
            for s in snapshots
        ]

    def get_current_state(self, name: str) -> dict:
        """Get the current configuration for a service.

        Raises:
            KeyError: If the service is not registered.
        """
        if name not in self._current_state:
            raise KeyError(f"Service '{name}' not registered")
        return deepcopy(self._current_state[name])

    # ---- internal helpers ----

    def _log_event(self, event_type: str, service: str, detail: str = ""):
        self._audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "service": service,
            "detail": detail,
        })
