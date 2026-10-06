from express_delivery.abstractions.predictions_writer import PredictionsWriter
from express_delivery.config import PREDICTIONS_PATH


class CsvPredictionsWriter(PredictionsWriter):
    """Prédictions batch écrites dans un fichier CSV (cellule 50)."""

    def export(self, batch_predictions):
        batch_predictions.to_csv(
            PREDICTIONS_PATH,
            index=False
        )

        print(f"Résultats batch sauvegardés dans : {PREDICTIONS_PATH}")
