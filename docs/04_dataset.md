# 04 — Dataset et représentation

## Stratégie

Le choix définitif sera effectué après inspection des variables disponibles et des exigences du modèle.

### Candidats publics

- CIC-IDS2017
- CSE-CIC-IDS2018
- UNSW-NB15
- TON_IoT

### Dataset expérimental

Génération contrôlée dans Mininet avec collecte des statistiques OpenFlow.

### Approche hybride

Utiliser les données publiques pour développer et comparer les modèles, puis valider le pipeline dans le laboratoire SDN.

## Transformation

~~~text
Flow record
   ↓
source / destination
   ↓
node mapping
   ↓
edge features
   ↓
node aggregation
   ↓
graph snapshot
~~~

Le format final sera documenté avant l'entraînement afin d'assurer la reproductibilité.
