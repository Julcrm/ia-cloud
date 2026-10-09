"""Constantes utiles en production, à la prédiction (cellules 3, 5, 20, 41 et 50)."""

import os
from pathlib import Path

RANDOM_STATE = 42

ARTIFACTS_DIR = Path("artifacts")

PROJECT_NAME = "eligibilite-livraison-express"
MODEL_VERSION = "1.0.0"

# Les identifiants et les dates brutes ne sont pas utilisés directement
# par le modèle dans cette première version.
FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "weekend",
    "distance_km",
    "order_value_eur",
    "weight_kg",
    "stock_available",
    "preparation_time_min",
    "carrier_capacity",
    "weather",
    "delivery_zone",
    "customer_type",
]

MODEL_PATH = ARTIFACTS_DIR / "express_delivery_model.joblib"
FEATURES_PATH = ARTIFACTS_DIR / "features.json"

PREDICTIONS_PATH = ARTIFACTS_DIR / "batch_predictions.csv"

# Stockage des commandes (ADR-0001). Par défaut : catalogue et fichiers locaux.
# En production : catalogue PostgreSQL et fichiers sur S3.
DUCKLAKE_CATALOG = os.environ.get("DUCKLAKE_CATALOG", "ducklake:data/catalog.ducklake")
DUCKLAKE_DATA_PATH = os.environ.get("DUCKLAKE_DATA_PATH", "data/lake/")

# Clé exigée sur les routes /v1/* (ADR-0006). Sans valeur, ces routes sont refusées.
API_KEY = os.environ.get("API_KEY")

# Seuil de décision par défaut, à choisir avec le métier.
DEFAULT_THRESHOLD = 0.5
