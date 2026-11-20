"""Consumer ia-cloud-ducklake-sink : copie le topic erp.orders dans DuckLake (table erp_orders).

Au moins une fois : l'offset n'est validé qu'après l'écriture, une commande relue après un
plantage est ignorée car déjà présente.
    python -m express_delivery.infrastructure.redpanda.erp_orders_consumer
"""

import json
import logging
import os
import signal
import time

from confluent_kafka import Consumer

from express_delivery.config import ERP_ORDERS_TOPIC, KAFKA_BOOTSTRAP_SERVERS
from express_delivery.infrastructure.ducklake.ducklake_erp_order_store import (
    ERP_COLUMNS,
    DuckLakeErpOrderStore,
)

logger = logging.getLogger("erp_ducklake_sink")


def decode(value):
    """Commande de l'ERP, ou None si le message est invalide (topic non authentifié)."""
    try:
        order = json.loads(value)
    except (TypeError, ValueError):
        return None
    if not isinstance(order, dict) or not order.get("order_id") or set(order) - set(ERP_COLUMNS):
        return None
    return order


def run(store, consumer, idle_limit=0.0):
    """Boucle de copie ; idle_limit > 0 : s'arrête après ce silence (tests de bout en bout)."""
    running = True

    def stop(*_args):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    last_activity = time.monotonic()
    while running:
        messages = consumer.consume(num_messages=500, timeout=1.0)
        for message in messages:
            if message.error():
                raise RuntimeError(f"Erreur Redpanda : {message.error()}")
        if not messages:
            if idle_limit and time.monotonic() - last_activity > idle_limit:
                logger.info("Aucun message depuis %.0f s : arrêt.", idle_limit)
                return
            continue
        orders = [decode(message.value()) for message in messages]
        valid = [order for order in orders if order is not None]
        if len(valid) < len(orders):
            # Ignoré plutôt que bloquant : sinon il ferait planter le consumer en boucle.
            logger.error("%d messages invalides ignorés.", len(orders) - len(valid))
        inserted = store.add_many(valid) if valid else 0
        consumer.commit(asynchronous=False)
        logger.info("%d messages lus, %d nouvelles commandes.", len(messages), inserted)
        last_activity = time.monotonic()


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    store = DuckLakeErpOrderStore()
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": os.environ.get("KAFKA_GROUP_ID", "ia-cloud-ducklake-sink"),
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([ERP_ORDERS_TOPIC])
    logger.info(
        "Lecture du topic %s vers DuckLake (%d commandes).", ERP_ORDERS_TOPIC, store.count()
    )
    try:
        run(store, consumer, float(os.environ.get("STOP_AFTER_IDLE_SECONDS", "0")))
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
