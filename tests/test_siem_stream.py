import csv

from gnn_sdn_apt.siem import SQLiteSiemStore
from gnn_sdn_apt.siem_stream import ingest_ryu_csv_incremental


FIELDS = [
    "timestamp", "datapath_id", "in_port", "ip_src", "ip_dst",
    "ip_proto", "src_port", "dst_port", "packet_count", "byte_count",
    "duration_sec",
]


def _row(index):
    return {
        "timestamp": 1700000000 + index,
        "datapath_id": 1,
        "in_port": 1,
        "ip_src": "10.0.0.1",
        "ip_dst": f"10.0.0.{index + 2}",
        "ip_proto": 6,
        "src_port": 40000 + index,
        "dst_port": 80,
        "packet_count": 10,
        "byte_count": 1000,
        "duration_sec": 1,
    }


def _write(path, count):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(_row(i) for i in range(count))


def _append(path, rows):
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writerows(rows)


def test_incremental_ingestion_reads_only_appended_rows_and_correlates(tmp_path):
    raw, database = tmp_path / "flow_stats.csv", tmp_path / "siem.db"
    _write(raw, 3)
    first = ingest_ryu_csv_incremental(raw, database, min_distinct_destinations=5)
    assert first["events_read"] == 3
    assert first["findings"] == 0

    _append(raw, [_row(3), _row(4)])
    second = ingest_ryu_csv_incremental(raw, database, min_distinct_destinations=5)
    assert second["events_read"] == 2
    assert second["findings"] == 1
    assert len(SQLiteSiemStore(database).list_events()) == 5

    repeated = ingest_ryu_csv_incremental(raw, database, min_distinct_destinations=5)
    assert repeated["events_read"] == 0
    assert len(SQLiteSiemStore(database).list_events()) == 5


def test_incremental_ingestion_holds_partial_record_until_newline(tmp_path):
    raw, database = tmp_path / "flow_stats.csv", tmp_path / "siem.db"
    _write(raw, 1)
    with raw.open("a", encoding="utf-8") as handle:
        handle.write("1700000001,1,1,10.0.0.1,10.0.0.3")

    first = ingest_ryu_csv_incremental(raw, database)
    assert first["events_read"] == 1
    assert len(SQLiteSiemStore(database).list_events()) == 1

    with raw.open("a", encoding="utf-8") as handle:
        handle.write(",6,40001,80,10,1000,1\n")
    second = ingest_ryu_csv_incremental(raw, database)
    assert second["events_read"] == 1
    assert len(SQLiteSiemStore(database).list_events()) == 2


def test_incremental_ingestion_resets_after_truncation_or_rotation(tmp_path):
    raw, database = tmp_path / "flow_stats.csv", tmp_path / "siem.db"
    _write(raw, 2)
    ingest_ryu_csv_incremental(raw, database)

    _write(raw, 1)
    result = ingest_ryu_csv_incremental(raw, database)
    assert result["cursor_reset"] is True
    # The rewritten row is deduplicated if its identity is unchanged.
    assert len(SQLiteSiemStore(database).list_events()) >= 1


def test_incremental_ingestion_detects_same_size_rewrite(tmp_path):
    raw, database = tmp_path / "flow_stats.csv", tmp_path / "siem.db"
    _write(raw, 2)
    ingest_ryu_csv_incremental(raw, database)
    before_size = raw.stat().st_size

    rows = [_row(0), _row(1)]
    rows[1]["ip_dst"] = "10.0.9.9"
    with raw.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    assert raw.stat().st_size == before_size

    result = ingest_ryu_csv_incremental(raw, database)
    assert result["cursor_reset"] is True
    assert len(SQLiteSiemStore(database).list_events()) == 3
