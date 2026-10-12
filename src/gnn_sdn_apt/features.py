"""Flow normalization and counter-delta feature engineering."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .labels import label_flow, load_annotations
from .schema import FLOW_FEATURE_COLUMNS, RAW_COLUMNS

FLOW_KEY = [
    "datapath_id", "in_port", "eth_src", "eth_dst", "ip_src", "ip_dst",
    "ip_proto", "src_port", "dst_port",
]


def load_raw_flows(path: str | Path) -> pd.DataFrame:
    """Read raw Ryu output and validate its minimum schema."""
    raw_path = Path(path)
    if not raw_path.exists():
        raise FileNotFoundError(
            f"Raw flow file not found: {raw_path}. Start Ryu and generate lab traffic first."
        )
    frame = pd.read_csv(raw_path)
    if frame.empty:
        return pd.DataFrame(columns=RAW_COLUMNS)
    for column in RAW_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan
    frame["timestamp"] = pd.to_numeric(frame["timestamp"], errors="coerce")
    frame = frame.dropna(subset=["timestamp"]).copy()
    return frame.sort_values("timestamp").reset_index(drop=True)


def engineer_flow_features(
    raw: pd.DataFrame,
    annotations_path: str | Path | None = None,
    default_window_seconds: float = 5.0,
) -> pd.DataFrame:
    """Convert cumulative OpenFlow counters to per-poll deltas and rates.

    The first observation for a flow uses its current counter values. Later
    observations use counter differences; counter resets are handled by using
    the new value rather than producing a negative rate.
    """
    if default_window_seconds <= 0:
        raise ValueError("default_window_seconds must be positive")
    if raw.empty:
        return pd.DataFrame(
            columns=RAW_COLUMNS + FLOW_FEATURE_COLUMNS + ["label", "scenario"]
        )

    frame = raw.copy()
    frame["_existing_label"] = (
        pd.to_numeric(frame["label"], errors="coerce")
        if "label" in frame.columns
        else -1
    )
    frame["_record_mode"] = (
        frame["record_mode"].fillna("counter").astype(str)
        if "record_mode" in frame.columns
        else "counter"
    )
    frame["_existing_scenario"] = (
        frame["scenario"].fillna("unlabeled").astype(str)
        if "scenario" in frame.columns
        else "unlabeled"
    )
    for column in RAW_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan

    numeric_columns = [
        "timestamp", "datapath_id", "in_port", "ip_proto", "src_port",
        "dst_port", "packet_count", "byte_count", "duration_sec",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    for column in FLOW_KEY:
        frame[column] = frame[column].fillna("").astype(str)

    frame["packet_count"] = frame["packet_count"].fillna(0).clip(lower=0)
    frame["byte_count"] = frame["byte_count"].fillna(0).clip(lower=0)
    frame = frame.sort_values(["timestamp"] + FLOW_KEY).reset_index(drop=True)

    group = frame.groupby(FLOW_KEY, dropna=False, sort=False)
    previous_packets = group["packet_count"].shift(1)
    previous_bytes = group["byte_count"].shift(1)
    previous_time = group["timestamp"].shift(1)

    frame["packets_delta"] = frame["packet_count"] - previous_packets
    frame["bytes_delta"] = frame["byte_count"] - previous_bytes
    frame["poll_seconds"] = frame["timestamp"] - previous_time

    first = previous_packets.isna()
    reset_packets = frame["packets_delta"] < 0
    reset_bytes = frame["bytes_delta"] < 0
    frame.loc[first | reset_packets, "packets_delta"] = frame.loc[
        first | reset_packets, "packet_count"
    ]
    frame.loc[first | reset_bytes, "bytes_delta"] = frame.loc[
        first | reset_bytes, "byte_count"
    ]
    invalid_interval = frame["poll_seconds"].isna() | (frame["poll_seconds"] <= 0)
    frame.loc[invalid_interval, "poll_seconds"] = default_window_seconds

    frame["packets_delta"] = frame["packets_delta"].fillna(0).clip(lower=0)
    frame["bytes_delta"] = frame["bytes_delta"].fillna(0).clip(lower=0)

    # Public IDS exports contain independent completed-flow records, not
    # cumulative counters. Never subtract a prior row from such a record,
    # even when the same five-tuple appears more than once in the CSV.
    flow_record_mask = frame["_record_mode"].eq("flow_record")
    frame.loc[flow_record_mask, "packets_delta"] = frame.loc[
        flow_record_mask, "packet_count"
    ]
    frame.loc[flow_record_mask, "bytes_delta"] = frame.loc[
        flow_record_mask, "byte_count"
    ]

    frame["packet_rate"] = frame["packets_delta"] / frame["poll_seconds"]
    frame["byte_rate"] = frame["bytes_delta"] / frame["poll_seconds"]

    frame["duration_sec"] = pd.to_numeric(frame["duration_sec"], errors="coerce").fillna(0)
    flow_record_with_duration = flow_record_mask & (frame["duration_sec"] > 0)
    frame["ip_proto_num"] = pd.to_numeric(frame["ip_proto"], errors="coerce").fillna(-1)
    frame["src_port_num"] = pd.to_numeric(frame["src_port"], errors="coerce").fillna(-1)
    frame["dst_port_num"] = pd.to_numeric(frame["dst_port"], errors="coerce").fillna(-1)
    frame["in_port_num"] = pd.to_numeric(frame["in_port"], errors="coerce").fillna(-1)

    # Public IDS CSVs store one completed flow per row rather than cumulative
    # switch counters. In that mode, use each flow duration for rates.
    frame.loc[flow_record_with_duration, "packet_rate"] = (
        frame.loc[flow_record_with_duration, "packets_delta"]
        / frame.loc[flow_record_with_duration, "duration_sec"]
    )
    frame.loc[flow_record_with_duration, "byte_rate"] = (
        frame.loc[flow_record_with_duration, "bytes_delta"]
        / frame.loc[flow_record_with_duration, "duration_sec"]
    )
    frame.loc[flow_record_mask & ~flow_record_with_duration, ["packet_rate", "byte_rate"]] = 0.0

    annotations = (
        load_annotations(annotations_path)
        if annotations_path is not None
        else pd.DataFrame()
    )
    labels = [
        label_flow(float(row.timestamp), str(row.ip_src), str(row.ip_dst), annotations)
        for row in frame.itertuples(index=False)
    ] if not annotations.empty else [(-1, "unlabeled")] * len(frame)

    merged_labels = []
    merged_scenarios = []
    for index, (annotation_label, annotation_scenario) in enumerate(labels):
        original_label = frame["_existing_label"].iloc[index]
        if annotation_label in (0, 1):
            merged_labels.append(int(annotation_label))
            merged_scenarios.append(annotation_scenario)
        elif pd.notna(original_label) and int(original_label) in (0, 1):
            merged_labels.append(int(original_label))
            merged_scenarios.append(str(frame["_existing_scenario"].iloc[index]))
        else:
            merged_labels.append(-1)
            merged_scenarios.append("unlabelled")
    frame["label"] = merged_labels
    frame["scenario"] = merged_scenarios
    frame = frame.drop(columns=["_existing_label", "_existing_scenario", "_record_mode"])

    frame = frame.replace([np.inf, -np.inf], np.nan)
    for column in FLOW_FEATURE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    return frame


def prepare_flow_file(
    raw_path: str | Path,
    output_path: str | Path,
    annotations_path: str | Path | None = None,
    default_window_seconds: float = 5.0,
) -> pd.DataFrame:
    """Read raw flow counters, engineer features and persist a CSV."""
    raw = load_raw_flows(raw_path)
    features = engineer_flow_features(
        raw,
        annotations_path=annotations_path,
        default_window_seconds=default_window_seconds,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(destination, index=False)
    return features
