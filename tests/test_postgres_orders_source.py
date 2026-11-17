"""Traduction des commandes de l'ERP vers les données du modèle (ADR-0007)."""

import pandas as pd

from express_delivery.domain.data_quality import DataCleaner, DataValidator
from express_delivery.infrastructure.postgres.postgres_orders_source import PostgresOrdersSource


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

    orders = PostgresOrdersSource.to_model_orders(erp)

    assert orders["weather"].eq("pluie").all()
    assert orders["delivery_zone"].eq("banlieue").all()
    assert orders["customer_type"].eq("premium").all()
    assert orders["carrier_capacity"].eq(0.5).all()
    assert orders["weekend"].eq(1).all()
    assert orders["express_eligible"].isna().tolist() == [True, False, False]

    cleaned = DataCleaner.clean_orders_data(orders)
    assert cleaned["order_id"].tolist() == ["ERP-00000002", "ERP-00000003"]
    assert DataValidator.validate_dataset(cleaned)
