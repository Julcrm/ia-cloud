"""Adaptateurs de persistance du simulateur ERP."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

import psycopg
from confluent_kafka import Consumer, Producer, TopicPartition
from psycopg.rows import dict_row

from messages import encode, sequence_of


Order = dict[str, object]


class OrderWriter(Protocol):
    def write(self, orders: Sequence[Order]) -> int:
        """Écrit les commandes et renvoie le nombre de nouvelles commandes."""

    def close(self) -> None:
        """Libère les ressources de connexion."""


@runtime_checkable
class SequenceSource(Protocol):
    def next_sequence(self) -> int:
        """Retourne le plus grand numéro de commande déjà écrit (0 si aucun)."""


@runtime_checkable
class OrderCounter(SequenceSource, Protocol):
    def count_from(self, start: date, end: date) -> int:
        """Compte les commandes sur une période."""


class KafkaWriter:
    """Publie les commandes dans le topic Redpanda ; un consumer par base les recopie."""

    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self.topic = topic
        self.brokers = {"bootstrap.servers": bootstrap_servers}
        # Idempotence : pas de doublon dans le topic si le producteur réessaie un envoi.
        self.producer = Producer({**self.brokers, "enable.idempotence": True})

    def write(self, orders: Sequence[Order]) -> int:
        errors = []

        def on_delivery(error, _message) -> None:
            if error:
                errors.append(error)

        for order in orders:
            key, value = encode(order)
            self.producer.produce(self.topic, key=key, value=value, on_delivery=on_delivery)
            self.producer.poll(0)
        remaining = self.producer.flush(60)
        if errors or remaining:
            raise RuntimeError(
                f"Publication incomplète : {len(errors)} erreurs, {remaining} en attente ({errors[:1]})"
            )
        return len(orders)

    def next_sequence(self) -> int:
        # Chaque partition reçoit des numéros croissants : le plus grand est le dernier d'une partition.
        consumer = Consumer({**self.brokers, "group.id": "erp-simulator", "enable.auto.commit": False})
        try:
            partitions = consumer.list_topics(self.topic, timeout=10).topics[self.topic].partitions
            last = 0
            for partition in partitions:
                low, high = consumer.get_watermark_offsets(
                    TopicPartition(self.topic, partition), timeout=10
                )
                if high <= low:
                    continue
                consumer.assign([TopicPartition(self.topic, partition, high - 1)])
                message = consumer.poll(10)
                if message is None or message.error():
                    raise RuntimeError(f"Dernier message illisible (partition {partition})")
                last = max(last, sequence_of(message.key()))
            return last
        finally:
            consumer.close()

    def close(self) -> None:
        self.producer.flush(60)


class PostgresWriter:
    def __init__(self, dsn: str) -> None:
        self.connection = psycopg.connect(dsn, row_factory=dict_row)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY, order_date DATE, hour INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL, weekend INTEGER,
            distance_km DOUBLE PRECISION NOT NULL, order_value_eur DOUBLE PRECISION NOT NULL,
            weight_kg DOUBLE PRECISION NOT NULL, stock_available INTEGER NOT NULL,
            preparation_time_min DOUBLE PRECISION, carrier_capacity DOUBLE PRECISION NOT NULL,
            weather TEXT NOT NULL, delivery_zone TEXT NOT NULL, customer_type TEXT NOT NULL)"""
        )
        self.connection.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_date DATE")
        self.connection.execute("ALTER TABLE orders ALTER COLUMN weekend DROP NOT NULL")
        self.connection.execute(
            "ALTER TABLE orders ALTER COLUMN preparation_time_min DROP NOT NULL"
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description TEXT NOT NULL)"""
        )
        self.connection.execute(
            """INSERT INTO schema_migrations (version, description) VALUES
            (2015, 'Ajout de la colonne weekend'),
            (2017, 'Ajout de la colonne preparation_time_min'),
            (2023, 'Extension du schéma pour le flux courant')
            ON CONFLICT (version) DO NOTHING"""
        )
        self.connection.commit()

    def write(self, orders: Sequence[Order]) -> int:
        inserted = 0
        with self.connection.transaction():
            for order in orders:
                columns = tuple(order)
                cursor = self.connection.execute(
                    f"INSERT INTO orders ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))}) ON CONFLICT (order_id) DO NOTHING",
                    tuple(order[column] for column in columns),
                )
                inserted += cursor.rowcount
        self.connection.commit()
        return inserted

    def count_from(self, start: date, end: date) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM orders WHERE order_date >= %s AND order_date < %s",
            (start, end),
        ).fetchone()
        self.connection.commit()
        return int(row["count"])

    def next_sequence(self) -> int:
        row = self.connection.execute(
            """SELECT COALESCE(MAX(
                CASE WHEN order_id ~ '^ERP-[0-9]+$'
                THEN SUBSTRING(order_id FROM 5)::BIGINT ELSE 0 END
            ), 0) AS max_sequence FROM orders"""
        ).fetchone()
        self.connection.commit()
        return int(row["max_sequence"])

    def close(self) -> None:
        self.connection.close()
