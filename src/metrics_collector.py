"""
Prometheus Metrics Collector for Trading Systems.

Provides counter, gauge, and histogram metric types with threshold-based
alert evaluation and JSON export for monitoring dashboards.
"""

import json
import math
from datetime import datetime, timezone


class MetricsCollector:
    """Collects Prometheus-style metrics for trading platform monitoring."""

    def __init__(self):
        self._counters = {}     # name -> current value
        self._gauges = {}       # name -> current value
        self._histograms = {}   # name -> list of observed values
        self._alerts = {}       # name -> alert config
        self._metadata = {}     # name -> {type, description, labels}

    def counter(self, name: str, description: str = "", labels: dict | None = None) -> dict:
        """Register a counter metric.

        Args:
            name: Metric name (must be unique across all types).
            description: Human-readable description.
            labels: Optional Prometheus labels.

        Returns:
            Counter registration dict.

        Raises:
            ValueError: If the metric name already exists.
        """
        if name in self._metadata:
            raise ValueError(f"Metric '{name}' already exists")

        self._counters[name] = 0.0
        self._metadata[name] = {
            "type": "counter",
            "description": description,
            "labels": labels or {},
        }
        return {"name": name, "type": "counter", "value": 0.0}

    def increment(self, name: str, value: float = 1.0) -> dict:
        """Increment a counter by a positive value.

        Raises:
            KeyError: If the counter does not exist.
            ValueError: If value is negative.
        """
        if name not in self._counters:
            raise KeyError(f"Counter '{name}' not found")
        if value < 0:
            raise ValueError("Counter increment must be non-negative")

        self._counters[name] += value
        return {"name": name, "value": self._counters[name]}

    def gauge(self, name: str, description: str = "", labels: dict | None = None) -> dict:
        """Register a gauge metric.

        Raises:
            ValueError: If the metric name already exists.
        """
        if name in self._metadata:
            raise ValueError(f"Metric '{name}' already exists")

        self._gauges[name] = 0.0
        self._metadata[name] = {
            "type": "gauge",
            "description": description,
            "labels": labels or {},
        }
        return {"name": name, "type": "gauge", "value": 0.0}

    def set_gauge(self, name: str, value: float) -> dict:
        """Set a gauge to a specific value.

        Raises:
            KeyError: If the gauge does not exist.
        """
        if name not in self._gauges:
            raise KeyError(f"Gauge '{name}' not found")

        self._gauges[name] = value
        return {"name": name, "value": value}

    def histogram(self, name: str, description: str = "", buckets: list | None = None) -> dict:
        """Register a histogram metric.

        Args:
            name: Metric name.
            description: Human-readable description.
            buckets: Optional bucket boundaries.

        Raises:
            ValueError: If the metric name already exists.
        """
        if name in self._metadata:
            raise ValueError(f"Metric '{name}' already exists")

        default_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._histograms[name] = []
        self._metadata[name] = {
            "type": "histogram",
            "description": description,
            "buckets": buckets or default_buckets,
        }
        return {"name": name, "type": "histogram", "observation_count": 0}

    def observe(self, name: str, value: float) -> dict:
        """Record an observation in a histogram.

        Raises:
            KeyError: If the histogram does not exist.
        """
        if name not in self._histograms:
            raise KeyError(f"Histogram '{name}' not found")

        self._histograms[name].append(value)
        return {
            "name": name,
            "value": value,
            "observation_count": len(self._histograms[name]),
        }

    def get_histogram_summary(self, name: str) -> dict:
        """Get summary statistics for a histogram.

        Raises:
            KeyError: If the histogram does not exist.
            ValueError: If no observations have been recorded.
        """
        if name not in self._histograms:
            raise KeyError(f"Histogram '{name}' not found")
        values = self._histograms[name]
        if not values:
            raise ValueError(f"No observations for histogram '{name}'")

        sorted_vals = sorted(values)
        count = len(sorted_vals)
        return {
            "name": name,
            "count": count,
            "sum": sum(sorted_vals),
            "mean": sum(sorted_vals) / count,
            "p50": sorted_vals[count // 2],
            "p95": sorted_vals[int(count * 0.95)] if count >= 20 else sorted_vals[-1],
            "p99": sorted_vals[int(count * 0.99)] if count >= 100 else sorted_vals[-1],
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
        }

    def export(self) -> str:
        """Export all metrics as a JSON string."""
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "counters": {
                name: {"value": val, **self._metadata[name]}
                for name, val in self._counters.items()
            },
            "gauges": {
                name: {"value": val, **self._metadata[name]}
                for name, val in self._gauges.items()
            },
            "histograms": {
                name: {
                    "observation_count": len(vals),
                    **self._metadata[name],
                }
                for name, vals in self._histograms.items()
            },
        }
        return json.dumps(data, indent=2)

    def create_alert(
        self,
        name: str,
        metric_name: str,
        threshold: float,
        comparison: str = "gt",
    ) -> dict:
        """Create an alert rule for a metric.

        Args:
            name: Alert name.
            metric_name: Metric to monitor.
            threshold: Threshold value.
            comparison: Comparison operator (gt, lt, gte, lte).

        Raises:
            ValueError: If the alert already exists or metric does not exist.
        """
        if name in self._alerts:
            raise ValueError(f"Alert '{name}' already exists")
        if metric_name not in self._metadata:
            raise ValueError(f"Metric '{metric_name}' does not exist")
        if comparison not in ("gt", "lt", "gte", "lte"):
            raise ValueError(f"Invalid comparison '{comparison}'")

        self._alerts[name] = {
            "name": name,
            "metric_name": metric_name,
            "threshold": threshold,
            "comparison": comparison,
        }
        return self._alerts[name]

    def evaluate_alerts(self) -> list:
        """Evaluate all alert rules against current metric values.

        Returns:
            List of firing alerts.
        """
        firing = []
        for alert in self._alerts.values():
            metric_name = alert["metric_name"]
            current = self._get_current_value(metric_name)
            if current is None:
                continue

            is_firing = self._compare(current, alert["threshold"], alert["comparison"])
            if is_firing:
                firing.append({
                    "alert": alert["name"],
                    "metric": metric_name,
                    "current_value": current,
                    "threshold": alert["threshold"],
                    "comparison": alert["comparison"],
                })
        return firing

    # ---- internal helpers ----

    def _get_current_value(self, metric_name: str) -> float | None:
        if metric_name in self._counters:
            return self._counters[metric_name]
        if metric_name in self._gauges:
            return self._gauges[metric_name]
        if metric_name in self._histograms and self._histograms[metric_name]:
            return sum(self._histograms[metric_name]) / len(self._histograms[metric_name])
        return None

    @staticmethod
    def _compare(value: float, threshold: float, comparison: str) -> bool:
        ops = {
            "gt": value > threshold,
            "lt": value < threshold,
            "gte": value >= threshold,
            "lte": value <= threshold,
        }
        return ops.get(comparison, False)
