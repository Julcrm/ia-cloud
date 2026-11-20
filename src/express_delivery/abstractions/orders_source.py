from abc import ABC, abstractmethod

import pandas as pd


class OrdersSource(ABC):
    """Source des commandes (collecte de données)."""

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Retourne les commandes brutes."""

    def describe(self) -> dict:
        """Origine des données du dernier load(), notée dans la fiche du modèle."""
        return {}
