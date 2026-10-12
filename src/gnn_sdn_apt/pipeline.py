"""End-to-end offline data preparation pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_config
from .features import prepare_flow_file
from .graph.builder import build_graph_snapshots
from .graph.io import write_graphs


def build_dataset(config_path: str | Path = "config/config.yaml") -> dict[str, Any]:
    """Run raw-flow normalization followed by temporal graph construction."""
    config = load_config(config_path)
    paths = config["paths"]
    graph_config = config["graph"]

    features_path = Path(paths["features"])
    graphs_path = Path(paths["graphs"])
    default_window = float(graph_config.get("temporal_window_seconds", 10))

    features = prepare_flow_file(
        raw_path=paths["raw_flows"],
        output_path=features_path,
        annotations_path=paths["scenario_labels"],
        default_window_seconds=min(5.0, default_window),
    )
    graphs = build_graph_snapshots(features, window_seconds=int(default_window))
    graph_count = write_graphs(graphs, graphs_path)
    return {
        "raw_flows": paths["raw_flows"],
        "feature_file": str(features_path),
        "graph_file": str(graphs_path),
        "flow_observations": int(len(features)),
        "graph_snapshots": graph_count,
        "labeled_flow_observations": int((features.get("label", []) >= 0).sum())
        if not features.empty else 0,
        "labeled_graph_nodes": sum(
            1 for graph in graphs for node in graph["nodes"] if node["label"] in (0, 1)
        ),
    }
