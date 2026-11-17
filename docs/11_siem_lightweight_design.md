# 11 — Conception fonctionnelle du SIEM léger spécialisé

## Objectif

Ce document définit les fonctions SIEM minimales à ajouter autour du pipeline de détection existant. Le périmètre initial reste limité aux événements réseau du laboratoire SDN et aux événements internes du détecteur.

## État réel et cible

| Fonction | État constaté dans le dépôt | Cible |
|---|---|---|
| Collecte OpenFlow | Présente dans Ryu | Tester en laboratoire |
| Annotations des scénarios | Présentes | Vérifier leur qualité temporelle |
| Normalisation canonique | Partielle, via CSV/features | Ajouter un schéma d'événement stable |
| Centralisation | Fichiers CSV et JSONL dispersés | Registre d'événements unique |
| Corrélation | Fenêtres et graphes du pipeline | Règles explicites par hôte/séquence |
| Détection | Baseline, GCN, GAT | Évaluation sur données réelles annotées |
| Alertes | JSONL | Ajouter identifiants, gravité et déduplication |
| Gestion d'incidents | Non complète | Cycle de vie et historique SQLite |
| Réponse SDN | Blocage temporaire optionnel | Tester sûreté, délai et impact |
| Tableau de bord | Non complet | Vue Flask minimale |

## 1. Schéma canonique d'événement

Chaque événement normalisé devrait comporter :

- `event_id` : UUID ou identifiant déterministe unique ;
- `timestamp` : date UTC ISO 8601 ;
- `source_component` : ryu, scenario, detector ou mitigation ;
- `event_type` : flow_observed, scenario_label, detection_alert ou mitigation_action ;
- `src_ip`, `dst_ip`, `protocol`, `src_port`, `dst_port` si disponibles ;
- `datapath_id`, `host_id`, `window_start`, `window_end) si disponibles ;
- `label` : 0 normal, 1 suspect, -1 inconnu, uniquement pour les événements annotés ;
- `payload` : champs propres à la source.

Les champs absents doivent être null, et non remplacés par des valeurs inventées. Les données brutes restent immuables et conservées à part.

## 2. Stockage progressif

### Version 1 : JSONL
Utiliser un fichier append-only par type d'événement ou un journal commun. Cette approche est simple, lisible, facile à versionner dans les tests et ne demande aucun service supplémentaire.

### Version 2 : SQLite
Ajouter une base locale pour :
- indexer les événements par timestamp, type et adresse IP ;
- retrouver les alertes d'un hôte ;
- regrouper plusieurs alertes dans un incident ;
- conserver le statut, la gravité et les horodatages d'un incident ;
- tracer les décisions et actions de mitigation.

Ne pas introduire Elasticsearch/OpenSearch dans la première version : ce serait disproportionné pour le laboratoire et la volumétrie visés.

## 3. Corrélation initiale

Commencer avec des règles explicables et testables :
- plusieurs destinations distinctes contactées par un même hôte dans une fenêtre ;
- augmentation inhabituelle des flux sortants par rapport à la fenêtre précédente ;
- communications successives entre hôtes internes ;
- combinaison d'événements recon, mouvement latéral et transfert de données factices sur une période définie.

Ces règles produisent du contexte et des alertes candidates ; elles ne prouvent pas à elles seules une APT. Le GNN apporte ensuite l'analyse relationnelle apprise.

## 4. Cycle de vie d'un incident

Un incident doit posséder :
- `incident_id` ;
- `first_seen` et `last_seen` ;
- `primary_host` et les hôtes associés ;
- `severity` et `confidence` ;
- la liste des événements/alertes liés ;
- `status` : open, investigating, contained ou closed ;
- les actions appliquées et leur résultat.

Une alerte est une observation du détecteur. Un incident est un regroupement contextualisé et suivi dans le temps. Ne pas confondre les deux notions.

## 5. Tableau de bord minimal

Une interface Flask peut présenter :
1. l'état du contrôleur et des composants ;
2. le nombre d'événements reçus ;
3. les dernières alertes ;
4. les incidents ouverts et leur statut ;
5. le score de menace par hôte ;
6. l'historique de mitigation et la latence décision-action.

La première version est en lecture seule. Toute action de blocage doit rester protégée par les garde-fous du contrôleur et ne pas être déclenchable librement depuis l'interface.

## 6. Ordre d'implémentation recommandé

1. Valider Mininet, OVS et Ryu sur la VM Linux.
2. Stabiliser le format canonique d'événement et ajouter des tests.
3. Ajouter le stockage JSONL centralisé et un identifiant d'événement.
4. Implémenter la corrélation par fenêtres avec tests unitaires.
5. Ajouter SQLite pour les incidents et leur cycle de vie.
6. Exposer les alertes/incidents en lecture seule via Flask.
7. Évaluer la chaîne complète avant de considérer la mitigation automatisée comme validée.

## 7. Critères d'acceptation

- Chaque événement normalisé conserve son horodatage et sa provenance.
- Les événements non annotés restent inconnus.
- Les événements bruts ne sont jamais écrasés par la normalisation.
- La corrélation est déterministe et couverte par des tests.
- Un incident conserve son historique et ses transitions d'état.
- Le tableau de bord n'expose pas d'action de blocage non protégée.
- Les métriques de détection et de mitigation proviennent d'expériences annotées, pas du jeu synthétique de démonstration.
