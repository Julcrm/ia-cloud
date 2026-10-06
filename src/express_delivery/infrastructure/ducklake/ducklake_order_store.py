import threading
from pathlib import Path

import duckdb

from express_delivery.abstractions.order_store import OrderStore
from express_delivery.config import DUCKLAKE_CATALOG, DUCKLAKE_DATA_PATH, FEATURE_COLUMNS

COLUMNS = ["order_id", *FEATURE_COLUMNS]


class DuckLakeOrderStore(OrderStore):
    """Commandes dans DuckLake (ADR-0001).

    `orders_raw` ne reçoit que des INSERT : l'inlining range les petites
    insertions dans le catalogue au lieu de créer un fichier Parquet chacune.
    La vue `orders` ne garde que la première ligne reçue par order_id, car
    DuckLake n'a pas de contrainte d'unicité.
    """

    def __init__(self, catalog=DUCKLAKE_CATALOG, data_path=DUCKLAKE_DATA_PATH):
        self._create_local_dirs(catalog, data_path)

        self._connection = duckdb.connect()
        self._lock = threading.Lock()

        self._connection.execute("INSTALL ducklake; LOAD ducklake;")
        if catalog.startswith("ducklake:postgres:"):
            self._connection.execute("INSTALL postgres; LOAD postgres;")
        self._connection.execute(
            f"ATTACH '{catalog}' AS lake (DATA_PATH '{data_path}')"
        )
        self._connection.execute("CALL lake.set_option('data_inlining_row_limit', 1000)")
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS lake.orders_raw (
                order_id VARCHAR NOT NULL,
                received_at TIMESTAMP NOT NULL,
                hour INTEGER,
                day_of_week INTEGER,
                weekend INTEGER,
                distance_km DOUBLE,
                order_value_eur DOUBLE,
                weight_kg DOUBLE,
                stock_available INTEGER,
                preparation_time_min DOUBLE,
                carrier_capacity DOUBLE,
                weather VARCHAR,
                delivery_zone VARCHAR,
                customer_type VARCHAR
            )
        """)
        self._connection.execute("""
            CREATE VIEW IF NOT EXISTS lake.orders AS
            SELECT * FROM lake.orders_raw
            QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY received_at) = 1
        """)

    @staticmethod
    def _create_local_dirs(catalog, data_path):
        if catalog.startswith("ducklake:") and ":" not in catalog.removeprefix("ducklake:"):
            Path(catalog.removeprefix("ducklake:")).parent.mkdir(parents=True, exist_ok=True)
        if "://" not in data_path:
            Path(data_path).mkdir(parents=True, exist_ok=True)

    def add(self, order):
        placeholders = ", ".join("?" for _ in COLUMNS)
        with self._lock:
            self._connection.execute(
                f"INSERT INTO lake.orders_raw ({', '.join(COLUMNS)}, received_at) "
                f"VALUES ({placeholders}, now()::TIMESTAMP)",
                [order[column] for column in COLUMNS],
            )

    def get(self, order_id):
        with self._lock:
            row = self._connection.execute(
                f"SELECT {', '.join(COLUMNS)} FROM lake.orders WHERE order_id = ?",
                [order_id],
            ).fetchone()
        return dict(zip(COLUMNS, row)) if row else None

    def ping(self):
        with self._lock:
            self._connection.execute("SELECT 1 FROM lake.orders_raw LIMIT 1").fetchall()
