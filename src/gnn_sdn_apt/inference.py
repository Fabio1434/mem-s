"""Inference adapters for the classical baseline and optional GNN models."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .models.baseline import load_baseline, load_baseline_threshold
from .schema import NODE_FEATURE_NAMES


def score_baseline_nodes(
    graph: dict[str, Any],
    model_path: str | Path,
) -> list[dict[str, Any]]:
    """Score source hosts in one graph snapshot with a fitted baseline model."""
    estimator, expected_features = load_baseline(model_path)
    if expected_features != NODE_FEATURE_NAMES:
        raise ValueError("Model feature schema differs from the current graph schema")

    # Supervision is assigned to source hosts; do not classify destination-only nodes.
    nodes = [
        node for node in graph.get("nodes", [])
        if node.get("features") and float(node["features"][0]) > 0
    ]
    if not nodes:
        return []
    matrix = np.asarray([node["features"] for node in nodes], dtype=float)
    probabilities = estimator.predict_proba(matrix)
    classes = list(estimator.classes_)
    suspicious_index = classes.index(1) if 1 in classes else -1
    scores = probabilities[:, suspicious_index] if suspicious_index >= 0 else np.zeros(len(nodes))
    return [
        {
            "source_ip": str(node["id"]),
            "score": float(score),
            "timestamp": float(graph.get("timestamp", 0)),
        }
        for node, score in zip(nodes, scores, strict=True)
    ]


def score_gnn_nodes(
    graph: dict[str, Any],
    model_path: str | Path,
) -> list[dict[str, Any]]:
    """Score source hosts while retaining all nodes for GNN message passing."""
    import torch

    from .models.gnn import create_model

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    model_name = str(checkpoint["model_name"])
    feature_dim = int(checkpoint.get("feature_dim", len(NODE_FEATURE_NAMES)))
    if feature_dim != len(NODE_FEATURE_NAMES):
        raise ValueError("Saved GNN feature schema differs from the current graph schema")
    saved_names = checkpoint.get("feature_names", NODE_FEATURE_NAMES)
    if list(saved_names) != NODE_FEATURE_NAMES:
        raise ValueError("Saved GNN feature names differ from the current graph schema")

    nodes = graph.get("nodes", [])
    if not nodes:
        return []
    source_positions = [
        i for i, node in enumerate(nodes)
        if node.get("features") and float(node["features"][0]) > 0
    ]
    if not source_positions:
        return []

    # Keep destination-only nodes in the graph so their features can propagate
    # through GCN/GAT layers even though they do not receive a direct decision.
    index = {node["id"]: i for i, node in enumerate(nodes)}
    x = torch.tensor([node["features"] for node in nodes], dtype=torch.float32)
    means = checkpoint.get("scaler_mean")
    scales = checkpoint.get("scaler_scale")
    if means is not None and scales is not None:
        mean_tensor = torch.tensor(means, dtype=torch.float32)
        scale_tensor = torch.tensor(scales, dtype=torch.float32).clamp_min(1e-12)
        x = (x - mean_tensor) / scale_tensor
    # Match training: retain the directed graph features but pass messages both ways.
    edge_pairs_set: set[tuple[int, int]] = set()
    for edge in graph.get("edges", []):
        source, target = edge.get("source"), edge.get("target")
        if source in index and target in index:
            src_index, dst_index = index[source], index[target]
            edge_pairs_set.add((src_index, dst_index))
            edge_pairs_set.add((dst_index, src_index))
    edge_pairs = sorted(edge_pairs_set)
    edge_index = (
        torch.tensor(edge_pairs, dtype=torch.long).t().contiguous()
        if edge_pairs else torch.empty((2, 0), dtype=torch.long)
    )

    model = create_model(
        model_name,
        input_dim=feature_dim,
        hidden_dim=int(checkpoint.get("hidden_dim", 32)),
    )
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    with torch.no_grad():
        probabilities = torch.softmax(model(x, edge_index), dim=1)[:, 1].tolist()
    return [
        {
            "source_ip": str(nodes[position]["id"]),
            "score": float(probabilities[position]),
            "timestamp": float(graph.get("timestamp", 0)),
        }
        for position in source_positions
    ]



def load_saved_threshold(
    model_name: str,
    model_path: str | Path,
    fallback: float = 0.9,
) -> float:
    """Load the threshold persisted alongside a trained baseline/GNN artifact."""
    if model_name.lower() == "baseline":
        return load_baseline_threshold(model_path, fallback=fallback)

    import torch

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    threshold = float(checkpoint.get("threshold", fallback))
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Saved model threshold must be in the [0, 1] interval")
    return threshold
