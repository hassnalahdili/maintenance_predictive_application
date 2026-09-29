# Application complète de maintenance prédictive industrielle

Cette application respecte l'esprit du cahier des charges :
- Backend FastAPI
- Frontend React + Material UI
- PostgreSQL
- Authentification JWT
- Gestion des machines, règles métier, alertes et dashboard
- Type de machine supplémentaire `four`
- Règles métier utilisées d'abord pour produire des signaux de risque
- Résultats des règles transformés en features pour le modèle IA
- Pipeline ML avec entraînement local et inférence en API
- Espace ML pour catalogue datasets et benchmarks multi-modèles
- Migrations de base de données avec Alembic
- Configuration `development` / `production`
- Backend proxy-aware avec HTTPS en production
- Dashboard live par WebSocket
- Jobs d'ingestion continue simulés ou rejoués
- Hiérarchie industrielle des actifs et interventions terrain
- Boucle MLOps avec labels terrain, drift et retraining

## Architecture

1. Les utilisateurs se connectent via JWT.
2. Les machines sont gérées depuis l'interface.
3. Les données capteurs sont ingérées dans PostgreSQL.
4. Les règles métier sont évaluées en premier.
5. Les résultats des règles sont transformés en features enrichies.
6. Le modèle IA prédit la probabilité de panne à partir de ces features.
7. Les alertes sont générées et historisées.
8. Le dashboard affiche les KPIs principaux.
9. Le flux live notifie le frontend dès qu'une nouvelle mesure ou intervention arrive.
10. Les interventions terrain servent de labels pour la boucle ML.

## Documentation interface

Un guide complet, page par page, est disponible ici :

- [docs/guide_interface_pages.md](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/docs/guide_interface_pages.md)
- [docs/fonctionnalites_ajoutees.md](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/docs/fonctionnalites_ajoutees.md)

## Lancer le projet avec Docker

```bash
cd predictive_maintenance_app
docker compose up --build
```

- Frontend : http://localhost:5173
- Backend : http://localhost:8000/docs
- PostgreSQL : localhost:5432

## Alembic et migrations

Les migrations sont maintenant gérées avec Alembic dans `backend/alembic/`.

Depuis `backend/` :

```bash
alembic upgrade head
```

Pour une base déjà existante que vous voulez raccorder à Alembic sans rejouer la migration initiale :

```bash
alembic stamp head
```

Le mode `development` garde `AUTO_CREATE_SCHEMA=true` pour ne pas casser le lancement local, mais en production il faut laisser :

- `AUTO_CREATE_SCHEMA=false`
- `AUTO_SEED_DATA=false`

## Entraîner le modèle IA

Dans le conteneur backend ou localement :

```bash
cd backend
python -m app.ml.train_model
```

Cela crée :
- `backend/app/ml/artifacts/maintenance_model.joblib`
- `backend/app/ml/artifacts/maintenance_scaler.joblib`

