"""Shared helpers for the algorithm tests."""

import math

import pytest

from gridbalance.grid import Branch, Bus, Generator, Grid


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
        Bus(index=i, id=i, bus_type=1, demand_mw=demands[i], base_kv=110.0, zone=1)
        for i in range(node_count)
    )
    branches = tuple(
        Branch(
            index=i,
            from_bus=edge[0],
            to_bus=edge[1],
            cost=edge[2],
            capacity_mva=edge[3] if len(edge) > 3 else math.inf,
            is_transformer=False,
        )
        for i, edge in enumerate(edges)
    )
    return Grid(
        name="test",
        base_mva=100.0,
        buses=buses,
        branches=branches,
        generators=tuple(Generator(bus=bus, pmax_mw=pmax) for bus, pmax in generators),
        cost_unit="ohm",
    )


@pytest.fixture
def make_grid():
    return build_test_grid
