"""Préparation, construction, évaluation et résumé du modèle (cellules 20 à 29 et 55)."""

import json

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from express_delivery.config import (
    DEFAULT_THRESHOLD,
    FEATURE_COLUMNS,
    MODEL_VERSION,
    PROJECT_NAME,
    RANDOM_STATE,
)
from express_delivery.training_config import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
)


class FeatureSelector:
    """Sélection des variables et séparation entraînement/test (cellules 20 et 22)."""

    def select(self, orders_clean):
        X = orders_clean[FEATURE_COLUMNS]
        y = orders_clean[TARGET_COLUMN]

        print("Variables numériques :", NUMERIC_FEATURES)
        print("Variables catégorielles :", CATEGORICAL_FEATURES)

        return X, y

    def split(self, X, y):
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=RANDOM_STATE,
            stratify=y
        )

        print(f"Jeu d'entraînement : {len(X_train):,} lignes")
        print(f"Jeu de test : {len(X_test):,} lignes")

        return X_train, X_test, y_train, y_test


class ModelPipelineFactory:
    """Construction de la pipeline de machine learning (cellule 24)."""

    def create(self):
        numeric_transformer = Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(strategy="median")
                ),
                (
                    "scaler",
                    StandardScaler()
                ),
            ]
        )

        categorical_transformer = Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(strategy="most_frequent")
                ),
                (
                    "onehot",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False
                    )
                ),
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "numeric",
                    numeric_transformer,
                    NUMERIC_FEATURES
                ),
                (
                    "categorical",
                    categorical_transformer,
                    CATEGORICAL_FEATURES
                ),
            ]
        )

        classifier = LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_STATE
        )

        model_pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("classifier", classifier),
            ]
        )

        print(model_pipeline)

        return model_pipeline


class ModelEvaluator:
    """Affichage des performances du modèle (cellules 28 et 29)."""

    def print_metrics(self, metrics):
        print("Métriques du modèle :")

        for metric_name, metric_value in metrics.items():
            print(f"{metric_name:>10} : {metric_value:.4f}")

    def print_report(self, y_test, y_pred):
        print(
            classification_report(
                y_test,
                y_pred,
                target_names=["Non éligible", "Éligible"],
                zero_division=0
            )
        )


class ModelCardBuilder:
    """Résumé du modèle entraîné (cellule 55)."""

    def build(self, metrics, X_train, X_test):
        model_card = {
            "project": PROJECT_NAME,
            "model_version": MODEL_VERSION,
            "model_type": "Régression logistique",
            "task": "Classification binaire",
            "target": TARGET_COLUMN,
            "positive_class": "Commande éligible à la livraison express",
            "negative_class": "Commande non éligible à la livraison express",
            "features": FEATURE_COLUMNS,
            "threshold": DEFAULT_THRESHOLD,
            "training_rows": len(X_train),
            "test_rows": len(X_test),
            "metrics": metrics,
            "limitations": [
                "Le jeu de données utilisé est synthétique.",
                "La décision ne doit pas être utilisée sans validation des règles métier.",
                "Les performances peuvent varier sur des données réelles.",
                "Le modèle ne remplace pas une analyse des contraintes opérationnelles.",
            ],
        }

        print(json.dumps(model_card, indent=2, ensure_ascii=False))

        return model_card
