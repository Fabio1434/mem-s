# 02 — Architecture technique

## Vue générale

~~~text
Mininet
  ↓
Open vSwitch / OpenFlow
  ↓
Ryu Controller
  ↓
Data Collector
  ↓
Feature Engineering
  ↓
Dynamic Graph / NetworkX
  ↓
GCN / GAT / PyTorch Geometric
  ↓
Threat Score
  ↓
Decision Engine
  ↓
Ryu / OpenFlow Action
  ↓
Alert / Block / Isolate
~~~

## Modèle de graphe

### Nœuds

Un nœud représente une entité réseau observable, principalement un hôte.

Caractéristiques envisagées et partiellement implémentées :

- nombre de flux entrants et sortants ;
- nombre de destinations, sources et ports distincts ;
- volumes de paquets/octets et taux moyens ;
- durée moyenne des flux ;
- activité à la fenêtre précédente ;
- variation du nombre de flux sortants ;
- nombre de nouvelles destinations dans la fenêtre ;
- longueur de la séquence d'activité consécutive.

Les features temporelles d'un nœud sont calculées à partir de la fenêtre précédente observée. Après une lacune de fenêtre, l'historique court est réinitialisé. Il s'agit d'une classification GNN par snapshot avec features temporelles explicites, pas d'une architecture récurrente temporelle.

### Arêtes

Une arête représente une relation de communication pendant une fenêtre temporelle.

Caractéristiques envisagées :

- protocole
- port source/destination
- nombre de paquets
- nombre d'octets
- durée
- débit
- indicateurs TCP

## Pipeline

~~~text
Flow statistics
      ↓
Cleaning / normalization
      ↓
Feature extraction
      ↓
Graph construction
      ↓
Graph snapshot
      ↓
GNN inference
      ↓
Threat score
      ↓
Policy
      ↓
SDN action
~~~

## Séparation des responsabilités

- simulation/ : laboratoire et génération de trafic contrôlé
- sdn/ : contrôleur et intégration OpenFlow
- src/collector/ : acquisition
- src/features/ : transformation
- src/graph/ : représentation
- src/detection/ : modèles et inférence
- src/mitigation/ : politiques et actions
- tests/ : validation
