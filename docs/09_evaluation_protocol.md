# 09 — Protocole d'évaluation

## Question expérimentale

La représentation relationnelle des communications réseau sous forme de graphes apporte-t-elle une amélioration mesurable par rapport à une baseline classique, et l'intégration SDN permet-elle une réponse de confinement mesurable dans le laboratoire ?

## Hypothèses à tester

- H1 : GCN ou GAT apporte une amélioration de F1 et/ou une réduction des faux positifs par rapport à Random Forest.
- H2 : le contrôleur SDN applique une décision de confinement dans un délai mesurable.
- H3 : la corrélation des événements par hôte et fenêtre permet de contextualiser des séquences de scénarios.

Ces hypothèses ne sont pas considérées comme vraies avant l'expérimentation.

## Protocole de collecte

1. Réinitialiser le laboratoire et vérifier les horloges.
2. Exécuter plusieurs répétitions de trafic normal.
3. Exécuter séparément recon, lateral et exfil, avec des périodes normales entre les scénarios.
4. Conserver les statistiques brutes OpenFlow et les annotations des scénarios.
5. Vérifier les labels, les fenêtres et les événements inconnus.
6. Enregistrer les versions du code, des dépendances, la configuration et la topologie.
7. Geler un jeu de données avant entraînement et évaluation.

## Protocole de comparaison

- Random Forest est la baseline.
- GCN et GAT utilisent le même périmètre de données et le même schéma de caractéristiques.
- Utiliser une séparation chronologique par snapshots lorsque le volume le permet.
- Réserver les données de test final jusqu'à la fin du choix des modèles et des seuils.
- Calibrer le seuil sur une partition de validation indépendante ; ne jamais sélectionner le seuil en fonction des résultats du test.
- Répéter les entraînements avec des graines documentées lorsque cela est pertinent.

## Métriques de détection

- précision, rappel, F1-score ;
- taux de faux positifs (FPR) et taux de faux négatifs (FNR) ;
- matrice de confusion ;
- latence d'inférence ;
- délai entre le début du comportement annoté et la première alerte.

## Métriques SIEM et corrélation

- nombre d'événements reçus, normalisés et rejetés ;
- taux d'événements avec horodatage et provenance valides ;
- délai d'ingestion ;
- nombre d'alertes corrélées en incidents ;
- délai de création et de mise à jour d'un incident.

## Métriques de mitigation

- délai entre création de décision et application de règle ;
- délai de confinement observé ;
- proportion de flux suspects bloqués ;
- impact sur les communications légitimes ;
- nombre de faux blocages ;
- durée réelle des règles temporaires.

## Reproductibilité

Conserver la version du dépôt, la configuration, la version Python et les bibliothèques, les commandes de scénario, la graine aléatoire, les annotations et les rapports. Garder les données brutes séparées des données transformées.

Les labels 0/1 ne sont appliqués qu'aux événements annotés. Les observations non annotées restent à -1 et ne sont pas traitées comme normales par défaut. Les scénarios du laboratoire sont des approximations expérimentales de comportements réseau ; ils ne constituent pas une vérité terrain exhaustive d'une campagne APT réelle.

## Limites à discuter

- topologie virtualisée de petite taille ;
- nombre limité de scénarios et de répétitions ;
- visibilité basée sur les statistiques de flux OpenFlow, pas sur une inspection exhaustive des paquets ;
- déséquilibre potentiel des classes ;
- dépendance des résultats aux annotations et aux fenêtres temporelles ;
- absence de garantie de généralisation aux réseaux de production.
