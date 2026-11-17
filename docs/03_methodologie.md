# 03 — Méthodologie expérimentale

## 1. Environnement de laboratoire

Construire une topologie Mininet contrôlée avec Open vSwitch et un contrôleur Ryu/OpenFlow 1.3. Le réseau de test utilise exclusivement le sous-réseau privé 10.0.0.0/24. Les tests d'intégration seront réalisés dans une VM Linux dédiée.

## 2. Collecte et centralisation SIEM légère

Collecter les statistiques de flux depuis Ryu et les annotations générées par les scénarios Mininet. Préserver les fichiers bruts. Normaliser ensuite les événements dans un schéma commun et les centraliser dans un stockage léger JSONL ; SQLite pourra être ajouté pour indexer les événements et gérer le cycle de vie des incidents.

## 3. Scénarios expérimentaux

Exécuter plusieurs répétitions de :
1. trafic normal ;
2. reconnaissance réseau lente ou distribuée simulée ;
3. compromission simulée sans exploitation réelle ;
4. mouvement latéral contrôlé ;
5. transfert de données factices vers un récepteur du laboratoire.

Les scénarios sont bornés et les annotations doivent être horodatées. Prévoir une période de trafic normal entre les scénarios afin de réduire les chevauchements.

## 4. Normalisation et corrélation

Vérifier les horodatages, adresses, protocoles, ports et compteurs. Regrouper les événements par hôte et fenêtre temporelle. Associer les annotations aux fenêtres correspondantes. Les événements non annotés restent inconnus (label -1) et ne sont pas transformés automatiquement en trafic normal.

## 5. Construction des graphes

Les hôtes constituent les nœuds et les communications les arêtes dirigées. Calculer des caractéristiques de volume, fréquence, diversité des destinations/ports, durée et variations par rapport à la fenêtre précédente. Chaque fenêtre produit un snapshot NetworkX.

Les GNN classent les nœuds de chaque snapshot. Il s'agit de graphes successifs avec caractéristiques temporelles explicites, pas d'un réseau neuronal récurrent temporel.

## 6. Modèles comparés

- Random Forest comme baseline classique ;
- GCN pour la propagation de voisinage ;
- GAT pour l'agrégation pondérée par attention.

Utiliser le même périmètre d'observations et des partitions comparables. Séparer les données chronologiquement par snapshots lorsque le volume le permet. Éviter toute fuite entre entraînement, calibration et test.

## 7. Détection et gestion des alertes/incidents

Produire un score de menace par hôte. Le moteur de décision applique des niveaux gradués : observation, alerte, ouverture ou mise à jour d'un incident. Les incidents doivent regrouper les alertes liées, conserver leur statut et tracer les actions. Une alerte individuelle ne doit pas être présentée comme un incident confirmé.

## 8. Mitigation SDN

Commencer en mode alerte uniquement. Après calibration et analyse des faux positifs, activer le blocage temporaire uniquement dans le réseau privé du laboratoire. Vérifier l'expiration de la règle et mesurer son impact sur les communications légitimes.

## 9. Évaluation

Comparer les modèles avec précision, rappel, F1, taux de faux positifs, taux de faux négatifs et latence. Pour la mitigation, mesurer délai décision-action, délai de confinement, taux de blocage et impact sur le trafic légitime.

## 10. Reproductibilité et limites

Conserver versions, configuration, graines aléatoires, topologie, commandes de scénarios, annotations et rapports. Les données synthétiques servent uniquement à vérifier le logiciel. Les scénarios de laboratoire ne prouvent pas une détection générale d'APT et les résultats ne sont pas directement généralisables à un réseau de production.
