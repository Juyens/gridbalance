import random
from itertools import combinations
from pathlib import Path

import pytest

from gridbalance.grid import load_grid
from gridbalance.mst import kruskal
from gridbalance.ufds import count, union

CASES_DIR = Path(__file__).resolve().parents[1] / "cases"

# (from_bus, to_bus, cost); the branch index is the position in the list.
TEXTBOOK_EDGES = [
    (0, 1, 4),  # 0
    (0, 2, 1),  # 1
    (1, 2, 2),  # 2
    (1, 3, 5),  # 3
    (2, 3, 8),  # 4
    (3, 4, 3),  # 5
    (2, 4, 9),  # 6
]


def tree_cost(grid, tree):
    return sum(grid.branches[i].cost for i in tree)


def is_spanning_tree(grid, edge_indices):
    s = list(range(len(grid.buses)))
    rank = [0] * len(grid.buses)
    for i in edge_indices:
        branch = grid.branches[i]
        if not union(s, rank, branch.from_bus, branch.to_bus):
            return False  # cycle
    return count(s) == 1


def brute_force_mst_cost(grid):
    """Tries every subset of V-1 branches: only feasible for tiny graphs."""
    size = len(grid.buses) - 1
    return min(
        tree_cost(grid, subset)
        for subset in combinations(range(len(grid.branches)), size)
        if is_spanning_tree(grid, subset)
    )


def test_textbook_graph(make_grid):
    grid = make_grid(5, TEXTBOOK_EDGES)

    tree = kruskal(grid)

    # Takes 0-2 (1), 1-2 (2), 3-4 (3), skips 0-1 (4, cycle), takes 1-3 (5).
    assert tree == [1, 2, 5, 3]
    assert tree_cost(grid, tree) == 11


def test_matches_brute_force_on_random_graphs(make_grid):
    rng = random.Random(2026)
    for _ in range(30):
        node_count = rng.randint(2, 6)
        # A random path guarantees the graph is connected; then add extra edges.
        order = rng.sample(range(node_count), node_count)
        edges = [
            (order[i], order[i + 1], rng.randint(1, 20)) for i in range(node_count - 1)
        ]
        for _ in range(rng.randint(0, 5)):
            u, v = rng.sample(range(node_count), 2)
            edges.append((u, v, rng.randint(1, 20)))
        grid = make_grid(node_count, edges)

        tree = kruskal(grid)

        assert is_spanning_tree(grid, tree)
        assert tree_cost(grid, tree) == brute_force_mst_cost(grid)


def test_parallel_branches_keep_the_cheaper_one(make_grid):
    grid = make_grid(2, [(0, 1, 7), (0, 1, 3)])

    assert kruskal(grid) == [1]


def test_disconnected_grid_gives_a_forest(make_grid):
    # Components {0, 1, 2} and {3, 4}.
    grid = make_grid(5, [(0, 1, 1), (1, 2, 1), (0, 2, 5), (3, 4, 2)])

    tree = kruskal(grid)

    assert sorted(tree) == [0, 1, 3]  # V - components = 5 - 2 edges


def test_polish_grid():
    grid = load_grid(CASES_DIR / "case2383wp.m")

    tree = kruskal(grid)

    assert len(tree) == len(grid.buses) - 1
    assert is_spanning_tree(grid, tree)
    assert tree_cost(grid, tree) == pytest.approx(10059, abs=1)
