from abc import ABC, abstractmethod


class PredictionsWriter(ABC):
    """Export des résultats d'une prédiction batch."""

    @abstractmethod
    def export(self, batch_predictions):
        """Écrit les prédictions batch vers leur destination."""
