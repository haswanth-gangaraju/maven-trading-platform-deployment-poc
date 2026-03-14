"""
Kubernetes Deployment Manager for Trading Systems.

Simulates K8s deployment operations including standard deploys, rollbacks,
canary releases, and blue-green switching for low-latency trading services.
"""

import uuid
from datetime import datetime, timezone
from copy import deepcopy


class DeploymentManager:
    """Manages Kubernetes-style deployments for trading platform services."""

    VALID_STRATEGIES = {"rolling", "canary", "blue-green"}

    def __init__(self):
        self._deployments = {}   # name -> deployment dict
        self._history = {}       # name -> list of past deployment snapshots

    def deploy(
        self,
        name: str,
        image: str,
        replicas: int = 3,
        strategy: str = "rolling",
        labels: dict | None = None,
    ) -> dict:
        """Deploy a service to the cluster.

        Args:
            name: Deployment name (must be unique).
            image: Container image URI.
            replicas: Number of replicas.
            strategy: Deployment strategy (rolling, canary, blue-green).
            labels: Optional labels dict.

        Returns:
            Deployment dict.

        Raises:
            ValueError: If the deployment already exists or strategy is invalid.
        """
        if name in self._deployments:
            raise ValueError(f"Deployment '{name}' already exists")
        if strategy not in self.VALID_STRATEGIES:
            raise ValueError(
                f"Invalid strategy '{strategy}'. Valid: {self.VALID_STRATEGIES}"
            )
        if replicas < 1:
            raise ValueError("replicas must be >= 1")

        deployment = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "image": image,
            "replicas": replicas,
            "strategy": strategy,
            "labels": labels or {},
            "status": "RUNNING",
            "version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._deployments[name] = deployment
        self._history[name] = [deepcopy(deployment)]
        return deployment

    def update_deployment(self, name: str, image: str, replicas: int | None = None) -> dict:
        """Update an existing deployment with a new image or replica count.

        Args:
            name: Deployment name.
            image: New container image.
            replicas: Optional new replica count.

        Returns:
            Updated deployment dict.

        Raises:
            KeyError: If the deployment does not exist.
        """
        if name not in self._deployments:
            raise KeyError(f"Deployment '{name}' not found")

        dep = self._deployments[name]
        # Save snapshot before update
        self._history[name].append(deepcopy(dep))

        dep["image"] = image
        if replicas is not None:
            dep["replicas"] = replicas
        dep["version"] += 1
        dep["updated_at"] = datetime.now(timezone.utc).isoformat()
        return dep

    def rollback(self, name: str, target_version: int | None = None) -> dict:
        """Rollback a deployment to a previous version.

        Args:
            name: Deployment name.
            target_version: Specific version to rollback to (defaults to previous).

        Returns:
            Rollback result dict.

        Raises:
            KeyError: If the deployment does not exist.
            ValueError: If the target version is not available.
        """
        if name not in self._deployments:
            raise KeyError(f"Deployment '{name}' not found")

        history = self._history[name]
        if len(history) < 2 and target_version is None:
            raise ValueError(f"No previous versions for deployment '{name}'")

        if target_version is not None:
            target = None
            for snap in history:
                if snap["version"] == target_version:
                    target = snap
                    break
            if target is None:
                raise ValueError(
                    f"Version {target_version} not found in history for '{name}'"
                )
        else:
            target = history[-1]

        current_version = self._deployments[name]["version"]
        restored = deepcopy(target)
        restored["version"] = current_version + 1
        restored["status"] = "RUNNING"
        restored["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._history[name].append(deepcopy(self._deployments[name]))
        self._deployments[name] = restored

        return {
            "name": name,
            "rolled_back_from": current_version,
            "rolled_back_to_image": restored["image"],
            "new_version": restored["version"],
        }

    def canary_release(
        self, name: str, new_image: str, canary_percent: int = 10
    ) -> dict:
        """Start a canary release for a deployment.

        Args:
            name: Deployment name.
            new_image: New image for canary pods.
            canary_percent: Percentage of traffic to route to canary (1-50).

        Returns:
            Canary release configuration dict.

        Raises:
            KeyError: If the deployment does not exist.
            ValueError: If canary_percent is out of range.
        """
        if name not in self._deployments:
            raise KeyError(f"Deployment '{name}' not found")
        if not 1 <= canary_percent <= 50:
            raise ValueError("canary_percent must be between 1 and 50")

        dep = self._deployments[name]
        return {
            "name": name,
            "stable_image": dep["image"],
            "canary_image": new_image,
            "canary_percent": canary_percent,
            "stable_percent": 100 - canary_percent,
            "status": "CANARY_ACTIVE",
        }

    def blue_green_switch(self, name: str, new_image: str) -> dict:
        """Perform a blue-green deployment switch.

        The current deployment becomes "blue" (standby) and the new image
        becomes "green" (active).

        Args:
            name: Deployment name.
            new_image: Image for the green environment.

        Returns:
            Blue-green switch result dict.

        Raises:
            KeyError: If the deployment does not exist.
        """
        if name not in self._deployments:
            raise KeyError(f"Deployment '{name}' not found")

        dep = self._deployments[name]
        old_image = dep["image"]

        self._history[name].append(deepcopy(dep))
        dep["image"] = new_image
        dep["version"] += 1
        dep["updated_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "name": name,
            "blue_image": old_image,
            "green_image": new_image,
            "active": "green",
            "new_version": dep["version"],
        }

    def list_deployments(self) -> list:
        """List all deployments."""
        return [
            {
                "name": d["name"],
                "image": d["image"],
                "replicas": d["replicas"],
                "status": d["status"],
                "version": d["version"],
            }
            for d in self._deployments.values()
        ]

    def delete_deployment(self, name: str) -> dict:
        """Delete a deployment.

        Raises:
            KeyError: If the deployment does not exist.
        """
        if name not in self._deployments:
            raise KeyError(f"Deployment '{name}' not found")
        dep = self._deployments.pop(name)
        self._history.pop(name, None)
        return {"deleted": name, "was_image": dep["image"]}
