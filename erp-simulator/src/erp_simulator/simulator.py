"""Orchestration du scénario ERP."""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta

from config import SimulationConfig
from generator import OrderGenerator
from storage import OrderCounter, OrderWriter, SequenceSource


class ErpSimulator:
    def __init__(
        self,
        config: SimulationConfig,
        generator: OrderGenerator,
        writer: OrderWriter,
        logger: logging.Logger,
    ) -> None:
        self.config = config
        self.generator = generator
        self.writer = writer
        self.logger = logger

    def run(self) -> None:
        try:
            # Lu avant tout envoi : au redémarrage, on reprend après la dernière commande écrite.
            last = self.writer.next_sequence() if isinstance(self.writer, SequenceSource) else 0
            history = self.config.postgres_old_history_orders + self.config.recent_history_orders
            if last < history:
                self._write_history()
            else:
                self.logger.info("Historique déjà écrit (dernière commande ERP-%08d).", last)
            self._write_live_stream(last)
        finally:
            self.writer.close()
            self.logger.info("Connexion fermée.")

    def _write_history(self) -> None:
        old_count = self.config.postgres_old_history_orders
        recent_count = self.config.recent_history_orders
        old_orders = self.generator.old_history(old_count, self.config.today, first_sequence=1)
        self.logger.info("Ancien historique : %d commandes.", self.writer.write(old_orders))

        recent_orders = self.generator.recent_history(
            recent_count, self.config.today, first_sequence=old_count + 1
        )
        self.logger.info(
            "Historique partagé 2023+ : %d commandes.", self.writer.write(recent_orders)
        )

        if isinstance(self.writer, OrderCounter):
            count = self.writer.count_from(date(2023, 1, 1), self.config.today)
            self.logger.info("%d commandes présentes depuis 2023.", count)

    def _write_live_stream(self, last: int) -> None:
        minimum_sequence = (
            self.config.postgres_old_history_orders + self.config.recent_history_orders + 1
        )
        sequence = max(minimum_sequence, last + 1)
        self.logger.info("Prochaine séquence live : ERP-%08d.", sequence)
        simulation_date = self.config.today
        while self.config.live_order_limit == 0 or sequence <= self.config.live_order_limit:
            size = self._next_batch_size(sequence)
            orders = self.generator.live_batch(sequence, size, simulation_date)
            written = self.writer.write(orders)
            self.logger.info(
                "Lot live : %d commandes, date=%s, dernière commande=%s.",
                written,
                orders[-1]["order_date"],
                orders[-1]["order_id"],
            )
            if isinstance(self.writer, OrderCounter):
                next_day = simulation_date + timedelta(days=1)
                count = self.writer.count_from(simulation_date, next_day)
                self.logger.info(
                    "%d commandes présentes pour la date live %s.", count, simulation_date
                )
            sequence += size
            simulation_date += timedelta(days=1)
            time.sleep(self.config.interval_seconds)
        self.logger.info("Flux live terminé : limite LIVE_ORDER_LIMIT atteinte.")

    def _next_batch_size(self, sequence: int) -> int:
        remaining = self.config.live_order_limit - sequence + 1
        return (
            min(self.config.batch_size, remaining)
            if self.config.live_order_limit
            else self.config.batch_size
        )
