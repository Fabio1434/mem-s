"""Bridge the Ryu CSV collector into the lightweight SIEM store."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .siem import SQLiteSiemStore, correlate_events


def ingest_ryu_csv(
    raw_path: str | Path,
    database_path: str | Path,
    *,
    window_seconds: int = 60,
    min_distinct_destinations: int = 5,
) -> dict[str, Any]:
    """Ingest Ryu's append-only flow_stats.csv and persist current findings.

    Stable event IDs make repeated polling idempotent. Correlation is restricted
    to the newest observed time window, so old traffic is not re-alerted forever.
    """
    if window_seconds < 1 or min_distinct_destinations < 2:
        raise ValueError("invalid SIEM correlation settings")
    source = Path(raw_path)
    if not source.exists() or source.stat().st_size == 0:
        return {"events_read": 0, "findings": 0, "database": str(database_path)}

    store = SQLiteSiemStore(database_path)
    events: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8", newline="") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            if not row.get("ip_src") or not row.get("ip_dst") or not row.get("timestamp"):
                continue
            identity = json.dumps(
                {"line": line_number, "row": row},
                sort_keys=True,
                separators=(",", ":"),
            )
            event_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            event = store.add_event({
                "event_id": event_id,
                "timestamp": float(row["timestamp"]),
                "source_component": "ryu_openflow",
                "event_type": "flow_stats",
                "src_ip": row["ip_src"],
                "dst_ip": row["ip_dst"],
                "src_port": row.get("src_port"),
                "dst_port": row.get("dst_port"),
                "protocol": row.get("ip_proto"),
                "datapath_id": row.get("datapath_id"),
                "label": row.get("label", -1),
                "payload": {
                    key: row.get(key)
                    for key in ("in_port", "packet_count", "byte_count", "duration_sec")
                },
            })
            events.append(event)

    if not events:
        return {"events_read": 0, "findings": 0, "database": str(database_path)}

    newest = max(
        datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).timestamp()
        for e in events
    )
    recent = [
        event for event in events
        if datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")).timestamp()
        >= newest - window_seconds
    ]
    findings = correlate_events(
        recent,
        window_seconds=window_seconds,
        min_distinct_destinations=min_distinct_destinations,
    )
    previous = {item["incident_id"]: item for item in store.list_incidents()}
    for finding in findings:
        existing = previous.get(finding["incident_id"])
        if existing:
            finding["status"] = existing["status"]
        store.upsert_incident(finding)

    return {
        "events_read": len(events),
        "recent_events": len(recent),
        "findings": len(findings),
        "database": str(database_path),
    }
