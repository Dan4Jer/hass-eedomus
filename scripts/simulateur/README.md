# Simulateur eedomus

## Présentation

Ce répertoire fournit un simulateur local de l’API eedomus destiné au développement et aux tests de l’intégration Home Assistant `hass-eedomus`.

Le dépôt peut être livré avec un jeu de données de démonstration directement exploitable :

```text
eedomus_dump.json
thermostat_rules.json
```

Ces deux fichiers constituent le jeu de simulation fourni par défaut.

L’utilisateur peut ensuite :

- utiliser directement ces données avec `simulator.py` ;
- extraire les données de sa propre box eedomus ;
- anonymiser et renommer ses périphériques ;
- générer de nouveaux fichiers avec `02_apply_renom.py` ;
- utiliser tout ou partie de ces fichiers générés pour compléter ou remplacer le jeu de données livré.

> `02_apply_renom.py` ne fusionne pas automatiquement les données avec les fichiers fournis dans le dépôt. Il génère de nouveaux fichiers `new_*` qui peuvent ensuite servir de source pour compléter manuellement `eedomus_dump.json` et `thermostat_rules.json`, ou les remplacer après vérification.

## Fichiers du répertoire

```text
simulateur/
├── 00_extract.py
├── 01_create_renom.py
├── 02_apply_renom.py
├── simulator.py
├── eedomus_dump.json
└── thermostat_rules.json
```

Des fichiers supplémentaires sont créés pendant le processus :

```text
eedomus_dump_box_<adresse>.json
renom.csv
new_<dump>.json
new_<thermostat>.json
```

# 1. Utilisation rapide

## Prérequis

```bash
python3 -m pip install flask requests
```

## Démarrer avec les données fournies

```bash
python3 simulator.py
```

Valeurs par défaut :

```text
Port       : 8080
API user   : apiUser
API secret : apiPassword
```

Le serveur écoute sur :

```text
http://0.0.0.0:8080
```

# 2. Configuration du simulateur

Le port et les identifiants peuvent être définis en ligne de commande :

```bash
python3 simulator.py --port 8081
python3 simulator.py --api-user testuser
python3 simulator.py --api-secret testsecret
```

ou par variables d’environnement :

```bash
export EEDOMUS_PORT=8080
export EEDOMUS_API_USER=apiUser
export EEDOMUS_API_SECRET=apiPassword

python3 simulator.py
```

# 3. Exécuter plusieurs simulateurs en parallèle

Il est possible d'exécuter plusieurs instances de `simulator.py` sur la même machine, à condition d'utiliser un port différent pour chaque instance.

Exemple avec trois simulateurs :

```bash
python3 simulator.py --port 8080
python3 simulator.py --port 8081
python3 simulator.py --port 8082
```

On obtient alors trois API indépendantes :

```text
http://<hôte>:8080
http://<hôte>:8081
http://<hôte>:8082
```

Les ports peuvent également être définis avec la variable d'environnement `EEDOMUS_PORT`.

Exemple :

```bash
EEDOMUS_PORT=8080 python3 simulator.py
EEDOMUS_PORT=8081 python3 simulator.py
EEDOMUS_PORT=8082 python3 simulator.py
```

Cela permet notamment de simuler plusieurs box eedomus et de tester plusieurs configurations de l'intégration `hass-eedomus` en parallèle.

### Jeu de données par instance

Dans l'implémentation actuelle, chaque instance de `simulator.py` charge les fichiers :

```text
eedomus_dump.json
thermostat_rules.json
```

situés dans le même répertoire que le script.

Pour faire fonctionner plusieurs simulateurs avec **des jeux de données différents**, utiliser un répertoire distinct par instance, contenant chacun son propre `simulator.py`, `eedomus_dump.json` et éventuellement `thermostat_rules.json`.

Exemple :

```text
simulateur_box_1/
├── simulator.py
├── eedomus_dump.json
└── thermostat_rules.json

simulateur_box_2/
├── simulator.py
├── eedomus_dump.json
└── thermostat_rules.json
```

Puis :

```bash
cd simulateur_box_1
python3 simulator.py --port 8080

cd ../simulateur_box_2
python3 simulator.py --port 8081
```

# 5. Données chargées

`simulator.py` charge :

```text
eedomus_dump.json
```

qui contient :

```json
{
  "periph_list": [],
  "value_list": [],
  "caract": []
}
```

Le fichier :

```text
thermostat_rules.json
```

est chargé s’il est présent.

# 5. API simulée

Le serveur expose :

```text
GET  /api/get
GET  /api/set
POST /simulate/change
```

Les actions prises en charge sont :

```text
auth.test
periph.list
periph.value_list
periph.caract
periph.value
```

Exemple :

```bash
curl "http://127.0.0.1:8080/api/get?action=auth.test&api_user=apiUser&api_secret=apiPassword"
```

Pour modifier un périphérique :

```bash
curl "http://127.0.0.1:8080/api/set?action=periph.value&periph_id=thermostat&value=20&api_user=apiUser&api_secret=apiPassword"
```

Les changements restent uniquement en mémoire.

# 6. Simuler une variation externe

```bash
curl -X POST   -H "Content-Type: application/json"   -d '{"periph_id":"thermostat_temp","value":"18.5"}'   http://127.0.0.1:8080/simulate/change
```

Cette route ne demande actuellement pas l’authentification API eedomus.

# 7. Simulation des thermostats

Une règle contient :

```text
setpoint_id
sensor_id
switch_id
on_value
off_value
```

Principe :

```text
si consigne > température mesurée
    commande = on_value
sinon
    commande = off_value
```

Il n’y a actuellement ni hystérésis ni temporisation.

