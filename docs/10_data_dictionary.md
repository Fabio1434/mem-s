# 10 — Dictionnaire des données

## Données brutes — flow_stats.csv

- timestamp : horodatage Unix de la réponse OpenFlow ;
- datapath_id : identifiant du commutateur ;
- in_port : port d'entrée dans la règle ;
- eth_src, eth_dst : adresses MAC observées dans le match ;
- ip_src, ip_dst : adresses IPv4 si le match inclut IPv4 ;
- ip_proto : numéro du protocole IP ;
- src_port, dst_port : ports TCP/UDP si présents dans le match ;
- packet_count, byte_count : compteurs cumulatifs de la règle ;
- duration_sec : durée de vie de la règle en secondes.

Les compteurs correspondent à des instantanés OpenFlow. Ils ne doivent pas être interprétés directement comme des paquets/secondes.

## Annotations — scenario_labels.csv

- timestamp_start, timestamp_end : intervalle de l'activité annotée ;
- src_ip : source concernée, vide pour toute source ;
- dst_ip : destination concernée, vide pour toute destination ;
- label : 0 trafic normal, 1 comportement suspect contrôlé ;
- scenario : identifiant lisible du scénario.

La valeur -1 est générée par le pipeline pour une observation qui n'entre dans aucune annotation.

## Features — flow_features.csv

En plus des champs bruts :
- packets_delta, bytes_delta : différences de compteurs entre deux observations consécutives du même match ;
- packet_rate, byte_rate : deltas divisés par l'intervalle d'observation ;
- ip_proto_num, src_port_num, dst_port_num, in_port_num : représentations numériques robustes.

Les compteurs négatifs ou remis à zéro sont traités comme un reset de règle : la valeur courante devient le nouveau delta.

## Graphe — graphs.jsonl

Chaque ligne représente une fenêtre :
- timestamp et window_id ;
- nodes : IP, vecteur de 12 caractéristiques, label et nombre de labels ;
- edges : source, cible, vecteur agrégé de 5 caractéristiques, label et nombre d'observations.

Les caractéristiques des nœuds agrègent les communications entrantes et sortantes : nombre de flux, nombre de sources/destinations/ports distincts, volumes, taux moyens et durée moyenne.

L'ordre des caractéristiques est figé dans src/gnn_sdn_apt/schema.py. Toute modification du schéma doit entraîner une réévaluation des modèles et de la compatibilité des artefacts.
