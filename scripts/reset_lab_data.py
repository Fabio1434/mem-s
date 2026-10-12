#!/usr/bin/env python3
"""Remove generated capture artifacts when starting a clean experiment."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = [
    ROOT / "data/raw/flow_stats.csv",
    ROOT / "data/raw/scenario_labels.csv",
    ROOT / "data/raw/public_flows.csv",
    ROOT / "data/processed/flow_features.csv",
    ROOT / "data/processed/graphs.jsonl",
    ROOT / "data/processed/alerts.jsonl",
    ROOT / "data/processed/decisions.jsonl",
    ROOT / "data/processed/mitigation_events.jsonl",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm deletion of generated capture/feature/decision files",
    )
    args = parser.parse_args()
    existing = [path for path in GENERATED if path.exists()]
    if not args.yes:
        print("No files were deleted. The following existing generated files would be removed:")
        for path in existing:
            print(f"  {path.relative_to(ROOT)}")
        print("Pass --yes to confirm. Trained models and reports are not removed.")
        return 0
    for path in existing:
        path.unlink()
        print(f"Removed {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
