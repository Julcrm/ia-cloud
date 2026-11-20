import io
import json
from datetime import UTC, datetime

import boto3
import joblib
from botocore.config import Config

from express_delivery.abstractions.model_repository import ModelRepository
from express_delivery.config import (
    AWS_ACCESS_KEY_ID,
    AWS_DEFAULT_REGION,
    AWS_SECRET_ACCESS_KEY,
    FEATURE_COLUMNS,
    MODEL_S3_BUCKET,
    MODEL_VERSION,
    S3_ENDPOINT_URL,
)
from express_delivery.training_config import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
)

# Versionnage porté par les chemins ; current.json désigne la version servie (ADR-0002).
PREFIX = "models/express-delivery"
CURRENT_KEY = f"{PREFIX}/current.json"


class S3ModelRepository(ModelRepository):
    """Artefacts du modèle versionnés sur S3/Garage (ADR-0002).

    Un dossier de version n'est jamais réécrit. Changer de version ou revenir en
    arrière = réécrire current.json, sans redéployer. Même stockage que les données
    (ADR-0001), donc aucun service supplémentaire.
    """

    def __init__(self, client=None, bucket=MODEL_S3_BUCKET):
        self._client = client
        self._bucket = bucket

    @property
    def client(self):
        if self._client is None:
            # URL_STYLE path : Garage n'accepte pas le style hébergeur (bucket en sous-domaine).
            self._client = boto3.client(
                "s3",
                endpoint_url=S3_ENDPOINT_URL,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_DEFAULT_REGION,
                config=Config(s3={"addressing_style": "path"}),
            )
        return self._client

    def save(self, model_pipeline, metrics, model_card):
        # Un dossier par entraînement : current.json change, l'API recharge le nouveau modèle,
        # et les dossiers précédents restent disponibles pour un retour arrière.
        version_id = f"{MODEL_VERSION}-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}"
        version = f"{PREFIX}/{version_id}"

        buffer = io.BytesIO()
        joblib.dump(model_pipeline, buffer)
        self._put(f"{version}/express_delivery_model.joblib", buffer.getvalue())

        self._put_json(f"{version}/metrics.json", metrics)
        self._put_json(
            f"{version}/features.json",
            {
                "model_version": MODEL_VERSION,
                "target": TARGET_COLUMN,
                "features": FEATURE_COLUMNS,
                "numeric_features": NUMERIC_FEATURES,
                "categorical_features": CATEGORICAL_FEATURES,
            },
        )
        # La fiche porte l'id du dossier : c'est lui qui identifie le modèle servi.
        self._put_json(f"{version}/model_card.json", {**model_card, "model_version": version_id})

        # En dernier : la version n'est servie qu'une fois tous ses fichiers écrits.
        self._put_json(CURRENT_KEY, {"version": version_id})
        print(f"Modèle sauvegardé sur s3://{self._bucket}/{version}/")

    def load(self):
        version = self._current_prefix()
        self._check_features(version)
        return joblib.load(io.BytesIO(self._get(f"{version}/express_delivery_model.joblib")))

    def load_model_card(self):
        return self._get_json(f"{self._current_prefix()}/model_card.json")

    def current_version(self):
        return self._get_json(CURRENT_KEY)["version"]

    def _current_prefix(self):
        return f"{PREFIX}/{self.current_version()}"

    def _check_features(self, version):
        """Refuse un modèle entraîné sur d'autres variables que celles du code."""
        saved_features = self._get_json(f"{version}/features.json")["features"]
        if saved_features != FEATURE_COLUMNS:
            raise ValueError(
                f"Le modèle sauvegardé attend les variables {saved_features}, "
                f"le code fournit {FEATURE_COLUMNS}. Réentraîner le modèle."
            )

    def _put(self, key, body):
        self.client.put_object(Bucket=self._bucket, Key=key, Body=body)

    def _put_json(self, key, value):
        self._put(key, json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8"))

    def _get(self, key):
        return self.client.get_object(Bucket=self._bucket, Key=key)["Body"].read()

    def _get_json(self, key):
        return json.loads(self._get(key))
