"""Conformité de /openapi.json au contrat openapi.yml, qui ne se modifie pas."""

from pathlib import Path

import pytest
import yaml

from express_delivery.api.app import app

CONTRACT = yaml.safe_load(Path("openapi.yml").read_text(encoding="utf-8"))
GENERATED = app.openapi()

OPERATIONS = [
    (path, method, operation)
    for path, operations in GENERATED["paths"].items()
    for method, operation in operations.items()
]


@pytest.mark.parametrize(
    ("path", "method", "operation"),
    OPERATIONS,
    ids=[f"{method.upper()} {path}" for path, method, _ in OPERATIONS],
)
def test_operation_matches_contract(path, method, operation):
    assert method in CONTRACT["paths"].get(path, {}), "opération absente du contrat"
    expected = CONTRACT["paths"][path][method]

    for key in ("operationId", "tags", "summary", "x-session"):
        assert operation.get(key) == expected.get(key), key
    assert (operation.get("description") or "").strip() == (expected.get("description") or "").strip()
    # FastAPI ajoute un 422 aux paramètres de chemin ; les codes du contrat doivent tous y être.
    assert set(expected["responses"]) <= set(operation["responses"])


SCHEMAS = sorted(set(GENERATED["components"]["schemas"]) & set(CONTRACT["components"]["schemas"]))


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_matches_contract(name):
    generated = GENERATED["components"]["schemas"][name]
    expected = CONTRACT["components"]["schemas"][name]

    assert set(generated["properties"]) == set(expected["properties"])
    assert set(generated.get("required", [])) == set(expected.get("required", []))
