#!/usr/bin/env python3
"""Report the availability of Python and system dependencies for this project."""
from __future__ import annotations

import importlib.util
import platform
import shutil
import socket
import sys


def main() -> int:
    print("GNN-SDN-APT environment report")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"Platform: {platform.platform()}")
    print("\nPython modules:")
    modules = [
        ("pandas", True),
        ("numpy", True),
        ("networkx", True),
        ("yaml", True),
        ("sklearn", True),
        ("joblib", True),
        ("mininet", True),
        ("ryu", True),
        ("torch", False),
        ("torch_geometric", False),
    ]
    missing_required = []
    for name, required in modules:
        available = importlib.util.find_spec(name) is not None
        status = "OK" if available else ("MISSING" if required else "optional/missing")
        print(f"  {name}: {status}")
        if required and not available:
            missing_required.append(name)

    print("\nSystem commands:")
    missing_commands = []
    for name in ("mn", "ovs-vsctl", "ryu-manager"):
        path = shutil.which(name)
        print(f"  {name}: {path or 'MISSING'}")
        if not path:
            missing_commands.append(name)

    try:
        with socket.create_connection(("127.0.0.1", 6653), timeout=0.5):
            controller_state = "reachable on 127.0.0.1:6653"
    except OSError:
        controller_state = "not listening on 127.0.0.1:6653 (start Ryu before Mininet)"
    print(f"\nOpenFlow controller: {controller_state}")

    if missing_required or missing_commands:
        print("\nSome mandatory environment components are missing.")
        return 1
    print("\nThe main environment checks passed. Optional GNN dependencies are reported separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
