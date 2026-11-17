# GNN-SDN-APT Detection

## Sujet du mémoire

**Détection et mitigation automatisées des comportements APT par Graph Neural Networks dans un environnement SDN.**

Prototype de recherche M2 : collecte de statistiques OpenFlow, transformation en graphes temporels, comparaison d'une baseline classique avec GCN/GAT, puis génération d'alertes et réponse SDN contrôlée dans un laboratoire Mininet.

## Architecture

Mininet / hôtes privés → Open vSwitch / OpenFlow 1.3 → Ryu → flow_stats.csv → ingestion SIEM SQLite / corrélation → ingénierie des caractéristiques → graphes temporels NetworkX → Random Forest / GCN / GAT → score de menace → alertes / incidents → règle SDN temporaire optionnelle.

## État du dépôt

Le squelette de conception et le pipeline principal sont implémentés. Les tests unitaires et le workflow CI sont présents. La validation d'intégration réelle Mininet/Ryu reste à faire dans une VM Linux compatible ; aucune mesure expérimentale n'est revendiquée avant cette validation.

## Installation Python

Sous Linux/VM Linux, avec Mininet, Open vSwitch et Ryu installés :

    python3 -m venv --system-site-packages .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

Pour les modèles GNN :

    pip install -e ".[ml]"

## Démarrer le laboratoire

Terminal 1 :

    ryu-manager --ofp-tcp-listen-port 6653 sdn/ryu_app.py

Terminal 2 :

    sudo -E .venv/bin/python simulation/topology.py

Dans la CLI Mininet :

    scenarios
    scenario normal
    scenario recon
    scenario lateral
    scenario exfil

Ces scénarios restent confinés aux hôtes privés 10.0.0.0/24. Les tentatives TCP sont bornées et n'exécutent pas d'exploits. Le transfert de données utilise des octets factices vers un récepteur dans la topologie.

## Smoke test hors Mininet

Pour vérifier tout le pipeline sans attendre d'avoir accès à une VM SDN, le dépôt fournit un captureur synthétique marqué comme tel :

    python scripts/run_demo.py --output-dir data/demo

Cette commande génère une capture fictive et ses annotations, prépare les features et les graphes temporels, entraîne la baseline Random Forest et écrit les rapports dans data/demo/reports/. Pour inclure aussi GCN et GAT :

    pip install -e ".[ml]"
    python scripts/run_demo.py --output-dir data/demo --with-gnn --epochs 3

**Important :** les métriques de ce smoke test servent uniquement à vérifier le fonctionnement du logiciel. Elles ne représentent pas la performance du détecteur sur de vraies attaques ou des APT. Pour l'évaluation du mémoire, utiliser des données collectées et annotées dans le labo ou un dataset public adapté.

## Comment l'IA intervient dans le pipeline

L'IA n'est pas un chatbot : ce sont des modèles de classification entraînés sur des exemples de trafic annotés. Une ligne de décision correspond à un hôte source dans une fenêtre temporelle.

1. Ryu écrit les statistiques OpenFlow dans le fichier de flux.
2. Le pipeline calcule les caractéristiques et construit un graphe par fenêtre : les hôtes sont les nœuds, les communications sont les arêtes.
3. Le modèle attribue à chaque hôte source un score entre 0 et 1. La Random Forest utilise les caractéristiques de l'hôte ; GCN et GAT exploitent aussi les relations entre hôtes.
4. Le seuil configuré convertit le score en décision. Par défaut, le service génère seulement des alertes ; le blocage SDN est une option séparée et désactivée par défaut.

### Essayer le cycle complet avec les données synthétiques

La démonstration inclut les modèles GCN et GAT si l'extra ML est installé :

    pip install -e ".[ml]"
    python scripts/run_demo.py --output-dir data/demo --with-gnn --epochs 3

Pour entraîner un modèle sur les données préparées du laboratoire, après avoir collecté et annoté suffisamment de fenêtres normales et suspectes :

    gnn-sdn-apt prepare
    gnn-sdn-apt train-gnn --model gcn --epochs 100 --calibrate-threshold

L'inférence continue peut alors utiliser ce modèle :

    gnn-sdn-apt-live --model gcn --interval 5

Pour GAT, remplacer `gcn` par `gat`. Pour la baseline, entraîner avec `gnn-sdn-apt train-baseline --calibrate-threshold`, puis lancer `gnn-sdn-apt-live --model baseline --interval 5`.

Le modèle chargé en direct doit avoir été entraîné sur le même schéma de caractéristiques. Les alertes et décisions sont écrites dans les chemins définis dans `config/config.yaml`. Le score est une estimation apprise à partir des données d'entraînement, pas une preuve qu'une APT est présente. Les performances ne sont pas validées tant que le pipeline n'a pas été évalué sur des captures annotées et séparées chronologiquement.

## Importer un dataset public horodaté

