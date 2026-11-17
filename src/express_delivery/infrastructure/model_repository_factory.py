from express_delivery.config import MODEL_S3_BUCKET
from express_delivery.infrastructure.dev.file_model_repository import FileModelRepository
from express_delivery.infrastructure.s3.s3_model_repository import S3ModelRepository


def build_model_repository():
    """S3/Garage en production (ADR-0002), fichiers locaux sinon."""
    return S3ModelRepository() if MODEL_S3_BUCKET else FileModelRepository()
