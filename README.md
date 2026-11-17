# SIEM léger GNN-SDN pour l'étude des comportements APT

## Sujet du mémoire

**Conception d'un SIEM intelligent et spécialisé basé sur les Graph Neural Networks et le Software-Defined Networking pour la détection et la mitigation automatisées des comportements caractéristiques des attaques APT.**

Prototype de recherche M2 limité à la télémétrie réseau d'un laboratoire SDN. Il étudie la collecte et la centralisation d'événements OpenFlow, leur corrélation temporelle, la représentation des communications en graphes, la comparaison Random Forest/GCN/GAT et une réponse SDN contrôlée.

Le projet ne vise pas à remplacer un SIEM d'entreprise multi-sources. Les journaux systèmes et applicatifs sont hors périmètre initial.

## Architecture cible

Mininet / hôtes privés → Open vSwitch / OpenFlow 1.3 → Ryu → collecte des statistiques → normalisation et centralisation légère → corrélation par fenêtres → graphes NetworkX → Random Forest / GCN / GAT → score de menace → alertes et incidents → décision → Ryu / OpenFlow → journal d'audit.

Le stockage commence avec des fichiers CSV/JSONL et doit évoluer vers SQLite pour l'indexation des événements et le cycle de vie des incidents. La conception fonctionnelle est décrite dans `docs/11_siem_lightweight_design.md`.

## État du dépôt

Le dépôt contient déjà la topologie Mininet, le contrôleur Ryu, les scénarios de laboratoire, le pipeline de caractéristiques et graphes, la baseline Random Forest, les modèles GCN/GAT, l'inférence, les alertes JSONL et un mécanisme de blocage temporaire protégé.

Les fonctions SIEM supplémentaires — schéma canonique unifié, corrélation explicite, base d'incidents et tableau de bord — sont des évolutions à implémenter. La validation d'intégration Mininet/Ryu et les mesures expérimentales réelles restent à effectuer. Aucune performance de détection APT n'est revendiquée à ce stade.

## Installation

Le laboratoire nécessite une VM Linux avec Mininet, Open vSwitch et Ryu installés selon les versions compatibles avec la distribution. Ne pas remplacer le Python système de Kali et ne pas utiliser `sudo pip`.

Depuis la racine du dépôt :

    python3 -m venv --system-site-packages .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -e ".[dev]"
    python scripts/check_environment.py

Pour les modèles GNN :

    pip install -e ".[ml]"

Si la version Python par défaut de la distribution est trop récente pour une dépendance SDN/ML, créer un environnement avec une version Python prise en charge plutôt que de modifier le Python système.

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

Les scénarios restent confinés aux hôtes privés 10.0.0.0/24. Ils n'exécutent pas d'exploits. Le transfert de données utilise des octets factices vers un récepteur du laboratoire.

## Smoke test logiciel sans Mininet

    python scripts/run_demo.py --output-dir data/demo

Pour inclure GCN et GAT :

    pip install -e ".[ml]"
    python scripts/run_demo.py --output-dir data/demo --with-gnn --epochs 3

Les données de démonstration sont synthétiques. Les métriques servent à vérifier le fonctionnement du logiciel et ne démontrent pas les performances sur des attaques réelles ou des APT.

## Entraînement et comparaison

Après avoir collecté et annoté suffisamment de fenêtres du laboratoire :

    gnn-sdn-apt prepare
    gnn-sdn-apt inspect
    gnn-sdn-apt train-baseline --calibrate-threshold
    gnn-sdn-apt train-gnn --model gcn --epochs 100 --calibrate-threshold
    gnn-sdn-apt train-gnn --model gat --epochs 100 --calibrate-threshold
    gnn-sdn-apt compare

Le découpage doit être chronologique lorsque le nombre de snapshots le permet. Les événements sans annotation restent inconnus (-1), et ne sont pas utilisés comme exemples normaux.

## Inférence et mitigation

    gnn-sdn-apt-live --model baseline --interval 5

La mitigation reste désactivée par défaut. Elle exige une activation explicite dans le YAML et `GNN_SDN_MITIGATION=1` dans l'environnement des processus concernés. Le contrôleur limite le blocage au sous-réseau de laboratoire 10.0.0.0/24 et utilise des règles temporaires. Ne jamais activer ce mécanisme sur un réseau de production.

## Documentation

- `docs/01_conception.md` — problématique, objectifs et hypothèses
- `docs/02_architecture.md` — architecture technique
- `docs/03_methodologie.md` — méthodologie expérimentale
- `docs/04_dataset.md` — données et graphes
- `docs/05_scenarios.md` — scénarios
- `docs/06_roadmap.md` — état d'avancement
- `docs/08_execution.md` — procédure d'exécution
- `docs/09_evaluation_protocol.md` — protocole d'évaluation
- `docs/10_data_dictionary.md` — dictionnaire des données
- `docs/11_siem_lightweight_design.md` — fonctions SIEM légères et critères d'acceptation

## Vérifications

    python scripts/check_environment.py
    python -m compileall -q src simulation sdn scripts
    pytest -q

Les tests unitaires ne remplacent pas les tests d'intégration Mininet/Ryu. Les résultats expérimentaux ne doivent être présentés qu'après collecte et évaluation de données annotées réelles du laboratoire.
