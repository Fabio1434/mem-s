# 07 — Exécution du laboratoire SDN

## Pré-requis

Le laboratoire est prévu pour une machine Linux ou une VM Linux disposant de :

- Python 3
- Mininet
- Open vSwitch
- Ryu
- accès administrateur pour lancer Mininet

Les dépendances d'environnement SDN ne sont volontairement pas mélangées aux dépendances Python du futur pipeline GNN.

## Démarrage

Depuis la racine du dépôt, terminal 1 :

```bash
ryu-manager --ofp-tcp-listen-port 6653 sdn/ryu_app.py
```

Terminal 2 :

```sudo python3 simulation/topology.py```

La topologie attend le contrôleur sur `127.0.0.1:6653`.

## Validation minimale

Dans la CLI Mininet :

```text
nodes
net
pingall
h1 ping -c 3 h2
h2 ping -c 3 h3
```

Puis quitter Mininet avec :

```text
exit
```

Le contrôleur doit avoir créé :

`data/raw/flow_stats.csv`

Le fichier peut ensuite être inspecté avec :

```bash
head data/raw/flow_stats.csv
```

## Ce qui doit être observé

1. Le switch `s1` se connecte à Ryu.
2. Une règle table-miss est installée.
3. Les premières trames déclenchent l'apprentissage L2.
4. Les flux établis sont installés comme règles OpenFlow.
5. Le collecteur demande périodiquement les statistiques.
6. Les compteurs sont ajoutés au CSV.

## Limitation volontaire

Aucune action de blocage, quarantaine ou modification automatique de politique de sécurité n'est active.

Cette étape sert à obtenir une base de données réseau fiable avant la construction des features et des graphes temporels.
