from gnn_sdn_apt.graph.io import write_graphs
from gnn_sdn_apt.models.baseline import load_baseline, train_baseline
from gnn_sdn_apt.schema import NODE_FEATURE_NAMES


def test_random_forest_baseline_trains_and_saves_metrics(tmp_path):
    graphs = []
    for index in range(6):
        graphs.append({
            "timestamp": float(100 + index * 10),
            "nodes": [
                {
                    "id": "10.0.0.1",
                    "features": [float(index + 1)] * len(NODE_FEATURE_NAMES),
                    "label": 0,
                },
                {
                    "id": "10.0.0.2",
                    "features": [float(index + 20)] * len(NODE_FEATURE_NAMES),
                    "label": 1,
                },
            ],
            "edges": [],
        })
    graph_file = tmp_path / "graphs.jsonl"
    model_file = tmp_path / "baseline.joblib"
    report_file = tmp_path / "metrics.json"
    write_graphs(graphs, graph_file)

    report = train_baseline(graph_file, model_file, report_file)
    estimator, feature_names = load_baseline(model_file)

    assert model_file.exists()
    assert report_file.exists()
    assert len(feature_names) == len(NODE_FEATURE_NAMES)
    assert report["model"] == "RandomForest"
    assert "f1" in report
    assert estimator.predict([[1.0] * len(NODE_FEATURE_NAMES)]).shape == (1,)


def test_baseline_can_calibrate_threshold_on_middle_temporal_windows(tmp_path):
    import json

    graphs = []
    for index in range(10):
        graphs.append({
            "timestamp": float(100 + index * 10),
            "nodes": [
                {
                    "id": "10.0.0.1",
                    "features": [float(index + 1)] * len(NODE_FEATURE_NAMES),
                    "label": 0,
                },
                {
                    "id": "10.0.0.2",
                    "features": [float(index + 20)] * len(NODE_FEATURE_NAMES),
                    "label": 1,
                },
            ],
            "edges": [],
        })
    graph_file = tmp_path / "graphs.jsonl"
    model_file = tmp_path / "baseline.joblib"
    report_file = tmp_path / "metrics.json"
    write_graphs(graphs, graph_file)

    report = train_baseline(
        graph_file,
        model_file,
        report_file,
        threshold=0.9,
        calibrate_threshold=True,
    )
    persisted = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["threshold_selection"] == "validation-f1"
    assert report["validation_observations"] > 0
    assert 0.0 <= report["threshold"] <= 1.0
    assert persisted["threshold"] == report["threshold"]
