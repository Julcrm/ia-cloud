import json

import joblib

from express_delivery.abstractions.model_repository import ModelRepository
from express_delivery.config import (
    ARTIFACTS_DIR,
    FEATURE_COLUMNS,
    FEATURES_PATH,
    MODEL_PATH,
    MODEL_VERSION,
)
from express_delivery.training_config import (
    CATEGORICAL_FEATURES,
    METRICS_PATH,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
)


class FileModelRepository(ModelRepository):
    """Modèle et métadonnées stockés en fichiers dans artifacts/ (cellules 3, 41 et 43)."""

    def save(self, model_pipeline, metrics):
        ARTIFACTS_DIR.mkdir(exist_ok=True)

        joblib.dump(model_pipeline, MODEL_PATH)

        with open(METRICS_PATH, "w", encoding="utf-8") as file:
            json.dump(metrics, file, indent=2)

        with open(FEATURES_PATH, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "model_version": MODEL_VERSION,
                    "target": TARGET_COLUMN,
                    "features": FEATURE_COLUMNS,
                    "numeric_features": NUMERIC_FEATURES,
                    "categorical_features": CATEGORICAL_FEATURES,
                },
                file,
                indent=2
            )

        print(f"Modèle sauvegardé dans : {MODEL_PATH}")
        print(f"Métriques sauvegardées dans : {METRICS_PATH}")
        print(f"Configuration sauvegardée dans : {FEATURES_PATH}")

    def load(self):
        self._check_features()

        loaded_model = joblib.load(MODEL_PATH)
        return loaded_model

    @staticmethod
    def _check_features():
        """Refuse un modèle entraîné sur d'autres variables que celles du code."""
        with open(FEATURES_PATH, encoding="utf-8") as file:
            saved_features = json.load(file)["features"]

        if saved_features != FEATURE_COLUMNS:
            raise ValueError(
                f"Le modèle sauvegardé attend les variables {saved_features}, "
                f"le code fournit {FEATURE_COLUMNS}. Réentraîner le modèle."
            )
