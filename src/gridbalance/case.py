"""Grid of a MATPOWER case, placed on the map.

The case has no coordinates: its drawing (the .layout.json file next to it) is
stretched over Poland, so the positions are only a reference.
"""

import json
import math

from gridbalance.grid import Branch, Bus, Generator, Grid
from gridbalance.matpower import CaseFormatError, read_case
from gridbalance.osm import Site, Zone
from gridbalance.zone import ZoneGrid

#Column positions defined by MATPOWER (idx_bus, idx_brch, idx_gen).
BUS_I, BUS_TYPE, PD, BASE_KV = 0, 1, 2, 9
F_BUS, T_BUS, BR_X, RATE_A, BR_STATUS = 0, 1, 3, 5, 10
GEN_BUS, GEN_STATUS, PMAX = 0, 7, 8

ISOLATED_BUS_TYPE = 4

#Rough outline of Poland, as (lon, lat).
POLAND = (
  (14.2, 53.9), (16.2, 54.25), (18.3, 54.75), (19.6, 54.4), (22.8, 54.3), (23.5, 53.9),
  (23.8, 52.7), (23.2, 52.3), (23.6, 51.5), (24.0, 50.8), (23.1, 50.3), (22.6, 49.6),
  (22.5, 49.2), (20.9, 49.4), (19.8, 49.3), (18.8, 49.6), (17.7, 50.1), (16.9, 50.35),
  (16.2, 50.6), (15.0, 50.95), (14.8, 51.6), (14.7, 52.4), (14.2, 52.9), (14.4, 53.3),
)
CENTER_LON, CENTER_LAT = 19.3, 52.0
EDGE = 0.95  #share of the way from the center to the border


def load_case(path):
  grid = build_grid(read_case(path))
  places = positions(path.with_name(path.stem + ".layout.json"), len(grid.buses))
  supply = grid.supply_mw()
  sites = [
    Site(
      id=bus.id,
      kind="bus",
      type="generator" if supply[bus.index] > 0 else "",
      name="",
      lat=lat,
      lon=lon,
      voltages_kv=[bus.base_kv],
      output_mw=None,
      population=None,
    )
    for bus, (lat, lon) in zip(grid.buses, places, strict=True)
  ]
  zone = Zone(CENTER_LAT, CENTER_LON, None, sites, [], len(sites))
  voltages = [grid.buses[branch.from_bus].base_kv for branch in grid.branches]
  return ZoneGrid(zone, grid, [None] * len(grid.branches), voltages)


def build_grid(raw):
  buses = build_buses(raw.matrices["bus"])
  #Ohms are only comparable across voltage levels if every bus has a base kV.
  cost_unit = "ohm" if all(bus.base_kv > 0 for bus in buses) else "p.u."
  return Grid(
    name=raw.name,
    buses=tuple(buses),
    branches=tuple(
      build_branches(raw.matrices["branch"], buses, raw.base_mva, cost_unit)
    ),
    generators=tuple(build_generators(raw.matrices["gen"], buses)),
    cost_unit=cost_unit,
  )


def build_buses(rows):
  buses = []
  for row in rows:
    if int(row[BUS_TYPE]) == ISOLATED_BUS_TYPE:
      continue
    buses.append(
      Bus(
        index=len(buses),
        id=int(row[BUS_I]),
        demand_mw=row[PD],
        base_kv=row[BASE_KV],
      )
    )
  return buses


def build_branches(rows, buses, base_mva, cost_unit):
  index_of = {bus.id: bus.index for bus in buses}
  branches = []
  for row in rows:
    if row[BR_STATUS] == 0:
      continue
    from_id, to_id = int(row[F_BUS]), int(row[T_BUS])
    if from_id not in index_of or to_id not in index_of:
      continue  #touches an isolated bus
    if from_id == to_id:
      raise CaseFormatError(f"branch connects bus {from_id} to itself")

    from_bus = buses[index_of[from_id]]
    #Series compensation can give negative reactance; cost uses magnitude.
    reactance_pu = abs(row[BR_X])
    if cost_unit == "ohm":
      #Z_base = kV^2 / MVA, using the from side for transformers.
      cost = reactance_pu * from_bus.base_kv**2 / base_mva
    else:
      cost = reactance_pu

    branches.append(
      Branch(
        index=len(branches),
        from_bus=from_bus.index,
        to_bus=index_of[to_id],
        cost=cost,
        capacity_mva=row[RATE_A] if row[RATE_A] > 0 else math.inf,
      )
    )
  return branches


def build_generators(rows, buses):
  index_of = {bus.id: bus.index for bus in buses}
  return [
    Generator(bus=index_of[int(row[GEN_BUS])], pmax_mw=max(row[PMAX], 0.0))
    for row in rows
    if row[GEN_STATUS] > 0 and int(row[GEN_BUS]) in index_of
  ]


def positions(path, bus_count):
  """One (lat, lon) per bus: the drawing stretched until it fills Poland."""
  points = json.loads(path.read_text(encoding="utf-8"))["positions"]
  if len(points) != bus_count:
    raise CaseFormatError(f"{path.name} does not belong to this case")
  width = max(abs(x) for x, _ in points)
  height = max(abs(y) for _, y in points)
  #Distance to the center and angle of each bus; the screen grows downwards.
  polar = [
    (math.hypot(x / width, y / height), math.atan2(-y / height, x / width))
    for x, y in points
  ]
  farthest = max(distance for distance, _ in polar)
  places = []
  for distance, angle in polar:
    reach = squeeze(distance, farthest) * EDGE * border_distance(angle)
    places.append(
      (CENTER_LAT + reach * math.sin(angle), CENTER_LON + reach * math.cos(angle))
    )
  return places


def squeeze(distance, farthest):
  """Keeps the few buses beyond the circle of radius 1 inside it."""
  limit = 0.9
  if distance <= limit:
    return distance
  return limit + (distance - limit) / (farthest - limit) * (1 - limit)


def border_distance(angle):
  """Degrees from the center to the border in the given direction."""
  dx, dy = math.cos(angle), math.sin(angle)
  distances = []
  for (x1, y1), (x2, y2) in zip(POLAND, POLAND[1:] + POLAND[:1], strict=True):
    px, py = x1 - CENTER_LON, y1 - CENTER_LAT
    ex, ey = x2 - x1, y2 - y1
    cross = dx * ey - dy * ex
    if cross == 0:
      continue  #parallel to this side
    distance = (px * ey - py * ex) / cross
    along = (px * dy - py * dx) / cross
    if distance > 0 and 0 <= along <= 1:
      distances.append(distance)
  return min(distances)
