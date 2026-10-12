"""Configuration loading with safe defaults."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
    "project": {"name": "gnn-sdn-apt-detection", "mode": "research"},
    "paths": {
        "raw_flows": "data/raw/flow_stats.csv",
        "scenario_labels": "data/raw/scenario_labels.csv",
        "features": "data/processed/flow_features.csv",
        "graphs": "data/processed/graphs.jsonl",
        "models": "models/checkpoints",
        "reports": "reports",
        "alerts": "data/processed/alerts.jsonl",
        "decisions": "data/processed/decisions.jsonl",
        "mitigation_events": "data/processed/mitigation_events.jsonl",
    },
    "graph": {"directed": True, "temporal_window_seconds": 10},
    "detection": {"model": "baseline", "threshold": 0.9, "use_model_threshold": True},
    "mitigation": {"enabled": False, "default_action": "alert"},
    "sdn": {"controller": "ryu", "openflow_version": "1.3"},
    "logging": {"level": "INFO"},
}


def load_config(path: str | Path = "config/config.yaml") -> dict[str, Any]:
    """Load YAML config and merge it over defaults."""
    config_path = Path(path)
    if not config_path.exists():
        return _deep_merge({}, DEFAULT_CONFIG)
    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Configuration root must be a mapping: {config_path}")
    return _deep_merge(loaded, DEFAULT_CONFIG)


def _deep_merge(loaded: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(defaults)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(defaults.get(key), dict):
            merged[key] = _deep_merge(value, defaults[key])
        else:
            merged[key] = value
    return merged
