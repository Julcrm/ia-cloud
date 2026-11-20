"""Point d'entrée du simulateur ERP Dockerisé."""

from __future__ import annotations

import logging

from config import SimulationConfig
from generator import OrderGenerator
from simulator import ErpSimulator
from storage import KafkaWriter


def main() -> None:
    config = SimulationConfig.from_environment()
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logger = logging.getLogger("erp_simulator")
    logger.info(
        "Démarrage ERP vers le topic %s : date=%s, ancien historique=%d, historique partagé 2023+=%d, live=%s.",
        config.kafka_topic,
        config.today,
        config.postgres_old_history_orders,
        config.recent_history_orders,
        "illimité" if config.live_order_limit == 0 else config.live_order_limit,
    )
    simulator = ErpSimulator(
        config,
        OrderGenerator(),
        KafkaWriter(config.kafka_bootstrap_servers, config.kafka_topic),
        logger,
    )
    simulator.run()


if __name__ == "__main__":
    main()
