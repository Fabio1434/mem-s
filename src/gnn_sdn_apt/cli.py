"""Command-line entry point for the GNN-SDN-APT workflow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .graph.io import read_graphs
from .pipeline import build_dataset


def _print_json(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gnn-sdn-apt",
        description="Graph-based threat detection pipeline for a controlled SDN lab",
    )
    parser.add_argument("--config", default="config/config.yaml", help="YAML configuration file")
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="normalize flows and build graph snapshots")
    prepare.add_argument("--raw-input", default=None, help="override configured raw flow file")
    prepare.add_argument("--labels", default=None, help="override configured scenario labels file")

    importer = commands.add_parser("import-csv", help="normalize a timestamped public flow dataset")
    importer.add_argument("--input", required=True, help="input CSV, e.g. a CICFlowMeter export")
    importer.add_argument("--output", default="data/raw/public_flows.csv")

    baseline = commands.add_parser("train-baseline", help="train and evaluate Random Forest")
    baseline.add_argument("--model-out", default=None)
    baseline.add_argument("--threshold", type=float, default=None)
    baseline.add_argument("--report-out", default=None)

    gnn = commands.add_parser("train-gnn", help="train a temporal GCN or GAT")
    gnn.add_argument("--model", choices=["gcn", "gat"], default="gcn")
    gnn.add_argument("--epochs", type=int, default=100)
    gnn.add_argument("--threshold", type=float, default=None)
    gnn.add_argument("--model-out", default=None)
    gnn.add_argument("--report-out", default=None)

    inspect = commands.add_parser("inspect", help="show graph dataset and label counts")
    inspect.add_argument("--graphs", default=None)

    compare = commands.add_parser("compare", help="combine saved model metrics into one CSV")
    compare.add_argument("--reports-dir", default=None)
    compare.add_argument("--output", default=None)

    mitigation = commands.add_parser("summarize-mitigation", help="summarize Ryu decision-action timings")
    mitigation.add_argument("--events", default=None)

    args = parser.parse_args()
    config = load_config(args.config)
    paths = config["paths"]

    if args.command == "prepare":
        _print_json(build_dataset(args.config, raw_path=args.raw_input, annotations_path=args.labels))
    elif args.command == "import-csv":
        from .dataset_import import import_flow_csv

        _print_json(import_flow_csv(args.input, args.output))
    elif args.command == "train-baseline":
        from .models.baseline import train_baseline

        model_path = args.model_out or str(Path(paths["models"]) / "baseline.joblib")
        report_path = args.report_out or str(Path(paths["reports"]) / "baseline_metrics.json")
        threshold = args.threshold if args.threshold is not None else float(config["detection"]["threshold"])
        _print_json(train_baseline(paths["graphs"], model_path, report_path, threshold=threshold))
    elif args.command == "train-gnn":
        from .models.train_gnn import train_gnn

        model_path = args.model_out or str(Path(paths["models"]) / f"{args.model}.pt")
        report_path = args.report_out or str(Path(paths["reports"]) / f"{args.model}_metrics.json")
        _print_json(
            train_gnn(
                paths["graphs"], model_path, report_path,
                model_name=args.model, epochs=args.epochs,
                threshold=args.threshold if args.threshold is not None else float(config["detection"]["threshold"]),
            )
        )
    elif args.command == "compare":
        from .evaluation import compare_model_reports

        reports_dir = args.reports_dir or paths["reports"]
        output_path = args.output or str(Path(reports_dir) / "model_comparison.csv")
        _print_json(compare_model_reports(reports_dir, output_path))
    elif args.command == "summarize-mitigation":
        from .evaluation import summarize_mitigation_events

        events_path = args.events or paths.get("mitigation_events", "data/processed/mitigation_events.jsonl")
        _print_json(summarize_mitigation_events(events_path))
    elif args.command == "inspect":
        graph_path = args.graphs or paths["graphs"]
        graphs = read_graphs(graph_path)
        nodes = [node for graph in graphs for node in graph.get("nodes", [])]
        edge_count = sum(len(graph.get("edges", [])) for graph in graphs)
        labels = [int(node.get("label", -1)) for node in nodes]
        _print_json({
            "graph_snapshots": len(graphs),
            "nodes_total": len(nodes),
            "edges_total": edge_count,
            "nodes_normal": sum(label == 0 for label in labels),
            "nodes_suspicious": sum(label == 1 for label in labels),
            "nodes_unlabeled": sum(label not in (0, 1) for label in labels),
        })


if __name__ == "__main__":
    main()
