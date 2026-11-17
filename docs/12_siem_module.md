# SIEM léger — ingestion et corrélation opérationnelles

Les modules `gnn_sdn_apt.siem`, `gnn_sdn_apt.siem_ingest` et `gnn_sdn_apt.siem_stream` fournissent une couche SIEM légère intégrée au service d'inférence live.

## Fonctions

- Normalisation vers un événement canonique avec horodatage UTC, provenance et label inconnu par défaut (`-1`).
- Stockage JSONL append-only disponible pour les usages d'audit hors ingestion live.
- Stockage SQLite des événements et du cycle de vie des incidents.
- Import des statistiques du collecteur Ryu depuis `data/raw/flow_stats.csv`.
- Identifiants stables afin de rendre les cycles de polling idempotents.
- Ingestion incrémentale : seuls les nouveaux enregistrements CSV complets sont lus ; le curseur (offset, numéro de ligne, signature et empreinte de contrôle) est conservé dans SQLite.
- Reprise après redémarrage, détection du remplacement, de la troncature et des réécritures détectables du fichier ; une ligne finale incomplète est attendue jusqu'à l'arrivée du saut de ligne.
- Corrélation explicable du fan-out par hôte et fenêtre temporelle.
- Persistance des alertes dépassant le seuil du modèle baseline/GCN/GAT comme incidents SIEM.
- Conservation du statut d'un incident existant lors d'une nouvelle ingestion.

## Intégration au service live

Le service `gnn-sdn-apt-live` exécute l'ingestion Ryu avant le scoring, puis enregistre les scores baseline/GCN/GAT dépassant le seuil comme incidents persistants. La configuration est définie dans `config/config.yaml` :

```yaml
paths:
  siem_db: data/siem/siem.db

siem:
  enabled: true
  correlation_window_seconds: 60
  min_distinct_destinations: 5
```

L'ingestion et la création des incidents sont passives : elles ne modifient pas les règles OpenFlow et n'activent pas la mitigation. Les scores ne constituent pas une preuve d'APT. La base SQLite est créée automatiquement. Le cycle de vie des incidents accepte les transitions contrôlées `open → investigating → contained → closed` (avec retour possible de `investigating` vers `open`) et journalise chaque changement. L'endpoint d'historique est en lecture seule.

## Tableau de bord local en lecture seule

Après avoir démarré la collecte et le service live, lancer :

```bash
gnn-sdn-apt-dashboard --host 127.0.0.1 --port 8080
```

Ouvrir `http://127.0.0.1:8080`. Le tableau affiche les incidents et les événements récents et expose deux endpoints GET (`/api/incidents`, `/api/events`, `/api/incidents/<id>/history`). Il écoute sur localhost par défaut, n'offre aucune route de modification et ne pilote jamais les règles OpenFlow. Ne pas l'exposer sur une interface publique sans ajouter une authentification et une configuration de déploiement sécurisée.

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

La règle fan-out constitue un indicateur de reconnaissance réseau, pas une preuve d'APT. Les événements sans annotation gardent le label `-1` ; ils ne sont pas convertis en trafic normal. La corrélation live travaille sur la fenêtre temporelle la plus récente des événements déjà centralisés dans SQLite. Le collecteur ne relit pas le CSV entier à chaque cycle : il reprend au dernier offset confirmé. Si le processus s'arrête avant la sauvegarde du curseur, les lignes sont rejouées sans doublon grâce aux identifiants stables.

## Tests

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Les tests d'ingestion et du tableau de bord utilisent des données synthétiques. Ils vérifient le rendu HTML échappé et les interfaces de stockage. Ils ne remplacent pas un test de bout en bout avec Mininet, Open vSwitch et Ryu réellement exécutés.
