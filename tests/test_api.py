import json
import shutil
from pathlib import Path

import pytest

from gridbalance.api import Api

CASES_DIR = Path(__file__).resolve().parents[1] / "cases"
CASE_FILE = "case2383wp.m"


def api_with_case(cases_dir: Path) -> tuple[Api, dict]:
    # Work on a copy so layout files are written to a temporary folder.
    shutil.copy(CASES_DIR / CASE_FILE, cases_dir)
    api = Api(cases_dir)
    return api, api.load_case(CASE_FILE)


@pytest.fixture(scope="module")
def loaded(tmp_path_factory):
    return api_with_case(tmp_path_factory.mktemp("cases"))


def test_list_cases(loaded):
    api, _ = loaded

    assert api.list_cases() == [CASE_FILE]


def test_design_before_loading_a_case_fails(tmp_path):
    with pytest.raises(RuntimeError, match="no case loaded"):
        Api(tmp_path).design({"cost": 1, "robustness": 1, "supply": 1})


def test_load_case_payload_is_valid_json(loaded):
    _, case = loaded

    # pywebview serializes with json; inf would not be valid JSON.
    json.dumps(case, allow_nan=False)
    assert case["name"] == "case2383wp"
    assert len(case["buses"]) == 2383
    assert len(case["branches"]) == 2896
    assert len(case["tree"]) == 2382
    assert case["original"]["bridges"] == 644
    assert case["mst"]["bridges"] == 2382
    assert case["totalLoadMw"] == pytest.approx(24580, abs=1)
    assert case["positions"] is None


def test_design_payload(loaded):
    api, case = loaded

    design = api.design({"cost": 0, "robustness": 1, "supply": 1})

    json.dumps(design, allow_nan=False)
    assert design["bridges"] == 644
    assert len(design["bridgeBranches"]) == 644
    assert [step["branch"] for step in design["steps"]] == design["added"]
    assert set(design["added"]).isdisjoint(case["tree"])


def test_layout_round_trip(tmp_path):
    api, case = api_with_case(tmp_path)
    positions = [[float(i), float(-i)] for i in range(len(case["buses"]))]

    api.save_layout(positions)

    assert api.load_case(CASE_FILE)["positions"] == positions


def test_layout_with_wrong_size_is_rejected(loaded):
    api, _ = loaded

    with pytest.raises(ValueError, match="one position per bus"):
        api.save_layout([[0.0, 0.0]])


def test_theme_defaults_to_system(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert Api(tmp_path).get_theme() is None


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_theme_survives_new_api_instance(tmp_path, monkeypatch, theme):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    Api(tmp_path).set_theme(theme)

    assert Api(tmp_path).get_theme() == theme


@pytest.mark.parametrize("theme", ["system", "", None, {}])
def test_invalid_theme_is_rejected(tmp_path, monkeypatch, theme):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    with pytest.raises(ValueError, match="light or dark"):
        Api(tmp_path).set_theme(theme)
    assert not (tmp_path / ".gridbalance").exists()


def test_invalid_saved_theme_falls_back_to_system(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    settings = tmp_path / ".gridbalance"
    settings.mkdir()
    (settings / "theme").write_text("unknown", encoding="utf-8")

    assert Api(tmp_path).get_theme() is None
