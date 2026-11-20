from express_delivery.config import DUCKLAKE_CATALOG, DUCKLAKE_DATA_PATH
from express_delivery.infrastructure.ducklake.ducklake_order_store import connect_lake

# Format de l'ERP (topic erp.orders), sans traduction : celle-ci reste à l'entraînement (ADR-0007).
ERP_COLUMNS = [
    "order_id",
    "order_date",
    "hour",
    "day_of_week",
    "weekend",
    "distance_km",
    "order_value_eur",
    "weight_kg",
    "stock_available",
    "preparation_time_min",
    "carrier_capacity",
    "weather",
    "delivery_zone",
    "customer_type",
]
_SCHEMA = """
    order_id VARCHAR NOT NULL, order_date DATE, hour INTEGER, day_of_week INTEGER,
    weekend INTEGER, distance_km DOUBLE, order_value_eur DOUBLE, weight_kg DOUBLE,
    stock_available INTEGER, preparation_time_min DOUBLE, carrier_capacity DOUBLE,
    weather VARCHAR, delivery_zone VARCHAR, customer_type VARCHAR
"""


class DuckLakeErpOrderStore:
    """Copie des commandes de l'ERP dans DuckLake (table `erp_orders`), alimentée par le topic.

    shortcut: l'unicité de order_id repose sur l'anti-jointure à l'insertion, valable avec un
    seul consumer qui écrit ; passer à une vue dédoublonnée (comme `orders`) s'il y en a plusieurs.
    """

    def __init__(self, catalog=DUCKLAKE_CATALOG, data_path=DUCKLAKE_DATA_PATH):
        self._connection = connect_lake(catalog, data_path)
        self._connection.execute(
            f"CREATE TABLE IF NOT EXISTS lake.erp_orders "
            f"({_SCHEMA}, ingested_at TIMESTAMP NOT NULL)"
        )
        self._connection.execute(f"CREATE TEMP TABLE erp_batch ({_SCHEMA})")

    def add_many(self, orders):
        """Ajoute les commandes absentes, renvoie le nombre de nouvelles lignes."""
        columns = ", ".join(ERP_COLUMNS)
        self._connection.execute("DELETE FROM erp_batch")
        self._connection.executemany(
            f"INSERT INTO erp_batch ({columns}) VALUES ({', '.join('?' for _ in ERP_COLUMNS)})",
            [[order.get(column) for column in ERP_COLUMNS] for order in orders],
        )
        # Une seule instruction : un snapshot DuckLake par lot.
        return self._connection.execute(f"""
            INSERT INTO lake.erp_orders ({columns}, ingested_at)
            SELECT {columns}, now()::TIMESTAMP
            FROM (SELECT DISTINCT ON (order_id) * FROM erp_batch) AS batch
            WHERE order_id NOT IN (SELECT order_id FROM lake.erp_orders)
        """).fetchone()[0]

    def count(self):
        return self._connection.execute("SELECT count(*) FROM lake.erp_orders").fetchone()[0]
