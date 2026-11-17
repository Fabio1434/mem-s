"""Lightweight SIEM primitives for the isolated SDN research lab.

This module is intentionally independent from Ryu/Mininet so ingestion,
normalization, correlation and incident persistence can be tested offline.
It does not execute network mitigation.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


def _utc_timestamp(value: Any = None) -> str:
    """Return an ISO-8601 UTC timestamp; accept epoch seconds or ISO strings."""
    if value is None or value == "":
        dt = datetime.now(timezone.utc)
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    else:
        raw = str(value).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize_event(raw: Mapping[str, Any], *, source_component: str = "unknown") -> dict[str, Any]:
    """Normalize a raw observation into the project's canonical SIEM event."""
    if not isinstance(raw, Mapping):
        raise TypeError("raw event must be a mapping")
    event = {
        "event_id": str(raw.get("event_id") or uuid.uuid4()),
        "timestamp": _utc_timestamp(raw.get("timestamp")),
        "source_component": str(raw.get("source_component") or source_component),
        "event_type": str(raw.get("event_type") or "flow_observation"),
        "src_ip": raw.get("src_ip") or raw.get("ip_src"),
        "dst_ip": raw.get("dst_ip") or raw.get("ip_dst"),
        "src_port": raw.get("src_port"),
        "dst_port": raw.get("dst_port"),
        "protocol": raw.get("protocol", raw.get("ip_proto")),
        "datapath_id": raw.get("datapath_id"),
        "host": raw.get("host") or raw.get("src_ip") or raw.get("ip_src"),
        "label": raw.get("label", -1),
        "payload": dict(raw.get("payload") or {}),
    }
    # Keep additional source fields without overwriting canonical keys.
    reserved = set(event)
    event["payload"].update({k: v for k, v in raw.items() if k not in reserved and k != "payload"})
    return event


