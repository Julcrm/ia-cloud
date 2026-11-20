"""Garde-fou de publication : un modèle moins bon que celui en service n'est pas publié."""

from sklearn.metrics import f1_score

from express_delivery.abstractions.model_repository import ModelRepository
from express_delivery.abstractions.model_trainer import ModelTrainer
from express_delivery.infrastructure.dev.synthetic_orders_source import SyntheticOrdersSource
from express_delivery.pipelines import TrainingPipeline


class Trainer(ModelTrainer):
    """Entraîne vraiment, mais peut annoncer un F1 imposé pour simuler un modèle moins bon."""

    def __init__(self, reported_f1=None):
        self.reported_f1 = reported_f1

    def train(self, model_pipeline, X_train, X_test, y_train, y_test):
        model_pipeline.fit(X_train, y_train)
        y_pred = model_pipeline.predict(X_test)
        f1 = f1_score(y_test, y_pred) if self.reported_f1 is None else self.reported_f1
        return {"f1_score": f1}, "run", y_pred


class InMemoryRepository(ModelRepository):
    def __init__(self):
        self.saved = []

    def save(self, model_pipeline, metrics, model_card):
        self.saved.append(model_pipeline)

    def load(self):
        if not self.saved:
            raise FileNotFoundError("aucun modèle")
        return self.saved[-1]

    def load_model_card(self):
        raise NotImplementedError

    def current_version(self):
        return str(len(self.saved))


def train(repository, reported_f1=None):
    return TrainingPipeline(SyntheticOrdersSource(), Trainer(reported_f1), repository).run()


def test_first_model_is_published():
    repository = InMemoryRepository()

    card = train(repository)

    assert card["promotion"] == {"published": True, "served_model_f1": None}
    assert len(repository.saved) == 1


def test_worse_model_is_not_published():
    repository = InMemoryRepository()
    train(repository)

    card = train(repository, reported_f1=0.0)

    assert card["promotion"]["published"] is False
    assert card["promotion"]["served_model_f1"] > 0
    assert len(repository.saved) == 1  # le modèle en service est conservé


def test_equal_model_is_published():
    repository = InMemoryRepository()
    train(repository)

    card = train(repository)  # mêmes données, même graine : même F1

    assert card["promotion"]["published"] is True
    assert len(repository.saved) == 2
