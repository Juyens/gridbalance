import io
import json
from pathlib import Path
from urllib.parse import parse_qs

import pytest

from gridbalance import overpass
from gridbalance.api import Api


def test_overpass_data_opens_a_network_outside_peru(monkeypatch, tmp_path):
    elements = [
        {
            "type": "way", "id": 20, "center": {"lat": 40.41, "lon": -3.71},
            "tags": {"power": "substation", "voltage": "66000;220000"},
        },
        {
            "type": "node", "id": 21, "lat": 40.42, "lon": -3.71,
            "tags": {"place": "quarter", "population": "2,500"},
        },
        {
            "type": "way", "id": 22,
            "geometry": [{"lat": 40.41, "lon": -3.71}, {"lat": 40.42, "lon": -3.71}],
            "tags": {"power": "line", "voltage": "66000"},
        },
    ]

    def respond(request, timeout):
        query = parse_qs(request.data.decode())["data"][0]
        assert "(around:3500.000,40.410000,-3.710000)" in query
        assert timeout > 0
        return io.BytesIO(json.dumps({"elements": elements}).encode())

    monkeypatch.setattr(overpass, "urlopen", respond)
    overpass.download_dataset.cache_clear()
    try:
        api = Api(tmp_path)
        case = api.load_zone(40.41, -3.71, 3.5, False)
        assert case["zone"]["radiusKm"] == 3.5
        assert case["buses"][0]["baseKv"] == 220
        assert case["buses"][1]["population"] == 2500
        assert len(case["existingLines"]) == 1
        design = api.design({"cost": 1, "robustness": 1, "supply": 1}, case["caseId"])
        assert design["suppliedMw"] >= case["mst"]["suppliedMw"]
    finally:
        overpass.download_dataset.cache_clear()


def test_incomplete_overpass_response_is_an_error(monkeypatch):
    def respond(*_args, **_kwargs):
        return io.BytesIO(b'{"remark":"query timed out"}')

    monkeypatch.setattr(overpass, "urlopen", respond)
    with pytest.raises(RuntimeError, match="incomplete data"):
        overpass.download_dataset(40, -3, 6)


def test_polish_case_stays_comparable_and_has_no_geographic_radius(tmp_path):
    case_path = Path(__file__).resolve().parents[1] / "cases" / "case2383wp.m"
    api = Api(tmp_path, case_path)
    case = api.load_case()
    assert case["name"] == "case2383wp"
    assert len(case["buses"]) == 2383
    assert case["zone"]["radiusKm"] is None
    assert case["costUnit"] == "ohm"
    assert case["original"]["cost"] >= case["mst"]["cost"]
