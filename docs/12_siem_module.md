# SIEM léger — premier module opérationnel

Le module `gnn_sdn_apt.siem` fournit une première couche indépendante de Mininet/Ryu :

- normalisation vers un événement canonique avec horodatage UTC, provenance et label inconnu par défaut (`-1`) ;
- stockage append-only JSONL ;
- stockage SQLite des événements et du cycle de vie des incidents ;
- corrélation explicable d'un comportement de fan-out/reconnaissance par source et fenêtre temporelle.

## Utilisation rapide

```python
from gnn_sdn_apt.siem import JsonlEventStore, SQLiteSiemStore, correlate_events

jsonl = JsonlEventStore("data/siem/events.jsonl")
sqlite = SQLiteSiemStore("data/siem/siem.db")

event = {
    "timestamp": 1700000000,
    "ip_src": "10.0.0.1",
    "ip_dst": "10.0.0.2",
    "ip_proto": 6,
    "byte_count": 1200,
}
jsonl.append(event)
stored = sqlite.add_event(event)
findings = correlate_events([stored], window_seconds=60, min_distinct_destinations=5)
```

La règle de fan-out ne s'active que si le nombre de destinations distinctes dépasse le seuil. Elle constitue un indicateur de reconnaissance réseau, pas une preuve d'APT. Les événements sans annotation gardent le label `-1` ; ils ne sont pas convertis en trafic normal.

## Tests

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Ce module ne déclenche aucune action SDN. L'intégration au collecteur Ryu, au moteur de détection GNN et à une interface de visualisation reste une étape distincte à valider.
