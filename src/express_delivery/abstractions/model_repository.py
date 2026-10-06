from abc import ABC, abstractmethod


class ModelRepository(ABC):
    """Persistance du modèle entraîné et de ses métadonnées."""

    @abstractmethod
    def save(self, model_pipeline, metrics):
        """Sauvegarde le modèle, ses métriques et sa configuration."""

    @abstractmethod
    def load(self):
        """Recharge le modèle sauvegardé."""
