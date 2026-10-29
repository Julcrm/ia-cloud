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

from express_delivery.infrastructure.dev.file_model_repository import FileModelRepository
from express_delivery.infrastructure.mlflow.mlflow_model_trainer import MlflowModelTrainer
from express_delivery.infrastructure.postgres.postgres_orders_source import PostgresOrdersSource
from express_delivery.pipelines import TrainingPipeline


@asset(description="Modèle d'éligibilité express entraîné sur les commandes de l'ERP (ADR-0007).")
def express_delivery_model() -> MaterializeResult:
    model_card = TrainingPipeline(
        PostgresOrdersSource(), MlflowModelTrainer(), FileModelRepository()
    ).run()
    return MaterializeResult(
        metadata={
            **model_card["metrics"],
            "training_rows": model_card["training_rows"],
            "test_rows": model_card["test_rows"],
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