# 8. Construire un jeu depuis une vraie box

Le flux recommandé est :

```text
Box eedomus
    |
    v
00_extract.py
    |
    v
eedomus_dump_box_<adresse>.json
    |
    v
01_create_renom.py
    |
    v
renom.csv
    |
    v
édition / anonymisation
    |
    v
02_apply_renom.py
    |
    +--> new_<dump>.json
    |
    +--> new_<thermostat>.json
```

# 9. `00_extract.py`

Les paramètres peuvent être fournis en ligne de commande :

```bash
python3 00_extract.py   --ip 192.168.1.10   --api-user mon_user   --api-secret mon_secret
```

ou via :

```bash
export EEDOMUS_HOST=192.168.1.10
export EEDOMUS_API_USER=mon_user
export EEDOMUS_API_SECRET=mon_secret
```

Le script récupère :

```text
periph.list
periph.value_list
periph.caract
```

et génère :

```text
eedomus_dump_box_<adresse>.json
```

# 10. `01_create_renom.py`

Exemple :

```bash
python3 01_create_renom.py   --json eedomus_dump_box_192_168_1_10.json   --csv renom.csv
```

Le CSV contient :

```text
periph_id
name
parent_periph_id
usage_id
new_periph_id
new_name
```

Pour supprimer un périphérique :

```text
new_periph_id = non
new_name      = vide
```

# 11. `02_apply_renom.py`

Exemple :

```bash
python3 02_apply_renom.py   --dump-file eedomus_dump_box_192_168_1_10.json   --csv renom.csv   --thermostat thermostat_rules.json
```

Par défaut, les fichiers produits reçoivent le préfixe :

```text
new_
```

Exemple :

```text
eedomus_dump_box_192_168_1_10.json
    -> new_eedomus_dump_box_192_168_1_10.json

thermostat_rules.json
    -> new_thermostat_rules.json
```

Les noms de sortie peuvent aussi être imposés avec :

```text
--news-dump-file
--new-thermostat
```

Le script valide notamment :

- les IDs ;
- les doublons ;
- la présence de tous les périphériques dans le CSV ;
- les relations parent/enfant ;
- les suppressions ;
- l’unicité des nouveaux IDs ;
- les références thermostat.

# 12. Compléter les fichiers livrés après `02_apply_renom.py`

Le jeu de référence livré est :

```text
eedomus_dump.json
thermostat_rules.json
```

Les fichiers `new_*` générés par `02_apply_renom.py` peuvent ensuite servir à le compléter.

## Remplacement complet

Après contrôle :

```bash
cp new_eedomus_dump_box_192_168_1_10.json eedomus_dump.json
cp new_thermostat_rules.json thermostat_rules.json
```

## Complément du jeu existant

Pour enrichir le jeu livré, reprendre les périphériques utiles du fichier :

```text
new_<dump>.json
```

et les ajouter dans les sections correspondantes de :

```text
eedomus_dump.json
```

Les sections à maintenir cohérentes sont :

```text
periph_list
value_list
caract
```

Les règles utiles de :

```text
new_thermostat_rules.json
```

peuvent de la même manière être ajoutées à :

```text
thermostat_rules.json
```

### Important

`02_apply_renom.py` ne fait pas cette fusion automatiquement.

Après un ajout manuel, vérifier :

- l’unicité des `periph_id` ;
- la cohérence des `parent_periph_id` ;
- la présence des périphériques dans les sections nécessaires ;
- les références `setpoint_id`, `sensor_id` et `switch_id`.

# 13. Sécurité et anonymisation

Les données provenant de :

```text
periph.caract?show_config=1
```

peuvent contenir des informations sensibles qui ne sont pas supprimées automatiquement par le renommage.

Avant publication, vérifier notamment :

```text
coordonnées GPS
latitude / longitude
URL
tokens OAuth
VAR1 / VAR2 / VAR3
identifiants externes
numéros de téléphone
adresses réseau
noms de personnes
noms de pièces pouvant révéler des informations personnelles
```

Le renommage avec `renom.csv` agit surtout sur :

```text
periph_id
name
parent_periph_id
```

Il ne constitue donc pas, à lui seul, une anonymisation complète.

# 14. Persistance

Les changements faits par :

```text
/api/set
/simulate/change
```

restent en mémoire et ne modifient pas `eedomus_dump.json`.

Après redémarrage du simulateur, les valeurs initiales du fichier sont restaurées.

# 15. Workflow recommandé pour ajouter des périphériques au jeu fourni

```bash
# 1. Extraction
python3 00_extract.py   --ip 192.168.1.10   --api-user mon_user   --api-secret mon_secret

# 2. Création du CSV
python3 01_create_renom.py   --json eedomus_dump_box_192_168_1_10.json   --csv renom.csv

# 3. Editer renom.csv

# 5. Génération des fichiers remappés
python3 02_apply_renom.py   --dump-file eedomus_dump_box_192_168_1_10.json   --csv renom.csv   --thermostat thermostat_rules.json

# 6. Vérifier les informations sensibles restantes

# 7. Compléter eedomus_dump.json
# 8. Compléter thermostat_rules.json si nécessaire

# 9. Tester
python3 simulator.py
```

# 16. Limites

Le simulateur n’émule pas l’ensemble d’une box eedomus.

Il reproduit uniquement les fonctions nécessaires aux tests actuels de `hass-eedomus`.

Le principe à retenir est :

```text
eedomus_dump.json
thermostat_rules.json
```

sont les fichiers de référence livrés avec le simulateur, tandis que les fichiers `new_*` produits par `02_apply_renom.py` servent à préparer, valider et compléter ce jeu de référence.

