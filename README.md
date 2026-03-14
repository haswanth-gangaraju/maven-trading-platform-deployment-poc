# Trading Platform Deployment Automation POC

Proof-of-concept demonstrating platform engineering skills for Kubernetes deployment management, health monitoring with circuit breakers, Prometheus metrics collection, and automated rollback with state snapshotting for a low-latency trading platform.

## Modules

- **deployment_manager** - K8s deployment management with rolling updates, canary releases, and blue-green switching
- **health_monitor** - Service health monitoring with circuit breaker patterns and dependency graph tracking
- **metrics_collector** - Prometheus-style counter, gauge, and histogram metrics with threshold-based alerting
- **rollback_controller** - Automated rollback with state snapshotting, validation, and audit logging

## Setup

```bash
pip install -r requirements.txt
```

## Running Tests

```bash
python -m pytest -q
```
