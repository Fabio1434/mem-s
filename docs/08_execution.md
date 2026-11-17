# 08 — Installation et exécution

## 1. Préparer la VM Linux

Le laboratoire nécessite Linux avec Mininet, Open vSwitch et Ryu. Kali peut être utilisé, mais il faut vérifier la version Python disponible avant d'installer les dépendances. Ne pas remplacer le Python système de Kali et ne pas utiliser `sudo pip`.

Vérifier l'environnement :

    cat /etc/os-release
    python3 --version
    uname -r

Installer les paquets système depuis les dépôts de la distribution :

    sudo apt update
    sudo apt install -y git curl wget python3-venv python3-pip python3-dev build-essential iproute2 iputils-ping net-tools openvswitch-switch openvswitch-common mininet

Démarrer et vérifier Open vSwitch :

    sudo systemctl enable --now openvswitch-switch
    sudo systemctl status openvswitch-switch --no-pager
    sudo ovs-vsctl show

Vérifier Mininet :

    mn --version
    sudo mn --switch ovsbr --test pingall

Le résultat attendu est 0 % de paquets perdus entre les hôtes du test. Si le service OVS ou le test Mininet échoue, résoudre cette étape avant de poursuivre.

## 2. Préparer le dépôt et l'environnement Python

    git clone https://github.com/Fabio1434/mem-s.git
    cd mem-s
    python3 -m venv --system-site-packages .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip setuptools wheel
    pip install -e ".[dev]"

L'option `--system-site-packages` permet à l'environnement virtuel d'accéder aux modules Mininet installés par le système lorsque la distribution les expose de cette façon. Si l'import Mininet échoue, vérifier le chemin du module et le Python utilisé avant de modifier les paquets système.

Installer Ryu selon une version Python/dépendances compatible avec la distribution. Éviter de forcer une installation sous Python 3.14 si ses dépendances ne sont pas compatibles ; privilégier un environnement Python pris en charge sans modifier le Python système. Le dépôt n'impose pas une version Ryu universelle.

Exécuter le diagnostic :

    python scripts/check_environment.py

## 3. Installer les dépendances GNN

Après validation du socle Python :

    pip install -e ".[ml]"

Si PyTorch nécessite une roue spécifique à la plateforme ou au matériel, suivre les instructions officielles PyTorch pour installer la bonne version avant PyTorch Geometric.

## 4. Smoke test logiciel sans Mininet

    python scripts/run_demo.py --output-dir data/demo

Pour inclure les tests de fumée GCN et GAT :

    python scripts/run_demo.py --output-dir data/demo --with-gnn --epochs 3

Ces données sont synthétiques. Elles vérifient le fonctionnement du pipeline et ne démontrent pas une performance de détection APT.

## 5. Démarrer le laboratoire SDN

Terminal 1 — contrôleur Ryu :

    ryu-manager --ofp-tcp-listen-port 6653 sdn/ryu_app.py

Terminal 2 — topologie :

    sudo -E .venv/bin/python simulation/topology.py

Dans la CLI Mininet :

    scenarios
    scenario normal
    scenario recon
    scenario lateral
    scenario exfil
    exit

Les scénarios sont confinés au réseau privé de laboratoire 10.0.0.0/24 et n'exécutent aucun exploit. Le scénario exfil transfère uniquement des données factices vers un récepteur du laboratoire.

## 6. Préparer les données

Après la collecte de fenêtres annotées :

    gnn-sdn-apt prepare
    gnn-sdn-apt inspect

Les observations sans annotation restent inconnues (label -1) et ne doivent pas être converties en trafic normal.

## 7. Entraîner et comparer

    gnn-sdn-apt train-baseline --calibrate-threshold
    gnn-sdn-apt train-gnn --model gcn --epochs 100 --calibrate-threshold
    gnn-sdn-apt train-gnn --model gat --epochs 100 --calibrate-threshold
    gnn-sdn-apt compare

Les commandes GCN/GAT requièrent l'extra ML. L'entraînement doit utiliser des partitions chronologiques séparées lorsque le nombre de snapshots le permet. Le seuil doit être calibré sur validation, jamais sur le test final.

## 8. Inférence

    gnn-sdn-apt-live --model baseline --interval 5

Remplacer baseline par gcn ou gat uniquement après avoir entraîné le modèle correspondant. Les alertes et décisions sont écrites dans les chemins définis dans config/config.yaml.

## 9. Mitigation en laboratoire uniquement

La mitigation est désactivée par défaut. Elle requiert les deux conditions suivantes :
- `mitigation.enabled: true` dans config/config.yaml ;
- `GNN_SDN_MITIGATION=1` dans l'environnement du contrôleur Ryu et du service d'inférence.

Démarrer Ryu et le service d'inférence avec cette variable uniquement pendant une expérience autorisée et isolée. Les règles sont temporaires et limitées à 10.0.0.0/24. Ne jamais activer le blocage sur un réseau de production.

## 10. Tests

    python -m compileall -q src simulation sdn scripts
    pytest -q

Les tests unitaires ne remplacent pas l'intégration Mininet/Ryu dans la VM Linux.
