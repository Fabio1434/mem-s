import pandas as pd

from gnn_sdn_apt.features import engineer_flow_features


def _raw_rows():
    return pd.DataFrame([
        {
            "timestamp": 100.0, "datapath_id": 1, "in_port": 1,
            "eth_src": "00:00:00:00:00:01", "eth_dst": "00:00:00:00:00:02",
            "ip_src": "10.0.0.1", "ip_dst": "10.0.0.2", "ip_proto": 6,
            "src_port": 40000, "dst_port": 80, "packet_count": 10,
            "byte_count": 1000, "duration_sec": 2.0,
        },
        {
            "timestamp": 105.0, "datapath_id": 1, "in_port": 1,
            "eth_src": "00:00:00:00:00:01", "eth_dst": "00:00:00:00:00:02",
            "ip_src": "10.0.0.1", "ip_dst": "10.0.0.2", "ip_proto": 6,
            "src_port": 40000, "dst_port": 80, "packet_count": 15,
            "byte_count": 1500, "duration_sec": 7.0,
        },
        {
            "timestamp": 110.0, "datapath_id": 1, "in_port": 1,
            "eth_src": "00:00:00:00:00:01", "eth_dst": "00:00:00:00:00:02",
            "ip_src": "10.0.0.1", "ip_dst": "10.0.0.2", "ip_proto": 6,
            "src_port": 40000, "dst_port": 80, "packet_count": 2,
            "byte_count": 200, "duration_sec": 1.0,
        },
    ])


def test_cumulative_counters_are_converted_to_deltas():
    features = engineer_flow_features(_raw_rows())
    assert features["packets_delta"].tolist() == [10.0, 5.0, 2.0]
    assert features["bytes_delta"].tolist() == [1000.0, 500.0, 200.0]
    assert features.loc[1, "packet_rate"] == 1.0
    assert features.loc[1, "byte_rate"] == 100.0
    assert (features["packets_delta"] >= 0).all()


def test_unknown_ground_truth_is_not_mislabeled_as_normal():
    features = engineer_flow_features(_raw_rows())
    assert set(features["label"].tolist()) == {-1}
