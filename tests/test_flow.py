import random
from itertools import product
from pathlib import Path

import pytest

from gridbalance.flow import FlowNetwork, max_flow
from gridbalance.grid import load_grid
from gridbalance.mst import kruskal

CASES_DIR = Path(__file__).resolve().parents[1] / "cases"


def brute_force_min_cut(grid, active):
    """
    Max-flow min-cut theorem: the maximum flow equals the cheapest cut. Tries
    every split of the buses into a source side S and a sink side; a cut pays
    the supply outside S, the load inside S and every branch crossing it.
    """
    supply, load = grid.supply_mw(), grid.load_mw()
    best = float("inf")
    for in_source_side in product([False, True], repeat=len(grid.buses)):
        cut = sum(
            s for s, inside in zip(supply, in_source_side, strict=True) if not inside
        )
        cut += sum(d for d, inside in zip(load, in_source_side, strict=True) if inside)
        for i in active:
            branch = grid.branches[i]
            if in_source_side[branch.from_bus] != in_source_side[branch.to_bus]:
                cut += min(branch.capacity_mva, sum(supply))
        best = min(best, cut)
    return best


def test_single_path_is_limited_by_its_weakest_branch(make_grid):
    grid = make_grid(
        3, [(0, 1, 1, 50), (1, 2, 1, 80)], demands=[0, 0, 60], generators=[(0, 100)]
    )

    assert max_flow(grid) == pytest.approx(50)


def test_parallel_paths_add_up(make_grid):
    # Two routes from 0 to 3: through 1 (cap 30) and through 2 (cap 40).
    grid = make_grid(
        4,
        [(0, 1, 1, 30), (1, 3, 1, 30), (0, 2, 1, 40), (2, 3, 1, 40)],
        demands=[0, 0, 0, 100],
        generators=[(0, 100)],
    )

    assert max_flow(grid) == pytest.approx(70)


def test_flow_is_limited_by_supply_and_load(make_grid):
    grid = make_grid(2, [(0, 1, 1)], demands=[0, 80], generators=[(0, 50)])
    assert max_flow(grid) == pytest.approx(50)

    grid = make_grid(2, [(0, 1, 1)], demands=[0, 30], generators=[(0, 50)])
    assert max_flow(grid) == pytest.approx(30)


def test_branches_carry_power_both_ways(make_grid):
    # Generator at bus 2, load at bus 0: power flows against the branch direction.
    grid = make_grid(
        3, [(0, 1, 1, 40), (1, 2, 1, 40)], demands=[25, 0, 0], generators=[(2, 100)]
    )
    network = FlowNetwork(grid, active=[0, 1])

    assert network.max_flow() == pytest.approx(25)
    assert network.branch_flow(0) == pytest.approx(-25)
    assert network.branch_flow(1) == pytest.approx(-25)


def test_negative_demand_acts_as_supply(make_grid):
    grid = make_grid(2, [(0, 1, 1)], demands=[-20, 20])

    assert max_flow(grid) == pytest.approx(20)


def test_source_side_marks_the_minimum_cut(make_grid):
    # Branch 1 (1-2, cap 10) is the bottleneck between the generator and the load.
    grid = make_grid(
        3, [(0, 1, 1, 100), (1, 2, 1, 10)], demands=[0, 0, 50], generators=[(0, 100)]
    )
    network = FlowNetwork(grid, active=[0, 1])
    network.max_flow()

    assert network.source_side() == [True, True, False]


def random_grid(make_grid, rng):
    node_count = rng.randint(2, 7)
    edges = [
        (*rng.sample(range(node_count), 2), 1, rng.choice([5, 10, 20, 40]))
        for _ in range(rng.randint(1, 10))
    ]
    demands = [rng.choice([0, 0, 10, 25, -5]) for _ in range(node_count)]
    generators = [(rng.randrange(node_count), rng.choice([20, 50])) for _ in range(2)]
    return make_grid(node_count, edges, demands=demands, generators=generators)


def test_matches_brute_force_min_cut(make_grid):
    rng = random.Random(2026)
    for _ in range(40):
        grid = random_grid(make_grid, rng)
        active = range(len(grid.branches))

        assert max_flow(grid) == pytest.approx(brute_force_min_cut(grid, active))


def test_incremental_flow_matches_flow_from_scratch(make_grid):
    rng = random.Random(7)
    for _ in range(40):
        grid = random_grid(make_grid, rng)
        network = FlowNetwork(grid)
        order = rng.sample(range(len(grid.branches)), len(grid.branches))

        for added, index in enumerate(order, start=1):
            network.add_branch(index)
            assert network.max_flow() == pytest.approx(
                max_flow(grid, active=order[:added])
            )


def test_polish_grid_and_its_mst():
    grid = load_grid(CASES_DIR / "case2383wp.m")

    # The full grid supplies the whole positive load.
    assert max_flow(grid) == pytest.approx(sum(grid.load_mw()))
    # The MST is cheap but carries only about 55% of it.
    assert max_flow(grid, active=kruskal(grid)) == pytest.approx(13641, abs=1)
