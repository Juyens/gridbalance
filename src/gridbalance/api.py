"""Methods exposed to the frontend as window.pywebview.api."""

import base64
import math
import threading
import time
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

import webview

from gridbalance.case import load_case
from gridbalance.osm import NoDataError, load_dataset
from gridbalance.reinforcement import Reinforcer, Weights
from gridbalance.zone import build_zone_grid


class Api:
  def __init__(self, data_dir, case_path):
    self._data_dir = data_dir
    self._case_path = case_path
    self._dataset = None  #read on the first zone
    self._theme_path = Path.home() / ".gridbalance" / "theme"
    self._language_path = Path.home() / ".gridbalance" / "language"
    self._reinforcer = None
    #One computation at a time: fast slider moves send calls in parallel.
    self._lock = threading.Lock()

  def ping(self):
    return f"Backend ready (gridbalance {version('gridbalance')})"

  def get_theme(self):
    try:
      theme = self._theme_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
      return None
    return theme if theme in ("light", "dark") else None

  def set_theme(self, theme):
    if theme not in ("light", "dark"):
      raise ValueError("theme must be light or dark")
    self._theme_path.parent.mkdir(parents=True, exist_ok=True)
    self._theme_path.write_text(theme, encoding="utf-8")

  def get_language(self):
    try:
      language = self._language_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
      return None
    return language if language in ("en", "es") else None

  def set_language(self, language):
    if language not in ("en", "es"):
      raise ValueError("language must be en or es")
    self._language_path.parent.mkdir(parents=True, exist_ok=True)
    self._language_path.write_text(language, encoding="utf-8")

  def load_zone(self, lat, lon, radius_km=None):
    """Network around a point; None when there is no data near it."""
    with self._lock:
      try:
        return self._open(self._zone_grid(lat, lon, radius_km))
      except NoDataError:
        return None

  def load_case(self):
    """The Polish grid, for any place in Poland."""
    with self._lock:
      return self._open(load_case(self._case_path))

  def measure(self, place):
    """Size and times of a place (None for the Polish grid), without opening it."""
    with self._lock:
      started = time.perf_counter()
      if place is None:
        zone_grid = load_case(self._case_path)
      else:
        zone_grid = self._zone_grid(place["lat"], place["lon"], place["radiusKm"])
      reinforcer = Reinforcer(zone_grid.grid)
      ready = time.perf_counter()
      design = reinforcer.design(Weights(1, 1, 1))
      done = time.perf_counter()
    return {
      "nodes": len(zone_grid.grid.buses),
      "lines": len(zone_grid.grid.branches),
      "prepareMs": (ready - started) * 1000,
      "designMs": (done - ready) * 1000,
      "treeBridges": len(reinforcer.tree),
      "designBridges": design.bridges,
    }

  def design(self, weights):
    with self._lock:
      reinforcer = self._require_zone()
      started = time.perf_counter()
      design = reinforcer.design(
        Weights(weights["cost"], weights["robustness"], weights["supply"])
      )
      elapsed_ms = (time.perf_counter() - started) * 1000
    return design_to_json(design, elapsed_ms)

  def save_export(self, kind, content):
    if kind not in ("png", "csv") or not isinstance(content, str):
      raise ValueError("export must be PNG or CSV text")
    if len(content) > 32 * 1024 * 1024:
      raise ValueError("export exceeds 32 MB")
    if kind == "png":
      data = base64.b64decode(content, validate=True)
      if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("invalid PNG image")
    else:
      data = content.encode("utf-8-sig")
    paths = webview.windows[0].create_file_dialog(
      webview.FileDialog.SAVE,
      save_filename=f"gridbalance.{kind}",
      file_types=(f"{kind.upper()} (*.{kind})",),
    )
    if not paths:
      return False
    target = Path(paths[0])
    if target.suffix.lower() != f".{kind}":
      raise ValueError(f"file extension must be .{kind}")
    #Stage on the same filesystem so failed writes preserve existing files.
    with TemporaryDirectory(prefix=".gridbalance-", dir=target.parent) as directory:
      staging = Path(directory) / target.name
      staging.write_bytes(data)
      staging.replace(target)
    return True

  def _zone_grid(self, lat, lon, radius_km):
    if self._dataset is None:
      self._dataset = load_dataset(self._data_dir)
    return build_zone_grid(self._dataset.zone(lat, lon, radius_km))

  def _open(self, zone_grid):
    self._reinforcer = Reinforcer(zone_grid.grid)
    return zone_to_json(zone_grid, self._reinforcer)

  def _require_zone(self):
    if self._reinforcer is None:
      raise RuntimeError("no zone loaded")
    return self._reinforcer


def finite_or_none(value):
  return None if math.isinf(value) else value


def zone_to_json(zone_grid, reinforcer):
  zone, grid = zone_grid.zone, zone_grid.grid
  supply, load = grid.supply_mw(), grid.load_mw()
  return {
    "name": grid.name,
    "costUnit": grid.cost_unit,
    "zone": {
      "lat": zone.lat,
      "lon": zone.lon,
      "radiusKm": zone.radius_km,  #None when it is not a circle
      "totalSites": zone.total_sites,
    },
    "buses": [
      {
        "index": bus.index,
        "id": bus.id,
        "kind": site.kind,
        "type": site.type,
        "name": site.name,
        "lat": site.lat,
        "lon": site.lon,
        "population": site.population,
        "baseKv": bus.base_kv,
        "supplyMw": supply[bus.index],
        "loadMw": load[bus.index],
      }
      for bus, site in zip(grid.buses, zone.sites, strict=True)
    ],
    "branches": [
      {
        "index": branch.index,
        "from": branch.from_bus,
        "to": branch.to_bus,
        "cost": branch.cost,
        "capacityMva": finite_or_none(branch.capacity_mva),
        "lengthKm": zone_grid.lengths_km[branch.index],
        "kv": zone_grid.voltages_kv[branch.index],
      }
      for branch in grid.branches
    ],
    "existingLines": [
      {
        "name": line.name,
        "voltagesKv": line.voltages_kv,
        "points": [[lon, lat] for lat, lon in line.points],
      }
      for line in zone.lines
    ],
    "tree": reinforcer.tree,
    "totalLoadMw": sum(load),
    "original": {
      "cost": grid.total_cost(),
      "bridges": reinforcer.full_bridges,
      "suppliedMw": reinforcer.full_flow,
    },
    "mst": {
      "cost": reinforcer.tree_cost,
      "bridges": len(reinforcer.tree),
      "suppliedMw": reinforcer.tree_flow.value,
    },
  }


def design_to_json(design, elapsed_ms):
  bridges = set(design.tree)  #in a tree every branch is a bridge
  for step in design.steps:
    bridges.difference_update(step.removed_bridges)
  return {
    "added": list(design.added),
    "bridgeBranches": sorted(bridges),
    "cost": design.cost,
    "bridges": design.bridges,
    "suppliedMw": design.supplied_mw,
    "steps": [
      {
        "branch": step.branch,
        "cost": step.cost,
        "bridges": step.bridges,
        "suppliedMw": step.supplied_mw,
        "removedBridges": step.removed_bridges,
      }
      for step in design.steps
    ],
    "elapsedMs": elapsed_ms,
  }
