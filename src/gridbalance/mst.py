"""Minimum spanning tree with Kruskal's algorithm.

Branches are taken from cheapest to most expensive, and each one is kept only if
it joins two buses that are not connected yet. UFDS answers that question.

Complexity: O(E log E) to sort the branches, plus O(E alpha(V)) for the UFDS
operations, so O(E log E) overall.
"""

from gridbalance.grid import Grid
from gridbalance.ufds import DisjointSets


def kruskal(grid: Grid) -> list[int]:
    """
    Indices of the branches in a minimum spanning tree of the grid.
    If the grid is disconnected, it returns a minimum spanning forest: one tree
    per connected component.
    """
    sets = DisjointSets(len(grid.buses))
    tree = []
    # Ties are broken by index so the result is always the same.
    for branch in sorted(grid.branches, key=lambda b: (b.cost, b.index)):
        # union() returns False when both ends are already connected: the
        # branch would close a cycle.
        if sets.union(branch.from_bus, branch.to_bus):
            tree.append(branch.index)
            if sets.count == 1:  # every bus connected: no branch can be added
                break
    return tree
