# 01 — Conception du projet

## Contexte

Les attaques persistantes avancées (APT) se caractérisent par une succession d'activités pouvant paraître légitimes lorsqu'elles sont observées individuellement : reconnaissance, compromission, découverte, mouvement latéral et exfiltration simulée.

Le projet étudie une représentation du réseau sous forme de graphe afin d'exploiter les relations entre entités réseau.

## Problématique

Comment exploiter la représentation dynamique d'une infrastructure réseau sous forme de graphe afin d'améliorer la détection de comportements caractéristiques d'attaques APT dans un environnement SDN, tout en permettant une réponse réseau automatisée ?

## Hypothèses

### H1 — Détection

La représentation relationnelle des communications réseau par un graphe peut apporter des informations complémentaires aux caractéristiques individuelles des flux pour identifier certains comportements multi-étapes.

### H2 — Mitigation

L'intégration du moteur de détection à un contrôleur SDN permet de réduire le délai entre la détection d'un comportement suspect et son confinement.

## Objectif général

Concevoir et évaluer un prototype de détection et de mitigation automatisées des comportements APT dans un environnement SDN en utilisant des Graph Neural Networks.

## Objectifs spécifiques

- Concevoir une infrastructure SDN expérimentale reproductible.
- Collecter les statistiques de communication réseau.
- Définir une représentation dynamique en graphe.
- Construire les caractéristiques des nœuds et des arêtes.
- Établir des modèles de référence classiques.
- Implémenter un GCN.
- Implémenter puis évaluer un GAT.
- Définir un score de menace et une politique de décision.
- Transmettre les décisions au contrôleur SDN.
- Appliquer des actions de confinement contrôlées.
- Mesurer la qualité de détection et les performances de mitigation.

## Périmètre

Le prototype sera réalisé dans un laboratoire virtualisé. Les scénarios d'attaque seront contrôlés et reproductibles. L'objectif n'est pas de construire une plateforme APT complète, mais d'étudier la détection de comportements réseau représentatifs de séquences multi-étapes.

## Critères d'évaluation

### Détection

- Precision
- Recall
- F1-score
- taux de faux positifs
- taux de faux négatifs
- temps de détection

### Mitigation

- temps entre détection et action
- temps de confinement
- proportion de trafic suspect bloqué
- impact sur le trafic légitime

## Principe expérimental

Une comparaison sera réalisée entre au moins une approche classique et les approches GCN/GAT. Le but est de mesurer l'apport réel de la représentation en graphe et non de supposer qu'un GNN est systématiquement supérieur.
