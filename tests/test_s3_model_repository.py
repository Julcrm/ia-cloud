import io
import json

import pytest

from express_delivery.config import FEATURE_COLUMNS, MODEL_VERSION
from express_delivery.infrastructure.s3.s3_model_repository import (
    CURRENT_KEY,
    PREFIX,
    S3ModelRepository,
)


class FakeS3:
    """S3 en mémoire : juste put_object / get_object, comme boto3."""

    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body):
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}


def test_save_puts_versioned_files_and_current_pointer():
    repo = S3ModelRepository(client=FakeS3(), bucket="artifacts")

    repo.save({"model": "stub"}, {"accuracy": 0.9}, {"name": "card"})

    keys = {key for _, key in repo.client.objects}
    assert repo.current_version().startswith(f"{MODEL_VERSION}-")
    version = f"{PREFIX}/{repo.current_version()}"
    assert keys == {
        f"{version}/express_delivery_model.joblib",
        f"{version}/metrics.json",
        f"{version}/features.json",
        f"{version}/model_card.json",
        CURRENT_KEY,
    }


def test_load_round_trips_the_model_pointed_by_current():
    repo = S3ModelRepository(client=FakeS3(), bucket="artifacts")
    repo.save({"model": "stub"}, {"accuracy": 0.9}, {"name": "card"})

    assert repo.load() == {"model": "stub"}
    assert repo.load_model_card() == {"name": "card", "model_version": repo.current_version()}


def test_load_refuses_a_model_trained_on_other_features():
    client = FakeS3()
    repo = S3ModelRepository(client=client, bucket="artifacts")
    repo.save({"model": "stub"}, {}, {})

    # features.json figé sur d'autres variables que celles du code.
    client.objects[("artifacts", f"{PREFIX}/{repo.current_version()}/features.json")] = json.dumps(
        {"features": FEATURE_COLUMNS[:-1]}
    ).encode()

    with pytest.raises(ValueError, match="Réentraîner"):
        repo.load()


def test_each_training_gets_its_own_folder_and_moves_current():
    repo = S3ModelRepository(client=FakeS3(), bucket="artifacts")
    repo.save({"model": "first"}, {}, {"name": "first"})
    first = repo.current_version()

    repo.save({"model": "second"}, {}, {"name": "second"})

    # current.json change : l'API voit le réentraînement et recharge le modèle.
    assert repo.current_version() != first
    assert repo.load() == {"model": "second"}
    # L'ancien dossier reste intact : retour arrière = réécrire current.json.
    repo._put_json(CURRENT_KEY, {"version": first})
    assert repo.load() == {"model": "first"}
