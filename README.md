# GNN-SDN-APT Detection

## Détection et mitigation automatisées des attaques APT par Graph Neural Networks dans un environnement SDN

Projet de mémoire de Master 2 visant à concevoir un système intelligent capable de représenter dynamiquement une infrastructure réseau sous forme de graphe, de détecter des comportements suspects avec des Graph Neural Networks (GNN), puis d'automatiser une réponse réseau via un contrôleur SDN.

## Chaîne cible

Mininet → Open vSwitch/OpenFlow → Ryu → collecte des flux → graphe dynamique → GNN → score de menace → moteur de décision → mitigation SDN

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

Le détail de la conception est disponible dans le dossier docs/.