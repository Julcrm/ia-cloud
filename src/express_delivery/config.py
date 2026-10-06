"""Constantes utiles en production, à la prédiction (cellules 3, 5, 20, 41 et 50)."""

from pathlib import Path

RANDOM_STATE = 42

ARTIFACTS_DIR = Path("artifacts")

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

# Seuil de décision par défaut, à choisir avec le métier.
DEFAULT_THRESHOLD = 0.5
