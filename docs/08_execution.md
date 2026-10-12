# 08 — Installation et exécution complète

## 1. Environnement

Le laboratoire SDN doit être exécuté sur Linux ou dans une VM Linux. Mininet et Open vSwitch nécessitent des privilèges système et ne sont pas pris en charge directement sur Windows natif.

Installer les dépendances système Mininet, Open vSwitch et une version compatible de Ryu selon la distribution. Le dépôt sépare volontairement les dépendances SDN système des bibliothèques Python d'analyse.

Depuis la racine du dépôt :

    python3 -m venv --system-site-packages .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -e ".[dev]"

Pour activer les modèles GNN :

    pip install -e ".[ml]"

Si les dépendances PyTorch doivent correspondre à CUDA, installer d'abord la version PyTorch adaptée à la machine puis installer PyTorch Geometric selon leurs instructions officielles.

## 2. Démarrer le laboratoire

Terminal 1 — contrôleur et collecte :

    ryu-manager --ofp-tcp-listen-port 6653 sdn/ryu_app.py

Terminal 2 — topologie :

    sudo -E .venv/bin/python simulation/topology.py

La topologie contient cinq hôtes privés sur un commutateur Open vSwitch. Elle effectue un ping initial puis ouvre une CLI Mininet étendue.

Dans la CLI Mininet :

    scenarios
    scenario normal
    scenario recon
    scenario lateral
    scenario exfil
    exit

Les scénarios ne déploient aucun exploit. La reconnaissance et le mouvement latéral sont des tentatives TCP bornées vers les IPs privées de la topologie. Le transfert dit « exfil » envoie uniquement des données factices de taille fixe vers un récepteur du laboratoire.

Chaque commande de scénario écrit une annotation dans data/raw/scenario_labels.csv. Le contrôleur écrit les statistiques OpenFlow dans data/raw/flow_stats.csv.

## 3. Construire le dataset de graphes

Après avoir collecté des flux et lancé des scénarios normaux et suspects :

    gnn-sdn-apt prepare
    gnn-sdn-apt inspect

Produits créés :
- data/processed/flow_features.csv : deltas de compteurs et débits par flux ;
- data/processed/graphs.jsonl : un graphe dirigé par fenêtre temporelle.

Une observation sans annotation correspond au label -1, pas à une observation normale. Les annotations du laboratoire utilisent 0 pour normal et 1 pour suspect.

## 4. Entraîner la baseline classique

    gnn-sdn-apt train-baseline
    gnn-sdn-apt inspect

Artefacts :
- models/checkpoints/baseline.joblib ;
- reports/baseline_metrics.json.

La baseline Random Forest est la référence de comparaison. Le rapport indique si le découpage temporel a pu être utilisé. Quand il y a trop peu de fenêtres, un repli au niveau des observations est marqué explicitement ; il ne faut pas le présenter comme une évaluation temporelle indépendante.

## 5. Entraîner un GCN ou un GAT

Après la baseline, installer l'extra ML et collecter suffisamment de graphes annotés dans plusieurs fenêtres temporelles :

    pip install -e ".[ml]"
    gnn-sdn-apt train-gnn --model gcn --epochs 100
    gnn-sdn-apt train-gnn --model gat --epochs 100

Artefacts : modèles .pt et rapports JSON correspondants dans models/checkpoints et reports.

L'entraînement GNN utilise un découpage chronologique par snapshots. Il échoue explicitement si les partitions ne contiennent pas les deux classes ou si le nombre de snapshots annotés est insuffisant.

## 6. Inférence en quasi-temps réel

Après entraînement du modèle choisi, lancer le service suivant dans un autre terminal :

    gnn-sdn-apt-live --model baseline --interval 5

Le nom de commande exposé par le package peut être lancé de façon équivalente avec :

    python -m gnn_sdn_apt.live --model baseline --interval 5

Utiliser --model gcn ou --model gat après entraînement de ces modèles. Les scores au-dessus du seuil sont ajoutés à data/processed/alerts.jsonl et data/processed/decisions.jsonl.

Le seuil de 0,90 est un paramètre de départ, pas un résultat validé. Il doit être sélectionné à partir des mesures sur le jeu de validation, avant l'évaluation finale.

## 7. Mitigation contrôlée

La mitigation est désactivée par défaut. Pour l'activer, deux conditions sont requises :
1. config/config.yaml doit contenir mitigation.enabled: true ;
2. le contrôleur Ryu doit démarrer avec GNN_SDN_MITIGATION=1.

Exemple uniquement dans le laboratoire :

    GNN_SDN_MITIGATION=1 ryu-manager --ofp-tcp-listen-port 6653 sdn/ryu_app.py

Le contrôleur n'accepte les ordres de blocage que pour une adresse IPv4 dans 10.0.0.0/24. Les règles de blocage expirent après 60 secondes. Il faut conserver le mode alerte pendant le développement et ne tester le blocage qu'après analyse des faux positifs.

## 8. Tests automatisés

    pip install -e ".[dev]"
    pytest -q

Le workflow GitHub Actions lance les tests unitaires à chaque push et pull request. Les tests Mininet/Ryu de bout en bout nécessitent une VM Linux configurée et doivent être validés dans cet environnement.
