# 04 — Dataset et représentation

## Sources des données

Le projet prend en charge deux voies compatibles avec le même schéma :

1. Données expérimentales du laboratoire Mininet/Ryu, collectées à partir des compteurs OpenFlow et annotées par les scénarios.
2. CSV de flux horodatés (par exemple un export de type CICFlowMeter ou UNSW-NB15), convertis vers le schéma normalisé du projet.

Les colonnes attendues dans l'import générique sont l'horodatage, l'adresse IP source et l'adresse IP destination. Les ports, le protocole, les volumes, la durée et une colonne de label sont utilisés lorsqu'ils existent.

## Importer un CSV public

    gnn-sdn-apt import-csv --input /chemin/vers/dataset.csv --output data/raw/public_flows.csv
    gnn-sdn-apt prepare --raw-input data/raw/public_flows.csv --labels data/raw/no_lab_annotations.csv
    gnn-sdn-apt inspect

L'importeur tente de reconnaître les colonnes courantes de CICFlowMeter et UNSW-NB15. Les labels BENIGN/normal deviennent 0, les catégories d'attaque étiquetées deviennent 1 et les valeurs inconnues restent -1. Cette binarisation « normal vs attaque » ne constitue pas un label APT spécifique. Le protocole de recherche doit préciser quel dataset et quelle définition de classe ont été utilisés.

Si le CSV ne contient pas d'horodatage, d'IP source ou d'IP destination, l'importeur s'arrête avec une erreur plutôt que d'inventer une chronologie ou une topologie.

## Transformation du flux vers le graphe

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

Les graphes sont dirigés et découpés par fenêtres temporelles. Les nœuds représentent les hôtes IP, les arêtes représentent les communications, les caractéristiques sont décrites dans docs/10_data_dictionary.md.

## Précautions méthodologiques

Un dataset public générique peut servir à valider l'importeur et à étudier des comportements réseau malveillants, mais il ne doit pas être présenté comme un dataset d'APT si ses annotations ne correspondent pas explicitement à cette classe. Les données de laboratoire doivent rester identifiables séparément des données publiques. La sélection définitive de dataset sera documentée avec sa version, sa licence et la définition des labels.
