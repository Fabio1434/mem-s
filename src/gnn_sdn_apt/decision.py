"""Threat score policy with safe-by-default mitigation controls."""
from __future__ import annotations

from typing import Any


def decide_action(
    source_ip: str,
    score: float,
    threshold: float = 0.9,
    mitigation_enabled: bool = False,
) -> dict[str, Any]:
    """Map a probability-like score to an observation, alert, or lab block action.

    Blocking is never selected unless the caller explicitly enables mitigation.
    The SDN controller additionally requires an environment opt-in.
    """
    if not 0.0 <= float(score) <= 1.0:
        raise ValueError("score must be in the [0, 1] interval")
    if not 0.0 <= float(threshold) <= 1.0:
        raise ValueError("threshold must be in the [0, 1] interval")

    suspicious = float(score) >= float(threshold)
    if not suspicious:
        action = "observe"
    elif mitigation_enabled:
        action = "block_source"
    else:
        action = "alert"

    return {
        "source_ip": str(source_ip),
        "score": float(score),
        "threshold": float(threshold),
        "suspicious": suspicious,
        "action": action,
    }
