"""Incremental, restart-safe ingestion of Ryu's append-only CSV export."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .siem import SQLiteSiemStore, correlate_events


def _cursor_connect(database_path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(database_path))
    db.execute("""
        CREATE TABLE IF NOT EXISTS ryu_ingest_cursor (
            source_path TEXT PRIMARY KEY,
            file_signature TEXT NOT NULL,
            header_hash TEXT NOT NULL,
            byte_offset INTEGER NOT NULL,
            next_line INTEGER NOT NULL,
            checkpoint_hash TEXT NOT NULL DEFAULT ''
        )
    """)
    columns = {row[1] for row in db.execute("PRAGMA table_info(ryu_ingest_cursor)")}
    if "checkpoint_hash" not in columns:
        db.execute(
            "ALTER TABLE ryu_ingest_cursor ADD COLUMN checkpoint_hash TEXT NOT NULL DEFAULT ''"
        )
    return db


def ingest_ryu_csv_incremental(
    raw_path: str | Path,
    database_path: str | Path,
    *,
    window_seconds: int = 60,
    min_distinct_destinations: int = 5,
) -> dict[str, Any]:
    """Consume only complete CSV records added since the previous successful poll.

    The byte cursor is persisted in SQLite. Replayed rows remain idempotent,
    file replacement/truncation resets the cursor, and a trailing partial line
    is held until its newline arrives.
    """
    if window_seconds < 1 or min_distinct_destinations < 2:
        raise ValueError("invalid SIEM correlation settings")
    source = Path(raw_path)
    if not source.exists() or source.stat().st_size == 0:
        return {
            "events_read": 0, "recent_events": 0, "findings": 0,
            "database": str(database_path), "cursor_reset": False,
        }

    store = SQLiteSiemStore(database_path)
    source_key = str(source.resolve())
    stat = source.stat()
    signature = f"{stat.st_dev}:{stat.st_ino}"

    with source.open("rb") as handle:
        header_bytes = handle.readline()
        if not header_bytes.endswith(b"\n"):
            return {
                "events_read": 0, "recent_events": 0, "findings": 0,
                "database": str(database_path), "cursor_reset": False,
            }
        header_hash = hashlib.sha256(header_bytes).hexdigest()
        handle.seek(0)
        with _cursor_connect(database_path) as db:
            saved = db.execute(
                "SELECT file_signature, header_hash, byte_offset, next_line, checkpoint_hash "
                "FROM ryu_ingest_cursor WHERE source_path=?",
                (source_key,),
            ).fetchone()

        checkpoint_matches = True
        if saved is not None and int(saved[2]) > 0 and saved[4]:
            saved_offset = int(saved[2])
            handle.seek(max(0, saved_offset - 256))
            checkpoint = handle.read(saved_offset - max(0, saved_offset - 256))
            checkpoint_matches = hashlib.sha256(checkpoint).hexdigest() == saved[4]
        reset = (
            saved is None
            or saved[0] != signature
            or saved[1] != header_hash
            or stat.st_size < int(saved[2])
            or not checkpoint_matches
        )
        if reset:
            offset, next_line = 0, 2
        else:
            offset, next_line = int(saved[2]), int(saved[3])

        handle.seek(offset)
        pending = handle.read()
        last_newline = pending.rfind(b"\n")
        if last_newline < 0:
            return {
                "events_read": 0, "recent_events": 0, "findings": 0,
                "database": str(database_path), "cursor_reset": reset,
            }
        complete = pending[: last_newline + 1]
        new_offset = offset + len(complete)
        text = complete.decode("utf-8-sig" if offset == 0 else "utf-8")
        if offset > 0:
            header = header_bytes.decode("utf-8-sig")
            text = header + text

    reader = csv.DictReader(io.StringIO(text, newline=""))
    required = {"timestamp", "ip_src", "ip_dst"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError("Ryu CSV must contain timestamp, ip_src and ip_dst columns")

    events_read = 0
    current_line = 2 if offset == 0 else next_line
    for row in reader:
        line_number = current_line
        current_line += 1
        if not row.get("ip_src") or not row.get("ip_dst") or not row.get("timestamp"):
            continue
        identity = json.dumps(
            {"signature": signature, "line": line_number, "row": row},
            sort_keys=True,
            separators=(",", ":"),
        )
        event_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        store.add_event({
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
        events_read += 1

    # Commit the cursor only after all complete rows have been persisted.
    # A crash before this point replays rows safely through stable event IDs.
    with source.open("rb") as handle:
        checkpoint_start = max(0, new_offset - 256)
        handle.seek(checkpoint_start)
        checkpoint = handle.read(new_offset - checkpoint_start)
    checkpoint_hash = hashlib.sha256(checkpoint).hexdigest()
    with _cursor_connect(database_path) as db:
        db.execute(
            """INSERT INTO ryu_ingest_cursor
            (source_path,file_signature,header_hash,byte_offset,next_line,checkpoint_hash)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(source_path) DO UPDATE SET
              file_signature=excluded.file_signature,
              header_hash=excluded.header_hash,
              byte_offset=excluded.byte_offset,
              next_line=excluded.next_line,
              checkpoint_hash=excluded.checkpoint_hash""",
            (source_key, signature, header_hash, new_offset, current_line, checkpoint_hash),
        )

    all_recent = store.list_events(limit=10000)
    if all_recent:
        newest = max(
            datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")).timestamp()
            for item in all_recent
        )
        recent = [
            item for item in all_recent
            if datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")).timestamp()
            >= newest - window_seconds
        ]
    else:
        recent = []
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
        "events_read": events_read,
        "recent_events": len(recent),
        "findings": len(findings),
        "database": str(database_path),
        "cursor_reset": reset,
    }
