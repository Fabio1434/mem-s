# SIEM léger — ingestion et corrélation opérationnelles

Les modules `gnn_sdn_apt.siem` et `gnn_sdn_apt.siem_ingest` fournissent une couche SIEM légère intégrée au service d'inférence live.

## Fonctions

- Normalisation vers un événement canonique avec horodatage UTC, provenance et label inconnu par défaut (`-1`).
- Stockage JSONL append-only disponible pour les usages d'audit hors ingestion live.
- Stockage SQLite des événements et du cycle de vie des incidents.
- Import des statistiques du collecteur Ryu depuis `data/raw/flow_stats.csv`.
- Identifiants stables afin de rendre les cycles de polling idempotents.
- Corrélation explicable du fan-out par hôte et fenêtre temporelle.
- Conservation du statut d'un incident existant lors d'une nouvelle ingestion.

## Intégration au service live

Le service `gnn-sdn-apt-live` exécute l'ingestion SIEM avant le scoring GNN/baseline. La configuration est définie dans `config/config.yaml` :

```yaml
paths:
  siem_db: data/siem/siem.db

siem:
  enabled: true
  correlation_window_seconds: 60
  min_distinct_destinations: 5
```

L'ingestion est passive : elle ne modifie pas les règles OpenFlow et n'active pas la mitigation. La base SQLite est créée automatiquement.

## Utilisation autonome

```python
from gnn_sdn_apt.siem import JsonlEventStore, SQLiteSiemStore, correlate_events

event = {
    "timestamp": 1700000000,
    "ip_src": "10.0.0.1",
    "ip_dst": "10.0.0.2",
    "ip_proto": 6,
    "byte_count": 1200,
}
JsonlEventStore("data/siem/events.jsonl").append(event)
store = SQLiteSiemStore("data/siem/siem.db")
stored = store.add_event(event)
findings = correlate_events([stored], window_seconds=60, min_distinct_destinations=5)
```

La règle fan-out constitue un indicateur de reconnaissance réseau, pas une preuve d'APT. Les événements sans annotation gardent le label `-1` ; ils ne sont pas convertis en trafic normal. La corrélation live travaille sur la fenêtre temporelle la plus récente du CSV. Les anciennes observations sont conservées dans SQLite, mais ne sont pas réalertées à chaque cycle.

## Tests

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Les tests d'ingestion utilisent un CSV Ryu synthétique. Ils ne remplacent pas un test de bout en bout avec Mininet, Open vSwitch et Ryu réellement exécutés.
