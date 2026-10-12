# SDN controller

The Ryu application at sdn/ryu_app.py handles OpenFlow 1.3, installs a table-miss rule, performs MAC learning and installs forwarding rules that include IP and TCP/UDP match fields when available. Every five seconds it requests flow statistics and appends them to data/raw/flow_stats.csv.

## Detection service

After preparing the data and training a model, start the inference service in a second terminal:

    gnn-sdn-apt-live --model baseline --interval 5

The service rebuilds the latest graph snapshot and appends above-threshold detections to data/processed/alerts.jsonl and data/processed/decisions.jsonl. Use model gcn or gat only after training that model. Repeated alerts for a host have a cooldown.

## Safety gates

Alert-only is the default. Automatic blocking requires mitigation.enabled: true in config/config.yaml and GNN_SDN_MITIGATION=1 in both the Ryu process environment and the live inference process environment. The controller ignores old decisions that already existed when it started, rejects source addresses outside 10.0.0.0/24, installs a temporary IPv4 source drop rule, and records decision-action latency in data/processed/mitigation_events.jsonl. The timeout is configured in YAML and bounded between 1 and 3600 seconds.

Do not enable blocking on a production controller. This is intended for the isolated Mininet research topology only; false-positive analysis must precede mitigation experiments.
