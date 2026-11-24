import random

import pytest

from gridbalance.bridges import find_bridges
from gridbalance.osm import Site, Zone
from gridbalance.reinforcement import Reinforcer, Weights
from gridbalance.ufds import count, union
from gridbalance.zone import (
  FEEDERS,
  Assumptions,
  build_zone_grid,
  candidate_pairs,
  estimate_people,
  joining_pairs,
  line_type,
  nearest_pairs,
  squared_distance,
)


def place(type, population=None, lat=-12.0, lon=-77.0):
  return Site("n1", "place", type, "", lat, lon, [], None, population)


def substation(lat=-12.0, lon=-77.0, voltages=(), main=True):
  id = "w1" if main else "n1"
  return Site(id, "substation", "", "", lat, lon, list(voltages), None, None)


def plant(output_mw=None, lat=-12.0, lon=-77.0):
  return Site("w2", "plant", "hydro", "", lat, lon, [], output_mw, None)


def zone_of(sites):
  return Zone(-12.0, -77.0, 5, sites, [], len(sites))


def random_points(n, seed=2026):
  rng = random.Random(seed)
  return [(rng.uniform(0, 50), rng.uniform(0, 20)) for _ in range(n)]


def brute_force_nearest_pairs(points, k):
  pairs = set()
  for i in range(len(points)):
    others = sorted(
      (squared_distance(points[i], points[j]), j)
      for j in range(len(points))
      if j != i
    )
    pairs |= {(min(i, j), max(i, j)) for _, j in others[:k]}
  return pairs


def groups(n, pairs):
  s, rank = list(range(n)), [0] * n
  for u, v in pairs:
    union(s, rank, u, v)
  return count(s)


@pytest.mark.parametrize("n", [2, 3, 10, 200])
@pytest.mark.parametrize("k", [1, 3])
def test_nearest_pairs_match_brute_force(n, k):
  points = random_points(n)
  everyone = list(range(n))

  pairs = nearest_pairs(points, everyone, everyone, k)

  assert pairs == brute_force_nearest_pairs(points, k)


def test_nearest_pairs_with_clusters_and_a_far_point():
  points = [*random_points(100), (500.0, 500.0)]
  points += [(x / 1000, y / 1000) for x, y in random_points(100, seed=7)]
  everyone = list(range(len(points)))

  pairs = nearest_pairs(points, everyone, everyone, 3)

  assert pairs == brute_force_nearest_pairs(points, 3)


def test_nearest_pairs_of_points_in_the_same_place():
  same = [(1.0, 1.0)] * 3

  assert nearest_pairs(same, [0, 1, 2], [0, 1, 2], 2) == {(0, 1), (0, 2), (1, 2)}


def test_only_the_starts_look_for_neighbors():
  points = [(0, 0), (1, 0), (2, 0), (9, 0), (10, 0)]

  assert nearest_pairs(points, [0], list(range(5)), 2) == {(0, 1), (0, 2)}


def test_one_member_has_no_neighbors():
  assert nearest_pairs([(0.0, 0.0)], [0], [0], 3) == set()


def test_joining_pairs_use_the_closest_points_of_each_group():
  points = [(0, 0), (1, 0), (5, 0), (6, 0), (100, 0), (101, 0)]
  pairs = {(0, 1), (2, 3), (4, 5)}

  added = joining_pairs(points, pairs)

  assert added == {(1, 2), (3, 4)}
  assert groups(6, pairs | added) == 1


def test_candidates_always_connect_every_site():
  rng = random.Random(5)
  # Three towns far from each other.
  sites = [
    place("hamlet", 100, lat + rng.uniform(0, 0.01), -77 + rng.uniform(0, 0.01))
    for lat in (-12.0, -12.2, -12.4)
    for _ in range(30)
  ]

  assert groups(len(sites), candidate_pairs(sites)) == 1


def test_source_has_several_feeders():
  sites = [substation(), *(place("hamlet", 10, -12 - i / 100) for i in range(1, 20))]

  feeders = [pair for pair in candidate_pairs(sites) if 0 in pair]

  assert len(feeders) == FEEDERS


