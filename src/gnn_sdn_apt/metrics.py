"""Shared metric helpers for thesis reports."""
from __future__ import annotations

from typing import Iterable

from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score


def binary_metrics(y_true: Iterable[int], y_pred: Iterable[int]) -> dict[str, float | list[list[int]]]:
    """Compute binary metrics with a fixed class order of normal=0, suspicious=1."""
    truth = list(y_true)
    predicted = list(y_pred)
    matrix = confusion_matrix(truth, predicted, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    return {
        "precision": float(precision_score(truth, predicted, zero_division=0)),
        "recall": float(recall_score(truth, predicted, zero_division=0)),
        "f1": float(f1_score(truth, predicted, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if tn + fp else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if fn + tp else 0.0,
        "confusion_matrix_labels_0_1": matrix.tolist(),
    }
