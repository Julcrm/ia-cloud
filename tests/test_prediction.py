"""Tests fonctionnels de la prédiction (cellules 39 et 44 du notebook)."""

import pytest

from express_delivery.domain.data_quality import DataCleaner
from express_delivery.domain.prediction import OrderEligibilityPredictor
from express_delivery.domain.training import FeatureSelector, ModelPipelineFactory
from express_delivery.infrastructure.dev.file_model_repository import FileModelRepository
from express_delivery.infrastructure.dev.synthetic_orders_source import SyntheticOrdersSource


def run_prediction_tests(model):
    valid_order = {
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

    result = OrderEligibilityPredictor.predict_order_eligibility(valid_order, model)

    assert result["decision"] in {"oui", "non"}
    assert isinstance(result["express_eligible"], bool)
    assert 0 <= result["probability"] <= 1
    assert "model_version" in result

    invalid_order = valid_order.copy()
    del invalid_order["distance_km"]

    try:
        OrderEligibilityPredictor.predict_order_eligibility(invalid_order, model)
        raise AssertionError(
            "Une variable obligatoire absente aurait dû provoquer une erreur."
        )
    except ValueError:
        pass

    print("Tous les tests de prédiction sont passés.")


@pytest.fixture(scope="module")
def model_pipeline():
    """Modèle entraîné comme dans le notebook, sans MLflow."""
    orders_clean = DataCleaner.clean_orders_data(SyntheticOrdersSource().load())

    feature_selector = FeatureSelector()
    X, y = feature_selector.select(orders_clean)
    X_train, X_test, y_train, y_test = feature_selector.split(X, y)

    model_pipeline = ModelPipelineFactory().create()
    model_pipeline.fit(X_train, y_train)

    return model_pipeline


@pytest.fixture
def loaded_model(model_pipeline, tmp_path, monkeypatch):
    """Modèle sauvegardé puis rechargé, dans un dossier temporaire."""
    monkeypatch.chdir(tmp_path)

    model_repository = FileModelRepository()
    model_repository.save(model_pipeline, metrics={})

    return model_repository.load()


def test_prediction_with_trained_model(model_pipeline):
    run_prediction_tests(model_pipeline)


def test_prediction_with_loaded_model(loaded_model):
    run_prediction_tests(loaded_model)