## Endpoints principaux

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET/POST /api/machines/`
- `GET/POST /api/rules/`
- `POST /api/sensors/ingest`
- `GET /api/alerts/`
- `POST /api/alerts/{id}/acknowledge`
- `GET /api/predictions/`
- `POST /api/predictions/simulate/{machine_id}`
- `GET /api/dashboard/summary`
- `GET /api/assets/tree`
- `GET/POST /api/interventions/`
- `GET/POST /api/ingestion-jobs/`
- `POST /api/ingestion-jobs/{id}/start`
- `POST /api/ingestion-jobs/{id}/stop`
- `GET /api/ml/overview`
- `GET /api/ml/replay/sources`
- `POST /api/ml/replay/step`
- `POST /api/ml/replay/reset/{source_id}`
- `GET /api/ml/feedback-summary`
- `GET /api/ml/drift-report`
- `GET /api/ml/business-metrics`
- `GET /api/ml/model-diagnostics`
- `GET /api/ml/explain/machines/{machine_id}`
- `POST /api/ml/retrain-from-feedback`
- `WS /ws/live?token=...`

## Secrets et environnements

Fichiers fournis :

- [backend/.env.example](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/backend/.env.example)
- [backend/.env.production.example](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/backend/.env.production.example)
- [.env.production.example](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/.env.production.example)
- [frontend/.env.production.example](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/frontend/.env.production.example)

Pour générer un secret fort :

```bash
cd backend
python scripts/generate_secret.py
```

En `production`, l'application refuse de démarrer si :

- `SECRET_KEY` est trop faible
- `ENFORCE_HTTPS=false`
- `AUTO_CREATE_SCHEMA=true`
- `AUTO_SEED_DATA=true`

## Base de données

Tables principales :
- users
- machines
- business_rules
- asset_nodes
- sensor_data
- alerts
- predictions
- maintenance_interventions
- ingestion_jobs

## Logique métier et IA

Le projet suit bien la logique demandée :

### Phase initiale
Les règles métier produisent :
- alertes simples
- score de sévérité
- nombre de règles déclenchées
- confiance maximale
- marges par rapport aux seuils

### Phase IA
Ces résultats deviennent des features d'entrée du modèle :
- `rule_count`
- `severity_score`
- `max_rule_confidence`
- `temperature_margin_85`
- `pressure_margin_7`
- `rpm_drop_margin`
- etc.

Le modèle apprend donc à partir des mesures capteurs + intelligence métier transformée.

## Datasets et benchmarks PFE

Les données brutes attendues sont placées dans `data/raw/`, un dossier par source.

Cette version détecte automatiquement les datasets présents et construit un rapport ML dans :

- `data/reports/dataset_catalog.json`
- `data/reports/ml_overview.json`

Elle prépare et benchmarke automatiquement les jeux exploitables déjà présents :

- `CWRU Bearing Features`
- `Hydraulic Systems`
- `Vibration Feature Dataset`
- `IMS Bearing RUL`
- `Electric Arc Furnace`

Les jeux `MetroPT-3`, `Pump time series` et les jeux audio `fan` restent disponibles pour le rejeu temps réel ou les prochaines itérations de l'étude.

Pour regénérer le rapport ML :

```powershell
.\pfe\Scripts\python.exe .\qa\run_ml_benchmarks.py
```

Dans l'interface, la page `ML` affiche :

- le catalogue des datasets détectés
- les benchmarks classification / anomaly detection / regression
- les modèles gagnants par dataset
- les diagnostics du modèle en service
- la calibration avant / après et la courbe de calibration
- les importances globales des variables
- les métriques métier dérivées des alertes et interventions
- l'explication locale de la dernière prédiction d'une machine
- le rejeu temps réel de vraies séries `pompe`, `compresseur` et `four`
- les prochaines recommandations pour la suite du PFE

La page `Operations` centralise :

- la hiérarchie des actifs `site > zone > ligne > composant`
- les interventions terrain et leurs labels métier
- les jobs d'ingestion continue
- le rapport de drift
- le retraining à partir des retours terrain

Le dashboard principal est maintenant branché sur un WebSocket (`/ws/live`) pour se rafraîchir dès qu'un signal ou une intervention est enregistré.

## Déploiement production HTTPS

Un stack production séparé est disponible dans [docker-compose.prod.yml](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/docker-compose.prod.yml).

Il utilise :

- [backend/Dockerfile.prod](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/backend/Dockerfile.prod)
- [backend/start-prod.sh](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/backend/start-prod.sh)
- [frontend/Dockerfile.prod](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/frontend/Dockerfile.prod)
- [frontend/nginx.prod.conf](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/frontend/nginx.prod.conf)

Étapes :

1. créer `.env.production` à partir de [.env.production.example](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/.env.production.example)
2. déposer vos certificats TLS dans `infra/certs/`
3. lancer :

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up --build -d
```

Le frontend est alors servi en HTTPS, et `/api` ainsi que `/ws` sont proxyfiés vers le backend.

## Limites actuelles

Cette version est complète et fonctionnelle pour un PFE, mais peut encore être enrichie avec :
- Celery/Redis pour batchs et alertes asynchrones
- vrais graphiques avancés
- export PDF/CSV
- supervision multi-instance des jobs d'ingestion
- modèle XGBoost et RUL plus avancé

## Recette et conformité

Le plan de recette et le runner automatique sont disponibles dans :

- `qa/plan_recette.md`
- `qa/run_recette.py`

Exemple d'execution :

```powershell
.\pfe\Scripts\python.exe .\qa\run_recette.py --start-db --output .\qa\reports\recette_report.json
```
