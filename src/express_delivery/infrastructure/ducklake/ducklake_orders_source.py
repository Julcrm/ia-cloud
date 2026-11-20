import numpy as np

from express_delivery.abstractions.orders_source import OrdersSource
from express_delivery.config import DUCKLAKE_CATALOG, DUCKLAKE_DATA_PATH, RANDOM_STATE
from express_delivery.infrastructure.dev.synthetic_orders_source import (
    simulate_express_eligibility,
)
from express_delivery.infrastructure.ducklake.ducklake_order_store import connect_lake

# Vocabulaire de l'ERP -> vocabulaire du modèle et de openapi.yml (ADR-0007).
WEATHER = {"clear": "normal", "rain": "pluie", "snow": "neige", "wind": "orage"}
DELIVERY_ZONE = {"centre": "centre", "suburb": "banlieue", "rural": "rurale"}
CUSTOMER_TYPE = {"individual": "standard", "business": "premium"}
# L'ERP exprime la capacité du transporteur entre 5 et 50 ; le modèle l'attend entre 0 et 1.
ERP_MAX_CARRIER_CAPACITY = 50


class DuckLakeOrdersSource(OrdersSource):
    """Commandes de l'ERP copiées dans DuckLake (table erp_orders, alimentée par le topic).

    Lecture sur un snapshot figé : la fiche du modèle le note, et le même snapshot redonne
    exactement les mêmes données pour rejouer un entraînement.
    """

    def __init__(self, snapshot_id=None, catalog=DUCKLAKE_CATALOG, data_path=DUCKLAKE_DATA_PATH):
        self.snapshot_id = snapshot_id  # None : dernier snapshot au moment de load()
        self.catalog = catalog
        self.data_path = data_path

    def load(self):
        connection = connect_lake(self.catalog, self.data_path)
        try:
            if self.snapshot_id is None:
                self.snapshot_id = connection.execute(
                    "SELECT max(snapshot_id) FROM ducklake_snapshots('lake')"
                ).fetchone()[0]
            # ORDER BY : même ordre à chaque lecture, donc même cible simulée.
            orders = connection.execute(
                "SELECT * EXCLUDE (ingested_at) FROM lake.erp_orders AT (VERSION => ?) "
                "ORDER BY order_id",
                [self.snapshot_id],
            ).df()
        finally:
            connection.close()
        return self.to_model_orders(orders)

    def describe(self):
        return {"source": "ducklake:erp_orders", "ducklake_snapshot_id": self.snapshot_id}

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
