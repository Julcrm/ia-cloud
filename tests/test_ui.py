"""Mini IHM : commandes ERP lues dans DuckLake, prédiction du modèle en service."""

from fastapi.testclient import TestClient
from test_api import InMemoryModelRepository
from test_ducklake_orders_source import erp_order, write

from express_delivery.domain.data_quality import DataCleaner
from express_delivery.domain.training import FeatureSelector, ModelPipelineFactory
from express_delivery.infrastructure.dev.synthetic_orders_source import SyntheticOrdersSource
from express_delivery.infrastructure.ducklake.ducklake_order_store import connect_lake
from express_delivery.ui.app import create_app


def trained_model():
    X, y = FeatureSelector().select(DataCleaner.clean_orders_data(SyntheticOrdersSource().load()))
    return ModelPipelineFactory().create().fit(X, y)


def client_for(tmp_path):
    lake = (f"ducklake:{tmp_path}/catalog.ducklake", f"{tmp_path}/lake/")
    write(lake, [erp_order(f"ERP-0000000{i}", 1, 20.0) for i in (3, 1, 2)])
    repository = InMemoryModelRepository(trained_model(), None, version="1.0.0-20261120T150149Z")
    return TestClient(create_app(lambda: connect_lake(*lake), repository))


def test_orders_arrive_in_order_in_model_vocabulary(tmp_path):
    orders = client_for(tmp_path).get("/api/orders?limit=2").json()

    # Les 2 plus récentes, de la plus ancienne à la plus récente.
    assert [o["order_id"] for o in orders] == ["ERP-00000002", "ERP-00000003"]
    assert orders[0]["weather"] == "pluie"
    assert "express_eligible" not in orders[0]  # la cible simulée ne sort pas


def test_prediction_of_an_order_with_served_model_version(tmp_path):
    client = client_for(tmp_path)

    prediction = client.get("/api/orders/ERP-00000001/prediction").json()

    assert prediction["decision"] in {"oui", "non"}
    assert 0 <= prediction["probability"] <= 1
    assert prediction["model_version"] == "1.0.0-20261120T150149Z"
    assert prediction["order"]["order_id"] == "ERP-00000001"
    assert client.get("/api/orders/ERP-99999999/prediction").status_code == 404


def test_page_is_served(tmp_path):
    assert "Suivant" in client_for(tmp_path).get("/").text
