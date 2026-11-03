"""Maximum flow with Edmonds-Karp (Ford-Fulkerson using BFS paths).

The grid becomes a flow network with two extra nodes:

    source -> bus     capacity = power the bus can inject (supply_mw)
    bus -> sink       capacity = power the bus consumes (load_mw)
    bus <-> bus       one per active branch, capacity = rateA in both directions

The demand is fully supplied when the maximum flow equals the total load. This
checks transport capacity only; it ignores the physics of power flow.

Complexity: O(V * E^2). BFS finds a shortest augmenting path in O(V + E), and
Edmonds and Karp proved that at most O(V * E) augmentations are needed.

The network is incremental: adding a branch keeps the current flow valid, so
max_flow() continues from it instead of starting from zero.
"""

import copy
from collections import deque
from collections.abc import Iterable
from typing import Self

from gridbalance.grid import Grid

EPSILON = 1e-9  # residual capacities below this count as zero (float rounding)
NO_ARC = -1


class FlowNetwork:
    def __init__(self, grid: Grid, active: Iterable[int] = ()) -> None:
        self.grid = grid
        self.source = len(grid.buses)
        self.sink = len(grid.buses) + 1
        self.node_count = len(grid.buses) + 2
        self.value = 0.0  # flow sent from source to sink so far

        # Residual graph as an arc list. Arcs are stored in pairs: arc e and its
        # reverse e ^ 1 (2 and 3, 4 and 5, ...). Pushing f units along e lowers
        # cap[e] by f and raises cap[e ^ 1] by f, which allows undoing it later.
        self.head: list[list[int]] = [[] for _ in range(self.node_count)]
        self.to: list[int] = []
        self.cap: list[float] = []
        self.arc_of: dict[int, int] = {}  # branch index -> its first arc

        supply, load = grid.supply_mw(), grid.load_mw()
        # A branch can never carry more than all the supply together, so this
        # finite value is equivalent to an unlimited (math.inf) capacity.
        self.unlimited = sum(supply)
        for bus, power in enumerate(supply):
            if power > 0:
                self.add_arc(self.source, bus, power, 0.0)
        for bus, power in enumerate(load):
            if power > 0:
                self.add_arc(bus, self.sink, power, 0.0)
        for index in active:
            self.add_branch(index)

    def copy(self) -> Self:
        """Independent copy: a flow computed once can be extended many times."""
        clone = copy.copy(self)
        clone.head = [list(arcs) for arcs in self.head]
        clone.to = list(self.to)
        clone.cap = list(self.cap)
        clone.arc_of = dict(self.arc_of)
        return clone

    def add_arc(self, u: int, v: int, forward: float, backward: float) -> int:
        arc = len(self.to)
        self.head[u].append(arc)
        self.to.append(v)
        self.cap.append(forward)
        self.head[v].append(arc + 1)
        self.to.append(u)
        self.cap.append(backward)
        return arc

    def add_branch(self, index: int) -> None:
        """
        Adds a branch to the network. Power can go either way, so both arcs of the
        pair start with the full capacity instead of the usual (capacity, 0).
        """
        if index in self.arc_of:
            return
        branch = self.grid.branches[index]
        capacity = min(branch.capacity_mva, self.unlimited)
        self.arc_of[index] = self.add_arc(
            branch.from_bus, branch.to_bus, capacity, capacity
        )

    def find_augmenting_path(self) -> list[int] | None:
        """Shortest source-sink path in the residual graph (BFS), as a list of arcs."""
        parent_arc = [NO_ARC] * self.node_count
        visited = [False] * self.node_count
        visited[self.source] = True
        queue = deque([self.source])
        while queue:
            u = queue.popleft()
            for arc in self.head[u]:
                v = self.to[arc]
                if not visited[v] and self.cap[arc] > EPSILON:
                    visited[v] = True
                    parent_arc[v] = arc
                    if v == self.sink:
                        return self.rebuild_path(parent_arc)
                    queue.append(v)
        return None

    def rebuild_path(self, parent_arc: list[int]) -> list[int]:
        path = []
        node = self.sink
        while node != self.source:
            arc = parent_arc[node]
            path.append(arc)
            node = self.to[arc ^ 1]  # the reverse arc points back to the tail
        return path

    def max_flow(self) -> float:
        """Augments along shortest paths until none is left; returns the total flow."""
        while (path := self.find_augmenting_path()) is not None:
            bottleneck = min(self.cap[arc] for arc in path)
            for arc in path:
                self.cap[arc] -= bottleneck
                self.cap[arc ^ 1] += bottleneck
            self.value += bottleneck
        return self.value

    def branch_flow(self, index: int) -> float:
        """
        Net power on a branch, positive from 'from_bus' to 'to_bus'. With both arcs
        starting at capacity c and a flow f: cap[e] = c - f and cap[e ^ 1] = c + f.
        """
        arc = self.arc_of[index]
        return (self.cap[arc + 1] - self.cap[arc]) / 2

    def source_side(self) -> list[bool]:
        """
        Buses still reachable from the source in the residual graph. After
        max_flow(), the branches from this side to the other form a minimum cut:
        the bottleneck that limits the supply.
        """
        reachable = [False] * self.node_count
        reachable[self.source] = True
        queue = deque([self.source])
        while queue:
            u = queue.popleft()
            for arc in self.head[u]:
                v = self.to[arc]
                if not reachable[v] and self.cap[arc] > EPSILON:
                    reachable[v] = True
                    queue.append(v)
        return reachable[: len(self.grid.buses)]


def max_flow(grid: Grid, active: Iterable[int] | None = None) -> float:
    """Maximum power the active branches (all if None) can carry to the loads."""
    if active is None:
        active = range(len(grid.branches))
    return FlowNetwork(grid, active).max_flow()
