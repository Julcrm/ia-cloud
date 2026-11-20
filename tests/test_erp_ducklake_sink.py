"""Copie du topic erp.orders dans DuckLake : table erp_orders et boucle du consumer."""

import json
from datetime import date

import pytest

from express_delivery.infrastructure.ducklake.ducklake_erp_order_store import DuckLakeErpOrderStore
from express_delivery.infrastructure.redpanda.erp_orders_consumer import decode, run


def erp_order(sequence, **changes):
    return {
        "order_id": f"ERP-{sequence:08d}",
        "order_date": "2015-03-01",
        "hour": 9,
        "day_of_week": 6,
        "weekend": None,
        "distance_km": 12.5,
        "order_value_eur": 80.0,
        "weight_kg": 3.2,
        "stock_available": 1,
        "preparation_time_min": None,
        "carrier_capacity": 30.0,
        "weather": "rain",
        "delivery_zone": "suburb",
        "customer_type": "business",
        **changes,
    }


@pytest.fixture
def store(tmp_path):
    return DuckLakeErpOrderStore(f"ducklake:{tmp_path}/catalog.ducklake", f"{tmp_path}/lake/")


def test_add_many_keeps_one_row_per_order_id(store):
    assert store.add_many([erp_order(1), erp_order(2), erp_order(2)]) == 2
    # Relecture du topic après un plantage : rien n'est ajouté deux fois.
    assert store.add_many([erp_order(2), erp_order(3)]) == 1
    assert store.count() == 3

    row = store._connection.execute(
        "SELECT order_date, weekend, weather FROM lake.erp_orders WHERE order_id = 'ERP-00000001'"
    ).fetchone()
    assert row == (date(2015, 3, 1), None, "rain")  # format de l'ERP, sans traduction


def test_decode_rejects_invalid_messages():
    assert decode(json.dumps(erp_order(1)).encode())["order_id"] == "ERP-00000001"
    assert decode(b"pas du json") is None
    assert decode(json.dumps({"hour": 9}).encode()) is None
    assert decode(json.dumps(erp_order(1, extra=1)).encode()) is None


class FakeMessage:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value

    def error(self):
        return None


class FakeConsumer:
    def __init__(self, batches):
        self.batches = list(batches)
        self.commits = 0

    def consume(self, num_messages, timeout):
        return self.batches.pop(0) if self.batches else []

    def commit(self, asynchronous):
        self.commits += 1


def test_run_skips_invalid_messages_and_commits_after_writing(store):
    consumer = FakeConsumer(
        [[FakeMessage(json.dumps(erp_order(1)).encode()), FakeMessage(b"invalide")]]
    )

    run(store, consumer, idle_limit=0.01)

    assert store.count() == 1
    assert consumer.commits == 1
