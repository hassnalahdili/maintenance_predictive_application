# Application de maintenance prédictive industrielle basée sur l'IA

Application développée dans le cadre d'un **Projet de Fin d'Études (PFE)** autour de la maintenance prédictive industrielle.

Le projet propose une plateforme combinant **règles métier, Machine Learning et suivi opérationnel** afin d'exploiter des données de capteurs, détecter des situations à risque et générer des alertes de maintenance.

> **Statut du projet :** prototype fonctionnel développé pour un contexte PFE.
> Les premières expérimentations ML utilisent notamment des données synthétiques et des jeux de données publics. Les performances obtenues avec les données synthétiques ne constituent donc pas une validation industrielle sur des machines réelles.

---

## Fonctionnalités principales

L'application intègre :

* Backend **FastAPI**
* Frontend **React + Material UI**
* Base de données **PostgreSQL**
* Authentification **JWT**
* Gestion des machines et des actifs industriels
* Gestion des règles métier
* Ingestion des données capteurs
* Détection de situations à risque
* Génération et historisation des alertes
* Prédiction de la probabilité de défaillance
* Dashboard avec indicateurs de suivi
* WebSocket pour les mises à jour en temps réel
* Gestion des interventions terrain
* Jobs d'ingestion continue simulés ou rejoués
* Pipeline ML avec entraînement local et inférence via API
* Catalogue de datasets et benchmarks ML
* Diagnostics et calibration du modèle
* Suivi du drift
* Retraining à partir des retours terrain
* Migrations de base de données avec Alembic
* Configurations `development` et `production`
* Déploiement HTTPS en production

---

## Architecture

Le pipeline général de l'application est organisé comme suit :

```text
Données capteurs
       ↓
PostgreSQL
       ↓
Règles métier
       ↓
Features enrichies
       ↓
Modèle Machine Learning
       ↓
Probabilité de défaillance
       ↓
Alertes
       ↓
Dashboard / Interventions
       ↓
Labels terrain
       ↓
Suivi ML / Drift / Retraining
```

### Fonctionnement

1. Les utilisateurs se connectent via une authentification JWT.
2. Les machines et les actifs industriels sont gérés depuis l'interface.
3. Les données provenant des capteurs sont enregistrées dans PostgreSQL.
4. Les règles métier sont évaluées en premier afin d'identifier les situations à risque.
5. Les résultats des règles sont transformés en variables utilisables par le modèle ML.
6. Le modèle prédit une probabilité de défaillance.
7. Les alertes sont générées et historisées.
8. Le dashboard présente les principaux indicateurs.
9. Le WebSocket permet de transmettre les nouveaux événements au frontend en temps réel.
10. Les interventions terrain peuvent fournir des labels utilisés dans la boucle d'amélioration du modèle.

---

## Architecture technique

| Composant                | Technologie             |
| ------------------------ | ----------------------- |
| Backend                  | FastAPI / Python        |
| Frontend                 | React / Material UI     |
| Base de données          | PostgreSQL              |
| Machine Learning         | Scikit-learn            |
| Authentification         | JWT                     |
| Migrations               | Alembic                 |
| Conteneurisation         | Docker / Docker Compose |
| Communication temps réel | WebSocket               |
| Gestion des données      | Pandas / NumPy          |

---

## Documentation

La documentation complémentaire se trouve dans le dossier `docs/`.

* `docs/guide_interface_pages.md`
* `docs/fonctionnalites_ajoutees.md`

---

## Installation avec Docker

Depuis la racine du projet :

```bash
docker compose up --build
```

Services disponibles en développement :

* Frontend : `http://localhost:5173`
* Backend : `http://localhost:8000`
* Documentation API : `http://localhost:8000/docs`
* PostgreSQL : `localhost:5432`

---

## Base de données et migrations

Les migrations sont gérées avec **Alembic** dans :

```text
backend/alembic/
```

Pour appliquer les migrations :

```bash
cd backend
alembic upgrade head
```

Pour rattacher une base existante à l'état courant d'Alembic sans rejouer les migrations :

```bash
alembic stamp head
```

En développement, `AUTO_CREATE_SCHEMA=true` peut être utilisé pour faciliter le démarrage local.

En production :

```text
AUTO_CREATE_SCHEMA=false
AUTO_SEED_DATA=false
```

---

## Entraînement du modèle

