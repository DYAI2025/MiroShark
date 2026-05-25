from pathlib import Path

import yaml


OPENAPI_PATH = Path(__file__).resolve().parents[1] / "openapi.yaml"


def test_openapi_yaml_is_parseable():
    """Guard against ScannerError/ParserError in CI due to malformed YAML."""
    with OPENAPI_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    assert isinstance(data, dict)
    assert data.get("openapi")


def test_outcome_path_schema_is_present():
    """Regression guard around the block that previously broke YAML parsing in CI."""
    with OPENAPI_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    outcome = data["paths"]["/api/simulation/{simulation_id}/outcome"]
    label_enum = outcome["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]["label"]["enum"]
    assert label_enum == ["correct", "incorrect", "partial"]
