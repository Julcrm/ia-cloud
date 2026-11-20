"""Format des commandes ERP dans le topic Redpanda (erp-simulator/src/erp_simulator/messages.py)."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "erp-simulator" / "src" / "erp_simulator"))
from generator import OrderGenerator  # noqa: E402
from messages import decode, encode, sequence_of  # noqa: E402


def test_round_trip_keeps_order_identical_including_dates_and_nulls():
    order = OrderGenerator.build(42, date(2015, 3, 1))  # avant les migrations : colonnes NULL
    key, value = encode(order)

    assert key == b"ERP-00000042"
    assert decode(value) == order


def test_decode_rejects_unknown_column():
    with pytest.raises(ValueError):
        decode(b'{"order_id": "ERP-00000001", "hour; DROP TABLE orders": 1}')


def test_sequence_of():
    assert sequence_of(b"ERP-00011001") == 11001
    assert sequence_of(b"autre") == 0
