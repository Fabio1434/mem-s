"""End-to-end offline data preparation pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_config
from .features import prepare_flow_file
from .graph.builder import build_graph_snapshots
from .graph.io import write_graphs


def build_dataset(
    config_path: str | Path = "config/config.yaml",
    raw_path: str | Path | None = None,
    annotations_path: str | Path | None = None,
) -> dict[str, Any]:
    """Normalize raw flow records and build temporal graph snapshots.

    Optional input overrides allow a public CSV imported into the raw schema to
    reuse the same pipeline without editing project configuration.
    """
    config = load_config(config_path)
    paths = config["paths"]
    graph_config = config["graph"]

    input_path = Path(raw_path or paths["raw_flows"])
    labels_path = annotations_path if annotations_path is not None else paths["scenario_labels"]
    features_path = Path(paths["features"])
    graphs_path = Path(paths["graphs"])
    default_window = float(graph_config.get("temporal_window_seconds", 10))

    features = prepare_flow_file(
        raw_path=input_path,
        output_path=features_path,
        annotations_path=labels_path,
        default_window_seconds=min(5.0, default_window),
    )
    graphs = build_graph_snapshots(features, window_seconds=int(default_window))
    graph_count = write_graphs(graphs, graphs_path)
    return {
        "raw_flows": str(input_path),
        "feature_file": str(features_path),
        "graph_file": str(graphs_path),
        "flow_observations": int(len(features)),
        "graph_snapshots": graph_count,
        "labeled_flow_observations": int((features["label"] >= 0).sum())
        if not features.empty else 0,
        "labeled_graph_nodes": sum(
            1 for graph in graphs for node in graph["nodes"] if node["label"] in (0, 1)
        ),
    }
