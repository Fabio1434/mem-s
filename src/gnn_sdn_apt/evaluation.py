"""Utilities to aggregate model reports and mitigation timing measurements."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


REPORT_FIELDS = [
    "model",
    "split_method",
    "threshold",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "false_positive_rate",
    "false_negative_rate",
    "test_observations",
]


def compare_model_reports(
    reports_dir: str | Path = "reports",
    output_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Combine any saved baseline/GCN/GAT reports into a comparable table."""
    directory = Path(reports_dir)
    candidates = [
        directory / "baseline_metrics.json",
        directory / "gcn_metrics.json",
        directory / "gat_metrics.json",
    ]
    rows: list[dict[str, Any]] = []
    for path in candidates:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            report = json.load(handle)
        row = {field: report.get(field) for field in REPORT_FIELDS}
        row["report_file"] = path.name
        rows.append(row)
    if not rows:
        raise FileNotFoundError(
            f"No model metrics reports found in {directory}. Train at least the baseline first."
        )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(target, index=False)
    return rows


def summarize_mitigation_events(path: str | Path) -> dict[str, Any]:
    """Summarize action timing from Ryu mitigation event JSONL."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Mitigation event log not found: {source}")
    events: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {number} of {source}") from exc
            events.append(event)
    latencies = [
        float(event["decision_action_latency_seconds"])
        for event in events
        if "decision_action_latency_seconds" in event
    ]
    return {
        "events": len(events),
        "unique_sources": len({event.get("source_ip") for event in events}),
        "mean_decision_action_latency_seconds": sum(latencies) / len(latencies) if latencies else None,
        "max_decision_action_latency_seconds": max(latencies) if latencies else None,
        "minimum_decision_action_latency_seconds": min(latencies) if latencies else None,
        "note": "Timing summaries are meaningful only for events actually observed in the lab.",
    }
