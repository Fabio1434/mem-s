"""Threat score policy with defence-in-depth lab-only mitigation controls."""
from __future__ import annotations

import ipaddress
from typing import Any

LAB_NETWORK = ipaddress.ip_network("10.0.0.0/24")


def decide_action(
    source_ip: str,
    score: float,
    threshold: float = 0.9,
    mitigation_enabled: bool = False,
) -> dict[str, Any]:
    """Map a model score to observe, alert, or an explicitly opted-in lab block.

    This policy refuses a block candidate for any source outside the private
    Mininet subnet. The Ryu controller repeats the same check independently.
    """
    if not 0.0 <= float(score) <= 1.0:
        raise ValueError("score must be in the [0, 1] interval")
    if not 0.0 <= float(threshold) <= 1.0:
        raise ValueError("threshold must be in the [0, 1] interval")

    suspicious = float(score) >= float(threshold)
    try:
        source_address = ipaddress.ip_address(str(source_ip))
    except ValueError:
        source_address = None

    if not suspicious:
        action = "observe"
        reason = "score_below_threshold"
    elif not mitigation_enabled:
        action = "alert"
        reason = "mitigation_disabled"
    elif (
        source_address is None
        or source_address.version != 4
        or source_address not in LAB_NETWORK
    ):
        action = "alert"
        reason = "source_outside_lab_network"
    else:
        action = "block_source"
        reason = "lab_source_and_explicit_opt_in"

    return {
        "source_ip": str(source_ip),
        "score": float(score),
        "threshold": float(threshold),
        "suspicious": suspicious,
        "action": action,
        "reason": reason,
    }
