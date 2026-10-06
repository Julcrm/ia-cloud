"""Point d'entrée : python main.py train | predict-batch"""

import argparse

from express_delivery.infrastructure.dev.csv_predictions_writer import CsvPredictionsWriter
from express_delivery.infrastructure.dev.file_model_repository import FileModelRepository
from express_delivery.infrastructure.dev.synthetic_orders_source import SyntheticOrdersSource
from express_delivery.infrastructure.mlflow.mlflow_model_trainer import MlflowModelTrainer
from express_delivery.pipelines import BatchPredictionPipeline, TrainingPipeline


def build_commands():
    """Seul endroit qui choisit les implémentations concrètes."""
    orders_source = SyntheticOrdersSource()
    model_repository = FileModelRepository()

    return {
        "train": TrainingPipeline(
            orders_source,
            MlflowModelTrainer(),
            model_repository,
        ),
        "predict-batch": BatchPredictionPipeline(
            orders_source,
            model_repository,
            CsvPredictionsWriter(),
        ),
    }


def main():
    commands = build_commands()

    parser = argparse.ArgumentParser(
        description="Éligibilité des commandes à la livraison express."
    )
    parser.add_argument("command", choices=commands)
    args = parser.parse_args()

    commands[args.command].run()


if __name__ == "__main__":
    main()
