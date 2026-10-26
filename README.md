# Éligibilité à la livraison express

> Prédire si une commande peut être livrée dans la journée.

**Stack** : Python 3.12 · uv · scikit-learn · MLflow · FastAPI · DuckDB / DuckLake

## Architecture

```
Commandes synthétiques
        ↓
Entraînement — scikit-learn + MLflow
        ↓
Artefacts — modèle, variables, métriques, model card
        ↓
FastAPI — 
        ↓                                        ↓
Prédiction                                       Collecte
POST /v1/predictions · GET /v1/model             POST /v1/orders · GET /v1/orders/{order_id}
                                                 ↓
                                                 DuckLake — Parquet sur Garage (S3),
                                                 catalogue PostgreSQL
```

Image Docker déployée sur un VPS netcup par **Coolify**, en rolling update piloté par
`/health/ready`. En local, le catalogue DuckLake et les fichiers Parquet restent dans `data/`.

---

## Démarrage rapide

Prérequis : [uv](https://docs.astral.sh/uv/). Il installe lui-même la bonne
version de Python.

```bash
uv sync                    # crée .venv et installe les dépendances et le package
uv run main.py train       # entraîne le modèle et l'enregistre dans artifacts/
API_KEY=dev uv run uvicorn express_delivery.api.app:app --reload
```

L'API est alors disponible sur <http://localhost:8000>, et sa documentation
interactive sur <http://localhost:8000/docs>.

## Commandes

| Commande | Rôle |
|----------|------|
| `uv run main.py train` | Entraîne le modèle, suit l'entraînement dans MLflow, sauvegarde les artefacts |
| `uv run main.py predict-batch` | Charge le modèle, prédit un lot de commandes, écrit le CSV |
| `API_KEY=... uv run uvicorn express_delivery.api.app:app` | Démarre l'API |
| `uv run pytest` | Lance les tests de prédiction, de l'API et de conformité au contrat |
| `uv run ruff check .` | Vérifie le code (erreurs, imports, syntaxe) |
| `uv run ruff format .` | Formate le code |
| `docker build --target api -t ia-cloud-api .` | Construit l'image de l'API, sans mlflow (modèle entraîné pendant le build) |
| `docker build --target train -t ia-cloud-train .` | Construit l'image d'entraînement, avec mlflow |
| `docker run -e API_KEY=... -p 8000:8000 ia-cloud-api` | Lance l'API en conteneur |
| `docker run --rm ia-cloud-train` | Entraîne le modèle ; le conteneur s'arrête à la fin |
| `uv run mlflow ui` | Ouvre l'interface MLflow sur <http://localhost:5000> |

### Artefacts produits

```text
artifacts/
├── express_delivery_model.joblib   # pipeline scikit-learn entraîné
├── features.json                   # variables attendues par le modèle
├── metrics.json                    # métriques sur le jeu de test
├── model_card.json                 # résumé du modèle (cellule 55), servi par GET /v1/model
└── batch_predictions.csv           # sortie de predict-batch
```

## Images publiées

Le pipeline publie les deux images sur le registre GitHub (GHCR) après chaque fusion,
jamais sur une pull request, et seulement si les tests, le démarrage et l'analyse de
vulnérabilités sont au vert.

| Image | Fusion dans `dev` | Fusion dans `main` |
|-------|-------------------|--------------------|
| `ghcr.io/julcrm/ia-cloud-api` | `dev`, `sha-<commit>` | `main`, `latest`, `sha-<commit>` |
| `ghcr.io/julcrm/ia-cloud-train` | `dev`, `sha-<commit>` | `main`, `latest`, `sha-<commit>` |

```bash
docker pull ghcr.io/julcrm/ia-cloud-api:latest
```

## API

Le contrat est [`openapi.yml`](openapi.yml) : il est fourni et ne se modifie pas. La
documentation générée (`/docs`, `/openapi.json`) doit décrire la même API. Chaque
opération y indique sa séance (`x-session`) ; celles des séances suivantes ne sont pas
encore implémentées : `POST /v1/predictions/batch`, `GET /v1/predictions/{order_id}`
(séance 5) et `GET /metrics` (séance 7).

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/health` | Sonde de vivacité : répond 200 tant que le processus tourne |
| `GET` | `/health/ready` | Sonde de disponibilité : vérifie le modèle, le stockage et la clé d'API, sinon 503 |
| `POST` | `/v1/orders` | Enregistre une commande (202) ; la prédiction est calculée en tâche de fond |
| `GET` | `/v1/orders/{order_id}` | Relit une commande enregistrée |
| `POST` | `/v1/predictions` | Prédiction synchrone pour une commande |
| `GET` | `/v1/model` | Model card du modèle en service : version, date d'entraînement, variables, métriques (503 sans modèle) |

Les routes `/v1/*` exigent l'en-tête `X-API-Key` (401 sinon) ; les sondes `/health`
restent ouvertes. Sans variable `API_KEY`, les routes `/v1/*` sont refusées et
`/health/ready` répond 503.

```bash
curl -H "X-API-Key: dev" http://localhost:8000/v1/model

curl -X POST http://localhost:8000/v1/predictions \
  -H "X-API-Key: dev" -H "Content-Type: application/json" \
  -d '{"hour": 14, "day_of_week": 2, "weekend": 0, "distance_km": 3.5,
       "order_value_eur": 89.9, "weight_kg": 2.4, "stock_available": 1,
       "preparation_time_min": 18, "carrier_capacity": 0.85,
       "weather": "normal", "delivery_zone": "centre", "customer_type": "premium"}'
```

## Contribuer

Branches (`main`, `dev`, `feature/*`, `hotfix/*`), commits, vérifications avant fusion,
contrat de l'API et ADR : voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Structure du projet

```text
.
├── main.py           # commandes train et predict-batch
├── openapi.yml       # contrat de l'API
├── Dockerfile        # image de l'API
├── CONTRIBUTING.md   # règles de travail
├── docs/adr/         # décisions d'architecture (PDF)
├── tests/            # tests de prédiction et de l'API
└── src/express_delivery/
    ├── abstractions/     # contrats (ABC) : sources, stockage, modèle, export
    ├── infrastructure/   # implémentations : dev/, mlflow/, ducklake/
    ├── domain/           # logique métier : qualité des données, entraînement, prédiction
    ├── pipelines.py      # TrainingPipeline, BatchPredictionPipeline
    ├── api/              # schémas Pydantic et routes FastAPI
    ├── config.py         # constantes de production
    └── training_config.py
```

## Décisions d'architecture

| ADR | Sujet | Décision |
|-----|-------|----------|
| [ADR-0001](docs/adr/ADR-0001-stockage-commandes-clients.pdf) | Stockage des commandes | DuckLake : Parquet sur S3, catalogue PostgreSQL |
| [ADR-0002](docs/adr/ADR-0002-stockage-artefacts-modele.pdf) | Artefacts du modèle | Dossiers versionnés sur S3 et `current.json` (pour l'instant : `artifacts/` local, modèle entraîné au build de l'image) |
| [ADR-0003](docs/adr/ADR-0003-plateforme-deploiement.pdf) | Plateforme de déploiement | VPS netcup + Coolify |
| [ADR-0004](docs/adr/ADR-0004-cloud-on-premise-local.pdf) | Cloud, on-premise ou local | Cloud IaaS pour test et prod, local pour le dev |
| [ADR-0005](docs/adr/ADR-0005-strategie-deploiement.pdf) | Stratégie de déploiement | Rolling update de Coolify |
| [ADR-0006](docs/adr/ADR-0006-securisation.pdf) | Sécurisation | Défense en profondeur, clé d'API sur `/v1/*` |

## Configuration

| Variable | Défaut (dev) | Rôle |
|----------|--------------|------|
| `DUCKLAKE_CATALOG` | `ducklake:data/catalog.ducklake` | Catalogue DuckLake ; `ducklake:postgres:` en production |
| `DUCKLAKE_DATA_PATH` | `data/lake/` | Fichiers Parquet ; `s3://<bucket>/<dossier>/` en production |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `localhost`, `5432`, `ia_cloud`, —, — | Connexion au catalogue PostgreSQL |
| `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` | `http://localhost:3900`, —, —, `us-east-1` | Accès à Garage (la région est obligatoire) |
| `API_KEY` | aucun | Clé exigée dans l'en-tête `X-API-Key` des routes `/v1/*` (secret Coolify en production) |

