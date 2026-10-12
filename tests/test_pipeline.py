import pandas as pd
import yaml

from gnn_sdn_apt.pipeline import build_dataset
from gnn_sdn_apt.graph.io import read_graphs


def test_build_dataset_creates_features_and_graph_snapshots(tmp_path):
    raw = tmp_path / "flow_stats.csv"
    labels = tmp_path / "scenario_labels.csv"
    features = tmp_path / "flow_features.csv"
    graphs_file = tmp_path / "graphs.jsonl"
    config_file = tmp_path / "config.yaml"

    pd.DataFrame([
        {
            "timestamp": 100.0, "datapath_id": 1, "in_port": 1,
            "eth_src": "aa", "eth_dst": "bb",
            "ip_src": "10.0.0.1", "ip_dst": "10.0.0.2", "ip_proto": 6,
            "src_port": 40000, "dst_port": 80, "packet_count": 5,
            "byte_count": 500, "duration_sec": 1,
        },
        {
            "timestamp": 110.0, "datapath_id": 1, "in_port": 1,
            "eth_src": "aa", "eth_dst": "bb",
            "ip_src": "10.0.0.1", "ip_dst": "10.0.0.2", "ip_proto": 6,
            "src_port": 40000, "dst_port": 80, "packet_count": 10,
            "byte_count": 1000, "duration_sec": 11,
        },
    ]).to_csv(raw, index=False)

    pd.DataFrame([
        {
            "timestamp_start": 99, "timestamp_end": 105,
            "src_ip": "10.0.0.1", "dst_ip": "10.0.0.2",
            "label": 0, "scenario": "normal",
        },
        {
            "timestamp_start": 106, "timestamp_end": 115,
            "src_ip": "10.0.0.1", "dst_ip": "10.0.0.2",
            "label": 1, "scenario": "recon",
        },
    ]).to_csv(labels, index=False)

    config_file.write_text(yaml.safe_dump({
        "paths": {
            "raw_flows": str(raw),
            "scenario_labels": str(labels),
            "features": str(features),
            "graphs": str(graphs_file),
        },
        "graph": {"temporal_window_seconds": 10},
    }), encoding="utf-8")

    result = build_dataset(config_file)

    assert result["flow_observations"] == 2
    assert result["graph_snapshots"] == 2
    assert result["labeled_flow_observations"] == 2
    assert features.exists()
    graphs = read_graphs(graphs_file)
    assert [graph["nodes"][0]["label"] for graph in graphs] == [0, 1]