Le modèle peut être entraîné localement depuis le dossier `backend` :

```bash
cd backend
python -m app.ml.train_model
```

Le script génère actuellement un **jeu de données synthétique** afin de tester le pipeline de maintenance prédictive.

Le processus comprend :

1. génération des mesures capteurs ;
2. application des règles métier ;
3. création des variables dérivées ;
4. génération de la variable cible synthétique ;
5. séparation entraînement/test ;
6. entraînement du Random Forest ;
7. calibration des probabilités ;
8. calcul des diagnostics ;
9. sauvegarde du modèle et du scaler.

### Important concernant les données

Les données synthétiques servent principalement à valider le fonctionnement technique du pipeline.

La variable `failure` est elle-même générée à partir d'un score de risque défini dans le projet. Les performances obtenues sur ces données ne doivent donc pas être interprétées comme une mesure de performance sur des défaillances industrielles réelles.

Le projet prévoit également l'utilisation de **jeux de données publics** pour les expérimentations et benchmarks.

Les artefacts principaux générés par l'entraînement sont :

```text
backend/app/ml/artifacts/maintenance_model.joblib
backend/app/ml/artifacts/maintenance_scaler.joblib
```

---

## Logique métier et Machine Learning

Le projet utilise une approche en deux niveaux.

### 1. Règles métier

Les règles permettent d'identifier rapidement des situations potentiellement anormales à partir des mesures des capteurs.

Elles produisent notamment :

* nombre de règles déclenchées ;
* score de sévérité ;
* niveau de confiance maximal ;
* dépassement des seuils ;
* marges par rapport aux seuils de référence.

### 2. Modèle Machine Learning

Les résultats des règles sont ensuite transformés en variables d'entrée du modèle.

Parmi les features utilisées :

```text
temperature
pressure
rpm
current
total_vibration
rule_count
max_rule_confidence
severity_score
temperature_margin_85
pressure_margin_7
rpm_drop_margin
```

Le modèle exploite ainsi à la fois les **mesures capteurs** et les **informations issues des règles métier**.

---

## Datasets et benchmarks

Les données utilisées dans les expérimentations sont organisées dans :

```text
data/raw/
```

avec un dossier par source lorsque cela est nécessaire.

Les datasets volumineux et les données externes ne sont pas destinés à être versionnés directement dans le dépôt Git.

Le projet peut construire un catalogue et des rapports de benchmark dans :

```text
data/reports/dataset_catalog.json
data/reports/ml_overview.json
```

Les jeux de données étudiés comprennent notamment :

* `CWRU Bearing Features`
* `Hydraulic Systems`
* `Vibration Feature Dataset`
* `IMS Bearing RUL`
* `Electric Arc Furnace`

D'autres sources telles que `MetroPT-3`, `Pump time series` et les données audio `fan` sont prévues pour le rejeu de séries temporelles ou les prochaines itérations du projet.

---

## Benchmarks ML

Le projet permet de comparer plusieurs approches selon les caractéristiques des datasets disponibles, notamment pour :

* classification ;
* détection d'anomalies ;
* régression ;
* estimation de durée de vie restante lorsque les données le permettent.

Pour regénérer les rapports ML, utiliser le script de benchmark présent dans :

```text
qa/run_ml_benchmarks.py
```

Les résultats peuvent ensuite être exploités depuis l'interface ML.

---

## Interface ML

La page `ML` permet notamment de consulter :

* le catalogue des datasets ;
* les résultats des benchmarks ;
* les diagnostics du modèle utilisé ;
* la calibration des probabilités ;
* les importances des variables ;
* les métriques liées aux alertes et interventions ;
* l'explication locale d'une prédiction ;
* le rejeu de séries temporelles disponibles ;
* les informations nécessaires aux prochaines itérations du PFE.

---

## Operations et boucle MLOps

La page `Operations` regroupe les fonctionnalités opérationnelles :

* hiérarchie des actifs :

```text
Site
  ↓
Zone
  ↓
Ligne
  ↓
Composant
```

* interventions terrain ;
* labels métier ;
* jobs d'ingestion ;
* suivi du drift ;
* retraining à partir des retours terrain.

Cette organisation permet de préparer une boucle d'amélioration progressive du modèle à partir des observations et interventions réalisées sur le terrain.

---

## API principale

### Authentification

