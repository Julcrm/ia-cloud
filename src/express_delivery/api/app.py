"""API HTTP, contrat : openapi.yml (opérations de la séance 1).

Lancement depuis la racine du projet :
    uv run uvicorn express_delivery.api.app:app
"""

import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from express_delivery.abstractions.model_repository import ModelRepository
from express_delivery.api.schemas import (
    Error,
    HealthStatus,
    OrderAccepted,
    OrderFeatures,
    Prediction,
    ReadinessStatus,
)
from express_delivery.config import MODEL_VERSION, PROJECT_NAME
from express_delivery.domain.prediction import OrderEligibilityPredictor
from express_delivery.infrastructure.dev.file_model_repository import FileModelRepository
from express_delivery.infrastructure.ducklake.ducklake_order_store import DuckLakeOrderStore


class ApiError(Exception):
    """Erreur renvoyée au client au format du schéma Error."""

    def __init__(self, status_code, error, message):
        self.status_code = status_code
        self.error = error
        self.message = message


def error_response(status_code, error, message, details=None):
    body = Error(error=error, message=message, details=details)
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))


def try_or_none(build):
    """Le service démarre même si une dépendance manque : /health/ready le signale."""
    try:
        return build()
    except Exception as error:
        print(f"Démarrage dégradé : {type(error).__name__}: {error}")
        return None


def predict(order_data, model):
    start = time.perf_counter()
    result = OrderEligibilityPredictor.predict_order_eligibility(order_data, model)
    latency_ms = (time.perf_counter() - start) * 1000

    return Prediction(
        order_id=order_data["order_id"],
        express_eligible=result["express_eligible"],
        decision=result["decision"],
        probability=result["probability"],
        model_version=result["model_version"],
        predicted_at=datetime.fromisoformat(result["prediction_timestamp"]).replace(tzinfo=UTC),
        latency_ms=round(latency_ms, 2),
    )


def predict_in_background(order_data, model):
    """Prédiction asynchrone d'une commande collectée. Stockage : séance 5."""
    if model is None:
        print(f"Commande {order_data['order_id']} non prédite : aucun modèle chargé.")
        return
    print(f"Prédiction asynchrone : {predict(order_data, model).model_dump_json()}")


def with_order_id(order: OrderFeatures):
    order_data = order.model_dump()
    order_data["order_id"] = order.order_id or f"CMD-{uuid.uuid4().hex}"
    return order_data


router = APIRouter()


@router.get(
    "/health",
    tags=["health"],
    operation_id="getHealth",
    summary="Sonde de vivacité",
    openapi_extra={"x-session": 1},
)
def get_health() -> HealthStatus:
    return HealthStatus(status="ok", service=PROJECT_NAME, version=MODEL_VERSION)


@router.get(
    "/health/ready",
    tags=["health"],
    operation_id="getReadiness",
    summary="Sonde de disponibilité",
    responses={503: {"model": ReadinessStatus, "description": "Le service n'est pas prêt"}},
    openapi_extra={"x-session": 1},
)
def get_readiness(request: Request) -> ReadinessStatus:
    checks = {
        "model": "loaded" if request.app.state.model is not None else "not_loaded",
        "order_store": "unreachable",
    }
    if request.app.state.order_store is not None:
        try:
            request.app.state.order_store.ping()
            checks["order_store"] = "reachable"
        except Exception:
            pass

    ready = checks == {"model": "loaded", "order_store": "reachable"}
    status = ReadinessStatus(
        status="ready" if ready else "not_ready", checks=checks, version=MODEL_VERSION
    )
    if not ready:
        return JSONResponse(status_code=503, content=status.model_dump())
    return status


@router.post(
    "/v1/orders",
    status_code=202,
    tags=["orders"],
    operation_id="createOrder",
    summary="Enregistrer une commande à prédire",
    responses={
        422: {"model": Error, "description": "Commande invalide"},
        500: {"model": Error, "description": "Erreur interne"},
    },
    openapi_extra={"x-session": 1},
)
def create_order(
    order: OrderFeatures, request: Request, background_tasks: BackgroundTasks
) -> OrderAccepted:
    order_store = request.app.state.order_store
    if order_store is None:
        raise ApiError(500, "order_store_unavailable", "Le stockage des commandes est indisponible.")

    order_data = with_order_id(order)
    order_store.add(order_data)
    background_tasks.add_task(predict_in_background, order_data, request.app.state.model)

    return OrderAccepted(order_id=order_data["order_id"], status="accepted")


@router.get(
    "/v1/orders/{order_id}",
    tags=["orders"],
    operation_id="getOrder",
    summary="Relire une commande collectée",
    responses={404: {"model": Error, "description": "Commande inconnue"}},
    openapi_extra={"x-session": 1},
)
def get_order(order_id: str, request: Request) -> OrderFeatures:
    order_store = request.app.state.order_store
    if order_store is None:
        raise ApiError(500, "order_store_unavailable", "Le stockage des commandes est indisponible.")

    order = order_store.get(order_id)
    if order is None:
        raise ApiError(404, "order_not_found", f"Commande inconnue : {order_id}")
    return OrderFeatures(**order)


@router.post(
    "/v1/predictions",
    tags=["predictions"],
    operation_id="createPrediction",
    summary="Prédire l'éligibilité express d'une commande",
    responses={
        422: {"model": Error, "description": "Commande invalide"},
        503: {"model": Error, "description": "Modèle indisponible"},
    },
    openapi_extra={"x-session": 1},
)
def create_prediction(order: OrderFeatures, request: Request) -> Prediction:
    model = request.app.state.model
    if model is None:
        raise ApiError(503, "model_unavailable", "Aucun modèle n'est chargé.")
    return predict(with_order_id(order), model)


def create_app(build_order_store, model_repository: ModelRepository) -> FastAPI:
    """Seul endroit de l'API qui choisit les implémentations concrètes."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.model = try_or_none(model_repository.load)
        app.state.order_store = try_or_none(build_order_store)
        yield

    app = FastAPI(
        title=f"{PROJECT_NAME} API",
        version=MODEL_VERSION,
        description="API de prédiction d'éligibilité à la livraison express.",
        lifespan=lifespan,
    )
    app.include_router(router)

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError):
        return error_response(error.status_code, error.error, error.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError):
        details = [
            f"{'.'.join(str(part) for part in item['loc'][1:])} : {item['msg']}"
            for item in error.errors()
        ]
        return error_response(422, "validation_error", "Requête invalide.", details)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception):
        return error_response(500, "internal_error", "Erreur interne.")

    return app


app = create_app(DuckLakeOrderStore, FileModelRepository())
