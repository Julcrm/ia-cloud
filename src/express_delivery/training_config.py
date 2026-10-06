"""Constantes utiles uniquement à l'entraînement (cellules 20 et 41)."""

from express_delivery.config import ARTIFACTS_DIR

TARGET_COLUMN = "express_eligible"

NUMERIC_FEATURES = [
    "hour",
    "day_of_week",
    "weekend",
    "distance_km",
    "order_value_eur",
    "weight_kg",
    "stock_available",
    "preparation_time_min",
    "carrier_capacity",
]

CATEGORICAL_FEATURES = [
    "weather",
    "delivery_zone",
    "customer_type",
]

METRICS_PATH = ARTIFACTS_DIR / "metrics.json"
