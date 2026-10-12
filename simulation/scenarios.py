"""Reproducible, annotated traffic scenarios for the isolated Mininet topology."""
from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LABELS_PATH = ROOT / "data" / "raw" / "scenario_labels.csv"
CLIENT_SCRIPT = Path(__file__).resolve().parent / "scenario_client.py"


def _append_label(start: float, end: float, src_ip: str, dst_ip: str, label: int, scenario: str) -> None:
    LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    exists = LABELS_PATH.exists() and LABELS_PATH.stat().st_size > 0
    with LABELS_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp_start", "timestamp_end", "src_ip", "dst_ip", "label", "scenario"],
        )
        if not exists:
            writer.writeheader()
        writer.writerow({
            "timestamp_start": start,
            "timestamp_end": end,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "label": label,
            "scenario": scenario,
        })


def run_scenario(net: Any, name: str) -> str:
    """Run a named bounded scenario and record labels around the observation window."""
    normalized = name.strip().lower()
    addresses = {host.name: host.IP() for host in net.hosts}
    script = str(CLIENT_SCRIPT)
    start = time.time()

    if normalized == "normal":
        net.get("h1").cmd(f"ping -c 3 -W 1 {addresses['h2']}")
        net.get("h2").cmd(f"ping -c 3 -W 1 {addresses['h3']}")
        _append_label(start - 1, time.time() + 7, addresses["h1"], addresses["h2"], 0, "normal_ping")
        _append_label(start - 1, time.time() + 7, addresses["h2"], addresses["h3"], 0, "normal_ping")
        return "Normal ping scenario completed and labeled."

    if normalized == "recon":
        src = net.get("h1")
        targets = ",".join(addresses[name] for name in ("h2", "h3", "h4", "h5"))
        src.cmd(f"python3 {script} scan --targets {targets} --ports 21,22,23,80,443,445,8080")
        _append_label(start - 1, time.time() + 7, addresses["h1"], "", 1, "controlled_reconnaissance")
        return "Bounded TCP connection-attempt scenario completed and labeled."

    if normalized == "lateral":
        src = net.get("h2")
        targets = ",".join(addresses[name] for name in ("h3", "h4", "h5"))
        src.cmd(f"python3 {script} scan --targets {targets} --ports 22,80,443,445,9001")
        _append_label(start - 1, time.time() + 7, addresses["h2"], "", 1, "simulated_lateral_movement")
        return "Internal host-to-host connection scenario completed and labeled."

    if normalized == "exfil":
        receiver = net.get("h5")
        sender = net.get("h4")
        receiver.cmd(
            f"python3 {script} listen --port 9001 --seconds 15 "
            "--output /tmp/gnn-sdn-received-bytes.txt >/tmp/gnn-sdn-listener.log 2>&1 &"
        )
        time.sleep(0.5)
        sender.cmd(f"python3 {script} send --target {addresses['h5']} --port 9001 --bytes 131072")
        _append_label(start - 1, time.time() + 7, addresses["h4"], addresses["h5"], 1, "simulated_data_transfer")
        return "Fixed-size dummy transfer to the lab sink completed and labeled."

    return "Unknown scenario. Use: normal, recon, lateral, exfil."
