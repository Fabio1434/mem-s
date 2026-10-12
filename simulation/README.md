# Simulation — Mininet

The topology creates one Open vSwitch switch (s1), five hosts (h1-h5), OpenFlow 1.3, and a remote Ryu controller at 127.0.0.1:6653.

## Start

The repository is designed for Linux or a Linux VM with Mininet, Open vSwitch, and Ryu installed. Create the Python environment with system packages available so the Mininet Python module installed by the operating system remains visible:

    python3 -m venv --system-site-packages .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

Terminal 1:

    ryu-manager --ofp-tcp-listen-port 6653 sdn/ryu_app.py

Terminal 2:

    sudo -E .venv/bin/python simulation/topology.py

## Available scenario commands

Inside the custom Mininet CLI:

    scenarios
    scenario normal
    scenario recon
    scenario lateral
    scenario exfil

These are bounded, lab-only behaviors. Reconnaissance/lateral cases make TCP connection attempts to the private 10.0.0.0/24 lab hosts without exploit payloads. The exfiltration surrogate transfers only 128 KiB of deterministic dummy bytes to a sink inside the topology.

Each scenario appends a label interval to data/raw/scenario_labels.csv. Wait at least 10 seconds between scenario commands to reduce label-window overlap. Ryu samples OpenFlow counters into data/raw/flow_stats.csv. Raw data and annotations stay local and are excluded from source control by .gitignore.

The initial pingAll traffic is not scenario-labeled. Run scenario normal explicitly to create normal labels.
