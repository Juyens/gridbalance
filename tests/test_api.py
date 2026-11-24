import json
from pathlib import Path

import pytest

from gridbalance.api import Api

ROOT = Path(__file__).resolve().parents[1]
PERU = ROOT / "data" / "peru"
CASE = ROOT / "cases" / "case2383wp.m"
UPC_SAN_MIGUEL = (-12.0764, -77.0934)
WEIGHTS = {"cost": 1, "robustness": 1, "supply": 1}


@pytest.fixture(scope="module")
def loaded():
    api = Api(PERU, CASE)
    return api, api.load_zone(*UPC_SAN_MIGUEL)


def test_design_before_loading_a_zone_fails(tmp_path):
    with pytest.raises(RuntimeError, match="no zone loaded"):
        Api(tmp_path, tmp_path).design(WEIGHTS)


def test_load_zone_payload_is_valid_json(loaded):
    _, zone = loaded

    # pywebview serializes with json; inf would not be valid JSON.
    json.dumps(zone, allow_nan=False)
    assert zone["zone"]["radiusKm"] == 5
    assert zone["zone"]["totalSites"] == len(zone["buses"])
    assert zone["costUnit"] == "kUSD"
    assert len(zone["tree"]) == len(zone["buses"]) - 1
    assert zone["mst"]["bridges"] == len(zone["tree"])
    assert zone["totalLoadMw"] > 0


def test_zone_payload_has_what_the_map_draws(loaded):
    _, zone = loaded

    maranga = next(b for b in zone["buses"] if b["name"] == "Subestación Maranga")
    assert maranga["kind"] == "substation"
    assert maranga["supplyMw"] > 0
    # OpenStreetMap order is (lat, lon); the map wants [lon, lat].
    lon, lat = zone["existingLines"][0]["points"][0]
    assert -82 < lon < -68
    assert -19 < lat < 0
    assert all(b["cost"] > 0 and b["lengthKm"] > 0 for b in zone["branches"])


def test_load_zone_with_a_given_radius(loaded):
    zone = Api(PERU, CASE).load_zone(*UPC_SAN_MIGUEL, 2)

    assert zone["zone"]["radiusKm"] == 2
    assert len(zone["buses"]) < len(loaded[1]["buses"])


def test_point_without_data_gives_none_and_keeps_the_zone():
    api = Api(PERU, CASE)
    api.load_zone(*UPC_SAN_MIGUEL)

    assert api.load_zone(40.4, -3.7) is None
    assert api.design(WEIGHTS)["cost"] > 0


def test_load_case_payload_is_the_polish_grid():
    api = Api(PERU, CASE)

    case = api.load_case()

    json.dumps(case, allow_nan=False)
    assert case["name"] == "case2383wp"
    assert case["zone"]["radiusKm"] is None
    assert len(case["buses"]) == 2383
    assert case["original"]["bridges"] == 644
    assert case["branches"][0]["lengthKm"] is None
    assert api.design(WEIGHTS)["bridges"] == 808


def test_measuring_does_not_change_the_open_zone(loaded):
    api, zone = loaded

    case = api.measure(None)
    small = api.measure({"lat": -10.5776, "lon": -75.4026, "radiusKm": None})

    assert (case["nodes"], case["lines"]) == (2383, 2896)
    assert (case["treeBridges"], case["designBridges"]) == (2382, 808)
    assert small["nodes"] < 50
    assert small["designMs"] >= 0
    assert set(api.design(WEIGHTS)["added"]).isdisjoint(zone["tree"])
    assert len(api.design(WEIGHTS)["bridgeBranches"]) < len(zone["tree"])


def test_design_payload(loaded):
    api, zone = loaded

    design = api.design(WEIGHTS)

    json.dumps(design, allow_nan=False)
    assert len(design["bridgeBranches"]) == design["bridges"]
    assert [step["branch"] for step in design["steps"]] == design["added"]
    assert set(design["added"]).isdisjoint(zone["tree"])
    assert design["suppliedMw"] >= zone["mst"]["suppliedMw"]


def test_theme_defaults_to_system(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert Api(tmp_path, tmp_path).get_theme() is None


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_theme_survives_new_api_instance(tmp_path, monkeypatch, theme):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    Api(tmp_path, tmp_path).set_theme(theme)

    assert Api(tmp_path, tmp_path).get_theme() == theme


@pytest.mark.parametrize("theme", ["system", "", None, {}])
def test_invalid_theme_is_rejected(tmp_path, monkeypatch, theme):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    with pytest.raises(ValueError, match="light or dark"):
        Api(tmp_path, tmp_path).set_theme(theme)
    assert not (tmp_path / ".gridbalance").exists()


def test_invalid_saved_theme_falls_back_to_system(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    settings = tmp_path / ".gridbalance"
    settings.mkdir()
    (settings / "theme").write_text("unknown", encoding="utf-8")

    assert Api(tmp_path, tmp_path).get_theme() is None


def test_language_defaults_to_system(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert Api(tmp_path, tmp_path).get_language() is None


@pytest.mark.parametrize("language", ["en", "es"])
def test_language_survives_new_instance_without_changing_theme(
    tmp_path, monkeypatch, language
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    api = Api(tmp_path, tmp_path)
    api.set_theme("dark")
    api.set_language(language)
    reopened = Api(tmp_path, tmp_path)
    assert reopened.get_language() == language
    assert reopened.get_theme() == "dark"


@pytest.mark.parametrize("language", ["fr", "", None, {}])
def test_invalid_language_is_rejected(tmp_path, monkeypatch, language):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with pytest.raises(ValueError, match="en or es"):
        Api(tmp_path, tmp_path).set_language(language)
    assert not (tmp_path / ".gridbalance").exists()


def test_invalid_saved_language_falls_back_to_system(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    settings = tmp_path / ".gridbalance"
    settings.mkdir()
    (settings / "language").write_text("unknown", encoding="utf-8")
    assert Api(tmp_path, tmp_path).get_language() is None
