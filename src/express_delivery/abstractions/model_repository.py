from abc import ABC, abstractmethod


class ModelRepository(ABC):
    """Persistance du modèle entraîné et de ses métadonnées."""

    @abstractmethod
    def save(self, model_pipeline, metrics, model_card):
        """Sauvegarde le modèle, ses métriques, sa configuration et sa model card."""

    @abstractmethod
    def load(self):
        """Recharge le modèle sauvegardé."""

    @abstractmethod
    def load_model_card(self):
        """Relit la model card du modèle sauvegardé."""
