"""Generate a synthetic capture for an end-to-end software smoke test.

This is deterministic benchmark plumbing only. It is not a real capture and
must never be used as empirical evidence for APT detection performance.
"""
from __future__ import annotations

from pathlib import Path
import random

import pandas as pd

from .schema import LABEL_COLUMNS, RAW_COLUMNS


def generate_demo_capture(
    raw_path: str | Path,
    labels_path: str | Path,
    polls: int = 40,
    seed: int = 17,
) -> dict[str, int | str]:
    """Write Ryu-shaped cumulative counters plus separate binary annotations.

    Every ten-second window contains a normal source and a suspicious source,
    making this small fixture suitable for exercising chronological train,
    validation and test splits. The events are synthetic and have no claim of
    realism.
    """
    if polls < 12:
        raise ValueError("polls must be >= 12 to cover temporal train/validation/test splits.")

    rng = random.Random(seed)
    raw_file = Path(raw_path)
    annotation_file = Path(labels_path)
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    annotation_file.parent.mkdir(parents=True, exist_ok=True)

    start_time = 1_800_000_000.0  # divisible by the default ten-second graph window
    interval = 5.0
    counter_state: dict[tuple, dict[str, float]] = {}
    records: list[dict] = []

    hosts = {
        "10.0.0.1": ("00:00:00:00:00:01", "normal"),
        "10.0.0.2": ("00:00:00:00:00:02", "server"),
        "10.0.0.3": ("00:00:00:00:00:03", "suspect"),
        **{
            f"10.0.0.{host}": (f"00:00:00:00:00:{host:02x}", "target")
            for host in range(4, 9)
        },
    }

    for index in range(polls):
        timestamp = start_time + index * interval

        # Repeated TCP flow with increasing cumulative OpenFlow counters.
        normal_src, normal_dst = "10.0.0.1", "10.0.0.2"
        normal_key = (normal_src, normal_dst, 6, 40100, 80)
        packet_delta = 3 + (index % 3)
        normal_state = counter_state.setdefault(
            normal_key, {"packets": 0.0, "bytes": 0.0, "first_seen": timestamp}
        )
        normal_state["packets"] += packet_delta
        normal_state["bytes"] += packet_delta * 160
        records.append({
            "timestamp": timestamp,
            "datapath_id": 1,
            "in_port": 1,
            "eth_src": hosts[normal_src][0],
            "eth_dst": hosts[normal_dst][0],
            "ip_src": normal_src,
            "ip_dst": normal_dst,
            "ip_proto": 6,
            "src_port": 40100,
            "dst_port": 80,
            "packet_count": normal_state["packets"],
            "byte_count": normal_state["bytes"],
            "duration_sec": timestamp - normal_state["first_seen"] + interval,
        })

        # Bounded, synthetic source fan-out to fixed private lab destinations.
        target_octet = 4 + (index % 5)
        port_choices = [22, 23, 80, 443, 445, 3389, 8080]
        port_index = index % len(port_choices)
        suspect_src = "10.0.0.3"
        suspect_dst = f"10.0.0.{target_octet}"
        suspect_port = port_choices[port_index]
        suspect_src_port = 45000 + (target_octet * 10) + port_index
        suspect_key = (suspect_src, suspect_dst, 6, suspect_src_port, suspect_port)
        state = counter_state.setdefault(
            suspect_key, {"packets": 0.0, "bytes": 0.0, "first_seen": timestamp}
        )
        packet_delta = 1 + (index % 2)
        state["packets"] += packet_delta
        state["bytes"] += packet_delta * rng.randint(45, 115)
        records.append({
            "timestamp": timestamp,
            "datapath_id": 1,
            "in_port": 3,
            "eth_src": hosts[suspect_src][0],
            "eth_dst": hosts[suspect_dst][0],
            "ip_src": suspect_src,
            "ip_dst": suspect_dst,
            "ip_proto": 6,
            "src_port": suspect_src_port,
            "dst_port": suspect_port,
            "packet_count": state["packets"],
            "byte_count": state["bytes"],
            "duration_sec": timestamp - state["first_seen"] + interval,
        })

    pd.DataFrame(records, columns=RAW_COLUMNS).to_csv(raw_file, index=False)
    final_time = start_time + (polls - 1) * interval + interval
    annotations = pd.DataFrame([
        {
            "timestamp_start": start_time - 1,
            "timestamp_end": final_time + 1,
            "src_ip": "10.0.0.1",
            "dst_ip": "",
            "label": 0,
            "scenario": "synthetic_normal",
        },
        {
            "timestamp_start": start_time - 1,
            "timestamp_end": final_time + 1,
            "src_ip": "10.0.0.3",
            "dst_ip": "",
            "label": 1,
            "scenario": "synthetic_suspicious",
        },
    ], columns=LABEL_COLUMNS)
    annotations.to_csv(annotation_file, index=False)
    return {
        "raw_file": str(raw_file),
        "labels_file": str(annotation_file),
        "polls": polls,
        "rows": len(records),
        "graph_windows_expected": (polls + 1) // 2,
        "note": "Synthetic software-smoke-test data only; not real attack evidence.",
    }
