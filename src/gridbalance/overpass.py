"""Download the OpenStreetMap data needed to model one local network."""

import json
import os
import re
from functools import lru_cache
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from gridbalance.osm import MIN_SITES, RADII_KM, Dataset, Line, NoDataError, Site

DEFAULT_URL = "https://overpass.openstreetmap.fr/api/interpreter"
PLACE_TYPES = (
  "city", "town", "village", "hamlet", "suburb", "quarter", "neighbourhood",
)
PLACE_PATTERN = "|".join(PLACE_TYPES)
LINE_TYPES = {"line", "cable", "minor_line"}
OUTPUT_UNITS = {"w": 1e-6, "kw": 1e-3, "mw": 1, "mwp": 1, "gw": 1000}
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


def load_world_zone(lat, lon, radius_km):
  if radius_km is not None:
    return download_dataset(lat, lon, radius_km).zone(lat, lon, radius_km)

  # Most searches only need the smaller area. Expand once in sparse regions.
  nearby = download_dataset(lat, lon, 20)
  try:
    zone = nearby.zone(lat, lon)
    if zone.total_sites >= MIN_SITES and any(site.is_source() for site in zone.sites):
      return zone
  except NoDataError:
    pass
  return download_dataset(lat, lon, max(RADII_KM)).zone(lat, lon)


@lru_cache(maxsize=8)
def download_dataset(lat, lon, radius_km):
  around = f"(around:{radius_km * 1000:.3f},{lat:.6f},{lon:.6f})"
  query = (
    "[out:json][timeout:20];"
    f'(nwr["power"~"^(substation|plant)$"]{around};'
    f'node["place"~"^({PLACE_PATTERN})$"]{around};);out center;'
    f'way["power"~"^(line|cable|minor_line)$"]{around};out geom;'
  )
  url = os.environ.get("PWRGRID_OVERPASS_URL", DEFAULT_URL)
  request = Request(
    url,
    data=urlencode({"data": query}).encode("ascii"),
    headers={"User-Agent": "PwrGrid/0.1 (https://github.com/Juyens/gridbalance)"},
  )
  try:
    with urlopen(request, timeout=25) as response:
      body = response.read(MAX_RESPONSE_BYTES + 1)
  except (URLError, TimeoutError) as error:
    raise RuntimeError(f"Overpass could not load the network: {error}") from error
  if len(body) > MAX_RESPONSE_BYTES:
    raise RuntimeError("Overpass response was too large. Use a smaller radius.")
  data = json.loads(body)
  if data.get("remark"):
    raise RuntimeError(f"Overpass returned incomplete data: {data['remark']}")
  return dataset_from_elements(data["elements"])


def dataset_from_elements(elements):
  sites, lines = [], []
  for element in elements:
    tags = element.get("tags", {})
    power = tags.get("power")
    identity = f"{element['type'][0]}{element['id']}"
    voltages = sorted({
      float(value) / 1000
      for value in re.findall(r"\d+(?:\.\d+)?", tags.get("voltage", ""))
      if float(value) >= 100
    }, reverse=True)
    name = tags.get("name", tags.get("ref", ""))
    if power in LINE_TYPES:
      points = [(p["lat"], p["lon"]) for p in element.get("geometry", []) if p]
      if len(points) >= 2:
        lines.append(Line(identity, name, voltages, points))
      continue
    point = element.get("center", element)
    if "lat" not in point or "lon" not in point:
      continue
    site_type = {
      "substation": tags.get("substation", ""),
      "plant": tags.get("plant:source", ""),
    }.get(power, tags.get("place"))
    if power not in ("substation", "plant") and site_type not in PLACE_TYPES:
      continue
    kind = power if power in ("substation", "plant") else "place"
    raw_population = tags.get("population", "")
    population = None
    if re.fullmatch(r"\s*\d[\d\s.,]*", raw_population):
      population = int(re.sub(r"\D", "", raw_population))
    sites.append(Site(
      identity, kind, site_type, name, point["lat"], point["lon"], voltages,
      output_mw(tags.get("plant:output:electricity", "")),
      population,
    ))
  return Dataset(sites, lines)


def output_mw(text):
  match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*([a-z]+)\s*", text, re.IGNORECASE)
  if not match or match[2].lower() not in OUTPUT_UNITS:
    return None
  return float(match[1].replace(",", ".")) * OUTPUT_UNITS[match[2].lower()]
