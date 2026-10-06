"""Qualité des données : règles de bornes, validation et nettoyage (cellules 14 et 18)."""

from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class DataRule:
    column: str
    is_valid: Callable[[pd.Series], pd.Series]
    error_message: str

    def valid_rows(self, df):
        return self.is_valid(df[self.column])


DATA_RULES = (
    DataRule(
        "distance_km",
        lambda values: values.ge(0),
        "La distance ne peut pas être négative.",
    ),
    DataRule(
        "weight_kg",
        lambda values: values.ge(0),
        "Le poids ne peut pas être négatif.",
    ),
    DataRule(
        "preparation_time_min",
        lambda values: values.ge(0),
        "Le temps de préparation ne peut pas être négatif.",
    ),
    DataRule(
        "carrier_capacity",
        lambda values: values.between(0, 1),
        "La capacité du transporteur doit être comprise entre 0 et 1.",
    ),
    DataRule(
        "stock_available",
        lambda values: values.isin([0, 1]),
        "La variable stock_available doit contenir uniquement 0 ou 1.",
    ),
)


class DataValidator:
    """Contrôles de qualité des données d'entrée (cellule 14)."""

    @staticmethod
    def validate_dataset(df):
        """
        Contrôles de qualité élémentaires sur les données d'entrée.
        """
        required_columns = {
            "order_id",
            "order_date",
            "hour",
            "day_of_week",
            "weekend",
            "distance_km",
            "order_value_eur",
            "weight_kg",
            "stock_available",
            "preparation_time_min",
            "carrier_capacity",
            "weather",
            "delivery_zone",
            "customer_type",
            "express_eligible",
        }

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"Colonnes obligatoires absentes : {sorted(missing_columns)}"
            )

        if df["order_id"].duplicated().any():
            raise ValueError("Des identifiants de commande sont dupliqués.")

        if df["express_eligible"].isna().any():
            raise ValueError("La variable cible contient des valeurs manquantes.")

        if not df["hour"].between(0, 23).all():
            raise ValueError("Certaines heures sont invalides.")

        for rule in DATA_RULES:
            if not rule.valid_rows(df).all():
                raise ValueError(rule.error_message)

        return True


class DataCleaner:
    """Nettoyage automatique des données (cellule 18)."""

    @staticmethod
    def clean_orders_data(df):
        """
        Nettoyage automatique des données.
        """
        cleaned = df.copy()

        # Suppression des doublons sur l'identifiant métier
        cleaned = cleaned.drop_duplicates(
            subset=["order_id"],
            keep="last"
        )

        # Conversion des dates
        cleaned["order_date"] = pd.to_datetime(
            cleaned["order_date"],
            errors="coerce"
        )

        # Suppression des lignes dont les champs essentiels sont invalides
        essential_columns = [
            "order_id",
            "distance_km",
            "weight_kg",
            "stock_available",
            "preparation_time_min",
            "carrier_capacity",
            "express_eligible",
        ]

        cleaned = cleaned.dropna(subset=essential_columns)

        # Bornage des valeurs numériques
        for rule in DATA_RULES:
            cleaned = cleaned[rule.valid_rows(cleaned)]

        return cleaned.reset_index(drop=True)
