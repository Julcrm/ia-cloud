"""Mini IHM : commandes de l'ERP qui arrivent (DuckLake) et prédiction du modèle en service.

Même modèle que l'API (current.json sur Garage) et même code de prédiction. Sans authentification :
publiée sur 127.0.0.1 du VPS seulement, ouverte par un tunnel SSH.
"""

import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from express_delivery.domain.prediction import OrderEligibilityPredictor
from express_delivery.infrastructure.ducklake.ducklake_order_store import connect_lake
from express_delivery.infrastructure.ducklake.ducklake_orders_source import DuckLakeOrdersSource
from express_delivery.infrastructure.model_repository_factory import build_model_repository
from express_delivery.ui.page import PAGE

SELECT_ORDERS = "SELECT * EXCLUDE (ingested_at) FROM lake.erp_orders"


def create_app(connect=connect_lake, model_repository=None):
    app = FastAPI(title="IHM livraison express", docs_url=None, redoc_url=None, openapi_url=None)
    repository = model_repository or build_model_repository()
    served = {"version": None, "model": None}

    def read_orders(sql, params):
        """Commandes ERP traduites dans le vocabulaire du modèle, en JSON (NaN -> null)."""
        connection = connect()
        try:
            orders = connection.execute(sql, params).df()
        finally:
            connection.close()
        if orders.empty:
            return []
        orders = DuckLakeOrdersSource.to_model_orders(orders).drop(columns="express_eligible")
        return json.loads(orders.to_json(orient="records", date_format="iso"))

    def served_model():
        # Recharge quand current.json change, comme l'API (ADR-0002).
        version = repository.current_version()
        if version != served["version"]:
            served["model"], served["version"] = repository.load(), version
        return served["model"], served["version"]

    @app.get("/", response_class=HTMLResponse)
    def page():
        return PAGE

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/orders")
    def latest_orders(limit: int = Query(30, ge=1, le=200)):
        orders = read_orders(f"{SELECT_ORDERS} ORDER BY order_id DESC LIMIT ?", [limit])
        return Response(json.dumps(orders[::-1]), media_type="application/json")

    @app.get("/api/orders/{order_id}/prediction")
    def prediction(order_id: str):
        orders = read_orders(f"{SELECT_ORDERS} WHERE order_id = ?", [order_id])
        if not orders:
            raise HTTPException(404, f"Commande {order_id} introuvable.")
        model, version = served_model()
        result = OrderEligibilityPredictor.predict_order_eligibility(orders[0], model)
        return {**result, "model_version": version, "order": orders[0]}

    return app


app = create_app()
