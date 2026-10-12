import pandas as pd

from gnn_sdn_apt.dataset_import import import_flow_csv
from gnn_sdn_apt.features import engineer_flow_features


def test_importer_normalizes_timestamped_flow_dataset_and_preserves_labels(tmp_path):
    source = tmp_path / "source.csv"
    target = tmp_path / "normalized.csv"
    pd.DataFrame([
        {
            "Timestamp": "2021-08-15 10:00:00",
            "Source IP": "10.0.0.1", "Destination IP": "10.0.0.2",
            "Source Port": 45000, "Destination Port": 80, "Protocol": "TCP",
            "Flow Duration": 2_000_000, "Total Fwd Packets": 4,
            "Total Length of Fwd Packets": 400, "Label": "BENIGN",
        },
        {
            "Timestamp": "2021-08-15 10:00:20",
            "Source IP": "10.0.0.3", "Destination IP": "10.0.0.4",
            "Source Port": 45001, "Destination Port": 445, "Protocol": "TCP",
            "Flow Duration": 1_000_000, "Total Fwd Packets": 20,
            "Total Length of Fwd Packets": 2000, "Label": "PortScan",
        },
    ]).to_csv(source, index=False)

    summary = import_flow_csv(source, target)
    normalized = pd.read_csv(target)
    features = engineer_flow_features(normalized)

    assert summary["rows_imported"] == 2
    assert normalized["label"].tolist() == [0, 1]
    assert normalized["ip_proto"].tolist() == [6, 6]
    assert normalized["duration_sec"].tolist() == [2.0, 1.0]
    assert features["label"].tolist() == [0, 1]
    assert features["scenario"].tolist() == ["normal", "portscan"]
