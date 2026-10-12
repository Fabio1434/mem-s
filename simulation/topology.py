#!/usr/bin/env python3
"""Reproducible Mininet topology for the GNN-SDN-APT research lab."""
from __future__ import annotations

from mininet.cli import CLI
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
import sys
from pathlib import Path

from mininet.topo import Topo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simulation.scenarios import run_scenario


class ResearchTopology(Topo):
    """Single-switch, five-host SDN topology using OpenFlow 1.3."""

    def build(self):
        core = self.addSwitch("s1", protocols="OpenFlow13")
        hosts = {
            "h1": "10.0.0.1/24",
            "h2": "10.0.0.2/24",
            "h3": "10.0.0.3/24",
            "h4": "10.0.0.4/24",
            "h5": "10.0.0.5/24",
        }
        for name, ip in hosts.items():
            self.addLink(self.addHost(name, ip=ip), core)


class ResearchCLI(CLI):
    """Mininet CLI extended with reproducible, labeled scenarios."""

    def do_scenario(self, line):
        """Run a bounded scenario: scenario normal|recon|lateral|exfil."""
        name = line.strip().lower()
        if not name:
            info("Usage: scenario normal|recon|lateral|exfil\n")
            return
        result = run_scenario(self.mn, name)
        info(f"*** {result}\n")

    def do_scenarios(self, _line):
        """List available annotated scenarios."""
        info(
            "Available scenarios:\n"
            "  scenario normal  - labeled benign ICMP traffic\n"
            "  scenario recon   - bounded TCP connection attempts\n"
            "  scenario lateral - controlled internal connection attempts\n"
            "  scenario exfil   - fixed-size dummy transfer to a lab sink\n"
        )


def run():
    """Start the topology with a remote Ryu controller."""
    net = Mininet(
        topo=ResearchTopology(),
        switch=OVSSwitch,
        controller=None,
        autoSetMacs=True,
        autoStaticArp=True,
    )
    net.addController("c0", controller=RemoteController, ip="127.0.0.1", port=6653)

    try:
        info("*** Starting research SDN topology\n")
        net.start()
        info("*** Connectivity check\n")
        net.pingAll()
        info("\n*** Hosts\n")
        for host in net.hosts:
            info(f"{host.name}: {host.IP()}\n")
        info("\n*** Custom Mininet CLI; type 'scenarios' for help\n")
        ResearchCLI(net)
    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run()
