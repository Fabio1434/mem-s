# 01 — Conception du projet

## Titre de travail

**Conception d'un SIEM intelligent et spécialisé basé sur les Graph Neural Networks et le Software-Defined Networking pour la détection et la mitigation automatisées des comportements caractéristiques des attaques APT.**

Le terme « spécialisé » indique que le périmètre de collecte est limité à la télémétrie réseau d'un laboratoire SDN. Le projet ne prétend pas remplacer un SIEM d'entreprise multi-sources.

## Contexte

Les attaques persistantes avancées (APT) peuvent se manifester par une succession d'activités qui paraissent isolément légitimes : reconnaissance, compromission simulée, découverte de ressources, mouvement latéral et exfiltration simulée. L'analyse d'un événement isolé peut être insuffisante ; les relations entre hôtes et l'évolution de leurs communications peuvent apporter un contexte supplémentaire.

Le SDN permet d'observer les flux réseau et de programmer des règles de réponse depuis un contrôleur. Les Graph Neural Networks permettent d'exploiter la structure relationnelle des communications.

## Problématique

Comment concevoir un SIEM léger spécialisé dans la télémétrie réseau SDN, capable de centraliser et corréler les événements de communication, d'exploiter leur représentation en graphes pour détecter des comportements multi-étapes caractéristiques d'APT et de déclencher une réponse réseau contrôlée ?

## Objectif général

Concevoir, développer et évaluer un prototype de SIEM léger spécialisé dans la sécurité réseau, intégrant les Graph Neural Networks et le Software-Defined Networking, afin de collecter, normaliser et corréler les événements réseau, détecter des comportements caractéristiques d'attaques APT et déclencher des mécanismes de mitigation contrôlés via le contrôleur SDN.

## Objectifs spécifiques

1. Mettre en place un laboratoire SDN reproductible avec Mininet, Open vSwitch et Ryu.
2. Collecter les statistiques de flux et les annotations de scénarios.
3. Définir un format canonique et centraliser les événements réseau.
4. Corréler les événements par hôte et fenêtre temporelle.
5. Représenter les communications sous forme de graphes dirigés.
6. Construire les caractéristiques des nœuds et des arêtes.
7. Établir une baseline Random Forest.
8. Implémenter et comparer GCN et GAT.
9. Définir un score de menace, une politique de décision et un suivi d'incidents.
10. Intégrer une mitigation temporaire via Ryu/OpenFlow dans le seul laboratoire.
11. Évaluer la détection, les faux positifs, la latence et l'impact de la mitigation.

## Hypothèses de recherche

- H1 : les relations entre hôtes représentées dans un graphe peuvent apporter un gain mesurable par rapport à une baseline fondée sur les caractéristiques agrégées des hôtes.
- H2 : le contrôleur SDN permet d'appliquer une action de confinement avec un délai décision-action mesurable.
- H3 : une corrélation par fenêtres temporelles aide à contextualiser plusieurs événements réseau liés à une même séquence expérimentale.

Ces hypothèses sont à tester. Aucune supériorité des GNN ni efficacité de mitigation n'est présumée.

## Périmètre et limites

Le prototype est destiné à un laboratoire virtualisé isolé. Les scénarios sont contrôlés, reproductibles et non destructifs. Le périmètre de la première version est la télémétrie réseau OpenFlow et les événements produits par le prototype. La collecte multi-sources de journaux systèmes et applicatifs est hors périmètre initial.

Les scénarios représentent des comportements réseau inspirés de phases APT ; ils ne reproduisent pas l'ensemble d'une campagne APT réelle. Les labels « normal » et « suspect » sont des annotations expérimentales et ne constituent pas une attribution certaine à une APT.

## Indicateurs d'évaluation

### Détection
- précision, rappel et F1-score ;
- taux de faux positifs et faux négatifs ;
- matrice de confusion ;
- latence d'inférence et délai entre activité et alerte.

### Mitigation
- délai décision-action ;
- délai de confinement ;
- proportion de flux suspects bloqués ;
- impact sur le trafic légitime ;
- nombre de faux blocages.

## Contribution attendue

La contribution est l'évaluation expérimentale d'une chaîne intégrée collecte réseau → corrélation → graphe → classification GNN → décision → action SDN, avec comparaison à une baseline classique et mesure de l'impact de la réponse automatisée.
