"""Tests de l'API : model card (séance 3)."""

import numpy as np
from fastapi.testclient import TestClient

from express_delivery.abstractions.model_repository import ModelRepository
from express_delivery.api.app import create_app

API_KEY = "test"

MODEL_CARD = {
    "project": "eligibilite-livraison-express",
    "model_version": "1.0.0",
    "model_type": "Régression logistique",
    "task": "Classification binaire",
    "target": "express_eligible",
    "positive_class": "Commande éligible à la livraison express",
    "threshold": 0.5,
    "trained_at": "2026-10-26T12:00:00+00:00",
    "features": ["hour", "distance_km"],
    "training_rows": 4800,
    "metrics": {"accuracy": 0.77, "roc_auc": 0.85},
    "limitations": ["Le jeu de données utilisé est synthétique."],
}


ORDER = {
    "hour": 10,
    "day_of_week": 1,
    "weekend": 0,
    "distance_km": 2,
    "order_value_eur": 50,
    "weight_kg": 1,
    "stock_available": 1,
    "preparation_time_min": 10,
    "carrier_capacity": 0.9,
    "weather": "normal",
    "delivery_zone": "centre",
    "customer_type": "premium",
}


class ConstantModel:
    def predict_proba(self, rows):
        return np.array([[0.2, 0.8]] * len(rows))


class InMemoryModelRepository(ModelRepository):
    def __init__(self, model, model_card, version="1.0.0"):
        self.model = model
        self.model_card = model_card
        self.version = version

    def save(self, model_pipeline, metrics, model_card):
        self.model, self.model_card = model_pipeline, model_card

    def load(self):
        if self.model is None:
            raise FileNotFoundError("aucun modèle")
        return self.model

    def load_model_card(self):
        if self.model_card is None:
            raise FileNotFoundError("aucune model card")
        return self.model_card

    def current_version(self):
        return self.version


def client_for(model_repository):
    app = create_app(lambda: None, model_repository, API_KEY)
    return TestClient(app, headers={"X-API-Key": API_KEY})


def test_model_card_of_loaded_model():
    with client_for(InMemoryModelRepository(object(), MODEL_CARD)) as client:
        response = client.get("/v1/model")

    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "1.0.0"
    assert body["metrics"] == {"accuracy": 0.77, "roc_auc": 0.85}
    assert body["trained_at"].startswith("2026-10-26T12:00:00")
    # Seuls les champs du schéma ModelCard du contrat sont renvoyés.
    assert "training_rows" not in body
    assert "positive_class" not in body


def test_model_card_without_model():
    with client_for(InMemoryModelRepository(None, None)) as client:
        response = client.get("/v1/model")

    assert response.status_code == 503
    assert response.json()["error"] == "model_unavailable"


def test_model_card_requires_api_key():
    with client_for(InMemoryModelRepository(object(), MODEL_CARD)) as client:
        response = client.get("/v1/model", headers={"X-API-Key": "mauvaise"})

    assert response.status_code == 401


def test_model_hot_reloads_when_current_version_changes():
    repo = InMemoryModelRepository(ConstantModel(), MODEL_CARD, version="1.0.0")
    with client_for(repo) as client:
        assert client.get("/v1/model").json()["model_version"] == "1.0.0"

        # Nouvelle version publiée (current.json flip) : l'API doit la prendre sans redémarrer.
        repo.model = ConstantModel()
        repo.model_card = {**MODEL_CARD, "model_version": "1.0.0-20261120T134920Z"}
        repo.version = "1.0.0-20261120T134920Z"

        client.get("/health/ready")  # la sonde déclenche le rechargement
        assert client.get("/v1/model").json()["model_version"] == "1.0.0-20261120T134920Z"
        # La prédiction indique le dossier exact du modèle qui l'a produite.
        prediction = client.post("/v1/predictions", json=ORDER).json()
        assert prediction["model_version"] == "1.0.0-20261120T134920Z"