def test_population_becomes_demand():
  zone_grid = build_zone_grid(zone_of([place("town", 10000), substation(lat=-12.01)]))

  assert zone_grid.grid.load_mw() == [pytest.approx(2.0), 0]  # 0.2 kW per person


def test_unknown_population_depends_on_the_type():
  people = estimate_people([place("village"), place("hamlet")], Assumptions())

  assert people == [500, 100]


def test_district_is_spread_over_its_neighborhoods_and_small_substations():
  sites = [
    place("suburb", 90000),
    place("neighbourhood"),
    substation(main=False),
    substation(),
  ]

  assert estimate_people(sites, Assumptions()) == [30000, 30000, 30000, 0]


def test_each_neighborhood_belongs_to_the_nearest_district():
  sites = [
    place("suburb", 10000, lat=-12.0),
    place("suburb", 50000, lat=-12.05),
    place("neighbourhood", lat=-12.01),
  ]

  assert estimate_people(sites, Assumptions()) == [5000, 50000, 5000]


def test_city_does_not_count_its_districts_twice():
  sites = [place("city", 10_000_000), place("suburb", 200_000, lat=-12.05)]

  assert estimate_people(sites, Assumptions()) == [200_000, 200_000]


def test_neighborhood_far_from_any_center_gets_the_default():
  sites = [place("city", 50000), place("neighbourhood", lat=-12.5)]

  assert estimate_people(sites, Assumptions()) == [50000, 1000]


def test_quarter_with_its_own_population_keeps_it():
  sites = [place("city", 50000), place("quarter", 700)]

  assert estimate_people(sites, Assumptions()) == [50000, 700]


def test_supply_comes_from_plants_and_main_substations():
  sites = [plant(120.0), plant(), substation(voltages=[220, 60]), substation()]

  grid = build_zone_grid(zone_of(sites)).grid

  assert grid.supply_mw() == [120, 10, 100, 40]


def test_zone_without_sources_is_fed_from_its_largest_site():
  grid = build_zone_grid(zone_of([place("hamlet", 100), place("town", 5000)])).grid

  assert grid.supply_mw()[0] == 0
  assert grid.supply_mw()[1] == pytest.approx(sum(grid.load_mw()))


@pytest.mark.parametrize(
  ("kv", "expected"), [(500, 500), (230, 220), (66, 60), (22.9, 22.9), (10, 22.9)]
)
def test_line_type_never_exceeds_the_voltage(kv, expected):
  assert line_type(kv, Assumptions()).kv == expected


def test_cost_is_length_times_the_cost_of_the_lowest_voltage():
  sites = [substation(voltages=[220]), substation(lat=-12.1, voltages=[60])]

  zone_grid = build_zone_grid(zone_of(sites))

  assert zone_grid.lengths_km == [pytest.approx(11.12, abs=0.01)]
  assert zone_grid.grid.branches[0].cost == pytest.approx(11.12 * 80, rel=1e-3)
  assert zone_grid.grid.branches[0].capacity_mva == 60


def test_one_site_is_a_grid_without_lines():
  design = Reinforcer(build_zone_grid(zone_of([place("town", 10)])).grid).design(
    Weights(1, 1, 1)
  )

  assert (design.branches, design.cost) == ((), 0)


def test_upc_zone_can_be_designed(peru):
  zone = peru.zone(-12.0764, -77.0934)
  reinforcer = Reinforcer(build_zone_grid(zone).grid)

  design = reinforcer.design(Weights(1, 1, 1))

  assert len(design.tree) == len(zone.sites) - 1
  assert design.supplied_mw >= reinforcer.tree_flow.value


def test_removed_bridges_of_each_step_match_tarjan(peru):
  grid = build_zone_grid(peru.zone(-12.0764, -77.0934)).grid
  design = Reinforcer(grid).design(Weights(1, 1, 1))

  active, bridges = list(design.tree), set(design.tree)
  for step in design.steps:
    active.append(step.branch)
    bridges -= set(step.removed_bridges)
    assert bridges == set(find_bridges(grid, active))
