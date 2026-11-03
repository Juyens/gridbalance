"""Methods exposed to the frontend as window.pywebview.api.

pywebview runs every call in its own thread and turns the return value into JSON,
so methods return plain dicts and lists, with camelCase keys for TypeScript.
JSON has no infinity, so unlimited capacities are sent as null. Attributes start
with '_' so pywebview does not try to expose them to JavaScript.
"""

import base64
import json
import math
import threading
import time
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import webview

from gridbalance.bridges import find_bridges
from gridbalance.grid import Grid, load_grid
from gridbalance.reinforcement import Design, Reinforcer, Weights

LAYOUT_SUFFIX = ".layout.json"


class Api:
    def __init__(self, cases_dir: Path) -> None:
        self._cases_dir = cases_dir
        self._theme_path = Path.home() / ".gridbalance" / "theme"
        self._language_path = Path.home() / ".gridbalance" / "language"
        self._case_path: Path | None = None
        self._reinforcer: Reinforcer | None = None
        # One computation at a time: fast slider moves send calls in parallel.
        self._lock = threading.Lock()

    def ping(self) -> str:
        return f"Backend ready (gridbalance {version('gridbalance')})"

    def get_theme(self) -> str | None:
        try:
            theme = self._theme_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        return theme if theme in ("light", "dark") else None

    def set_theme(self, theme: str) -> None:
        if theme not in ("light", "dark"):
            raise ValueError("theme must be light or dark")
        self._theme_path.parent.mkdir(parents=True, exist_ok=True)
        self._theme_path.write_text(theme, encoding="utf-8")

    def get_language(self) -> str | None:
        try:
            language = self._language_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        return language if language in ("en", "es") else None

    def set_language(self, language: str) -> None:
        if language not in ("en", "es"):
            raise ValueError("language must be en or es")
        self._language_path.parent.mkdir(parents=True, exist_ok=True)
        self._language_path.write_text(language, encoding="utf-8")

    def list_cases(self) -> list[str]:
        """MATPOWER case files bundled in the cases folder."""
        return sorted(path.name for path in self._cases_dir.glob("*.m"))

    def load_case(self, file_name: str) -> dict[str, Any]:
        return self._load(self._cases_dir / file_name)

    def open_case(self) -> dict[str, Any] | None:
        """Lets the user pick any .m file; returns None if the dialog is cancelled."""
        paths = webview.windows[0].create_file_dialog(
            webview.FileDialog.OPEN, file_types=("MATPOWER case (*.m)",)
        )
        return self._load(Path(paths[0])) if paths else None

    def design(self, weights: dict[str, float]) -> dict[str, Any]:
        with self._lock:
            reinforcer = self._require_case()
            started = time.perf_counter()
            design = reinforcer.design(
                Weights(weights["cost"], weights["robustness"], weights["supply"])
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
        return design_to_json(reinforcer.grid, design, elapsed_ms)

    def save_layout(self, positions: list[list[float]]) -> None:
        """Stores bus positions next to the case file so the next load is instant."""
        with self._lock:
            reinforcer = self._require_case()
            if len(positions) != len(reinforcer.grid.buses):
                raise ValueError("one position per bus is required")
            layout = {"buses": len(positions), "positions": positions}
            layout_path(self._case_path).write_text(
                json.dumps(layout), encoding="utf-8"
            )

    def save_export(self, kind: str, content: str) -> bool:
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
        # Stage on the same filesystem so failed writes preserve existing files.
        with TemporaryDirectory(prefix=".gridbalance-", dir=target.parent) as directory:
            staging = Path(directory) / target.name
            staging.write_bytes(data)
            staging.replace(target)
        return True

    def _load(self, path: Path) -> dict[str, Any]:
        with self._lock:
            reinforcer = Reinforcer(load_grid(path))
            self._case_path, self._reinforcer = path, reinforcer
        return case_to_json(reinforcer, read_layout(path, len(reinforcer.grid.buses)))

    def _require_case(self) -> Reinforcer:
        if self._reinforcer is None:
            raise RuntimeError("no case loaded")
        return self._reinforcer


def layout_path(case_path: Path) -> Path:
    return case_path.with_name(case_path.stem + LAYOUT_SUFFIX)


def read_layout(case_path: Path, bus_count: int) -> list[list[float]] | None:
    """Cached positions, or None if missing or made for a different grid."""
    path = layout_path(case_path)
    if not path.exists():
        return None
    layout = json.loads(path.read_text(encoding="utf-8"))
    return layout["positions"] if layout.get("buses") == bus_count else None


def finite_or_none(value: float) -> float | None:
    return None if math.isinf(value) else value


def case_to_json(
    reinforcer: Reinforcer, positions: list[list[float]] | None
) -> dict[str, Any]:
    grid = reinforcer.grid
    supply, load = grid.supply_mw(), grid.load_mw()
    return {
        "name": grid.name,
        "costUnit": grid.cost_unit,
        "buses": [
            {
                "index": bus.index,
                "id": bus.id,
                "baseKv": bus.base_kv,
                "zone": bus.zone,
                "supplyMw": supply[bus.index],
                "loadMw": load[bus.index],
            }
            for bus in grid.buses
        ],
        "branches": [
            {
                "index": branch.index,
                "from": branch.from_bus,
                "to": branch.to_bus,
                "cost": branch.cost,
                "capacityMva": finite_or_none(branch.capacity_mva),
                "isTransformer": branch.is_transformer,
            }
            for branch in grid.branches
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
        "positions": positions,
    }


def design_to_json(grid: Grid, design: Design, elapsed_ms: float) -> dict[str, Any]:
    active = list(design.tree)
    remaining = set(active)
    steps = []
    for step in design.steps:
        active.append(step.branch)
        bridges = set(find_bridges(grid, active))
        steps.append(
            {
                "branch": step.branch,
                "cost": step.cost,
                "bridges": step.bridges,
                "suppliedMw": step.supplied_mw,
                "removedBridges": sorted(remaining - bridges),
            }
        )
        remaining = bridges
    return {
        "added": list(design.added),
        "bridgeBranches": sorted(remaining),
        "cost": design.cost,
        "bridges": design.bridges,
        "suppliedMw": design.supplied_mw,
        "steps": steps,
        "elapsedMs": elapsed_ms,
    }
