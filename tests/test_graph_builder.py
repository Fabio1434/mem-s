import pandas as pd

from gnn_sdn_apt.graph.builder import build_graph_snapshots
from gnn_sdn_apt.schema import FLOW_FEATURE_COLUMNS


def test_build_graph_snapshot_aggregates_flows_and_labels_source():
    row = {
        "timestamp": 100.0, "ip_src": "10.0.0.1", "ip_dst": "10.0.0.2",
        "label": 1, "scenario": "recon",
    }
    row.update({name: 0.0 for name in FLOW_FEATURE_COLUMNS})
    row.update({
        "packets_delta": 5.0, "bytes_delta": 500.0,
        "packet_rate": 1.0, "byte_rate": 100.0,
        "duration_sec": 4.0, "dst_port_num": 80.0,
    })
    graphs = build_graph_snapshots(pd.DataFrame([row]), window_seconds=10)
    assert len(graphs) == 1
    graph = graphs[0]
    assert graph["nodes"][0]["id"] == "10.0.0.1"
    source = next(node for node in graph["nodes"] if node["id"] == "10.0.0.1")
    assert source["label"] == 1
    assert source["features"][0] == 1.0
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["label"] == 1


def test_graph_builder_skips_rows_without_ip_endpoints():
    graphs = build_graph_snapshots(pd.DataFrame([
        {"timestamp": 100, "ip_src": "", "ip_dst": "", "label": -1}
    ]), window_seconds=10)
    assert graphs == []


def test_temporal_features_track_new_destinations_and_activity_streak():
    rows = []
    for timestamp, destination, destination_port in [
        (100.0, "10.0.0.2", 80),
        (110.0, "10.0.0.3", 443),
    ]:
        row = {
            "timestamp": timestamp, "ip_src": "10.0.0.1", "ip_dst": destination,
            "label": 1, "scenario": "recon", "dst_port_num": destination_port,
        }
        row.update({name: 0.0 for name in FLOW_FEATURE_COLUMNS})
        row.update({
            "packets_delta": 3.0, "bytes_delta": 300.0,
            "packet_rate": 0.6, "byte_rate": 60.0,
            "duration_sec": 2.0, "dst_port_num": float(destination_port),
        })
        rows.append(row)

    graphs = build_graph_snapshots(pd.DataFrame(rows), window_seconds=10)
    assert len(graphs) == 2
    node = next(item for item in graphs[1]["nodes"] if item["id"] == "10.0.0.1")
    features = node["features"]
    assert features[12] == 1.0  # active in previous window
    assert features[13] == 0.0  # same outgoing-flow count
    assert features[14] == 1.0  # new destination
    assert features[15] == 2.0  # consecutive active windows
