import mlflow
import mlflow.sklearn
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from express_delivery.abstractions.model_trainer import ModelTrainer
from express_delivery.config import FEATURE_COLUMNS, RANDOM_STATE


class MlflowModelTrainer(ModelTrainer):
    """Entraînement suivi dans MLflow (cellule 26)."""

    def train(self, model_pipeline, X_train, X_test, y_train, y_test):
        mlflow.set_experiment("livraison-express")

        with mlflow.start_run(run_name="logistic-regression-baseline") as run:
            model_pipeline.fit(X_train, y_train)

            y_pred = model_pipeline.predict(X_test)
            y_proba = model_pipeline.predict_proba(X_test)[:, 1]

            metrics = {
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred, zero_division=0),
                "recall": recall_score(y_test, y_pred, zero_division=0),
                "f1_score": f1_score(y_test, y_pred, zero_division=0),
                "roc_auc": roc_auc_score(y_test, y_proba),
            }

            mlflow.log_param("model_type", "LogisticRegression")
            mlflow.log_param("random_state", RANDOM_STATE)
            mlflow.log_param("feature_count", len(FEATURE_COLUMNS))

            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, metric_value)

            mlflow.sklearn.log_model(
                model_pipeline,
                name="model",
                skops_trusted_types=["numpy.dtype"]
            )

            run_id = run.info.run_id

        print("Entraînement terminé.")
        print(f"Run MLflow : {run_id}")

        return metrics, run_id, y_pred
