"""La code location Dagster se charge, avec son job et son planning de réentraînement."""

from dagster import Definitions

from express_delivery.orchestration.definitions import defs


def test_definitions_load():
    Definitions.validate_loadable(defs)
    assert defs.get_job_def("retrain_model")
    assert defs.get_schedule_def("retrain_model_schedule").cron_schedule == "0 3 * * *"
