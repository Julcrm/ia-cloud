"""Entraînement sur les commandes de l'ERP copiées dans DuckLake (table erp_orders)."""

import pandas as pd

from express_delivery.domain.data_quality import DataCleaner, DataValidator
from express_delivery.infrastructure.ducklake.ducklake_erp_order_store import DuckLakeErpOrderStore
from express_delivery.infrastructure.ducklake.ducklake_orders_source import DuckLakeOrdersSource


def erp_order(order_id, weekend, preparation_time_min):
    return {
        "order_id": order_id,
        "order_date": pd.Timestamp("2016-01-02"),
        "hour": 10,
        "day_of_week": 5,
        "weekend": weekend,
        "distance_km": 3.0,
        "order_value_eur": 50.0,
        "weight_kg": 2.0,
        "stock_available": 1,
        "preparation_time_min": preparation_time_min,
        "carrier_capacity": 25.0,
        "weather": "rain",
        "delivery_zone": "suburb",
        "customer_type": "business",
    }


def test_erp_orders_are_translated_and_labelled():
    erp = pd.DataFrame(
        [
            erp_order("ERP-00000001", None, None),  # avant les migrations de 2015 et 2017
            erp_order("ERP-00000002", None, 20.0),
            erp_order("ERP-00000003", 1, 20.0),
        ]
    )

    orders = DuckLakeOrdersSource.to_model_orders(erp)

    assert orders["weather"].eq("pluie").all()
    assert orders["delivery_zone"].eq("banlieue").all()
    assert orders["customer_type"].eq("premium").all()
    assert orders["carrier_capacity"].eq(0.5).all()
    assert orders["weekend"].eq(1).all()
    assert orders["express_eligible"].isna().tolist() == [True, False, False]

    cleaned = DataCleaner.clean_orders_data(orders)
    assert cleaned["order_id"].tolist() == ["ERP-00000002", "ERP-00000003"]
    assert DataValidator.validate_dataset(cleaned)


def write(lake, orders):
    store = DuckLakeErpOrderStore(*lake)
    store.add_many(orders)
    store._connection.close()  # un seul processus à la fois sur un catalogue local


def test_snapshot_pins_the_training_data(tmp_path):
    lake = (f"ducklake:{tmp_path}/catalog.ducklake", f"{tmp_path}/lake/")
    write(lake, [erp_order("ERP-00000001", 1, 20.0), erp_order("ERP-00000002", 1, 20.0)])
    first = DuckLakeOrdersSource(None, *lake)
    assert len(first.load()) == 2
    snapshot = first.describe()["ducklake_snapshot_id"]

    write(lake, [erp_order("ERP-00000003", 1, 20.0)])

    assert len(DuckLakeOrdersSource(None, *lake).load()) == 3
    # Rejouer l'entraînement sur l'ancien snapshot redonne exactement ses données.
    replay = DuckLakeOrdersSource(snapshot, *lake).load()
    assert replay["order_id"].tolist() == ["ERP-00000001", "ERP-00000002"]
