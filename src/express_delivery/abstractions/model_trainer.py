from abc import ABC, abstractmethod


class ModelTrainer(ABC):
    """Entraînement du modèle et calcul des métriques sur le jeu de test."""

    @abstractmethod
    def train(self, model_pipeline, X_train, X_test, y_train, y_test):
        """Entraîne le modèle et retourne (metrics, run_id, y_pred)."""
