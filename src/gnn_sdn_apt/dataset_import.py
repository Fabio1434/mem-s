"""Import common timestamped flow datasets into the project's normalized schema."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from .schema import RAW_COLUMNS


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


ALIASES = {
    "timestamp": ["timestamp", "stime", "starttime", "flowstart", "startdatetime"],
    "ip_src": ["ipsrc", "srcip", "sourceip", "sourceaddress", "srcaddress"],
    "ip_dst": ["ipdst", "dstip", "destinationip", "destinationaddress", "dstaddress"],
    "src_port": ["srcport", "sport", "sourceport"],
    "dst_port": ["dstport", "dsport", "destinationport"],
    "ip_proto": ["ipproto", "proto", "protocol"],
    "packet_count": [
        "packetcount", "packets", "totfwdpackets", "totalfwdpackets", "spkts", "fwdpackets"
    ],
    "byte_count": [
        "bytecount", "bytes", "sbytes", "totallengthoffwdpackets",
        "totalfwdbytes", "fwdbytes", "totlenfwdpkts"
    ],
    "duration_sec": ["durationsec", "duration", "dur", "flowduration", "flowdurationus"],
    "label": ["label", "attackcat", "attackcategory", "class", "target"],
}
BENIGN_LABELS = {"benign", "normal", "normaltraffic", "0", "false", "none", "-", "nan"}
UNLABELED_LABELS = {"", "unknown", "unlabeled", "unlabelled", "?"}


def _resolve_column(columns: list[str], target: str) -> str | None:
    keyed = {_key(column): column for column in columns}
    for alias in ALIASES[target]:
        if _key(alias) in keyed:
            return keyed[_key(alias)]
    return None


def _timestamps(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().mean() >= 0.95:
        return numeric
    parsed = pd.to_datetime(series, errors="coerce", utc=True, format="mixed")
    return parsed.astype("int64", copy=False).where(parsed.notna(), np.nan) / 1e9


def _labels(series: pd.Series | None, count: int) -> tuple[list[int], list[str]]:
    if series is None:
        return [-1] * count, ["unlabeled"] * count
    numeric = pd.to_numeric(series, errors="coerce")
    labels: list[int] = []
    scenarios: list[str] = []
    for original, number in zip(series.astype(str).tolist(), numeric.tolist(), strict=True):
        token = original.strip().lower()
        if token in BENIGN_LABELS:
            labels.append(0)
            scenarios.append("normal")
        elif token in UNLABELED_LABELS:
            labels.append(-1)
            scenarios.append("unlabeled")
        elif pd.notna(number) and number in (0, 1):
            labels.append(int(number))
            scenarios.append("normal" if number == 0 else "suspicious")
        else:
            labels.append(1)
            scenarios.append(re.sub(r"[^a-z0-9_-]+", "_", token)[:80] or "attack")
    return labels, scenarios


def import_flow_csv(input_path: str | Path, output_path: str | Path) -> dict[str, int | str]:
    """Normalize a CICFlowMeter/UNSW-like CSV into the raw flow schema.

    Labels are binary: benign/normal -> 0, labeled attacks -> 1, unknown -> -1.
    This generic attack label must not be described as an APT-specific label.
    """
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Dataset CSV not found: {source}")
    frame = pd.read_csv(source, low_memory=False)
    if frame.empty:
        raise ValueError("Dataset CSV contains no records")

    resolved = {name: _resolve_column(list(frame.columns), name) for name in ALIASES}
    missing = [name for name in ("timestamp", "ip_src", "ip_dst") if resolved[name] is None]
    if missing:
        raise ValueError(
            "Dataset is missing required timestamp/source/destination columns. "
            f"Could not map: {', '.join(missing)}. Available columns: {list(frame.columns)[:30]}"
        )

    count = len(frame)
    timestamps = _timestamps(frame[resolved["timestamp"]])
    if timestamps.isna().all():
        raise ValueError("No timestamps could be parsed from the dataset")

    def numeric_column(name: str, default: float = -1.0) -> pd.Series:
        column = resolved.get(name)
        if column is None:
            return pd.Series([default] * count, index=frame.index, dtype=float)
        return pd.to_numeric(frame[column], errors="coerce").fillna(default)

    protocol = frame[resolved["ip_proto"]].copy() if resolved["ip_proto"] else pd.Series([""] * count)
    protocol_numeric = pd.to_numeric(protocol, errors="coerce")
    protocol_lookup = {"tcp": 6, "udp": 17, "icmp": 1, "icmpv6": 58}
    protocol_values = [
        int(value) if pd.notna(value) else protocol_lookup.get(str(raw).strip().lower(), -1)
        for raw, value in zip(protocol.tolist(), protocol_numeric.tolist(), strict=True)
    ]

    duration = numeric_column("duration_sec", default=0.0).clip(lower=0)
    duration_column = resolved.get("duration_sec")
    if duration_column and _key(duration_column) in {"flowduration", "flowdurationus"}:
        duration = duration / 1_000_000.0

    src = frame[resolved["ip_src"]].fillna("").astype(str)
    dst = frame[resolved["ip_dst"]].fillna("").astype(str)
    labels, scenarios = _labels(
        frame[resolved["label"]] if resolved.get("label") else None,
        count,
    )

    normalized = pd.DataFrame({
        "timestamp": timestamps,
        "datapath_id": 0,
        "in_port": -1,
        "eth_src": [f"dataset-row-{index}" for index in range(count)],
        "eth_dst": [f"destination-{index}" for index in range(count)],
        "ip_src": src,
        "ip_dst": dst,
        "ip_proto": protocol_values,
        "src_port": numeric_column("src_port"),
        "dst_port": numeric_column("dst_port"),
        "packet_count": numeric_column("packet_count", default=0.0).clip(lower=0),
        "byte_count": numeric_column("byte_count", default=0.0).clip(lower=0),
        "duration_sec": duration,
        "label": labels,
        "scenario": scenarios,
    })
    normalized = normalized.dropna(subset=["timestamp"]).sort_values("timestamp")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(destination, index=False)
    return {
        "input_file": str(source),
        "output_file": str(destination),
        "rows_imported": int(len(normalized)),
        "normal_rows": int((normalized["label"] == 0).sum()),
        "attack_rows": int((normalized["label"] == 1).sum()),
        "unlabeled_rows": int((normalized["label"] < 0).sum()),
    }
