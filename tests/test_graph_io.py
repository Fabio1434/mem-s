from gnn_sdn_apt.graph.io import read_graphs, write_graphs


def test_graph_jsonl_round_trip(tmp_path):
    graphs = [{
        "timestamp": 12.0,
        "nodes": [{"id": "10.0.0.1", "features": [1.0], "label": 0}],
        "edges": [],
    }]
    output = tmp_path / "graphs.jsonl"
    assert write_graphs(graphs, output) == 1
    assert read_graphs(output) == graphs
