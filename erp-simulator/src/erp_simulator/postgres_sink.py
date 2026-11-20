"""Consumer erp-postgres-sink : recopie le topic erp.orders dans la base de l'ERP.

Au moins une fois : l'offset n'est validé qu'après l'écriture, un message relu après un
plantage est ignoré par ON CONFLICT (order_id) DO NOTHING.
"""

from __future__ import annotations

import logging
import os
import signal
import time

from confluent_kafka import Consumer

from messages import decode
from storage import PostgresWriter


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logger = logging.getLogger("erp_postgres_sink")
    topic = os.getenv("KAFKA_TOPIC", "erp.orders")
    # 0 = tourne sans fin (prod) ; > 0 = s'arrête après ce silence (tests de bout en bout).
    idle_limit = float(os.getenv("STOP_AFTER_IDLE_SECONDS", "0"))

    writer = PostgresWriter(os.environ["POSTGRES_DSN"])
    consumer = Consumer({
        "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        "group.id": os.getenv("KAFKA_GROUP_ID", "erp-postgres-sink"),
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([topic])
    running = True

    def stop(*_args) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    logger.info("Lecture du topic %s vers PostgreSQL.", topic)
    last_activity = time.monotonic()
    try:
        while running:
            messages = consumer.consume(num_messages=500, timeout=1.0)
            for message in messages:
                if message.error():
                    raise RuntimeError(f"Erreur Redpanda : {message.error()}")
            if messages:
                inserted = writer.write([decode(message.value()) for message in messages])
                consumer.commit(asynchronous=False)
                logger.info("%d messages lus, %d nouvelles commandes.", len(messages), inserted)
                last_activity = time.monotonic()
            elif idle_limit and time.monotonic() - last_activity > idle_limit:
                logger.info("Aucun message depuis %.0f s : arrêt.", idle_limit)
                break
    finally:
        consumer.close()
        writer.close()


if __name__ == "__main__":
    main()
