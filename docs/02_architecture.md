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

Caractéristiques envisagées :

- nombre de connexions
- nombre de destinations
- nombre de ports utilisés
- octets entrants et sortants
- paquets entrants et sortants
- connexions échouées
- fréquence des connexions

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
