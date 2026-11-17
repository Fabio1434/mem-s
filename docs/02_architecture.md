# 02 — Architecture technique du SIEM léger spécialisé

## 1. Périmètre architectural

Le projet est un SIEM léger spécialisé dans la télémétrie réseau d'un laboratoire SDN. Il ne vise pas à collecter les journaux de tous les systèmes, applications et équipements d'une entreprise. Sa portée est volontairement limitée aux événements réseau observables par Open vSwitch/Ryu et aux événements produits par le moteur de détection.

La qualification « SIEM » repose sur les fonctions à mettre en place autour du détecteur : collecte, centralisation, normalisation, corrélation, génération et suivi des incidents, puis réponse contrôlée. Les fonctions déjà présentes et celles restant à développer sont distinguées dans `docs/11_siem_lightweight_design.md`.

## 2. Architecture logique cible

```text
Mininet (hôtes de laboratoire)
        |
Open vSwitch / OpenFlow 1.3
        |
Ryu : collecte des statistiques de flux
        |
Adaptateur de collecte
        |
Normalisation des événements réseau
        |
Stockage central léger (JSONL puis SQLite)
        |
Corrélation par hôte et fenêtre temporelle
        |
Construction de snapshots de graphes (NetworkX)
        |
Random Forest / GCN / GAT
        |
Score de menace + moteur de décision
        |
Gestion des alertes et incidents
        |
Ryu / OpenFlow : blocage temporaire contrôlé
        |
Journal d'audit et tableau de bord léger
```

## 3. Sources et collecte

### Sources incluses dans le périmètre
- statistiques de flux OpenFlow remontées par Ryu ;
- annotations des scénarios Mininet ;
- scores, alertes, décisions et événements de mitigation produits par le prototype.

Les journaux système ou applicatifs ne sont pas requis dans la première version. Ils pourront être ajoutés comme sources complémentaires si le temps et les besoins expérimentaux le permettent.

### Adaptateur de collecte
L'adaptateur reçoit les lignes CSV issues de Ryu et les transforme en événements internes. La collecte doit préserver l'horodatage, l'identité du commutateur, les adresses source/destination, le protocole, les ports, les compteurs et la durée.

## 4. Normalisation et stockage

Le format canonique d'un événement doit contenir au minimum :
- `event_id` : identifiant unique ;
- `timestamp` : horodatage UTC ISO 8601 ;
- `source_component` : composant émetteur (ryu, scenario, detector, mitigation) ;
- `event_type` : flow_observed, scenario_label, detection_alert ou mitigation_action ;
- `src_ip` et `dst_ip`, lorsqu'ils sont disponibles ;
- `protocol`, `src_port`, `dst_port`, lorsqu'ils sont disponibles ;
- `host_id` ou `datapath_id`, lorsqu'ils sont disponibles ;
- `window_id), `label) et `payload` selon le type d'événement.

Les événements sont d'abord stockés en JSONL pour rester simples, inspectables et compatibles avec le pipeline actuel. Une base SQLite pourra ensuite apporter des requêtes, des index, un cycle de vie d'incident et un historique sans imposer une plateforme lourde.

Les événements bruts doivent être conservés séparément des données normalisées et des résultats de détection. Une transformation ne doit jamais écraser la preuve source.

## 5. Corrélation et modèle graphe

La corrélation initiale est bornée au réseau de laboratoire :
- regrouper les événements par hôte source et fenêtre temporelle ;
- relier les communications entre hôtes ;
- associer les annotations de scénarios aux fenêtres concernées ;
- rechercher des séquences compatibles avec reconnaissance, mouvement latéral et transfert de données factices ;
- garder les événements non annotés comme inconnus (label -1), jamais comme normaux par défaut.

Le graphe est dirigé : les nœuds représentent les hôtes et les arêtes représentent les communications observées pendant une fenêtre. Les caractéristiques temporelles décrivent notamment les variations d'activité par rapport à la fenêtre précédente.

GCN et GAT classent les nœuds dans chaque snapshot. Le système actuel n'est pas un GNN récurrent : il s'agit de graphes successifs avec des caractéristiques temporelles explicites.

## 6. Détection et gestion des incidents

Random Forest constitue la baseline. GCN et GAT sont évalués avec le même périmètre de données et un découpage chronologique comparable.

Le moteur de décision transforme un score en action graduée :
1. observation ;
2. alerte ;
3. incident à examiner ;
4. confinement temporaire, uniquement après activation explicite et dans le laboratoire.

Une alerte est un événement de détection. Un incident est un regroupement suivi d'événements liés à un même hôte ou à une même séquence, avec un statut (open, investigating, contained, closed), une gravité, des horodatages et une trace des actions. La gestion persistante de ces incidents est une évolution à réaliser ; elle ne doit pas être considérée comme terminée sur la seule présence de fichiers JSONL.

## 7. Réponse SDN et sécurité

Ryu applique des règles OpenFlow temporaires uniquement dans le sous-réseau expérimental `10.0.0.0/24`. Le blocage est désactivé par défaut et nécessite deux activations indépendantes : `mitigation.enabled: true` et `GNN_SDN_MITIGATION=1`.

Le mode alerte doit être utilisé pendant le développement et la calibration. Toute expérimentation de blocage doit mesurer les faux positifs et l'impact sur le trafic légitime. Aucun contrôleur de production ne doit être utilisé.

## 8. Observabilité et interface

La première version peut exposer un tableau de bord Flask léger avec :
- état du contrôleur et du laboratoire ;
- volume d'événements collectés ;
- dernières alertes et incidents ;
- score de menace par hôte ;
- historique des décisions et actions de mitigation ;
- latence détection-action.

L'interface est une couche de supervision, pas une preuve de performance du détecteur.

## 9. Séparation des modules

- `simulation/` : topologie et scénarios de laboratoire ;
- `sdn/` : contrôleur Ryu et collecte OpenFlow ;
- `src/collector/` : ingestion et normalisation ;
- `src/gnn_sdn_apt/features.py` : caractéristiques ;
- `src/gnn_sdn_apt/graph/` : construction et sérialisation des graphes ;
- `src/gnn_sdn_apt/models/` : baseline, GCN, GAT et entraînement ;
- `src/gnn_sdn_apt/decision.py` : politique de décision ;
- `src/gnn_sdn_apt/live.py` : inférence continue et alertes ;
- `src/mitigation/` ou adaptateur SDN dédié : réponse contrôlée à isoler lors d'une évolution ultérieure ;
- `tests/` : tests unitaires et d'intégration ;
- `docs/` : protocole, limites et reproductibilité.
