# SDN

The initial SDN component is `ryu_app.py`.

## Current capabilities

- OpenFlow 1.3
- switch registration
- periodic flow-statistics requests
- CSV export to `data/raw/flow_stats.csv`
- observation-only behavior

## Deliberate limitation

Automatic mitigation is **disabled** in this phase. The research workflow must first establish reliable collection, feature extraction and detection before any SDN action is enabled.

Future components will connect the threat decision engine to controlled OpenFlow actions such as blocking or quarantine.
