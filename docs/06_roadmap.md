# 06 — Roadmap du projet

## Phase 1 — Conception
- [x] Initialiser le dépôt
- [x] Définir la problématique, les objectifs et les hypothèses
- [x] Définir l'architecture et le périmètre
- [x] Définir la méthodologie et les métriques
- [ ] Valider les choix avec l'encadrement

## Phase 2 — Laboratoire SDN
- [x] Définir la topologie Mininet à cinq hôtes
- [x] Préparer OpenFlow 1.3 et le contrôleur Ryu
- [x] Apprentissage de forwarding et collecte des statistiques
- [x] Préparer des scénarios normaux/suspects bornés et annotés
- [ ] Installer les dépendances et valider le laboratoire en VM Linux

## Phase 3 — Pipeline de données
- [x] Définir les schémas des flux, annotations et graphes
- [x] Calculer deltas de compteurs et débits
- [x] Construire des snapshots de graphes temporels NetworkX
- [x] Sérialiser les graphes en JSONL
- [x] Ajouter des tests unitaires
- [ ] Valider le volume et la qualité des données réelles du laboratoire

## Phase 4 — Modèles IA
- [x] Random Forest comme baseline
- [x] Architecture GCN
- [x] Architecture GAT
- [x] Entraînement avec séparation chronologique par snapshots pour GNN
- [x] Rapports de métriques reproductibles
- [ ] Collecter un dataset annoté suffisant et produire les résultats expérimentaux

## Phase 5 — Détection intégrée
- [x] Inférence périodique sur le snapshot le plus récent
- [x] Score de menace et seuil configurable
- [x] Journaux d'alertes et de décisions
- [x] Cooldown des alertes par hôte
- [ ] Calibrer le seuil avec un jeu de validation dédié

## Phase 6 — Mitigation SDN
- [x] Liaison des décisions au contrôleur Ryu
- [x] Blocage IPv4 temporaire en laboratoire, explicitement désactivé par défaut
- [x] Garde-fou sur le sous-réseau 10.0.0.0/24 et expiration après 60 s
- [ ] Mesurer le délai de décision-action et l'impact sur le trafic légitime
- [ ] Évaluer les faux positifs avant toute activation contrôlée

## Phase 7 — Validation scientifique
- [x] Protocole d'évaluation documenté
- [x] Dictionnaire des données et limitations documentés
- [x] Workflow GitHub Actions pour les tests unitaires
- [ ] Exécuter les tests unitaires sur l'état complet du dépôt
- [ ] Valider l'intégration Mininet/Ryu sur VM Linux
- [ ] Comparer les modèles sur les mêmes données et partitions
- [ ] Analyser les limites et documenter la reproductibilité

**Important :** un module marqué comme implémenté n'est pas considéré comme expérimentalement validé tant que son test et ses mesures ne sont pas réalisés.
