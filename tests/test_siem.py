import json

import pytest

from gnn_sdn_apt.siem import (
    JsonlEventStore,
    SQLiteSiemStore,
    correlate_events,
    normalize_event,
)


def test_normalize_event_maps_ryu_fields_and_unknown_label():
    event = normalize_event({"timestamp": 1700000000, "ip_src": "10.0.0.1",
                             "ip_dst": "10.0.0.2", "ip_proto": 6,
                             "byte_count": 120}, source_component="ryu")
    assert event["src_ip"] == "10.0.0.1"
    assert event["dst_ip"] == "10.0.0.2"
    assert event["protocol"] == 6
    assert event["label"] == -1
    assert event["source_component"] == "ryu"
    assert event["payload"]["byte_count"] == 120
    assert event["timestamp"].endswith("Z")


def test_jsonl_store_appends_and_reads(tmp_path):
    store = JsonlEventStore(tmp_path / "events.jsonl")
    store.append({"timestamp": 1700000000, "src_ip": "10.0.0.1", "dst_ip": "10.0.0.2"})
    store.append({"timestamp": 1700000001, "src_ip": "10.0.0.2", "dst_ip": "10.0.0.3"})
    rows = list(store.read())
    assert len(rows) == 2
    assert rows[0]["event_type"] == "flow_observation"
    assert len((tmp_path / "events.jsonl").read_text().splitlines()) == 2


def test_sqlite_persists_events_and_incident_lifecycle(tmp_path):
    store = SQLiteSiemStore(tmp_path / "siem.db")
    event = store.add_event({"timestamp": 1700000000, "src_ip": "10.0.0.1",
                             "dst_ip": "10.0.0.2"})
    store.upsert_incident({
        "incident_id": "inc-1", "rule_id": "test-rule", "host": "10.0.0.1",
        "status": "open", "severity": "medium", "confidence": 0.8,
        "first_seen": event["timestamp"], "last_seen": event["timestamp"],
        "event_ids": [event["event_id"]], "summary": "test incident",
    })
    assert store.list_events()[0]["src_ip"] == "10.0.0.1"
    assert store.list_incidents(status="open")[0]["event_ids"] == [event["event_id"]]
    store.upsert_incident({
        "incident_id": "inc-1", "rule_id": "test-rule", "host": "10.0.0.1",
        "status": "contained", "severity": "medium", "confidence": 0.8,
        "first_seen": event["timestamp"], "last_seen": event["timestamp"],
        "event_ids": [event["event_id"]], "summary": "contained",
    })
    assert store.list_incidents()[0]["status"] == "contained"


def test_correlates_fanout_by_host_and_time_window():
    events = [
        {"timestamp": 1700000000 + i, "src_ip": "10.0.0.1",
         "dst_ip": f"10.0.0.{i + 2}", "label": -1}
        for i in range(5)
    ]
    findings = correlate_events(events, window_seconds=60, min_distinct_destinations=5)
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "SDN-RECON-FANOUT-001"
    assert len(findings[0]["event_ids"]) == 5


def test_correlator_does_not_alert_below_threshold():
    events = [{"timestamp": 1700000000, "src_ip": "10.0.0.1", "dst_ip": "10.0.0.2"}]
    assert correlate_events(events, min_distinct_destinations=5) == []


def test_invalid_parameters_are_rejected():
    with pytest.raises(ValueError):
        correlate_events([], window_seconds=0)
    with pytest.raises(TypeError):
        normalize_event(["not", "a", "mapping"])



def test_incident_lifecycle_transitions_are_validated_and_audited(tmp_path):
    store = SQLiteSiemStore(tmp_path / "siem.db")
    store.upsert_incident({
        "incident_id": "lifecycle-1", "rule_id": "test", "host": "10.0.0.9",
        "status": "open", "severity": "medium", "confidence": 0.8,
        "first_seen": "2023-11-14T22:13:20Z",
        "last_seen": "2023-11-14T22:13:20Z",
        "event_ids": [], "summary": "lifecycle test",
    })

    store.transition_incident("lifecycle-1", "investigating", changed_by="analyst")
    store.transition_incident("lifecycle-1", "contained", changed_by="analyst",
                              note="lab host isolated")
    store.transition_incident("lifecycle-1", "closed", changed_by="analyst")

    assert store.list_incidents()[0]["status"] == "closed"
    history = store.list_incident_history("lifecycle-1")
    assert [item["new_status"] for item in history] == [
        "investigating", "contained", "closed"
    ]
    assert history[1]["note"] == "lab host isolated"

    with pytest.raises(ValueError):
        store.transition_incident("lifecycle-1", "open")
    with pytest.raises(KeyError):
        store.transition_incident("missing", "open")
