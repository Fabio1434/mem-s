"""JSON Lines persistence for graph snapshots."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def write_graphs(graphs: Iterable[dict[str, Any]], path: str | Path) -> int:
    """Write one graph snapshot per JSONL record and return its count."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with target.open("w", encoding="utf-8") as handle:
        for graph in graphs:
            handle.write(json.dumps(graph, separators=(",", ":"), allow_nan=False) + "\n")
            count += 1
    return count


def read_graphs(path: str | Path) -> list[dict[str, Any]]:
    """Read a JSONL graph dataset, ignoring blank lines."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Graph dataset not found: {source}")
    graphs = []
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                graphs.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {source}") from exc
    return graphs
