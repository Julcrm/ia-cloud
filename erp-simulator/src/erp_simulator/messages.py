"""Format des commandes dans le topic Redpanda : clé = order_id, valeur = JSON."""

from __future__ import annotations

import json
from datetime import date

# Colonnes de la table orders. Le topic n'est pas authentifié : un message ne peut pas
# choisir les colonnes écrites (PostgresWriter les met telles quelles dans le SQL).
COLUMNS = (
    "order_id", "order_date", "hour", "day_of_week", "weekend", "distance_km",
    "order_value_eur", "weight_kg", "stock_available", "preparation_time_min",
    "carrier_capacity", "weather", "delivery_zone", "customer_type",
)


def encode(order: dict[str, object]) -> tuple[bytes, bytes]:
    return str(order["order_id"]).encode(), json.dumps(order, default=date.isoformat).encode()


def decode(value: bytes) -> dict[str, object]:
    payload = json.loads(value)
    unknown = set(payload) - set(COLUMNS)
    if unknown or "order_id" not in payload:
        raise ValueError(f"Commande invalide : colonnes inconnues {sorted(unknown)} ou order_id absent")
    if payload.get("order_date") is not None:
        payload["order_date"] = date.fromisoformat(payload["order_date"])
    return payload


def sequence_of(order_id: bytes) -> int:
    """ERP-00011001 -> 11001 ; 0 pour une clé d'un autre format."""
    text = order_id.decode()
    return int(text[4:]) if text.startswith("ERP-") and text[4:].isdigit() else 0
