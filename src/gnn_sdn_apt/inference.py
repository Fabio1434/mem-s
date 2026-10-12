"""Inference adapters for the classical baseline and optional GNN models."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .models.baseline import load_baseline
from .schema import NODE_FEATURE_NAMES


def score_baseline_nodes(
    graph: dict[str, Any],
    model_path: str | Path,
) -> list[dict[str, Any]]:
    """Score each node in one graph snapshot with a fitted baseline model."""
    estimator, expected_features = load_baseline(model_path)
    if expected_features != NODE_FEATURE_NAMES:
        raise ValueError("Model feature schema differs from the current graph schema")

    nodes = graph.get("nodes", [])
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
    """Score one snapshot with a saved GCN/GAT model."""
    import torch

    from .models.gnn import create_model

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    model_name = str(checkpoint["model_name"])
    feature_dim = int(checkpoint.get("feature_dim", len(NODE_FEATURE_NAMES)))
    if feature_dim != len(NODE_FEATURE_NAMES):
        raise ValueError("Saved GNN feature schema differs from the current graph schema")

    nodes = graph.get("nodes", [])
    if not nodes:
        return []
    index = {node["id"]: i for i, node in enumerate(nodes)}
    x = torch.tensor([node["features"] for node in nodes], dtype=torch.float32)
    edge_pairs = [
        [index[edge["source"]], index[edge["target"]]]
        for edge in graph.get("edges", [])
        if edge.get("source") in index and edge.get("target") in index
    ]
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
            "source_ip": str(node["id"]),
            "score": float(score),
            "timestamp": float(graph.get("timestamp", 0)),
        }
        for node, score in zip(nodes, probabilities, strict=True)
    ]
