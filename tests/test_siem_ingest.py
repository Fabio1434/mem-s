import csv

from gnn_sdn_apt.siem import SQLiteSiemStore
from gnn_sdn_apt.siem_ingest import ingest_ryu_csv, persist_model_findings


def _write_flows(path):
    fields = [
        "timestamp", "datapath_id", "in_port", "ip_src", "ip_dst",
        "ip_proto", "src_port", "dst_port", "packet_count", "byte_count",
        "duration_sec",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(5):
            writer.writerow({
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
            })


def test_ingests_ryu_csv_and_persists_correlated_incident(tmp_path):
    raw = tmp_path / "flow_stats.csv"
    database = tmp_path / "siem.db"
    _write_flows(raw)

    result = ingest_ryu_csv(raw, database, window_seconds=60, min_distinct_destinations=5)

    assert result["events_read"] == 5
    assert result["findings"] == 1
    store = SQLiteSiemStore(database)
    assert len(store.list_events()) == 5
    incidents = store.list_incidents(status="open")
    assert len(incidents) == 1
    assert incidents[0]["rule_id"] == "SDN-RECON-FANOUT-001"


def test_repeated_ingestion_is_idempotent_and_preserves_incident_status(tmp_path):
    raw = tmp_path / "flow_stats.csv"
    database = tmp_path / "siem.db"
    _write_flows(raw)

    ingest_ryu_csv(raw, database, window_seconds=60, min_distinct_destinations=5)
    store = SQLiteSiemStore(database)
    incident = store.list_incidents()[0]
    incident["status"] = "contained"
    store.upsert_incident(incident)

    result = ingest_ryu_csv(raw, database, window_seconds=60, min_distinct_destinations=5)

    assert result["events_read"] == 5
    assert len(store.list_events()) == 5
    assert store.list_incidents()[0]["status"] == "contained"


def test_missing_csv_is_a_safe_noop(tmp_path):
    result = ingest_ryu_csv(tmp_path / "missing.csv", tmp_path / "siem.db")
    assert result["events_read"] == 0
    assert result["findings"] == 0



def test_model_scores_create_persistent_incidents_and_preserve_status(tmp_path):
    database = tmp_path / "siem.db"
    scores = [{"source_ip": "10.0.0.7", "score": 0.96, "timestamp": 1700000000}]
    assert persist_model_findings(
        database, scores, model_name="gcn", threshold=0.85, window_seconds=10
    ) == 1

    store = SQLiteSiemStore(database)
    incident = store.list_incidents()[0]
    assert incident["rule_id"] == "MODEL-GCN-THRESHOLD"
    assert incident["severity"] == "high"
    assert incident["confidence"] == 0.96

    incident["status"] = "contained"
    store.upsert_incident(incident)
    persist_model_findings(
        database, scores, model_name="gcn", threshold=0.9, window_seconds=10
    )
    assert store.list_incidents()[0]["status"] == "contained"


def test_model_scores_below_threshold_do_not_create_incidents(tmp_path):
    count = persist_model_findings(
        tmp_path / "siem.db",
        [{"source_ip": "10.0.0.8", "score": 0.2, "timestamp": 1700000000}],
        model_name="baseline",
        threshold=0.9,
    )
    assert count == 0
    assert SQLiteSiemStore(tmp_path / "siem.db").list_incidents() == []
