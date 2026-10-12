#!/usr/bin/env python3
"""Small traffic generators restricted to the Mininet research lab."""
from __future__ import annotations

import argparse
import socket
import time


def scan(targets: list[str], ports: list[int], timeout: float, delay: float) -> None:
    """Attempt a bounded list of TCP connections; no exploit payloads are sent."""
    for target in targets:
        for port in ports:
            try:
                with socket.create_connection((target, port), timeout=timeout):
                    pass
            except OSError:
                pass
            if delay:
                time.sleep(delay)


def listen(port: int, seconds: float, output_path: str) -> None:
    """Receive a fixed-size transfer sink for an isolated local lab."""
    received = 0
    deadline = time.monotonic() + seconds
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", port))
        server.listen(4)
        server.settimeout(max(0.1, seconds))
        while time.monotonic() < deadline:
            try:
                connection, _ = server.accept()
            except socket.timeout:
                break
            with connection:
                connection.settimeout(2.0)
                while True:
                    try:
                        chunk = connection.recv(8192)
                    except socket.timeout:
                        break
                    if not chunk:
                        break
                    received += len(chunk)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(str(received))


def send(target: str, port: int, byte_count: int) -> None:
    """Send deterministic dummy bytes to the designated lab receiver."""
    if byte_count < 1 or byte_count > 2_000_000:
        raise ValueError("byte count must be between 1 and 2,000,000")
    payload = b"LAB-DATA-" * 1024
    remaining = byte_count
    with socket.create_connection((target, port), timeout=5.0) as client:
        while remaining > 0:
            chunk = payload[:min(len(payload), remaining)]
            client.sendall(chunk)
            remaining -= len(chunk)
        client.shutdown(socket.SHUT_WR)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("--targets", required=True, help="comma-separated lab IPs")
    scan_parser.add_argument("--ports", default="22,80,443,445")
    scan_parser.add_argument("--timeout", type=float, default=0.15)
    scan_parser.add_argument("--delay", type=float, default=0.02)

    listen_parser = subparsers.add_parser("listen")
    listen_parser.add_argument("--port", type=int, default=9001)
    listen_parser.add_argument("--seconds", type=float, default=20)
    listen_parser.add_argument("--output", default="/tmp/gnn-sdn-received-bytes.txt")

    send_parser = subparsers.add_parser("send")
    send_parser.add_argument("--target", required=True)
    send_parser.add_argument("--port", type=int, default=9001)
    send_parser.add_argument("--bytes", type=int, default=131072)

    args = parser.parse_args()
    if args.mode == "scan":
        scan(
            [item.strip() for item in args.targets.split(",") if item.strip()],
            [int(item) for item in args.ports.split(",")],
            args.timeout,
            args.delay,
        )
    elif args.mode == "listen":
        listen(args.port, args.seconds, args.output)
    elif args.mode == "send":
        send(args.target, args.port, args.bytes)


if __name__ == "__main__":
    main()
