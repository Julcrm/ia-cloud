# Éligibilité à la livraison express

> Prédire si une commande peut être livrée dans la journée.

**Stack** : Python 3.12 · uv · scikit-learn · MLflow · FastAPI · DuckDB / DuckLake

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
| `uv run pytest` | Lance les tests de prédiction |
| `docker build -t ia-cloud .` | Construit l'image de l'API (modèle entraîné pendant le build) |
| `docker run -e API_KEY=... -p 8000:8000 ia-cloud` | Lance l'API en conteneur |
| `uv run mlflow ui` | Ouvre l'interface MLflow sur <http://localhost:5000> |

### Artefacts produits

```text
artifacts/
├── express_delivery_model.joblib   # pipeline scikit-learn entraîné
├── features.json                   # variables attendues par le modèle
├── metrics.json                    # métriques sur le jeu de test
└── batch_predictions.csv           # sortie de predict-batch
```

## API

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/health` | Sonde de vivacité : répond 200 tant que le processus tourne |
| `GET` | `/health/ready` | Sonde de disponibilité : vérifie le modèle et le stockage, sinon 503 |
| `POST` | `/v1/orders` | Enregistre une commande (202) ; la prédiction est calculée en tâche de fond |
| `GET` | `/v1/orders/{order_id}` | Relit une commande enregistrée |
| `POST` | `/v1/predictions` | Prédiction synchrone pour une commande |

Les routes `/v1/*` exigent l'en-tête `X-API-Key` (401 sinon) ; les sondes `/health`
restent ouvertes. Sans variable `API_KEY`, les routes `/v1/*` sont refusées et
`/health/ready` répond 503.

## Architecture

```text
src/express_delivery/
├── abstractions/     # contrats (ABC) : sources, stockage, modèle, export
├── infrastructure/   # implémentations : dev/, mlflow/, ducklake/
├── domain/           # logique métier : qualité des données, entraînement, prédiction
├── pipelines.py      # TrainingPipeline, BatchPredictionPipeline
├── api/              # schémas Pydantic et routes FastAPI
├── config.py         # constantes de production
└── training_config.py
```

### Décisions d'architecture

| ADR | Sujet | Décision |
|-----|-------|----------|
| [ADR-0001](docs/adr/ADR-0001-stockage-commandes-clients.pdf) | Stockage des commandes | DuckLake : Parquet sur S3, catalogue PostgreSQL |
| [ADR-0002](docs/adr/ADR-0002-stockage-artefacts-modele.pdf) | Artefacts du modèle | Dossiers versionnés sur S3 et `current.json` |
| [ADR-0003](docs/adr/ADR-0003-plateforme-deploiement.pdf) | Plateforme de déploiement | VPS netcup + Coolify |
| [ADR-0004](docs/adr/ADR-0004-cloud-on-premise-local.pdf) | Cloud, on-premise ou local | Cloud IaaS pour test et prod, local pour le dev |
| [ADR-0005](docs/adr/ADR-0005-strategie-deploiement.pdf) | Stratégie de déploiement | Rolling update de Coolify |
| [ADR-0006](docs/adr/ADR-0006-securisation.pdf) | Sécurisation | Défense en profondeur, clé d'API sur `/v1/*` |

### Configuration

| Variable | Défaut (dev) | Rôle |
|----------|--------------|------|
| `DUCKLAKE_CATALOG` | `ducklake:data/catalog.ducklake` | Catalogue DuckLake (PostgreSQL en production) |
| `DUCKLAKE_DATA_PATH` | `data/lake/` | Emplacement des fichiers Parquet (S3 en production) |
| `API_KEY` | aucun | Clé exigée dans l'en-tête `X-API-Key` des routes `/v1/*` (secret Coolify en production) |

