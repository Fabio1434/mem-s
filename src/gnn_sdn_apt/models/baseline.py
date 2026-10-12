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


def _temporal_three_way_split(
    x: np.ndarray, y: np.ndarray, times: np.ndarray
) -> tuple[np.ndarray, ...] | None:
    """Use early snapshots for fitting, middle snapshots for threshold validation and late ones for test."""
    unique_times = np.unique(times)
    if len(unique_times) < 6:
        return None
    train_cut = max(2, int(len(unique_times) * 0.6))
    validation_cut = max(train_cut + 1, int(len(unique_times) * 0.8))
    validation_cut = min(validation_cut, len(unique_times) - 1)
    train_mask = times < unique_times[train_cut]
    validation_mask = (times >= unique_times[train_cut]) & (times < unique_times[validation_cut])
    test_mask = times >= unique_times[validation_cut]
    masks = (train_mask, validation_mask, test_mask)
    if any(mask.sum() == 0 or len(np.unique(y[mask])) != 2 for mask in masks):
        return None
    return (
        x[train_mask], y[train_mask],
        x[validation_mask], y[validation_mask],
        x[test_mask], y[test_mask],
    )


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


def _choose_threshold(
    y_true: np.ndarray,
    scores: np.ndarray,
    configured_threshold: float,
) -> tuple[float, dict[str, float]]:
    """Select a threshold on validation F1; ties prefer fewer false positives."""
    candidates = sorted(set(np.linspace(0.05, 0.95, 19).tolist() + [configured_threshold]))
    best_threshold = configured_threshold
    best_metrics: tuple[float, float, float] = (-1.0, -1.0, -1.0)
    for candidate in candidates:
        predicted = (scores >= candidate).astype(int)
        matrix = confusion_matrix(y_true, predicted, labels=[0, 1])
        tn, fp, _fn, _tp = matrix.ravel()
        f1 = float(f1_score(y_true, predicted, zero_division=0))
        fpr = float(fp / (fp + tn)) if tn + fp else 0.0
        key = (f1, -fpr, candidate)
        if key > best_metrics:
            best_metrics = key
            best_threshold = float(candidate)
    return best_threshold, {
        "validation_f1": float(best_metrics[0]),
        "validation_false_positive_rate": float(-best_metrics[1]),
    }


def train_baseline(
    graphs_path: str | Path,
    model_path: str | Path,
    report_path: str | Path,
    threshold: float = 0.9,
    calibrate_threshold: bool = False,
) -> dict[str, Any]:
    """Train Random Forest; optionally tune threshold on a separate temporal validation split."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in the [0, 1] interval")
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

    three_way = _temporal_three_way_split(x, y, times) if calibrate_threshold else None
    validation_metrics: dict[str, float] = {}
    if three_way is not None:
        x_train, y_train, x_validation, y_validation, x_test, y_test = three_way
        split_method = "temporal-train-validation-test"
    else:
        x_train, x_test, y_train, y_test, split_method = _temporal_split(x, y, times)
        x_validation = y_validation = None

    if len(np.unique(y_train)) != 2:
        raise ValueError("Training split contains only one class; collect more varied scenarios.")

    estimator = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=42,
            min_samples_leaf=2,
            n_jobs=-1,
        )),
    ])
    estimator.fit(x_train, y_train)
    class_labels = list(estimator.classes_)
    if 1 not in class_labels:
        raise ValueError("The fitted baseline has no suspicious class")

    threshold_used = float(threshold)
    threshold_selection = "configured"
    if three_way is not None:
        validation_scores = estimator.predict_proba(x_validation)[:, class_labels.index(1)]
        threshold_used, validation_metrics = _choose_threshold(
            y_validation, validation_scores, configured_threshold=threshold
        )
        threshold_selection = "validation-f1"

    probabilities = estimator.predict_proba(x_test)[:, class_labels.index(1)]
    predictions = (probabilities >= threshold_used).astype(int)
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    report: dict[str, Any] = {
        "model": "RandomForest",
        "split_method": split_method,
        "threshold": threshold_used,
        "threshold_selection": threshold_selection,
        "configured_threshold": float(threshold),
        "node_feature_names": NODE_FEATURE_NAMES,
        "train_observations": int(len(y_train)),
        "validation_observations": int(len(y_validation)) if y_validation is not None else 0,
        "test_observations": int(len(y_test)),
        "test_class_counts": {
            "normal": int((y_test == 0).sum()),
            "suspicious": int((y_test == 1).sum()),
        },
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else 0.0,
        "confusion_matrix_labels_0_1": matrix.tolist(),
        "validation_metrics": validation_metrics,
        "note": (
            "If threshold_selection is configured, the supplied threshold was used. "
            "If threshold_selection is validation-f1, threshold tuning used a separate "
            "middle chronological partition and the final metrics use later snapshots. "
            "A stratified node fallback can mix nodes from the same snapshot across partitions."
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
