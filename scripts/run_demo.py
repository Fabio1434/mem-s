#!/usr/bin/env python3
"""Run the whole offline pipeline on a clearly labelled synthetic capture."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from gnn_sdn_apt.demo_data import generate_demo_capture
from gnn_sdn_apt.models.baseline import train_baseline
from gnn_sdn_apt.pipeline import build_dataset


def run_demo(output_dir: Path, with_gnn: bool = False, epochs: int = 3) -> dict:
    """Generate capture, build graphs, fit baseline and optionally fit GCN/GAT."""
    output_dir = output_dir.resolve()
    raw_path = output_dir / "flow_stats.csv"
    labels_path = output_dir / "scenario_labels.csv"
    feature_path = output_dir / "flow_features.csv"
    graphs_path = output_dir / "graphs.jsonl"
    model_dir = output_dir / "models"
    report_dir = output_dir / "reports"
    config_path = output_dir / "config.yaml"

    generated = generate_demo_capture(raw_path, labels_path)
    config = {
        "paths": {
            "raw_flows": str(raw_path),
            "scenario_labels": str(labels_path),
            "features": str(feature_path),
            "graphs": str(graphs_path),
            "models": str(model_dir),
            "reports": str(report_dir),
            "alerts": str(output_dir / "alerts.jsonl"),
            "decisions": str(output_dir / "decisions.jsonl"),
            "mitigation_events": str(output_dir / "mitigation_events.jsonl"),
        },
        "graph": {"directed": True, "temporal_window_seconds": 10},
        "detection": {"model": "baseline", "threshold": 0.9},
        "mitigation": {"enabled": False, "default_action": "alert"},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    prepared = build_dataset(config_path)
    baseline_report = train_baseline(
        graphs_path,
        model_dir / "baseline.joblib",
        report_dir / "baseline_metrics.json",
        threshold=0.9,
        calibrate_threshold=True,
    )
    result = {
        "synthetic_data": generated,
        "preparation": prepared,
        "baseline": {
            "model": baseline_report["model"],
            "split_method": baseline_report["split_method"],
            "threshold": baseline_report["threshold"],
            "test_observations": baseline_report["test_observations"],
            "accuracy": baseline_report["accuracy"],
            "f1": baseline_report["f1"],
        },
        "gnn": {},
        "disclaimer": (
            "These results verify software execution on synthetic data only. "
            "They are not evidence of real-world or APT detection performance."
        ),
    }

    if with_gnn:
        try:
            from gnn_sdn_apt.models.train_gnn import train_gnn
        except ImportError as exc:
            raise SystemExit(
                "GCN/GAT dependencies are missing. Install with: pip install -e '.[ml]'"
            ) from exc
        for model_name in ("gcn", "gat"):
            report = train_gnn(
                graphs_path,
                model_dir / f"{model_name}.pt",
                report_dir / f"{model_name}_metrics.json",
                model_name=model_name,
                epochs=epochs,
                threshold=0.9,
                calibrate_threshold=True,
            )
            result["gnn"][model_name] = {
                "threshold": report["threshold"],
                "split_method": report["split_method"],
                "test_observations": report["test_observations"],
                "accuracy": report["accuracy"],
                "f1": report["f1"],
            }

    report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = report_dir / "demo_summary.json"
    summary_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["summary_file"] = str(summary_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/demo"))
    parser.add_argument(
        "--with-gnn",
        action="store_true",
        help="also train GCN and GAT; requires pip install -e '.[ml]'",
    )
    parser.add_argument("--epochs", type=int, default=3)
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("--epochs must be positive")
    print(json.dumps(run_demo(args.output_dir, args.with_gnn, args.epochs), indent=2))


if __name__ == "__main__":
    main()
