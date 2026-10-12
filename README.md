# GNN-SDN-APT Detection

## Détection et mitigation automatisées des attaques APT par Graph Neural Networks dans un environnement SDN

Projet de mémoire de Master 2 visant à concevoir un prototype reproductible capable de représenter dynamiquement une infrastructure réseau sous forme de graphe, de détecter des comportements suspects avec des Graph Neural Networks (GNN), puis de préparer une réponse réseau contrôlée via un contrôleur SDN.

## Architecture de recherche

`Mininet → Open vSwitch/OpenFlow → Ryu → collecte des flux → graphe dynamique → GNN → score de menace → moteur de décision → mitigation SDN`

## État actuel

La Phase 2 commence par une chaîne **observation-only** :

`Mininet → OVS/OpenFlow 1.3 → Ryu → flow_stats.csv`

Aucune mitigation automatique n'est encore activée. Cette séparation permet de valider d'abord la qualité et la reproductibilité des données avant d'introduire la détection et la réponse.

## Phases

1. Conception et architecture
2. Laboratoire Mininet/Ryu
3. Collecte et normalisation
4. Construction du graphe
5. Baselines classiques
6. GCN
7. GAT
8. Détection temps quasi réel
9. Moteur de décision
10. Mitigation SDN
11. Évaluation

Voir `docs/` pour la conception détaillée et `simulation/` + `sdn/` pour la première implémentation.
