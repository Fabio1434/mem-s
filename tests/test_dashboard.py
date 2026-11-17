from gnn_sdn_apt.dashboard import render_dashboard_html
from gnn_sdn_apt.siem import SQLiteSiemStore


def test_dashboard_renders_incidents_and_events_as_escaped_read_only_html(tmp_path):
    store = SQLiteSiemStore(tmp_path / "siem.db")
    store.add_event({
        "timestamp": 1700000000,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "source_component": "ryu",
    })
    store.upsert_incident({
        "incident_id": "inc-1",
        "rule_id": "test",
        "host": "10.0.0.1",
        "status": "open",
        "severity": "medium",
        "confidence": 0.8,
        "first_seen": "2023-11-14T22:13:20Z",
        "last_seen": "2023-11-14T22:13:20Z",
        "event_ids": [],
        "summary": "<script>alert(1)</script>",
    })

    html = render_dashboard_html(store)

    assert "SIEM léger" in html
    assert "10.0.0.1" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "lecture seule" in html
