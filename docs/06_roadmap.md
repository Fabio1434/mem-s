# 06 — Roadmap du projet

## Phase 1 — Conception scientifique
- [x] Définir la problématique, le sujet et les hypothèses GNN/SDN
- [x] Définir le périmètre d'un SIEM léger spécialisé dans la télémétrie réseau
- [x] Définir l'architecture cible et les limites du prototype
- [x] Définir la méthodologie et les métriques
- [ ] Faire valider le périmètre et les hypothèses par l'encadreur

## Phase 2 — Environnement expérimental
- [x] Définir la topologie Mininet et les scénarios contrôlés
- [x] Préparer le contrôleur Ryu/OpenFlow 1.3 dans le dépôt
- [ ] Installer Mininet et Open vSwitch dans la VM Kali/Linux
- [ ] Vérifier la connectivité Mininet et la connexion au contrôleur Ryu
- [ ] Exécuter les scénarios et vérifier la collecte des statistiques

## Phase 3 — Pipeline SIEM léger
- [x] Collecter les statistiques OpenFlow en CSV
- [x] Produire des annotations de scénarios
- [x] Produire des alertes, décisions et journaux de mitigation en JSONL
- [x] Définir la cible fonctionnelle de normalisation et centralisation dans docs/11
- [x] Implémenter un schéma canonique d'événement avec provenance et identifiant
- [ ] Centraliser les événements normalisés en JSONL append-only
- [x] Ajouter une première règle de corrélation explicable par hôte/fenêtre (fan-out)
- [x] Ajouter SQLite pour l'indexation des événements et la persistance des incidents
- [x] Ajouter des tests unitaires pour normalisation, stockage, corrélation et ingestion CSV Ryu
- [x] Ajouter une ingestion CSV incrémentale avec curseur SQLite, reprise après redémarrage et détection de rotation/troncature
- [ ] Valider l'intégration de bout en bout dans Mininet/OVS/Ryu

## Phase 4 — Modélisation GNN
- [x] Préparer les caractéristiques des hôtes et des flux
- [x] Construire des snapshots NetworkX
- [x] Implémenter Random Forest comme baseline
- [x] Implémenter les modèles GCN et GAT
- [ ] Collecter suffisamment de fenêtres annotées réelles dans le laboratoire
- [ ] Entraîner et calibrer les modèles sur les données du laboratoire
- [ ] Comparer les modèles sur les mêmes partitions chronologiques

## Phase 5 — Détection et incidents
- [x] Inférence périodique et score de menace
- [x] Alertes et décisions JSONL
- [x] Ajouter des identifiants stables d'incident et des niveaux de gravité
- [x] Relier les scores baseline/GCN/GAT au stockage des incidents persistants
- [x] Ajouter une machine à états SQLite pour open / investigating / contained / closed avec journal append-only
- [ ] Ajouter une API authentifiée pour modifier le statut des incidents
- [ ] Évaluer la qualité de détection et les faux positifs

## Phase 6 — Mitigation SDN
- [x] Préparer un blocage IPv4 temporaire dans Ryu
- [x] Garde-fou sur le sous-réseau 10.0.0.0/24 et double activation
- [x] Mitigation désactivée par défaut
- [ ] Valider le chemin complet décision → Ryu → règle OpenFlow dans Mininet
- [ ] Mesurer le délai décision-action et le délai de confinement
- [ ] Mesurer l'impact sur le trafic légitime et les faux blocages

## Phase 7 — Supervision
- [x] Développer un tableau de bord local en lecture seule (stdlib, sans dépendance Flask)
- [x] Afficher les événements et incidents récents, avec score de confiance
- [ ] Afficher l'historique et les latences de mitigation

## Phase 8 — Évaluation scientifique et rédaction
- [x] Définir le protocole d'évaluation et le dictionnaire des données
- [ ] Figer les captures, annotations, versions et configurations expérimentales
- [ ] Produire les métriques Random Forest, GCN et GAT
- [ ] Produire les mesures de mitigation
- [ ] Analyser les limites, menaces à la validité et pistes futures

**Règle de suivi :** une fonctionnalité présente dans le code n'est considérée comme validée qu'après son test dans l'environnement prévu. Les données synthétiques valident le fonctionnement logiciel, pas la performance sur des attaques APT.
