# /// script
# requires-python = ">=3.13"
# dependencies = ["osmium>=4.3"]
# ///
"""Extracts the power grid of a country from an OpenStreetMap file (.osm.pbf).

uv run tools/build_dataset.py peru-261122.osm.pbf data/peru

The app does not need this script: it reads the CSV files written here.
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

import osmium

PLACE_TYPES = {
  "city", "town", "village", "hamlet", "suburb", "quarter", "neighbourhood"
}
LINE_TYPES = {"line", "cable", "minor_line"}
NODE_COLUMNS = (
  "id", "kind", "type", "name", "lat", "lon", "voltage_kv", "output_mw", "population"
)
LINE_COLUMNS = ("id", "type", "name", "voltage_kv", "points")
MEGAWATTS = {"w": 1e-6, "kw": 1e-3, "mw": 1.0, "mwp": 1.0, "gw": 1e3}


def parse_voltages(text):
  """"220000;60000" in volts becomes [220.0, 60.0] in kV, highest first."""
  numbers = (float(n) / 1000 for n in re.findall(r"\d+(?:\.\d+)?", text or ""))
  return sorted({kv for kv in numbers if kv >= 0.1}, reverse=True)


def parse_output(text):
  """"120 MW" becomes 120.0; None when there is no usable number."""
  match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)\s*", text or "")
  if not match or match[2].lower() not in MEGAWATTS:
    return None
  return float(match[1].replace(",", ".")) * MEGAWATTS[match[2].lower()]


def parse_population(text):
  match = re.fullmatch(r"\s*\d[\d\s.,]*\s*", text or "")
  return int(re.sub(r"\D", "", text)) if match else None


def center(points):
  """Middle of the box that contains the points, as (lat, lon)."""
  lats = [lat for lat, _ in points]
  lons = [lon for _, lon in points]
  return (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2


def way_points(way):
  return [(n.lat, n.lon) for n in way.nodes if n.location.valid()]


def number(value):
  return "" if value is None else f"{value:g}"


def node_row(id, tags, lat, lon):
  """CSV row for a substation, plant or place; None for anything else."""
  power, place = tags.get("power"), tags.get("place")
  if power == "substation":
    kind, type = "substation", tags.get("substation", "")
  elif power == "plant":
    kind, type = "plant", tags.get("plant:source", "")
  elif place in PLACE_TYPES:
    kind, type = "place", place
  else:
    return None
  return (
    id,
    kind,
    type,
    tags.get("name", tags.get("ref", "")),
    f"{lat:.6f}",
    f"{lon:.6f}",
    ";".join(number(kv) for kv in parse_voltages(tags.get("voltage"))),
    number(parse_output(tags.get("plant:output:electricity"))),
    number(parse_population(tags.get("population"))) if kind == "place" else "",
  )


def line_row(way, tags):
  points = way_points(way)
  if len(points) < 2:
    return None
  return (
    f"w{way.id}",
    tags["power"],
    tags.get("name", ""),
    ";".join(number(kv) for kv in parse_voltages(tags.get("voltage"))),
    ";".join(f"{lat:.5f} {lon:.5f}" for lat, lon in points),
  )


def read_relations(path):
  """Substations and plants drawn as relations: id -> (tags, member way ids)."""
  relations = {}
  for relation in osmium.FileProcessor(path, osmium.osm.RELATION):
    tags = dict(relation.tags)
    if tags.get("power") in ("substation", "plant"):
      ways = {m.ref for m in relation.members if m.type == "w"}
      relations[relation.id] = (tags, ways)
  return relations


def extract(path):
  relations = read_relations(path)
  member_ways = set().union(*(ways for _, ways in relations.values()))
  member_points = {}
  nodes, lines = [], []
  entities = osmium.osm.NODE | osmium.osm.WAY
  for element in osmium.FileProcessor(path, entities).with_locations():
    is_way = element.is_way()
    if is_way and element.id in member_ways:
      member_points[element.id] = way_points(element)
    if "power" not in element.tags and "place" not in element.tags:
      continue
    tags = dict(element.tags)
    if is_way and tags.get("power") in LINE_TYPES:
      row = line_row(element, tags)
      if row:
        lines.append(row)
    elif is_way and "power" in tags:
      points = way_points(element)
      if points:
        nodes.append(node_row(f"w{element.id}", tags, *center(points)))
    elif not is_way:
      nodes.append(node_row(f"n{element.id}", tags, element.lat, element.lon))

  for id, (tags, ways) in relations.items():
    points = [point for way in ways for point in member_points.get(way, [])]
    if points:
      nodes.append(node_row(f"r{id}", tags, *center(points)))
  return [row for row in nodes if row], lines


def write_csv(path, columns, rows):
  with path.open("w", encoding="utf-8", newline="") as file:
    writer = csv.writer(file, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)


def main():
  if len(sys.argv) != 3:
    sys.exit("usage: build_dataset.py <file.osm.pbf> <output folder>")
  source, folder = sys.argv[1], Path(sys.argv[2])
  nodes, lines = extract(source)
  folder.mkdir(parents=True, exist_ok=True)
  write_csv(folder / "nodes.csv", NODE_COLUMNS, nodes)
  write_csv(folder / "lines.csv", LINE_COLUMNS, lines)
  print(dict(Counter(row[1] for row in nodes)), f"lines: {len(lines)}")


if __name__ == "__main__":
  main()
