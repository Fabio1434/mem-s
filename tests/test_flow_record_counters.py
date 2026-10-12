import pandas as pd

from gnn_sdn_apt.features import engineer_flow_features


def test_repeated_five_tuple_public_records_are_not_counter_differenced():
    rows = []
    for timestamp, packets, byte_count, duration in [
        (100.0, 10, 1000, 2.0),
        (105.0, 15, 1500, 3.0),
    ]:
        rows.append({
            "timestamp": timestamp,
            "datapath_id": 0,
            "in_port": -1,
            "eth_src": "dataset-row",
            "eth_dst": "destination",
            "ip_src": "10.0.0.1",
            "ip_dst": "10.0.0.2",
            "ip_proto": 6,
            "src_port": 45000,
            "dst_port": 80,
            "packet_count": packets,
            "byte_count": byte_count,
            "duration_sec": duration,
            "record_mode": "flow_record",
            "label": 0,
            "scenario": "normal",
        })

    features = engineer_flow_features(pd.DataFrame(rows))

    assert features["packets_delta"].tolist() == [10.0, 15.0]
    assert features["bytes_delta"].tolist() == [1000.0, 1500.0]
    assert features["packet_rate"].tolist() == [5.0, 5.0]
    assert features["byte_rate"].tolist() == [500.0, 500.0]
    assert features["label"].tolist() == [0, 0]
