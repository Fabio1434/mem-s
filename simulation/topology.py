#!/usr/bin/env python3
"""Reproducible Mininet topology for the GNN-SDN-APT research lab.

This topology intentionally contains only benign hosts and services.
It is used to generate normal and controlled research traffic.
"""
from mininet.cli import CLI
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import Topo


class ResearchTopology(Topo):
    """Small SDN topology suitable for the first experimental iteration."""

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
            host = self.addHost(name, ip=ip)
            self.addLink(host, core)


def run():
    """Start the topology with a remote Ryu controller."""
    net = Mininet(
        topo=ResearchTopology(),
        switch=OVSSwitch,
        controller=None,
        autoSetMacs=True,
        autoStaticArp=True,
    )

    net.addController(
        "c0",
        controller=RemoteController,
        ip="127.0.0.1",
        port=6653,
    )

    info("*** Starting research SDN topology\n")
    net.start()

    info("*** Connectivity check\n")
    net.pingAll()

    info("\n*** Hosts\n")
    for host in net.hosts:
        info(f"{host.name}: {host.IP()}\n")

    info("\n*** Mininet CLI\n")
    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run()
