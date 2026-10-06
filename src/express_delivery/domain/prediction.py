"""Prédiction unitaire et batch, et leurs règles communes (cellules 34 et 46)."""

from datetime import datetime

import numpy as np
import pandas as pd

from express_delivery.config import DEFAULT_THRESHOLD, FEATURE_COLUMNS, MODEL_VERSION


class EligibilityRules:

    @staticmethod
    def ensure_features(available_features, error_label):
        missing_features = set(FEATURE_COLUMNS) - set(available_features)

        if missing_features:
            raise ValueError(
                f"{error_label} : {sorted(missing_features)}"
            )

    @staticmethod
    def is_eligible(probability, threshold):
        return probability >= threshold

    @staticmethod
    def to_decision(eligible):
        decisions = np.where(eligible, "oui", "non")
        return decisions.item() if decisions.ndim == 0 else decisions


class OrderEligibilityPredictor:
    """Prédiction métier pour une commande (cellule 34), futur cœur de l'API."""

    @staticmethod
    def predict_order_eligibility(order_data, model, threshold=DEFAULT_THRESHOLD):
        """
        Effectue une prédiction pour une commande.

        Parameters
        ----------
        order_data : dict
            Données d'une commande.
        model : Pipeline
            Pipeline scikit-learn entraînée.
        threshold : float
            Seuil à partir duquel la commande est considérée comme éligible.

        Returns
        -------
        dict
            Résultat de la prédiction.
        """
        EligibilityRules.ensure_features(order_data.keys(), "Variables manquantes")

        input_df = pd.DataFrame(
            [{feature: order_data[feature] for feature in FEATURE_COLUMNS}]
        )

        probability = float(model.predict_proba(input_df)[0, 1])
        eligible = EligibilityRules.is_eligible(probability, threshold)

        return {
            "express_eligible": bool(eligible),
            "decision": EligibilityRules.to_decision(eligible),
            "probability": round(probability, 4),
            "model_version": MODEL_VERSION,
            "prediction_timestamp": datetime.utcnow().isoformat()
        }


class BatchPredictor:
    """Prédiction sur un ensemble de commandes (cellule 46)."""

    @staticmethod
    def batch_predict_orders(input_df, model, threshold=DEFAULT_THRESHOLD):
        """
        Réalise une prédiction batch sur plusieurs commandes.
        """
        EligibilityRules.ensure_features(
            input_df.columns, "Variables manquantes dans le batch"
        )

        result = input_df.copy()
        result["eligibility_probability"] = model.predict_proba(
            input_df[FEATURE_COLUMNS]
        )[:, 1]

        result["express_eligible"] = EligibilityRules.is_eligible(
            result["eligibility_probability"], threshold
        ).astype(int)

        result["decision"] = EligibilityRules.to_decision(
            result["express_eligible"] == 1
        )

        return result
