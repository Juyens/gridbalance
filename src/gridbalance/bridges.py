"""Bridge detection with Tarjan's DFS-based algorithm.

A bridge is a branch whose failure splits the grid in two: no other path joins
its ends. One depth-first search labels every bus with:

    disc[u]  order in which the DFS discovers u
    low[u]   smallest 'disc' reachable from the subtree of u using at most one
             back edge (a branch to an already discovered bus)

The tree branch (parent, u) is a bridge when low[u] > disc[parent]: nothing below
u can reach parent or above without that branch.

Complexity: O(V + E), every bus and branch is visited a constant number of times.
"""

from collections.abc import Iterable

from gridbalance.grid import Grid

UNVISITED = -1


def build_adjacency(grid: Grid, active: Iterable[int]) -> list[list[tuple[int, int]]]:
    """adjacency[u] = [(v, branch_index), ...] using only the active branches."""
    adjacency: list[list[tuple[int, int]]] = [[] for _ in grid.buses]
    for index in active:
        branch = grid.branches[index]
        adjacency[branch.from_bus].append((branch.to_bus, index))
        adjacency[branch.to_bus].append((branch.from_bus, index))
    return adjacency


def find_bridges(grid: Grid, active: Iterable[int] | None = None) -> list[int]:
    """
    Indices of the bridges of the network formed by the active branches (all
    branches of the grid when 'active' is None).

    The DFS is iterative so large grids do not hit Python's recursion limit.
    We skip the parent by branch index, not by bus, so a parallel branch to the
    parent counts as a back edge and neither branch is reported as a bridge.
    """
    if active is None:
        active = range(len(grid.branches))
    adjacency = build_adjacency(grid, active)

    disc = [UNVISITED] * len(grid.buses)
    low = [UNVISITED] * len(grid.buses)
    bridges = []
    time = 0

    for root in range(len(grid.buses)):
        if disc[root] != UNVISITED:
            continue
        disc[root] = low[root] = time
        time += 1
        # Each frame: (bus, branch used to reach it, iterator over its neighbors).
        stack = [(root, -1, iter(adjacency[root]))]
        while stack:
            u, parent_branch, neighbors = stack[-1]
            step = next(neighbors, None)

            if step is None:  # u finished: report to its parent
                stack.pop()
                if stack:
                    parent = stack[-1][0]
                    low[parent] = min(low[parent], low[u])
                    if low[u] > disc[parent]:
                        bridges.append(parent_branch)
                continue

            v, branch_index = step
            if branch_index == parent_branch:
                continue
            if disc[v] != UNVISITED:  # back edge
                low[u] = min(low[u], disc[v])
            else:  # tree edge: go down into v
                disc[v] = low[v] = time
                time += 1
                stack.append((v, branch_index, iter(adjacency[v])))

    return bridges
