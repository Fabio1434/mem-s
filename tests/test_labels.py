import pandas as pd

from gnn_sdn_apt.labels import label_flow


def test_label_flow_requires_matching_time_and_endpoints():
    annotations = pd.DataFrame([{
        "timestamp_start": 10.0, "timestamp_end": 20.0,
        "src_ip": "10.0.0.1", "dst_ip": "", "label": 1, "scenario": "recon",
    }])
    assert label_flow(15.0, "10.0.0.1", "10.0.0.4", annotations) == (1, "recon")
    assert label_flow(15.0, "10.0.0.2", "10.0.0.4", annotations) == (-1, "unlabelled")
    assert label_flow(25.0, "10.0.0.1", "10.0.0.4", annotations) == (-1, "unlabelled")


def test_latest_overlapping_annotation_takes_precedence():
    annotations = pd.DataFrame([
        {
            "timestamp_start": 10.0, "timestamp_end": 30.0,
            "src_ip": "10.0.0.1", "dst_ip": "", "label": 0, "scenario": "normal",
        },
        {
            "timestamp_start": 15.0, "timestamp_end": 25.0,
            "src_ip": "10.0.0.1", "dst_ip": "", "label": 1, "scenario": "recon",
        },
    ])
    assert label_flow(20.0, "10.0.0.1", "10.0.0.2", annotations) == (1, "recon")
