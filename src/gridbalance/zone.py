"""Turns the sites of a zone into the grid the algorithms work on.

OpenStreetMap has no demand, no line capacities and no costs, so this module
estimates them. Every estimate is in Assumptions.
"""

import math

from gridbalance.grid import Branch, Bus, Generator, Grid
from gridbalance.osm import KM_PER_DEGREE, distance_km, longitude_near
from gridbalance.ufds import count, find, union

NEIGHBORS = 3  #candidate lines from each site to its nearest ones
SOURCE_NEIGHBORS = 2  #candidate lines from each source to its nearest sources
FEEDERS = 8  #candidate lines from each source to its nearest sites
MIN_LENGTH_KM = 0.01

#Places whose people are spread over the neighbourhoods around them.
CENTER_TYPES = {"city", "suburb"}
SHARED_TYPES = {"suburb", "quarter", "neighbourhood"}
CENTER_REACH_KM = 10


class LineType:
  """Line built at one voltage level."""

  def __init__(self, kv, cost_per_km, capacity_mva):
    self.kv = kv
    self.cost_per_km = cost_per_km  #thousands of US dollars
    self.capacity_mva = capacity_mva


class Assumptions:
  """Estimated values; their sources are in docs/sources.md."""

  def __init__(self):
    self.kw_per_person = 0.2
    #People of a site whose population is unknown.
    self.default_population = {
      "city": 50000,
      "town": 5000,
      "village": 500,
      "hamlet": 100,
    }
    self.default_shared_population = 1000
    self.plant_mw = 10.0
    #Power a main substation can take from the national grid, by its highest kV.
    self.substation_mw = {500: 600.0, 220: 100.0, 138: 50.0, 60: 40.0}
    #Highest voltage first. The last one also feeds the loads.
    self.line_types = (
      LineType(500, 327.0, 750.0),
      LineType(220, 238.0, 180.0),
      LineType(138, 99.0, 80.0),
      LineType(60, 80.0, 60.0),  #cost without a source yet
      LineType(22.9, 12.3, 10.0),  #capacity without a source yet
    )


class ZoneGrid:
  """Grid of a zone; buses and sites share their indices."""

  def __init__(self, zone, grid, lengths_km, voltages_kv):
    self.zone = zone
    self.grid = grid
    self.lengths_km = lengths_km  #one per branch
    self.voltages_kv = voltages_kv  #one per branch


def build_zone_grid(zone, assumptions=None):
  assumptions = assumptions or Assumptions()
  sites = zone.sites
  people = estimate_people(sites, assumptions)
  buses = [
    Bus(
      index=i,
      id=site.id,
      demand_mw=people[i] * assumptions.kw_per_person / 1000,
      base_kv=site_kv(site, assumptions),
    )
    for i, site in enumerate(sites)
  ]
  branches, lengths, voltages = [], [], []
  for u, v in candidate_pairs(sites):
    length = max(distance_between(sites[u], sites[v]), MIN_LENGTH_KM)
    kind = line_type(min(buses[u].base_kv, buses[v].base_kv), assumptions)
    branches.append(
      Branch(
        index=len(branches),
        from_bus=u,
        to_bus=v,
        cost=length * kind.cost_per_km,
        capacity_mva=kind.capacity_mva,
      )
    )
    lengths.append(length)
    voltages.append(kind.kv)
  generators = [
    Generator(bus=i, pmax_mw=source_mw(site, assumptions))
    for i, site in enumerate(sites)
    if site.is_source()
  ]
  if not generators:
    #Nobody feeds the zone: its most populated site is taken as the entry point.
    entry = max(range(len(sites)), key=people.__getitem__)
    generators = [Generator(bus=entry, pmax_mw=sum(bus.demand_mw for bus in buses))]
  grid = Grid(
    name=f"{zone.lat:.4f}, {zone.lon:.4f}",
    buses=tuple(buses),
    branches=tuple(branches),
    generators=tuple(generators),
    cost_unit="kUSD",
  )
  return ZoneGrid(zone, grid, lengths, voltages)


def site_kv(site, assumptions):
  if not site.is_source():
    return assumptions.line_types[-1].kv
  return site.voltages_kv[0] if site.voltages_kv else assumptions.line_types[-2].kv


def line_type(kv, assumptions):
  """Highest line type that does not exceed the voltage."""
  for kind in assumptions.line_types:
    if kind.kv <= kv:
      return kind
  return assumptions.line_types[-1]


def source_mw(site, assumptions):
  if site.kind == "plant":
    return site.output_mw if site.output_mw is not None else assumptions.plant_mw
  levels = sorted(assumptions.substation_mw, reverse=True)
  kv = site_kv(site, assumptions)
  level = next((level for level in levels if level <= kv), levels[-1])
  return assumptions.substation_mw[level]


