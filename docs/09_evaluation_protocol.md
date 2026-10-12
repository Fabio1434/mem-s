# 09 — Protocole d'évaluation

## Question expérimentale

La représentation relationnelle d'un réseau sous forme de graphes temporels améliore-t-elle la détection de comportements suspects par rapport à un modèle classique utilisant les caractéristiques agrégées des hôtes ?

## Hypothèses à mesurer

- H1 : le GCN/GAT atteint un F1 supérieur ou un taux de faux positifs inférieur au modèle Random Forest, sur un protocole de séparation comparable.
- H2 : une décision issue de l'inférence peut être transmise au contrôleur et appliquée dans la topologie de recherche dans un délai mesurable.

Ces hypothèses doivent être confirmées par les résultats ; aucune supériorité d'un GNN n'est présupposée.

## Protocole

1. Réinitialiser le laboratoire et vérifier l'heure système.
2. Capturer plusieurs répétitions de trafic normal.
3. Capturer les scénarios recon, lateral et exfil, chacun avec annotation.
4. Vérifier l'équilibre des labels, les fenêtres temporelles et les observations non annotées.
5. Construire le dataset et figer une version des données utilisée pour l'expérience.
6. Entraîner Random Forest comme baseline.
7. Entraîner GCN puis GAT avec un découpage chronologique par snapshots.
8. Choisir le seuil sur un jeu de validation séparé ; ne pas choisir le seuil en regardant le test final.
9. Comparer les métriques sur le même périmètre d'évaluation.
10. Répéter les scénarios et enregistrer les délais de détection et de réponse SDN.

## Métriques

Détection :
- précision, rappel et F1 ;
- taux de faux positifs (FPR) et taux de faux négatifs (FNR) ;
- matrice de confusion ;
- latence d'inférence et délai entre l'activité suspecte et l'alerte.

Mitigation :
- délai décision-action et délai de confinement ;
- proportion de flux suspects bloqués ;
- impact sur les communications légitimes ;
- faux blocages et durée effective des règles.

## Reproductibilité

Enregistrer la version du code, la configuration, la version de Python et des bibliothèques, la topologie, les commandes des scénarios, la graine aléatoire et les rapports. Conserver les labels séparés des caractéristiques pour éviter une fuite de données.

Le label de nœud est attribué au nœud source d'une communication annotée. Les observations sans vérité terrain restent en label -1 et ne sont pas incluses dans l'entraînement supervisé. Les annotations de scénario sont des étiquettes expérimentales et ne représentent pas une vérité terrain exhaustive sur un réseau réel.

## Limites à discuter dans le mémoire

- topologie très petite et synthétique ;
- signatures de scénarios limitées et dépendantes de l'annotation ;
- fenêtres de statistiques OpenFlow, et non capture paquet complète ;
- classes potentiellement déséquilibrées ;
- résultats de labo non généralisables directement à des réseaux de production ;
- coût mémoire, latence et robustesse des modèles à mesurer avant toute affirmation de déploiement.
