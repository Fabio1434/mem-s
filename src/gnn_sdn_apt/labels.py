"""Scenario annotation utilities for controlled laboratory traffic."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schema import LABEL_COLUMNS


def load_annotations(path: str | Path) -> pd.DataFrame:
    """Load scenario intervals. Missing annotation files mean data is unlabeled."""
    annotation_path = Path(path)
    if not annotation_path.exists() or annotation_path.stat().st_size == 0:
        return pd.DataFrame(columns=LABEL_COLUMNS)
    annotations = pd.read_csv(annotation_path)
    for column in LABEL_COLUMNS:
        if column not in annotations.columns:
            annotations[column] = ""
    annotations["timestamp_start"] = pd.to_numeric(annotations["timestamp_start"], errors="coerce")
    annotations["timestamp_end"] = pd.to_numeric(annotations["timestamp_end"], errors="coerce")
    annotations["label"] = pd.to_numeric(annotations["label"], errors="coerce")
    return annotations.dropna(subset=["timestamp_start", "timestamp_end", "label"]).assign(
        label=lambda frame: frame["label"].astype(int)
    )


def label_flow(
    timestamp: float,
    src_ip: str,
    dst_ip: str,
    annotations: pd.DataFrame,
) -> tuple[int, str]:
    """Return (label, scenario); -1 means that the observation has no ground truth."""
    if annotations.empty:
        return -1, "unlabelled"
    eligible = annotations[
        (annotations["timestamp_start"] <= timestamp)
        & (annotations["timestamp_end"] >= timestamp)
    ]
    eligible = eligible.sort_values("timestamp_start", ascending=False)\n    for row in eligible.itertuples(index=False):
        expected_src = str(row.src_ip).strip()
        expected_dst = str(row.dst_ip).strip()
        if expected_src and expected_src.lower() != "nan" and expected_src != src_ip:
            continue
        if expected_dst and expected_dst.lower() != "nan" and expected_dst != dst_ip:
            continue
        return int(row.label), str(row.scenario)
    return -1, "unlabelled"


def append_annotation(
    path: str | Path,
    *,
    start: float,
    end: float,
    src_ip: str,
    dst_ip: str = "",
    label: int,
    scenario: str,
) -> None:
    """Append one label interval, creating the CSV file if necessary."""
    if label not in (0, 1):
        raise ValueError("label must be 0 (normal) or 1 (suspicious)")
    annotation_path = Path(path)
    annotation_path.parent.mkdir(parents=True, exist_ok=True)
    exists = annotation_path.exists() and annotation_path.stat().st_size > 0
    pd.DataFrame([{
        "timestamp_start": float(start), "timestamp_end": float(end),
        "src_ip": src_ip, "dst_ip": dst_ip, "label": label, "scenario": scenario,
    }]).to_csv(annotation_path, mode="a", header=not exists, index=False)