def estimate_people(sites, assumptions):
  """People each site feeds.

  A city or district is one point with all its people, so they are spread over
  the neighbourhoods and small substations that have it as their nearest center.
  """
  people = [0.0] * len(sites)
  centers = {
    i: float(site.population)
    for i, site in enumerate(sites)
    if site.kind == "place" and site.type in CENTER_TYPES and site.population
  }
  districts = [pop for i, pop in centers.items() if sites[i].type == "suburb"]
  if districts:
    #The population of a city already includes its districts.
    average = sum(districts) / len(districts)
    for i in centers:
      if sites[i].type == "city":
        centers[i] = min(centers[i], average)

  members = {i: [i] for i in centers}
  for i, site in enumerate(sites):
    if i in centers or site.is_source():
      continue
    if is_shared(site):
      center = nearest_center(site, sites, centers)
      if center is None:
        people[i] = assumptions.default_shared_population
      else:
        members[center].append(i)
    elif site.population is not None:
      people[i] = site.population
    else:
      people[i] = assumptions.default_population[site.type]

  for center, group in members.items():
    for i in group:
      people[i] = centers[center] / len(group)
  return people


def is_shared(site):
  if site.kind == "substation":
    return True
  return site.type in SHARED_TYPES and site.population is None


def nearest_center(site, sites, centers):
  best, best_km = None, CENTER_REACH_KM
  for i in centers:
    km = distance_between(site, sites[i])
    if km <= best_km:
      best, best_km = i, km
  return best


def distance_between(a, b):
  return distance_km(a.lat, a.lon, b.lat, b.lon)


def candidate_pairs(sites):
  """Lines worth considering, always enough to connect every site.

  All the pairs would be n(n-1)/2, about three million for 2500 sites.
  """
  points = project(sites)
  everyone = list(range(len(sites)))
  sources = [i for i in everyone if sites[i].is_source()]
  pairs = nearest_pairs(points, everyone, everyone, NEIGHBORS)
  pairs |= nearest_pairs(points, sources, everyone, FEEDERS)
  pairs |= nearest_pairs(points, sources, sources, SOURCE_NEIGHBORS)
  return sorted(pairs | joining_pairs(points, pairs))


def project(sites):
  """Coordinates in km on a plane, precise enough for a few tens of km."""
  if not sites:
    return []
  scale = KM_PER_DEGREE * math.cos(math.radians(sites[0].lat))
  center_lon = sites[0].lon
  return [
    (longitude_near(site.lon, center_lon) * scale, site.lat * KM_PER_DEGREE)
    for site in sites
  ]


def squared_distance(p, q):
  return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2


def nearest_pairs(points, starts, members, k):
  """Pairs (u, v), u < v, of each start with its k nearest members.

  The starts must be members.

  The plane is divided into square cells, so each search only looks at the
  cells around the point instead of at every point.
  """
  k = min(k, len(members) - 1)
  if k <= 0:
    return set()
  xs = [points[i][0] for i in members]
  ys = [points[i][1] for i in members]
  side = max(max(xs) - min(xs), max(ys) - min(ys), MIN_LENGTH_KM)
  size = side / math.sqrt(len(members))  #about one point per cell
  cells = {}
  for i in members:
    cells.setdefault(cell_of(points[i], size), []).append(i)

  pairs = set()
  for i in starts:
    for j in nearest(points, cells, size, i, k):
      pairs.add((min(i, j), max(i, j)))
  return pairs


def cell_of(point, size):
  return math.floor(point[0] / size), math.floor(point[1] / size)


def nearest(points, cells, size, i, k):
  x, y = cell_of(points[i], size)
  found = []
  ring = 0
  while True:
    for cell in ring_cells(x, y, ring):
      for j in cells.get(cell, ()):
        if j != i:
          found.append((squared_distance(points[i], points[j]), j))
    #A point outside the rings seen so far is farther than ring * size.
    if len(found) >= k:
      found.sort()
      if found[k - 1][0] <= (ring * size) ** 2:
        return [j for _, j in found[:k]]
    ring += 1


def ring_cells(x, y, ring):
  """Cells at the given distance from the cell (x, y)."""
  if ring == 0:
    return [(x, y)]
  cells = []
  for step in range(-ring, ring + 1):
    cells.append((x + step, y - ring))
    cells.append((x + step, y + ring))
  for step in range(-ring + 1, ring):
    cells.append((x - ring, y + step))
    cells.append((x + ring, y + step))
  return cells


def joining_pairs(points, pairs):
  """Pairs that connect the groups left apart by the nearest neighbors."""
  n = len(points)
  s, rank = list(range(n)), [0] * n
  for u, v in pairs:
    union(s, rank, u, v)
  added = set()
  while n > 0 and count(s) > 1:
    groups = {}
    for i in range(n):
      groups.setdefault(find(s, i), []).append(i)
    #Every group but the largest one is joined to its closest outsider.
    for group in sorted(groups.values(), key=len)[:-1]:
      root = find(s, group[0])
      _, u, v = min(
        (squared_distance(points[u], points[v]), u, v)
        for u in group
        for v in range(n)
        if find(s, v) != root
      )
      union(s, rank, u, v)
      added.add((min(u, v), max(u, v)))
  return added
