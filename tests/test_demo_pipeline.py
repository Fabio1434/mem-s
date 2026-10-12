from pathlib import Path

import pandas as pd
import yaml

from gnn_sdn_apt.demo_data import generate_demo_capture
from gnn_sdn_apt.models.baseline import train_baseline
from gnn_sdn_apt.pipeline import build_dataset


def test_synthetic_capture_runs_through_features_graphs_and_baseline(tmp_path: Path):
    raw_path = tmp_path / "raw" / "flow_stats.csv"
    labels_path = tmp_path / "raw" / "scenario_labels.csv"
    features_path = tmp_path / "processed" / "features.csv"
    graphs_path = tmp_path / "processed" / "graphs.jsonl"
    config_path = tmp_path / "config.yaml"

    source_summary = generate_demo_capture(raw_path, labels_path, polls=40)
    assert source_summary["rows"] == 80
    assert len(pd.read_csv(labels_path)) == 2

    config_path.write_text(yaml.safe_dump({
        "paths": {
            "raw_flows": str(raw_path),
            "scenario_labels": str(labels_path),
            "features": str(features_path),
            "graphs": str(graphs_path),
            "models": str(tmp_path / "models"),
            "reports": str(tmp_path / "reports"),
        },
        "graph": {"temporal_window_seconds": 10},
    }), encoding="utf-8")

    prepared = build_dataset(config_path)
    assert prepared["flow_observations"] == 80
    assert prepared["graph_snapshots"] >= 12
    assert prepared["labeled_flow_observations"] == 80
    assert features_path.exists() and graphs_path.exists()

    report = train_baseline(
        graphs_path,
        tmp_path / "models" / "baseline.joblib",
        tmp_path / "reports" / "baseline_metrics.json",
        threshold=0.9,
        calibrate_threshold=True,
    )
    assert report["threshold_selection"] == "validation-f1"
    assert report["train_observations"] > 0
    assert report["test_observations"] > 0
    assert 0.0 <= report["f1"] <= 1.0
