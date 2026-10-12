# Collector

The first collector is implemented in `sdn/ryu_app.py`.

It periodically requests OpenFlow 1.3 flow statistics from connected switches and writes:

`data/raw/flow_stats.csv`

The collector is observation-only at this stage. It does not modify flows or block traffic.

## Output fields

- timestamp
- datapath_id
- in_port
- Ethernet/IP endpoints
- IP protocol
- transport ports
- packet_count
- byte_count
- duration_sec

The CSV is an intermediate research format. The feature-engineering stage will later transform it into temporal graph snapshots.
