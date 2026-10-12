# 03 — Méthodologie expérimentale

## Étape 1 — Laboratoire

Créer une topologie Mininet contrôlée avec plusieurs hôtes, commutateurs virtuels et services simples.

## Étape 2 — Trafic normal

Générer des communications légitimes et enregistrer les statistiques de flux.

## Étape 3 — Scénarios suspects

Introduire progressivement des comportements contrôlés représentant :

1. reconnaissance distribuée ou lente ;
2. compromission simulée ;
3. mouvement latéral ;
4. accès à une ressource sensible ;
5. exfiltration simulée.

## Étape 4 — Dataset

Évaluer les données produites par Mininet et, si pertinent, un dataset public adapté au format graphe.

## Étape 5 — Baselines

Établir au moins une baseline classique avant le GNN.

## Étape 6 — GNN

Commencer avec GCN, puis évaluer GAT.

## Étape 7 — Détection

Produire un score ou une classe de menace au niveau défini par l'analyse des données.

## Étape 8 — Réponse

Associer les niveaux de confiance à des politiques contrôlées : observation, alerte, blocage, quarantaine.

## Étape 9 — Évaluation

Comparer les modèles et mesurer séparément la qualité de détection et la rapidité/efficacité de la mitigation.
