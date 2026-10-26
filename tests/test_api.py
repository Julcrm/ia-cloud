"""Tests de l'API : model card (séance 3)."""

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


class InMemoryModelRepository(ModelRepository):
    def __init__(self, model, model_card):
        self.model = model
        self.model_card = model_card

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
