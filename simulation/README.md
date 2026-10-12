# Simulation

This directory contains the reproducible Mininet laboratory.

## Topology

`topology.py` creates:

- 1 Open vSwitch switch (`s1`)
- 5 hosts (`h1` ... `h5`)
- OpenFlow 1.3
- a remote Ryu controller on `127.0.0.1:6653`

## Run

On a Linux machine with Mininet installed:

1. Start the Ryu collector from the repository root:
   `ryu-manager --ofp-tcp-listen-port 6653 sdn/ryu_app.py`
2. In another terminal, start:
   `sudo python3 simulation/topology.py`

The script performs `pingAll()` and then opens the Mininet CLI.

## Basic benign traffic

Inside the Mininet CLI:

```text
h1 ping -c 3 h2
h2 ping -c 3 h3
h3 ping -c 3 h4
h4 ping -c 3 h5
```

For the first phase, only benign and controlled traffic should be used. Attack scenarios will be added after the observation pipeline is validated.
