# GNN-SDN-APT Detection

## Sujet du mémoire

**Détection et mitigation automatisées des comportements APT par Graph Neural Networks dans un environnement SDN.**

Prototype de recherche M2 : collecte de statistiques OpenFlow, transformation en graphes temporels, comparaison d'une baseline classique avec GCN/GAT, puis génération d'alertes et réponse SDN contrôlée dans un laboratoire Mininet.

## Architecture

Mininet / hôtes privés → Open vSwitch / OpenFlow 1.3 → Ryu → flow_stats.csv → ingénierie des caractéristiques → graphes temporels NetworkX → Random Forest / GCN / GAT → score de menace → journal d'alerte → règle SDN temporaire optionnelle.

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

## Importer un dataset public horodaté

L'importeur générique convertit notamment des CSV de type CICFlowMeter/UNSW vers le schéma du projet. Les labels de catégorie d'attaque deviennent « normal vs attaque » et ne doivent pas être décrits comme des labels APT spécifiques.

    gnn-sdn-apt import-csv --input /chemin/vers/dataset.csv --output data/raw/public_flows.csv
    gnn-sdn-apt prepare --raw-input data/raw/public_flows.csv --labels data/raw/no_lab_annotations.csv

## Entraîner et comparer les modèles

Après la collecte de flux et l'annotation des scénarios :

    gnn-sdn-apt prepare
    gnn-sdn-apt inspect
    gnn-sdn-apt train-baseline
    gnn-sdn-apt train-gnn --model gcn --epochs 100
    gnn-sdn-apt train-gnn --model gat --epochs 100
    gnn-sdn-apt compare

Les commandes GCN/GAT requièrent l'extra ML. Il faut collecter suffisamment de fenêtres annotées comprenant les deux classes avant l'entraînement. Les métriques sont sauvegardées dans reports/.

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

## Vérifications et tests

    python scripts/check_environment.py
    python -m compileall -q src simulation sdn scripts
    pytest -q

GitHub Actions lance également les tests unitaires à chaque push et pull request. Les tests de bout en bout nécessitent Mininet, Open vSwitch et Ryu sur une VM Linux ; ils ne peuvent pas être certifiés par les tests Python unitaires seuls.
