"""Classical node-level baseline for comparison with GNNs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ..graph.io import read_graphs
from ..schema import NODE_FEATURE_NAMES


def _node_table(graphs: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features: list[list[float]] = []
    labels: list[int] = []
    times: list[float] = []
    for graph in graphs:
        for node in graph.get("nodes", []):
            label = int(node.get("label", -1))
            if label not in (0, 1):
                continue
            vector = node.get("features", [])
            if len(vector) != len(NODE_FEATURE_NAMES):
                continue
            features.append([float(value) for value in vector])
            labels.append(label)
            times.append(float(graph.get("timestamp", 0)))
    return np.asarray(features, dtype=float), np.asarray(labels, dtype=int), np.asarray(times)


def _temporal_split(
    x: np.ndarray,
    y: np.ndarray,
    times: np.ndarray,
    test_size: float = 0.25,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
    unique_times = np.unique(times)
    if len(unique_times) >= 4:
        cutoff = unique_times[max(1, int(len(unique_times) * (1 - test_size)) - 1)]
        train_mask = times < cutoff
        test_mask = times >= cutoff
        if (
            train_mask.sum() > 0
            and test_mask.sum() > 0
            and len(np.unique(y[train_mask])) == 2
            and len(np.unique(y[test_mask])) == 2
        ):
            return x[train_mask], x[test_mask], y[train_mask], y[test_mask], "temporal"
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=test_size, random_state=42, stratify=y
    )
    return x_train, x_test, y_train, y_test, "stratified-node-fallback"


def train_baseline(
    graphs_path: str | Path,
    model_path: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    """Train a Random Forest and store model plus a metrics JSON report."""
    graphs = read_graphs(graphs_path)
    x, y, times = _node_table(graphs)
    if len(y) < 8:
        raise ValueError(
            f"Need at least 8 labeled node observations; found {len(y)}. "
            "Generate normal and controlled suspicious scenarios first."
        )
    if len(np.unique(y)) != 2:
        raise ValueError(
            "Training labels must contain both 0 (normal) and 1 (suspicious). "
            "Check scenario_labels.csv before training."
        )

    x_train, x_test, y_train, y_test, split_method = _temporal_split(x, y, times)
    if len(np.unique(y_train)) != 2:
        raise ValueError("Training split contains only one class; collect more varied scenarios.")

    estimator = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    class_weight="balanced",
                    random_state=42,
                    min_samples_leaf=2,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    estimator.fit(x_train, y_train)
    predictions = estimator.predict(x_test)
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    report: dict[str, Any] = {
        "model": "RandomForest",
        "split_method": split_method,
        "node_feature_names": NODE_FEATURE_NAMES,
        "train_observations": int(len(y_train)),
        "test_observations": int(len(y_test)),
        "test_class_counts": {"normal": int((y_test == 0).sum()), "suspicious": int((y_test == 1).sum())},
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else 0.0,
        "confusion_matrix_labels_0_1": matrix.tolist(),
        "note": (
            "For a small number of graph windows, a stratified node-level fallback may split "
            "nodes from the same snapshot across train and test. Prefer temporal results once "
            "enough snapshots are collected."
        ),
    }
    artifact = Path(model_path)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"estimator": estimator, "feature_names": NODE_FEATURE_NAMES}, artifact)
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def load_baseline(path: str | Path) -> tuple[Any, list[str]]:
    """Load the serialized baseline and its feature schema."""
    bundle = joblib.load(path)
    return bundle["estimator"], list(bundle.get("feature_names", NODE_FEATURE_NAMES))
