"""Orchestration : un pipeline par commande de main.py."""

from sklearn.metrics import f1_score

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

        model_card = self.model_card_builder.build(
            metrics, X_train, X_test, self.orders_source.describe()
        )

        # Garde-fou : on ne remplace pas le modèle en service par un moins bon, comparés
        # sur le même jeu de test (des F1 calculés sur des données différentes ne se comparent pas).
        served_f1 = self.served_model_f1(X_test, y_test)
        published = served_f1 is None or metrics["f1_score"] >= served_f1
        model_card["promotion"] = {"published": published, "served_model_f1": served_f1}

        if published:
            self.model_repository.save(model_pipeline, metrics, model_card)
        else:
            print(
                f"Modèle non publié : F1 {metrics['f1_score']:.4f} < {served_f1:.4f} "
                "(modèle en service, même jeu de test). Le modèle en service est conservé."
            )

        return model_card

    def served_model_f1(self, X_test, y_test):
        """F1 du modèle en service sur ce jeu de test ; None s'il n'y en a pas d'utilisable."""
        try:
            served_model = self.model_repository.load()
        except Exception as error:  # premier entraînement, variables changées... : on publie
            print(f"Pas de modèle en service à comparer ({error}).")
            return None
        return f1_score(y_test, served_model.predict(X_test), zero_division=0)


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

        batch_input = orders_clean.sample(n=10, random_state=RANDOM_STATE)[FEATURE_COLUMNS]

        batch_predictions = BatchPredictor.batch_predict_orders(batch_input, loaded_model)

        self.predictions_writer.export(batch_predictions)

        return batch_predictions