class JsonlEventStore:
    """Append-only JSONL event store; each event is one UTF-8 JSON record."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: Mapping[str, Any]) -> None:
        normalized = normalize_event(event)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(normalized, ensure_ascii=False, sort_keys=True) + "\n")

    def read(self) -> Iterable[dict[str, Any]]:
        if not self.path.exists():
            return []
        def records():
            with self.path.open("r", encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"invalid JSONL at line {line_number}") from exc
                    yield item
        return records()


class SQLiteSiemStore:
    """Small SQLite backend for events and incident lifecycle."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    source_component TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    src_ip TEXT,
                    dst_ip TEXT,
                    label INTEGER NOT NULL DEFAULT -1,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_src_time ON events(src_ip, timestamp);
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    host TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    event_ids_json TEXT NOT NULL,
                    summary TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
                CREATE TABLE IF NOT EXISTS incident_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    old_status TEXT NOT NULL,
                    new_status TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    note TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_incident_history_id ON incident_history(incident_id, history_id);
            """)

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def add_event(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        event = normalize_event(raw)
        with self._connect() as db:
            db.execute(
                """INSERT OR IGNORE INTO events
                (event_id,timestamp,source_component,event_type,src_ip,dst_ip,label,payload_json)
                VALUES (?,?,?,?,?,?,?,?)""",
                (event["event_id"], event["timestamp"], event["source_component"],
                 event["event_type"], event["src_ip"], event["dst_ip"],
                 int(event["label"] if event["label"] is not None else -1),
                 json.dumps(event, ensure_ascii=False, sort_keys=True)),
            )
        return event

    def list_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as db:
            rows = db.execute(
                "SELECT payload_json FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def upsert_incident(self, incident: Mapping[str, Any]) -> dict[str, Any]:
        required = ("incident_id", "rule_id", "host", "status", "severity",
                    "confidence", "first_seen", "last_seen", "summary")
        missing = [key for key in required if key not in incident]
        if missing:
            raise ValueError("missing incident fields: " + ", ".join(missing))
        record = dict(incident)
        record.setdefault("event_ids", [])
        with self._connect() as db:
            db.execute(
                """INSERT INTO incidents
                (incident_id,rule_id,host,status,severity,confidence,first_seen,last_seen,event_ids_json,summary)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(incident_id) DO UPDATE SET
                  status=excluded.status, severity=excluded.severity,
                  confidence=excluded.confidence, last_seen=excluded.last_seen,
                  event_ids_json=excluded.event_ids_json, summary=excluded.summary""",
                (record["incident_id"], record["rule_id"], record["host"], record["status"],
                 record["severity"], float(record["confidence"]), record["first_seen"],
                 record["last_seen"], json.dumps(record["event_ids"]), record["summary"]),
            )
        return record

    def list_incidents(self, *, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            if status:
                rows = db.execute("SELECT * FROM incidents WHERE status=? ORDER BY last_seen DESC",
                                  (status,)).fetchall()
            else:
                rows = db.execute("SELECT * FROM incidents ORDER BY last_seen DESC").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["event_ids"] = json.loads(item.pop("event_ids_json"))
            result.append(item)
        return result


    def transition_incident(
        self,
        incident_id: str,
        new_status: str,
        *,
        changed_by: str = "system",
        note: str = "",
    ) -> dict[str, Any]:
        """Apply an allowed incident-state transition and append an audit record."""
        transitions = {
            "open": {"investigating", "contained", "closed"},
            "investigating": {"open", "contained", "closed"},
            "contained": {"investigating", "closed"},
            "closed": set(),
        }
        if new_status not in transitions:
            raise ValueError(f"unknown incident status: {new_status}")
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM incidents WHERE incident_id=?", (incident_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"incident not found: {incident_id}")
            old_status = row["status"]
            if new_status == old_status:
                return self._incident_row(row)
            if new_status not in transitions.get(old_status, set()):
                raise ValueError(f"transition not allowed: {old_status} -> {new_status}")
            changed_at = _utc_timestamp()
            db.execute(
                "UPDATE incidents SET status=? WHERE incident_id=?",
                (new_status, incident_id),
            )
            db.execute(
                """INSERT INTO incident_history
                (incident_id,changed_at,old_status,new_status,changed_by,note)
                VALUES (?,?,?,?,?,?)""",
                (incident_id, changed_at, old_status, new_status,
                 str(changed_by), str(note)),
            )
            updated = db.execute(
                "SELECT * FROM incidents WHERE incident_id=?", (incident_id,)
            ).fetchone()
        return self._incident_row(updated)

    @staticmethod
    def _incident_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["event_ids"] = json.loads(item.pop("event_ids_json"))
        return item

    def list_incident_history(self, incident_id: str) -> list[dict[str, Any]]:
        """Return the append-only status-transition audit trail for one incident."""
        with self._connect() as db:
            rows = db.execute(
                """SELECT changed_at,old_status,new_status,changed_by,note
                FROM incident_history WHERE incident_id=? ORDER BY history_id""",
                (incident_id,),
            ).fetchall()
        return [dict(row) for row in rows]


def correlate_events(
    events: Iterable[Mapping[str, Any]], *, window_seconds: int = 60,
    min_distinct_destinations: int = 5,
) -> list[dict[str, Any]]:
    """Detect explainable fan-out/reconnaissance patterns per source host.

    Only explicit observations are used. Unknown labels remain unknown (-1);
    this rule output is an analytic finding, not proof of an APT.
    """
    if window_seconds < 1 or min_distinct_destinations < 2:
        raise ValueError("window_seconds must be >= 1 and min_distinct_destinations >= 2")
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for raw in events:
        event = normalize_event(raw)
        host = event.get("src_ip") or event.get("host")
        destination = event.get("dst_ip")
        if not host or not destination:
            continue
        epoch = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")).timestamp()
        bucket = int(epoch // window_seconds)
        groups[(str(host), bucket)].append(event)

    findings = []
    for (host, bucket), observations in groups.items():
        destinations = sorted({e["dst_ip"] for e in observations if e.get("dst_ip")})
        if len(destinations) < min_distinct_destinations:
            continue
        timestamps = [e["timestamp"] for e in observations]
        findings.append({
            "incident_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"sdn-recon:{host}:{bucket}")),
            "rule_id": "SDN-RECON-FANOUT-001",
            "host": host,
            "status": "open",
            "severity": "medium" if len(destinations) < min_distinct_destinations * 2 else "high",
            "confidence": min(0.99, 0.55 + 0.05 * (len(destinations) - min_distinct_destinations)),
            "first_seen": min(timestamps),
            "last_seen": max(timestamps),
            "event_ids": sorted({e["event_id"] for e in observations}),
            "summary": f"{host} contacted {len(destinations)} distinct destinations in a {window_seconds}s window.",
            "evidence": {"distinct_destinations": destinations, "observation_count": len(observations)},
        })
    return sorted(findings, key=lambda item: (item["first_seen"], item["host"]))
