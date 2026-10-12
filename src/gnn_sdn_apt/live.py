"""Polling inference service that translates fresh flow stats into decisions.

Run this in parallel with the Ryu controller after training a model. The
service defaults to alert-only; automatic SDN blocking requires both the YAML
mitigation flag and GNN_SDN_MITIGATION=1.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from .config import load_config
from .graph.builder import build_graph_snapshots
from .graph.io import write_graphs
from .inference import score_baseline_nodes, score_gnn_nodes
from .features import prepare_flow_file

LOGGER = logging.getLogger("gnn_sdn_apt.live")


def _append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, allow_nan=False) + "\n")


def run_once(
    config_path: str = "config/config.yaml",
    model_name: str | None = None,
    model_path: str | None = None,
) -> int:
    """Prepare the latest snapshot, score it, and append suspicious decisions."""
    config = load_config(config_path)
    paths = config["paths"]
    model_name = (model_name or config["detection"].get("model", "baseline")).lower()
    raw_path = Path(paths["raw_flows"])
    if not raw_path.exists() or raw_path.stat().st_size == 0:
        LOGGER.warning("No raw flow data is available yet: %s", raw_path)
        return 0

    features = prepare_flow_file(
        raw_path,
        paths["features"],
        paths["scenario_labels"],
        default_window_seconds=5.0,
    )
    graphs = build_graph_snapshots(
        features,
        window_seconds=int(config["graph"].get("temporal_window_seconds", 10)),
    )
    write_graphs(graphs, paths["graphs"])
    if not graphs:
        LOGGER.info("No IP-level graph can be built from the current flow counters")
        return 0

    if model_path:
        artifact = Path(model_path)
    elif model_name == "baseline":
        artifact = Path(paths["models"]) / "baseline.joblib"
    else:
        artifact = Path(paths["models"]) / f"{model_name}.pt"
    if not artifact.exists():
        LOGGER.warning("No trained model found at %s; train a model before live scoring", artifact)
        return 0

    if model_name == "baseline":
        scores = score_baseline_nodes(graphs[-1], artifact)
    elif model_name in ("gcn", "gat"):
        scores = score_gnn_nodes(graphs[-1], artifact)
    else:
        raise ValueError("model must be baseline, gcn, or gat")

    threshold = float(config["detection"].get("threshold", 0.9))
    mitigation_enabled = (
        bool(config.get("mitigation", {}).get("enabled", False))
        and os.getenv("GNN_SDN_MITIGATION", "0") == "1"
    )
    emitted = 0
    for item in scores:
        if item["score"] < threshold:
            continue
        record = {
            **item,
            "threshold": threshold,
            "suspicious": True,
            "action": "block_source" if mitigation_enabled else "alert",
            "model": model_name,
            "mitigation_enabled": mitigation_enabled,
            "created_at": time.time(),
        }
        _append_jsonl(paths["alerts"], record)
        _append_jsonl(paths["decisions"], record)
        LOGGER.warning(
            "Threat score %.3f for %s; action=%s",
            item["score"],
            item["source_ip"],
            record["action"],
        )
        emitted += 1
    LOGGER.info("Scored %d graph nodes; emitted %d suspicious decisions", len(scores), emitted)
    return emitted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--model", choices=["baseline", "gcn", "gat"], default=None)
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--once", action="store_true", help="run one inference cycle and exit")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be positive")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.once:
        run_once(args.config, args.model, args.model_path)
        return
    while True:
        try:
            run_once(args.config, args.model, args.model_path)
        except (OSError, ValueError, KeyError) as exc:
            LOGGER.exception("Live inference cycle failed: %s", exc)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
