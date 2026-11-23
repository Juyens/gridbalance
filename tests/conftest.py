"""Shared helpers for the algorithm tests."""

import math
from pathlib import Path

import pytest

from gridbalance.grid import Branch, Bus, Generator, Grid
from gridbalance.osm import load_dataset
from gridbalance.zone import build_zone_grid

PERU = Path(__file__).resolve().parents[1] / "data" / "peru"
UPC_SAN_MIGUEL = (-12.0764, -77.0934)


def build_test_grid(
    node_count: int,
    edges: list[tuple],
    demands: list[float] | None = None,
    generators: list[tuple[int, float]] = (),
) -> Grid:
    """
    Small grid for tests; buses use their index as id.
    edges: (from_bus, to_bus, cost) or (from_bus, to_bus, cost, capacity); the
    capacity defaults to unlimited.
    generators: (bus, pmax) pairs.
    """
    demands = demands or [0.0] * node_count
    buses = tuple(
        Bus(index=i, id=i, demand_mw=demands[i], base_kv=110.0)
        for i in range(node_count)
    )
    branches = tuple(
        Branch(
            index=i,
            from_bus=edge[0],
            to_bus=edge[1],
            cost=edge[2],
            capacity_mva=edge[3] if len(edge) > 3 else math.inf,
        )
        for i, edge in enumerate(edges)
    )
    return Grid(
        name="test",
        buses=buses,
        branches=branches,
        generators=tuple(Generator(bus=bus, pmax_mw=pmax) for bus, pmax in generators),
        cost_unit="kUSD",
    )


@pytest.fixture
def make_grid():
    return build_test_grid


@pytest.fixture(scope="session")
def peru():
    return load_dataset(PERU)


@pytest.fixture(scope="session")
def upc_grid(peru):
    """Zone of 10 km around UPC San Miguel: more than 1000 buses."""
    return build_zone_grid(peru.zone(*UPC_SAN_MIGUEL, 10)).grid


@pytest.fixture(scope="session")
def lima_grid(peru):
    """Zone of 20 km around UPC San Miguel: the largest one the app accepts."""
    return build_zone_grid(peru.zone(*UPC_SAN_MIGUEL, 20)).grid
