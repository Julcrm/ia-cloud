import duckdb
import numpy as np

from express_delivery.abstractions.orders_source import OrdersSource
from express_delivery.config import (
    ERP_POSTGRES_DB,
    ERP_POSTGRES_HOST,
    ERP_POSTGRES_PASSWORD,
    ERP_POSTGRES_PORT,
    ERP_POSTGRES_USER,
    RANDOM_STATE,
)
from express_delivery.infrastructure.dev.synthetic_orders_source import (
    simulate_express_eligibility,
)
from express_delivery.infrastructure.ducklake.ducklake_order_store import sql_literal

# Vocabulaire de l'ERP -> vocabulaire du modèle et de openapi.yml.
WEATHER = {"clear": "normal", "rain": "pluie", "snow": "neige", "wind": "orage"}
DELIVERY_ZONE = {"centre": "centre", "suburb": "banlieue", "rural": "rurale"}
CUSTOMER_TYPE = {"individual": "standard", "business": "premium"}
# L'ERP exprime la capacité du transporteur entre 5 et 50 ; le modèle l'attend entre 0 et 1.
ERP_MAX_CARRIER_CAPACITY = 50


class PostgresOrdersSource(OrdersSource):
    """Commandes de l'ERP, lues dans sa base PostgreSQL (ADR-0007).

    Lecture seule. Les identifiants passent par un secret DuckDB, comme pour DuckLake.
    """

    def load(self):
        connection = duckdb.connect()
        connection.execute("INSTALL postgres; LOAD postgres;")
        connection.execute(f"""
            CREATE SECRET erp (
                TYPE postgres, HOST {sql_literal(ERP_POSTGRES_HOST)}, PORT {ERP_POSTGRES_PORT},
                DATABASE {sql_literal(ERP_POSTGRES_DB)}, USER {sql_literal(ERP_POSTGRES_USER)},
                PASSWORD {sql_literal(ERP_POSTGRES_PASSWORD)}
            )
        """)
        connection.execute("ATTACH '' AS erp (TYPE postgres, SECRET erp, READ_ONLY)")
        # ORDER BY : même ordre à chaque lecture, donc même cible simulée.
        orders = connection.execute("SELECT * FROM erp.public.orders ORDER BY order_id").df()
        connection.close()
        return self.to_model_orders(orders)

    @staticmethod
    def to_model_orders(orders):
        orders = orders.copy()
        orders["weather"] = orders["weather"].map(WEATHER)
        orders["delivery_zone"] = orders["delivery_zone"].map(DELIVERY_ZONE)
        orders["customer_type"] = orders["customer_type"].map(CUSTOMER_TYPE)
        orders["carrier_capacity"] = orders["carrier_capacity"] / ERP_MAX_CARRIER_CAPACITY
        # weekend n'existe pas avant juillet 2015, mais se déduit du jour de la semaine.
        orders["weekend"] = orders["weekend"].fillna((orders["day_of_week"] >= 5).astype(int))

        # Pas de cible sans preparation_time_min (avant juillet 2017) : DataCleaner les écarte.
        known = orders["preparation_time_min"].notna()
        orders["express_eligible"] = np.nan
        orders.loc[known, "express_eligible"] = simulate_express_eligibility(
            orders[known], np.random.default_rng(RANDOM_STATE)
        )
        return orders
