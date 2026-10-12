"""Optional GNN smoke tests; they run in CI with the ml extra installed."""
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from gnn_sdn_apt.demo_data import generate_demo_capture
from gnn_sdn_apt.pipeline import build_dataset
from gnn_sdn_apt.models.train_gnn import train_gnn


@pytest.mark.parametrize("model_name", ["gcn", "gat"])
def test_gnn_train_and_save_checkpoint_on_synthetic_graphs(tmp_path, model_name):
    import yaml

    raw = tmp_path / "raw.csv"
    labels = tmp_path / "labels.csv"
    graphs = tmp_path / "graphs.jsonl"
    features = tmp_path / "features.csv"
    config = tmp_path / "config.yaml"
    generate_demo_capture(raw, labels, polls=40)
    config.write_text(yaml.safe_dump({
        "paths": {
            "raw_flows": str(raw),
            "scenario_labels": str(labels),
            "features": str(features),
            "graphs": str(graphs),
        },
        "graph": {"temporal_window_seconds": 10},
    }), encoding="utf-8")

    prepared = build_dataset(config)
    assert prepared["graph_snapshots"] >= 12

    checkpoint = tmp_path / f"{model_name}.pt"
    report_file = tmp_path / f"{model_name}_metrics.json"
    report = train_gnn(
        graphs, checkpoint, report_file,
        model_name=model_name, epochs=2, calibrate_threshold=True,
    )
    assert checkpoint.exists() and report_file.exists()
    assert report["split_method"] == "temporal-train-validation-test"
    assert report["test_observations"] > 0
    assert 0.0 <= report["f1"] <= 1.0