```text
POST /api/auth/register
POST /api/auth/login
```

### Machines et règles

```text
GET/POST /api/machines/
GET/POST /api/rules/
```

### Données capteurs et alertes

```text
POST /api/sensors/ingest
GET /api/alerts/
POST /api/alerts/{id}/acknowledge
```

### Prédictions

```text
GET /api/predictions/
POST /api/predictions/simulate/{machine_id}
```

### Dashboard

```text
GET /api/dashboard/summary
```

### Actifs et interventions

```text
GET /api/assets/tree
GET/POST /api/interventions/
```

### Ingestion

```text
GET/POST /api/ingestion-jobs/
POST /api/ingestion-jobs/{id}/start
POST /api/ingestion-jobs/{id}/stop
```

### Machine Learning

```text
GET /api/ml/overview
GET /api/ml/replay/sources
POST /api/ml/replay/step
POST /api/ml/replay/reset/{source_id}

GET /api/ml/feedback-summary
GET /api/ml/drift-report
GET /api/ml/business-metrics
GET /api/ml/model-diagnostics

GET /api/ml/explain/machines/{machine_id}
POST /api/ml/retrain-from-feedback
```

### Temps réel

```text
WS /ws/live?token=...
```

---

## Sécurité et gestion des environnements

Le projet fournit des fichiers d'exemple pour les différents environnements :

```text
backend/.env.example
backend/.env.production.example
.env.production.example
frontend/.env.production.example
```

Les secrets réels doivent être stockés dans les fichiers d'environnement locaux et **ne doivent pas être versionnés dans Git**.

Pour générer un secret :

```bash
cd backend
python scripts/generate_secret.py
```

En production, plusieurs contrôles empêchent un démarrage avec une configuration dangereuse, notamment lorsque :

```text
SECRET_KEY
ENFORCE_HTTPS
AUTO_CREATE_SCHEMA
AUTO_SEED_DATA
```

ne respectent pas les paramètres attendus pour un environnement de production.

---

## Déploiement HTTPS

Un environnement de production séparé est disponible avec :

```text
docker-compose.prod.yml
```

Il utilise notamment :

```text
backend/Dockerfile.prod
backend/start-prod.sh
frontend/Dockerfile.prod
frontend/nginx.prod.conf
```

### Configuration

Créer le fichier :

```text
.env.production
```

à partir de :

```text
.env.production.example
```

Les certificats TLS doivent être placés dans :

```text
infra/certs/
```

Puis lancer :

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up --build -d
```

Le frontend est servi en HTTPS et les routes `/api` et `/ws` sont proxyfiées vers le backend.

---

## Structure principale du projet

```text
.
├── backend/
│   ├── app/
│   │   ├── ml/
│   │   └── ...
│   ├── alembic/
│   └── ...
├── frontend/
├── data/
│   ├── raw/
│   └── reports/
├── docs/
├── qa/
├── infra/
├── docker-compose.yml
└── docker-compose.prod.yml
```

---

## Limites actuelles et perspectives

Le projet constitue un **prototype fonctionnel de PFE** et peut encore évoluer vers un environnement industriel plus complet.

Les principales pistes d'amélioration sont :

* intégration de données industrielles réelles et labellisées ;
* validation du modèle sur des données indépendantes ;
* comparaison avec des modèles supplémentaires comme XGBoost ;
* modèles dédiés à l'estimation du RUL ;
* traitement asynchrone avec Celery/Redis ;
* supervision avancée des jobs d'ingestion ;
* enrichissement des visualisations ;
* export des données et rapports en PDF/CSV.

---

## Tests et recette

Le projet contient un plan de recette et un runner automatique dans :

```text
qa/plan_recette.md
qa/run_recette.py
```

Exemple :

```bash
python qa/run_recette.py --start-db --output qa/reports/recette_report.json
```

---

## Objectif du projet

L'objectif est de construire une plateforme permettant d'expérimenter une approche complète de **maintenance prédictive basée sur l'IA**, depuis l'acquisition des données jusqu'à la prédiction, la génération d'alertes et l'exploitation des retours terrain.

Le projet met ainsi en pratique plusieurs domaines :

* Data Science ;
* Machine Learning ;
* traitement des données ;
* développement d'API ;
* bases de données ;
* visualisation ;
* déploiement avec Docker ;
* sécurité applicative ;
* premiers principes de MLOps.