L'importeur générique convertit notamment des CSV de type CICFlowMeter/UNSW vers le schéma du projet. Les labels de catégorie d'attaque deviennent « normal vs attaque » et ne doivent pas être décrits comme des labels APT spécifiques.

    gnn-sdn-apt import-csv --input /chemin/vers/dataset.csv --output data/raw/public_flows.csv
    gnn-sdn-apt prepare --raw-input data/raw/public_flows.csv --labels data/raw/no_lab_annotations.csv

## Entraîner et comparer les modèles

Après la collecte de flux et l'annotation des scénarios :

    gnn-sdn-apt prepare
    gnn-sdn-apt inspect
    gnn-sdn-apt train-baseline --calibrate-threshold
    gnn-sdn-apt train-gnn --model gcn --epochs 100 --calibrate-threshold
    gnn-sdn-apt train-gnn --model gat --epochs 100 --calibrate-threshold
    gnn-sdn-apt compare

Les commandes GCN/GAT requièrent l'extra ML. Il faut collecter suffisamment de fenêtres annotées comprenant les deux classes avant l'entraînement. Avec --calibrate-threshold et suffisamment de snapshots, un seuil est choisi sur une partition chronologique de validation séparée. Si ce découpage n'est pas viable, le seuil configuré est conservé et indiqué dans le rapport. Les métriques sont sauvegardées dans reports/.

## Inférence et mitigation optionnelle

Après avoir entraîné le modèle :

    gnn-sdn-apt-live --model baseline --interval 5

Les alertes et décisions sont écrites dans data/processed/. En cas de blocage expérimental, les latences décision-action sont résumées par gnn-sdn-apt summarize-mitigation. La mitigation SDN est désactivée par défaut et requiert une activation explicite dans le YAML ainsi que GNN_SDN_MITIGATION=1 dans l'environnement du contrôleur. Les blocs n'acceptent que des sources du sous-réseau de laboratoire et expirent après 60 secondes. Ne pas l'activer sur un réseau de production.

## Documentation

- docs/01_conception.md — problématique et objectifs
- docs/02_architecture.md — architecture technique
- docs/03_methodologie.md — méthodologie
- docs/04_dataset.md — données et graphes
- docs/05_scenarios.md — scénarios
- docs/06_roadmap.md — état d'avancement
- docs/08_execution.md — procédure d'exécution complète
- docs/09_evaluation_protocol.md — protocole expérimental
- docs/10_data_dictionary.md — dictionnaire des données
- docs/11_siem_lightweight_design.md — conception du SIEM léger
- docs/12_siem_module.md — ingestion et corrélation SIEM

## Vérifications et tests

    python scripts/check_environment.py
    python -m compileall -q src simulation sdn scripts
    pytest -q

GitHub Actions lance également les tests unitaires à chaque push et pull request. Les tests de bout en bout nécessitent Mininet, Open vSwitch et Ryu sur une VM Linux ; ils ne peuvent pas être certifiés par les tests Python unitaires seuls.

## SIEM léger — ingestion, stockage, corrélation et supervision

Une première couche SIEM indépendante de Mininet/Ryu est disponible :

- normalisation des événements réseau vers un schéma canonique UTC ;
- stockage append-only JSONL pour l'audit ;
- stockage SQLite des événements et incidents ;
- corrélation explicable des connexions vers plusieurs destinations dans une fenêtre temporelle.

Exemple d'utilisation :

```python
from gnn_sdn_apt.siem import JsonlEventStore, SQLiteSiemStore, correlate_events

event = {"timestamp": 1700000000, "ip_src": "10.0.0.1",
         "ip_dst": "10.0.0.2", "ip_proto": 6, "byte_count": 1200}
JsonlEventStore("data/siem/events.jsonl").append(event)
store = SQLiteSiemStore("data/siem/siem.db")
stored = store.add_event(event)
findings = correlate_events([stored], window_seconds=60, min_distinct_destinations=5)
```

Le service `gnn-sdn-apt-live` ingère également les lignes Ryu de `flow_stats.csv` dans `data/siem/siem.db`, met à jour les incidents corrélés et persiste les scores baseline/GCN/GAT dépassant le seuil. L'ingestion est incrémentale : le curseur est conservé dans SQLite, les lignes incomplètes sont différées et le service détecte les rotations/troncatures du CSV. Le paramètre `siem.enabled` permet de désactiver cette ingestion. Un tableau de bord local en lecture seule est disponible :

    gnn-sdn-apt-dashboard --host 127.0.0.1 --port 8080

Ouvrir ensuite `http://127.0.0.1:8080`. Voir [docs/12_siem_module.md](docs/12_siem_module.md). La règle fan-out et les scores modèles sont des indicateurs, pas une preuve d'APT. Les événements non annotés conservent le label `-1`. Le dashboard n'offre aucune action de mitigation.
