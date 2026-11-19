import random
from pathlib import Path

from gridbalance.bridges import find_bridges
from gridbalance.grid import load_grid
from gridbalance.mst import kruskal
from gridbalance.ufds import count, union

CASES_DIR = Path(__file__).resolve().parents[1] / "cases"


def component_count(grid, active):
    s = list(range(len(grid.buses)))
    rank = [0] * len(grid.buses)
    for i in active:
        branch = grid.branches[i]
        union(s, rank, branch.from_bus, branch.to_bus)
    return count(s)


def brute_force_bridges(grid):
    """A branch is a bridge if removing it increases the number of components."""
    everything = range(len(grid.branches))
    base = component_count(grid, everything)
    return sorted(
        i
        for i in everything
        if component_count(grid, [j for j in everything if j != i]) > base
    )


def test_path_is_all_bridges(make_grid):
    grid = make_grid(4, [(0, 1, 1), (1, 2, 1), (2, 3, 1)])

    assert sorted(find_bridges(grid)) == [0, 1, 2]


def test_cycle_has_no_bridges(make_grid):
    grid = make_grid(4, [(0, 1, 1), (1, 2, 1), (2, 3, 1), (3, 0, 1)])

    assert find_bridges(grid) == []


def test_two_cycles_joined_by_one_branch(make_grid):
    # Triangle 0-1-2, triangle 3-4-5, and branch 6 (2-3) joining them.
    grid = make_grid(
        6,
        [(0, 1, 1), (1, 2, 1), (2, 0, 1), (3, 4, 1), (4, 5, 1), (5, 3, 1), (2, 3, 1)],
    )

    assert find_bridges(grid) == [6]


def test_parallel_branches_are_not_bridges(make_grid):
    grid = make_grid(3, [(0, 1, 1), (0, 1, 1), (1, 2, 1)])

    assert find_bridges(grid) == [2]


def test_only_active_branches_count(make_grid):
    grid = make_grid(3, [(0, 1, 1), (1, 2, 1), (2, 0, 1)])

    assert find_bridges(grid) == []
    assert sorted(find_bridges(grid, active=[0, 1])) == [0, 1]


def test_matches_brute_force_on_random_graphs(make_grid):
    rng = random.Random(2026)
    for _ in range(50):
        node_count = rng.randint(2, 9)
        edges = [
            (*rng.sample(range(node_count), 2), 1) for _ in range(rng.randint(1, 12))
        ]
        grid = make_grid(node_count, edges)

        assert sorted(find_bridges(grid)) == brute_force_bridges(grid)


def test_polish_grid_and_its_mst():
    grid = load_grid(CASES_DIR / "case2383wp.m")

    # Same count as the Hito 1 report.
    assert len(find_bridges(grid)) == 644
    # A tree has no cycles, so every one of its branches is a bridge.
    tree = kruskal(grid)
    assert sorted(find_bridges(grid, active=tree)) == sorted(tree)
