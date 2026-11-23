import pytest

from gridbalance import osm
from gridbalance.osm import Dataset, Line, NoDataError, Site, distance_km, load_dataset

UPC_SAN_MIGUEL = (-12.0764, -77.0934)

NODES_CSV = """id,kind,type,name,lat,lon,voltage_kv,output_mw,population
w1,substation,transmission,Norte,-12.0,-77.0,220;60,,
w2,plant,hydro,Central,-12.1,-77.0,,120.5,
n3,place,town,Pueblo,-12.2,-77.0,,,1500
n4,substation,,SE 15,-12.3,-77.0,,,
"""
LINES_CSV = """id,type,name,voltage_kv,points
w9,line,L-2001,220,-12.0 -77.0;-12.1 -77.0
"""


def site(id, lat, lon=-77.0, kind="place"):
  return Site(id, kind, "", id, lat, lon, [], None, None)


def ids(sites):
  return [s.id for s in sites]


def test_reads_the_csv_files(tmp_path):
  (tmp_path / "nodes.csv").write_text(NODES_CSV, encoding="utf-8")
  (tmp_path / "lines.csv").write_text(LINES_CSV, encoding="utf-8")

  data = load_dataset(tmp_path)

  north, plant, town, small = data.sites
  assert north.voltages_kv == [220, 60]
  assert north.output_mw is None
  assert north.population is None
  assert plant.output_mw == 120.5
  assert town.population == 1500
  assert small.name == "SE 15"
  assert [s.is_source() for s in data.sites] == [True, True, False, False]
  assert data.lines[0].points == [(-12.0, -77.0), (-12.1, -77.0)]


def test_distance_matches_one_degree():
  assert distance_km(-12, -77, -13, -77) == pytest.approx(111.2, abs=0.1)
  assert distance_km(-12, -77, -12, -77) == 0
  # A degree of longitude shrinks with the cosine of the latitude.
  assert distance_km(60, 0, 60, 1) == pytest.approx(55.6, abs=0.1)


def test_sites_come_nearest_first_and_inside_the_circle():
  data = Dataset([site("far", -12.2), site("b", -12.02), site("a", -12.01)], [])

  assert ids(data.sites_within(-12.0, -77.0, 5)) == ["a", "b"]


def test_radius_grows_until_there_are_enough_sites_and_a_source():
  near = [site(f"n{i}", -12.0) for i in range(osm.MIN_SITES)]
  data = Dataset([*near, site("w1", -12.15, kind="substation")], [])

  zone = data.zone(-12.0, -77.0)

  assert zone.radius_km == 20  # the source is about 17 km away
  assert len(zone.sites) == osm.MIN_SITES + 1


def test_a_given_radius_is_never_changed():
  data = Dataset([site("n1", -12.0), site("n2", -12.2)], [])

  assert ids(data.zone(-12.0, -77.0, 3).sites) == ["n1"]


def test_sparse_zone_returns_what_there_is():
  zone = Dataset([site("n1", -12.0)], []).zone(-12.0, -77.0)

  assert zone.radius_km == osm.RADII_KM[-1]
  assert ids(zone.sites) == ["n1"]


def test_point_without_data_is_reported():
  with pytest.raises(NoDataError):
    Dataset([site("n1", -12.0)], []).zone(40.0, -3.7)


def test_crowded_zone_keeps_every_source_and_the_nearest_sites(monkeypatch):
  monkeypatch.setattr(osm, "MAX_SITES", 3)
  small = [site(f"n{i}", -12.0 - i / 1000) for i in range(5)]
  data = Dataset([*small, site("w1", -12.04, kind="substation")], [])

  zone = data.zone(-12.0, -77.0, 5)

  assert ids(zone.sites) == ["w1", "n0", "n1"]
  assert zone.total_sites == 6


def test_lines_that_touch_the_circle_are_included():
  touching = Line("w1", "", [], [(-12.01, -77.0), (-13.0, -77.0)])
  away = Line("w2", "", [], [(-14.0, -77.0), (-13.0, -77.0)])

  zone = Dataset([site("n1", -12.0)], [touching, away]).zone(-12.0, -77.0, 5)

  assert zone.lines == [touching]


def test_upc_san_miguel_has_a_network(peru):
  zone = peru.zone(*UPC_SAN_MIGUEL)

  assert zone.radius_km == 5
  assert "Subestación Maranga" in {s.name for s in zone.sites}
  assert zone.lines


def test_lima_reaches_the_size_required_by_the_course(peru):
  assert len(peru.zone(*UPC_SAN_MIGUEL, 20).sites) >= 1500


@pytest.mark.parametrize(
  ("lat", "lon"),
  [
    pytest.param(-13.517, -71.9785, id="Cusco"),
    pytest.param(-10.5776, -75.4026, id="Oxapampa"),
    pytest.param(-12.5933, -69.1891, id="Puerto Maldonado"),
    pytest.param(-3.7494, -73.2444, id="Iquitos"),
  ],
)
def test_other_cities_have_enough_sites_and_a_source(peru, lat, lon):
  zone = peru.zone(lat, lon)

  assert len(zone.sites) >= osm.MIN_SITES
  assert any(s.is_source() for s in zone.sites)
