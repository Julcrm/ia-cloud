from abc import ABC, abstractmethod


class OrderStore(ABC):
    """Persistance des commandes collectées par l'API."""

    @abstractmethod
    def add(self, order: dict) -> None:
        """Enregistre une commande (contient toujours un order_id)."""

    @abstractmethod
    def get(self, order_id: str) -> dict | None:
        """Relit une commande, None si elle est inconnue."""

    @abstractmethod
    def ping(self) -> None:
        """Lève une exception si le stockage n'est pas joignable."""
