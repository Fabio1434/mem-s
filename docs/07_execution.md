# 07 — Exécution du laboratoire

La procédure d'installation, de collecte, d'entraînement des modèles, d'inférence et de mitigation optionnelle a été regroupée dans docs/08_execution.md.

La topologie Mininet est dans simulation/topology.py et le contrôleur dans sdn/ryu_app.py. Consultez aussi simulation/README.md et sdn/README.md pour les détails opérationnels.

Le test d'intégration de la topologie doit être exécuté sur une VM Linux où Mininet, Open vSwitch et Ryu sont installés. Les tests unitaires Python ne remplacent pas cette validation de bout en bout.
