"""Build temporal directed communication graphs from engineered flow records."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import networkx as nx
import pandas as pd

from ..schema import FLOW_FEATURE_COLUMNS, NODE_FEATURE_NAMES

EDGE_FEATURES = ["packets_delta", "bytes_delta", "packet_rate", "byte_rate", "duration_sec"]


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if pd.notna(number) else default
    except (TypeError, ValueError):
        return default


def build_graph_snapshots(
    flows: pd.DataFrame,
    window_seconds: int = 10,
) -> list[dict[str, Any]]:
    """Build one graph document per time window.

    Nodes are IP endpoints. A node label describes the observed source host:
    1 if its outgoing flow is annotated suspicious, 0 if normal, and -1 if
    there is no ground truth for that host in that window.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    if flows.empty:
        return []

    data = flows.copy()
    for required in [
        "timestamp", "ip_src", "ip_dst", "label", *FLOW_FEATURE_COLUMNS
    ]:
        if required not in data.columns:
            data[required] = -1 if required == "label" else 0

    data["timestamp"] = pd.to_numeric(data["timestamp"], errors="coerce")
    data = data.dropna(subset=["timestamp"])
    data["src_ip"] = data["ip_src"].fillna("").astype(str)
    data["dst_ip"] = data["ip_dst"].fillna("").astype(str)
    data = data[
        (data["src_ip"] != "")
        & (data["dst_ip"] != "")
        & (data["src_ip"] != "nan")
        & (data["dst_ip"] != "nan")
    ].copy()
    if data.empty:
        return []

    data["window_id"] = (data["timestamp"] // window_seconds).astype("int64")
    snapshots: list[dict[str, Any]] = []

    for window_id, group in data.groupby("window_id", sort=True):
        graph = nx.DiGraph()
        node_labels: dict[str, list[int]] = defaultdict(list)
        edge_records: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)

        for row in group.to_dict(orient="records"):
            src, dst = row["src_ip"], row["dst_ip"]
            label = int(_safe_number(row.get("label", -1), -1))
            if label in (0, 1):
                node_labels[src].append(label)

            graph.add_node(src)
            graph.add_node(dst)
            edge_records[(src, dst)].append(
                {
                    feature: _safe_number(row.get(feature, 0))
                    for feature in EDGE_FEATURES
                }
            )

        for (src, dst), records in edge_records.items():
            graph.add_edge(src, dst, records=records)

        node_rows: list[dict[str, Any]] = []
        for node in sorted(graph.nodes):
            outgoing = [
                record
                for neighbor in graph.successors(node)
                for record in graph[node][neighbor]["records"]
            ]
            incoming = [
                record
                for neighbor in graph.predecessors(node)
                for record in graph[neighbor][node]["records"]
            ]
            outgoing_rows = group[group["src_ip"] == node]
            incoming_rows = group[group["dst_ip"] == node]

            dst_ports = set()
            for value in outgoing_rows.get("dst_port_num", pd.Series(dtype=float)).tolist():
                number = int(_safe_number(value, -1))
                if number >= 0:
                    dst_ports.add(number)

            feature_values = [
                float(len(outgoing)),
                float(len(incoming)),
                float(outgoing_rows["dst_ip"].nunique()),
                float(incoming_rows["src_ip"].nunique()),
                float(len(dst_ports)),
                sum(item["packets_delta"] for item in outgoing),
                sum(item["packets_delta"] for item in incoming),
                sum(item["bytes_delta"] for item in outgoing),
                sum(item["bytes_delta"] for item in incoming),
                _mean([item["packet_rate"] for item in outgoing]),
                _mean([item["byte_rate"] for item in outgoing]),
                _mean([item["duration_sec"] for item in outgoing]),
            ]
            labels = node_labels.get(node, [])
            node_label = max(labels) if labels else -1
            node_rows.append(
                {
                    "id": node,
                    "features": feature_values,
                    "label": node_label,
                    "label_count": len(labels),
                }
            )

        edge_rows: list[dict[str, Any]] = []
        for (src, dst), records in sorted(edge_records.items()):
            edge_label_values = group[
                (group["src_ip"] == src) & (group["dst_ip"] == dst)
            ]["label"].tolist()
            known_labels = [
                int(_safe_number(value, -1)) for value in edge_label_values
                if int(_safe_number(value, -1)) in (0, 1)
            ]
            edge_rows.append(
                {
                    "source": src,
                    "target": dst,
                    "features": [
                        _mean([item[name] for item in records])
                        for name in EDGE_FEATURES
                    ],
                    "label": max(known_labels) if known_labels else -1,
                    "observations": len(records),
                }
            )

        snapshots.append(
            {
                "timestamp": float(group["timestamp"].max()),
                "window_id": int(window_id),
                "node_feature_names": NODE_FEATURE_NAMES,
                "edge_feature_names": EDGE_FEATURES,
                "nodes": node_rows,
                "edges": edge_rows,
            }
        )
    return snapshots


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
