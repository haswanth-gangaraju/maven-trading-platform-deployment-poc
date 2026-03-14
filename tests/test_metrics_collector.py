"""Tests for Prometheus Metrics Collector."""

import json

import pytest
from src.metrics_collector import MetricsCollector


@pytest.fixture
def collector():
    return MetricsCollector()


def test_counter_register_and_increment(collector):
    collector.counter("http_requests_total", description="Total HTTP requests")
    result = collector.increment("http_requests_total", 5.0)
    assert result["value"] == 5.0
    result = collector.increment("http_requests_total", 3.0)
    assert result["value"] == 8.0


def test_counter_negative_increment_raises(collector):
    collector.counter("c")
    with pytest.raises(ValueError, match="non-negative"):
        collector.increment("c", -1)


def test_counter_duplicate_raises(collector):
    collector.counter("dup")
    with pytest.raises(ValueError, match="already exists"):
        collector.counter("dup")


def test_gauge_set(collector):
    collector.gauge("cpu_usage", description="CPU utilisation")
    result = collector.set_gauge("cpu_usage", 72.5)
    assert result["value"] == 72.5


def test_gauge_not_found_raises(collector):
    with pytest.raises(KeyError, match="not found"):
        collector.set_gauge("ghost", 1.0)


def test_histogram_observe(collector):
    collector.histogram("request_duration_seconds")
    result = collector.observe("request_duration_seconds", 0.042)
    assert result["observation_count"] == 1
    collector.observe("request_duration_seconds", 0.15)
    result = collector.observe("request_duration_seconds", 0.008)
    assert result["observation_count"] == 3


def test_histogram_summary(collector):
    collector.histogram("latency")
    for v in [10, 20, 30, 40, 50]:
        collector.observe("latency", v)
    summary = collector.get_histogram_summary("latency")
    assert summary["count"] == 5
    assert summary["mean"] == 30.0
    assert summary["min"] == 10
    assert summary["max"] == 50


def test_histogram_no_observations_raises(collector):
    collector.histogram("empty")
    with pytest.raises(ValueError, match="No observations"):
        collector.get_histogram_summary("empty")


def test_export_json(collector):
    collector.counter("req")
    collector.increment("req", 10)
    collector.gauge("mem")
    collector.set_gauge("mem", 85.0)
    exported = json.loads(collector.export())
    assert "counters" in exported
    assert "gauges" in exported
    assert exported["counters"]["req"]["value"] == 10
    assert exported["gauges"]["mem"]["value"] == 85.0


def test_create_and_evaluate_alert(collector):
    collector.gauge("error_rate")
    collector.set_gauge("error_rate", 5.0)
    collector.create_alert("high_errors", "error_rate", threshold=3.0, comparison="gt")
    firing = collector.evaluate_alerts()
    assert len(firing) == 1
    assert firing[0]["alert"] == "high_errors"
    assert firing[0]["current_value"] == 5.0


def test_alert_not_firing(collector):
    collector.gauge("latency")
    collector.set_gauge("latency", 1.0)
    collector.create_alert("slow", "latency", threshold=5.0, comparison="gt")
    firing = collector.evaluate_alerts()
    assert len(firing) == 0
