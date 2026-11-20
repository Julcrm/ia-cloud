"""Code location Dagster ia_cloud : réentraînement planifié du modèle sur les commandes de l'ERP.

Servie en gRPC sur le port 4000 au dagster-workspace du VPS, comme les autres projets.
Les runs s'exécutent dans ce conteneur (DefaultRunLauncher du workspace).
"""

from dagster import (
    DefaultScheduleStatus,
    Definitions,
    MaterializeResult,
    ScheduleDefinition,
    asset,
    define_asset_job,
)

from express_delivery.infrastructure.ducklake.ducklake_orders_source import DuckLakeOrdersSource
from express_delivery.infrastructure.mlflow.mlflow_model_trainer import MlflowModelTrainer
from express_delivery.infrastructure.model_repository_factory import build_model_repository
from express_delivery.pipelines import TrainingPipeline


@asset(description="Modèle d'éligibilité express entraîné sur les commandes de l'ERP (DuckLake).")
def express_delivery_model() -> MaterializeResult:
    model_card = TrainingPipeline(
        DuckLakeOrdersSource(), MlflowModelTrainer(), build_model_repository()
    ).run()
    served_f1 = model_card["promotion"]["served_model_f1"]
    return MaterializeResult(
        metadata={
            **model_card["metrics"],
            "training_rows": model_card["training_rows"],
            "test_rows": model_card["test_rows"],
            "ducklake_snapshot_id": model_card["data_source"]["ducklake_snapshot_id"],
            "published": model_card["promotion"]["published"],
            # -1 : aucun modèle en service à comparer (Dagster refuse None en métadonnée).
            "served_model_f1": -1.0 if served_f1 is None else served_f1,
        }
    )


retrain_model = define_asset_job("retrain_model", selection=[express_delivery_model])

defs = Definitions(
    assets=[express_delivery_model],
    jobs=[retrain_model],
    schedules=[
        ScheduleDefinition(
            job=retrain_model,
            cron_schedule="0 3 * * *",
            execution_timezone="Europe/Paris",
            default_status=DefaultScheduleStatus.RUNNING,
        )
    ],
)
