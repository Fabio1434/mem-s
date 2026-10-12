"""Train and evaluate a GCN or GAT on temporal graph snapshots."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler
from torch_geometric.data import Data

from ..graph.io import read_graphs
from ..schema import NODE_FEATURE_NAMES
from .gnn import create_model


def _to_data(graph: dict[str, Any]) -> Data:
    index = {node["id"]: position for position, node in enumerate(graph.get("nodes", []))}
    if not index:
        return Data(
            x=torch.zeros((0, len(NODE_FEATURE_NAMES)), dtype=torch.float32),
            edge_index=torch.empty((2, 0), dtype=torch.long),
            y=torch.empty((0,), dtype=torch.long),
        )
    x = torch.tensor([node["features"] for node in graph["nodes"]], dtype=torch.float32)
    y = torch.tensor(
        [int(node.get("label", -1)) for node in graph["nodes"]], dtype=torch.long
    )
    # The stored graph stays directed, but message passing sees both directions.
    edge_pairs: set[tuple[int, int]] = set()
    for edge in graph.get("edges", []):
        source, target = edge.get("source"), edge.get("target")
        if source in index and target in index:
            src_index, dst_index = index[source], index[target]
            edge_pairs.add((src_index, dst_index))
            edge_pairs.add((dst_index, src_index))
    edges = sorted(edge_pairs)
    edge_index = (
        torch.tensor(edges, dtype=torch.long).t().contiguous()
        if edges else torch.empty((2, 0), dtype=torch.long)
    )
    return Data(x=x, edge_index=edge_index, y=y)


def _labels_in(graphs: list[Data]) -> set[int]:
    values = {
        int(label)
        for data in graphs
        for label in data.y[data.y >= 0].tolist()
    }
    return values


def _choose_threshold(
    y_true: np.ndarray,
    scores: np.ndarray,
    configured_threshold: float,
) -> tuple[float, dict[str, float]]:
    """Select validation threshold by F1, tie-breaking toward lower FPR then higher threshold."""
    candidates = sorted(set(np.linspace(0.05, 0.95, 19).tolist() + [configured_threshold]))
    best_threshold = configured_threshold
    best_key = (-1.0, -1.0, -1.0)
    for candidate in candidates:
        predicted = (scores >= candidate).astype(int)
        matrix = confusion_matrix(y_true, predicted, labels=[0, 1])
        tn, fp, _fn, _tp = matrix.ravel()
        f1 = float(f1_score(y_true, predicted, zero_division=0))
        fpr = float(fp / (fp + tn)) if tn + fp else 0.0
        key = (f1, -fpr, candidate)
        if key > best_key:
            best_key = key
            best_threshold = float(candidate)
    return best_threshold, {
        "validation_f1": float(best_key[0]),
        "validation_false_positive_rate": float(-best_key[1]),
    }


def train_gnn(
    graphs_path: str | Path,
    model_path: str | Path,
    report_path: str | Path,
    model_name: str = "gcn",
    epochs: int = 100,
    learning_rate: float = 0.005,
    hidden_dim: int = 32,
    threshold: float = 0.9,
    calibrate_threshold: bool = False,
) -> dict[str, Any]:
    """Train with earlier snapshots, optionally calibrate on middle snapshots, and test on later snapshots."""
    if epochs < 1:
        raise ValueError("epochs must be positive")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in the [0, 1] interval")

    graphs = read_graphs(graphs_path)
    graphs = sorted(graphs, key=lambda graph: float(graph.get("timestamp", 0)))
    datasets = [_to_data(graph) for graph in graphs]
    datasets = [data for data in datasets if data.num_nodes > 0 and bool((data.y >= 0).any())]
    if len(datasets) < 3:
        raise ValueError(
            f"Need at least 3 labeled graph snapshots for a temporal GNN split; found {len(datasets)}."
        )
    if _labels_in(datasets) != {0, 1}:
        raise ValueError("Graph dataset must include both normal (0) and suspicious (1) labels.")

    use_validation = False
    if calibrate_threshold and len(datasets) >= 6:
        train_cut = max(2, int(len(datasets) * 0.6))
        validation_cut = max(train_cut + 1, int(len(datasets) * 0.8))
        validation_cut = min(validation_cut, len(datasets) - 1)
        candidate_train = datasets[:train_cut]
        candidate_validation = datasets[train_cut:validation_cut]
        candidate_test = datasets[validation_cut:]
        if (
            _labels_in(candidate_train) == {0, 1}
            and _labels_in(candidate_validation) == {0, 1}
            and _labels_in(candidate_test) == {0, 1}
        ):
            train_graphs = candidate_train
            validation_graphs = candidate_validation
            test_graphs = candidate_test
            use_validation = True
            split_method = "temporal-train-validation-test"
        else:
            split_method = "temporal-train-test-validation-unavailable"
    else:
        split_method = "temporal-train-test-validation-unavailable"

    if not use_validation:
        split_at = max(1, int(len(datasets) * 0.7))
        split_at = min(split_at, len(datasets) - 1)
        train_graphs, test_graphs = datasets[:split_at], datasets[split_at:]
        validation_graphs = []

    if _labels_in(train_graphs) != {0, 1}:
        raise ValueError(
            "The chronological training partition does not contain both classes. "
            "Collect more normal and suspicious windows before training."
        )
    if _labels_in(test_graphs) != {0, 1}:
        raise ValueError(
            "The chronological test partition does not contain both classes. "
            "Collect more normal and suspicious windows before training."
        )

    # Fit normalization on train snapshots only to prevent temporal leakage.
    scaler = StandardScaler()
    train_matrix = torch.cat([graph.x for graph in train_graphs], dim=0).numpy()
    scaler.fit(train_matrix)
    for data in datasets:
        data.x = torch.tensor(scaler.transform(data.x.numpy()), dtype=torch.float32)

    model = create_model(model_name, input_dim=len(NODE_FEATURE_NAMES), hidden_dim=hidden_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=5e-4)
    loss_fn = torch.nn.CrossEntropyLoss()
    for _ in range(epochs):
        model.train()
        for data in train_graphs:
            mask = data.y >= 0
            if not bool(mask.any()):
                continue
            optimizer.zero_grad()
            logits = model(data.x, data.edge_index)
            loss = loss_fn(logits[mask], data.y[mask])
            loss.backward()
            optimizer.step()

    threshold_used = float(threshold)
    threshold_selection = "configured"
    validation_metrics: dict[str, float] = {}
    if use_validation:
        model.eval()
        validation_truth: list[int] = []
        validation_scores: list[float] = []
        with torch.no_grad():
            for data in validation_graphs:
                mask = data.y >= 0
                if not bool(mask.any()):
                    continue
                scores = torch.softmax(model(data.x, data.edge_index), dim=1)[:, 1]
                validation_truth.extend(data.y[mask].tolist())
                validation_scores.extend(scores[mask].tolist())
        threshold_used, validation_metrics = _choose_threshold(
            np.asarray(validation_truth, dtype=int),
            np.asarray(validation_scores, dtype=float),
            configured_threshold=threshold,
        )
        threshold_selection = "validation-f1"

    model.eval()
    truth: list[int] = []
    predicted: list[int] = []
    with torch.no_grad():
        for data in test_graphs:
            mask = data.y >= 0
            if not bool(mask.any()):
                continue
            scores = torch.softmax(model(data.x, data.edge_index), dim=1)[:, 1]
            truth.extend(data.y[mask].tolist())
            predicted.extend((scores[mask] >= threshold_used).to(torch.long).tolist())

    if not truth:
        raise ValueError("The temporal test partition contains no labeled nodes.")
    matrix = confusion_matrix(truth, predicted, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    report = {
        "model": model_name.upper(),
        "split_method": split_method,
        "threshold": threshold_used,
        "threshold_selection": threshold_selection,
        "configured_threshold": float(threshold),
        "validation_metrics": validation_metrics,
        "graph_snapshots": len(datasets),
        "train_graph_snapshots": len(train_graphs),
        "validation_graph_snapshots": len(validation_graphs),
        "test_graph_snapshots": len(test_graphs),
        "epochs": epochs,
        "node_feature_names": NODE_FEATURE_NAMES,
        "test_observations": len(truth),
        "accuracy": float(accuracy_score(truth, predicted)),
        "precision": float(precision_score(truth, predicted, zero_division=0)),
        "recall": float(recall_score(truth, predicted, zero_division=0)),
        "f1": float(f1_score(truth, predicted, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else 0.0,
        "confusion_matrix_labels_0_1": matrix.tolist(),
    }

    artifact = Path(model_path)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_name": model_name.lower(),
        "feature_dim": len(NODE_FEATURE_NAMES),
        "hidden_dim": hidden_dim,
        "feature_names": NODE_FEATURE_NAMES,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "threshold": threshold_used,
        "threshold_selection": threshold_selection,
        "state_dict": model.state_dict(),
    }, artifact)
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
