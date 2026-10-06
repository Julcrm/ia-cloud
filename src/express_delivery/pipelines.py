"""Orchestration : un pipeline par commande de main.py."""

from express_delivery.abstractions.model_repository import ModelRepository
from express_delivery.abstractions.model_trainer import ModelTrainer
from express_delivery.abstractions.orders_source import OrdersSource
from express_delivery.abstractions.predictions_writer import PredictionsWriter
from express_delivery.config import FEATURE_COLUMNS, RANDOM_STATE
from express_delivery.domain.data_quality import DataCleaner, DataValidator
from express_delivery.domain.prediction import BatchPredictor
from express_delivery.domain.training import (
    FeatureSelector,
    ModelCardBuilder,
    ModelEvaluator,
    ModelPipelineFactory,
)


class TrainingPipeline:
    """Entraîne le modèle de bout en bout : données -> modèle sauvegardé."""

    def __init__(
        self,
        orders_source: OrdersSource,
        model_trainer: ModelTrainer,
        model_repository: ModelRepository,
    ):
        self.orders_source = orders_source
        self.model_trainer = model_trainer
        self.model_repository = model_repository
        self.feature_selector = FeatureSelector()
        self.model_factory = ModelPipelineFactory()
        self.evaluator = ModelEvaluator()
        self.model_card_builder = ModelCardBuilder()

    def run(self):
        orders = self.orders_source.load()

        orders_clean = DataCleaner.clean_orders_data(orders)

        print(f"Nombre de lignes avant nettoyage : {len(orders)}")
        print(f"Nombre de lignes après nettoyage : {len(orders_clean)}")

        DataValidator.validate_dataset(orders_clean)
        print("Les données nettoyées sont valides.")

        X, y = self.feature_selector.select(orders_clean)
        X_train, X_test, y_train, y_test = self.feature_selector.split(X, y)

        model_pipeline = self.model_factory.create()
        metrics, run_id, y_pred = self.model_trainer.train(
            model_pipeline, X_train, X_test, y_train, y_test
        )

        self.evaluator.print_metrics(metrics)
        self.evaluator.print_report(y_test, y_pred)

        self.model_repository.save(model_pipeline, metrics)

        return self.model_card_builder.build(metrics, X_train, X_test)


class BatchPredictionPipeline:
    """Prédit l'éligibilité d'un lot de commandes avec le modèle sauvegardé."""

    def __init__(
        self,
        orders_source: OrdersSource,
        model_repository: ModelRepository,
        predictions_writer: PredictionsWriter,
    ):
        self.orders_source = orders_source
        self.model_repository = model_repository
        self.predictions_writer = predictions_writer

    def run(self):
        loaded_model = self.model_repository.load()

        orders_clean = DataCleaner.clean_orders_data(self.orders_source.load())
        DataValidator.validate_dataset(orders_clean)

        batch_input = orders_clean.sample(
            n=10,
            random_state=RANDOM_STATE
        )[FEATURE_COLUMNS]

        batch_predictions = BatchPredictor.batch_predict_orders(
            batch_input,
            loaded_model
        )

        self.predictions_writer.export(batch_predictions)

        return batch_predictions
