"""Real sites and power lines around a point, from OpenStreetMap data.

The data folder is written by tools/build_dataset.py.
"""

import csv
import math

EARTH_RADIUS_KM = 6371.0088
KM_PER_DEGREE = 111.2  #of latitude

#Radii tried in order until the zone has enough sites to design a network.
RADII_KM = (5, 10, 20, 40, 80)
MIN_SITES = 15
MAX_SITES = 2500


class NoDataError(Exception):
  """There is no site near the requested point."""


class Site:
  """Substation, power plant or populated place."""

  def __init__(
    self, id, kind, type, name, lat, lon, voltages_kv, output_mw, population
  ):
    self.id = id
    self.kind = kind  #"substation", "plant" or "place"
    self.type = type
    self.name = name
    self.lat = lat
    self.lon = lon
    self.voltages_kv = voltages_kv  #highest first; empty when unknown
    self.output_mw = output_mw  #None when unknown
    self.population = population  #None when unknown

  def is_source(self):
    """Plants and the substations mapped with their own enclosure feed the zone.

    The substations mapped as a single point are the small ones of the street.
    """
    return self.kind == "plant" or (self.kind == "substation" and self.id[0] != "n")


class Line:
  """Existing power line, only drawn as a reference."""

  def __init__(self, id, name, voltages_kv, points):
    self.id = id
    self.name = name
    self.voltages_kv = voltages_kv
    self.points = points  #list of (lat, lon)


class Zone:
  """Sites and lines inside a circle."""

  def __init__(self, lat, lon, radius_km, sites, lines, total_sites):
    self.lat = lat
    self.lon = lon
    self.radius_km = radius_km
    self.sites = sites
    self.lines = lines
    self.total_sites = total_sites  #before keeping at most MAX_SITES


class Dataset:
  """Every site and line of the data folder."""

  def __init__(self, sites, lines):
    self.sites = sites
    self.lines = lines

  def zone(self, lat, lon, radius_km=None):
    """Zone of the given radius, or of the smallest one that is big enough."""
    for radius in RADII_KM if radius_km is None else (radius_km,):
      sites = self.sites_within(lat, lon, radius)
      if len(sites) >= MIN_SITES and any(site.is_source() for site in sites):
        break
    if not sites:
      raise NoDataError(f"no power data within {radius} km of {lat:.4f}, {lon:.4f}")
    return Zone(
      lat,
      lon,
      radius,
      select_sites(sites),
      self.lines_within(lat, lon, radius),
      len(sites),
    )

  def sites_within(self, lat, lon, radius_km):
    """Sites inside the circle, nearest first."""
    near = []
    for site in self.sites:
      distance = distance_within(lat, lon, site.lat, site.lon, radius_km)
      if distance is not None:
        near.append((distance, site))
    near.sort(key=lambda pair: pair[0])
    return [site for _, site in near]

  def lines_within(self, lat, lon, radius_km):
    return [
      line
      for line in self.lines
      if any(
        distance_within(lat, lon, y, x, radius_km) is not None for y, x in line.points
      )
    ]


def select_sites(sites):
  """At most MAX_SITES: every source first, then the nearest of the rest."""
  if len(sites) <= MAX_SITES:
    return sites
  #sorted is stable, so each group stays ordered by distance.
  return sorted(sites, key=lambda site: not site.is_source())[:MAX_SITES]


def distance_km(lat1, lon1, lat2, lon2):
  """Great-circle distance (haversine formula)."""
  phi1, phi2 = math.radians(lat1), math.radians(lat2)
  half_lat = math.sin((phi2 - phi1) / 2)
  half_lon = math.sin(math.radians(lon2 - lon1) / 2)
  h = half_lat**2 + math.cos(phi1) * math.cos(phi2) * half_lon**2
  return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def distance_within(lat1, lon1, lat2, lon2, limit_km):
  """Distance, or None beyond the limit."""
  #Most points are far in latitude: skip the trigonometry for them.
  if abs(lat2 - lat1) * KM_PER_DEGREE > limit_km * 1.01:
    return None
  distance = distance_km(lat1, lon1, lat2, lon2)
  return distance if distance <= limit_km else None


def load_dataset(folder):
  with (folder / "nodes.csv").open(encoding="utf-8", newline="") as file:
    sites = [read_site(row) for row in csv.DictReader(file)]
  with (folder / "lines.csv").open(encoding="utf-8", newline="") as file:
    lines = [read_line(row) for row in csv.DictReader(file)]
  return Dataset(sites, lines)


def read_site(row):
  return Site(
    id=row["id"],
    kind=row["kind"],
    type=row["type"],
    name=row["name"],
    lat=float(row["lat"]),
    lon=float(row["lon"]),
    voltages_kv=read_voltages(row["voltage_kv"]),
    output_mw=float(row["output_mw"]) if row["output_mw"] else None,
    population=int(float(row["population"])) if row["population"] else None,
  )


def read_line(row):
  points = [tuple(map(float, point.split())) for point in row["points"].split(";")]
  return Line(row["id"], row["name"], read_voltages(row["voltage_kv"]), points)


def read_voltages(text):
  return [float(kv) for kv in text.split(";")] if text else []
