"""Greedy reinforcement of the minimum spanning tree, driven by three weights.

The MST is the cheapest connected network, but every branch in it is a bridge and
it supplies only part of the demand. Reinforcing it means adding back some of the
other branches (the candidates). Finding the cheapest set of branches that removes
every bridge is already NP-complete (Eswaran and Tarjan, 1976), so we use a greedy
heuristic. Each step adds the candidate with the highest score

    score(e) =   w_robustness * bridges_removed(e) / R
               + w_supply     * supply_gain(e)     / S
               - w_cost       * cost(e)            / C

and it stops when no candidate has a positive score. R, S and C are the totals of
adding every candidate: the bridges removed, the extra supply and the extra cost.
Dividing by them turns each term into a fraction of the most that can be gained or
spent, so the three terms are comparable and the weights set the trade-off.
"""

from collections import deque
from dataclasses import dataclass

from gridbalance.bridges import find_bridges
from gridbalance.flow import FlowNetwork, max_flow
from gridbalance.grid import Grid
from gridbalance.mst import kruskal
from gridbalance.ufds import DisjointSets

NO_PARENT = -1
EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class Weights:
    cost: float
    robustness: float
    supply: float

    def normalized(self) -> "Weights":
        """Same proportions scaled to add up to 1."""
        total = self.cost + self.robustness + self.supply
        if min(self.cost, self.robustness, self.supply) < 0 or total <= 0:
            raise ValueError("weights must be non-negative and not all zero")
        return Weights(self.cost / total, self.robustness / total, self.supply / total)


@dataclass(frozen=True, slots=True)
class Step:
    """Network totals right after the greedy added 'branch'."""

    branch: int
    cost: float
    bridges: int
    supplied_mw: float


@dataclass(frozen=True, slots=True)
class Design:
    tree: tuple[int, ...]  # MST branches
    added: tuple[int, ...]  # reinforcement branches, in the order they were chosen
    cost: float
    bridges: int
    supplied_mw: float
    steps: tuple[Step, ...]

    @property
    def branches(self) -> tuple[int, ...]:
        return self.tree + self.added


class BridgeTracker:
    """
    Bridges of a spanning tree while non-tree branches are added to it.

    Adding the branch (u, v) closes a cycle with the tree path from u to v, so every
    tree branch on that path stops being a bridge. Buses joined by tree branches
    that are no longer bridges are merged in a UFDS, and top[root] keeps the bus of
    each group closest to the tree root. Walking up from group top to group top
    then steps only over bridges, which makes counting them fast.
    """

    def __init__(self, grid: Grid, tree: list[int]) -> None:
        bus_count = len(grid.buses)
        neighbors: list[list[int]] = [[] for _ in range(bus_count)]
        for index in tree:
            branch = grid.branches[index]
            neighbors[branch.from_bus].append(branch.to_bus)
            neighbors[branch.to_bus].append(branch.from_bus)

        # Root every tree of the forest with BFS to get parent and depth.
        self.parent = [NO_PARENT] * bus_count
        self.depth = [0] * bus_count
        visited = [False] * bus_count
        for root in range(bus_count):
            if visited[root]:
                continue
            visited[root] = True
            queue = deque([root])
            while queue:
                u = queue.popleft()
                for v in neighbors[u]:
                    if not visited[v]:
                        visited[v] = True
                        self.parent[v] = u
                        self.depth[v] = self.depth[u] + 1
                        queue.append(v)

        self.sets = DisjointSets(bus_count)
        self.top = list(range(bus_count))
        self.count = len(tree)  # in a tree every branch is a bridge

    def group_top(self, bus: int) -> int:
        return self.top[self.sets.find(bus)]

    def walk(self, u: int, v: int, remove: bool) -> int:
        """Bridges on the tree path from u to v; 'remove' marks them as covered."""
        x, y = self.group_top(u), self.group_top(v)
        found = 0
        while x != y:
            # The deeper top cannot be an ancestor of the other one, so the tree
            # branch to its parent lies on the path, and it is a bridge.
            if self.depth[x] < self.depth[y]:
                x, y = y, x
            parent = self.parent[x]
            found += 1
            if remove:
                parent_top = self.group_top(parent)
                self.sets.union(x, parent)
                self.top[self.sets.find(x)] = parent_top
            x = self.group_top(parent)
        if remove:
            self.count -= found
        return found

    def bridges_on_path(self, u: int, v: int) -> int:
        return self.walk(u, v, remove=False)

    def remove_bridges_on_path(self, u: int, v: int) -> int:
        return self.walk(u, v, remove=True)


class Reinforcer:
    """
    Everything that does not depend on the weights is computed once per grid, so
    each call to design() only runs the greedy loop.
    """

    def __init__(self, grid: Grid) -> None:
        self.grid = grid
        self.tree = kruskal(grid)
        in_tree = set(self.tree)
        self.candidates = [i for i in range(len(grid.branches)) if i not in in_tree]
        self.tree_cost = sum(grid.branches[i].cost for i in self.tree)

        self.tree_flow = FlowNetwork(grid, self.tree)
        self.tree_flow.max_flow()
        self.full_flow = max_flow(grid)
        self.full_bridges = len(find_bridges(grid))

        # Totals of adding every candidate, used to normalize the score terms.
        self.max_bridges_removed = len(self.tree) - self.full_bridges
        self.max_supply_gain = self.full_flow - self.tree_flow.value
        self.max_extra_cost = grid.total_cost() - self.tree_cost

    def design(self, weights: Weights) -> Design:
        w = weights.normalized()
        tracker = BridgeTracker(self.grid, self.tree)
        network = self.tree_flow.copy()
        remaining = list(self.candidates)
        # Bridges each candidate would remove. They can only go down as branches
        # are added, so a stored value is an upper bound of the current one.
        removable = {
            i: tracker.bridges_on_path(
                self.grid.branches[i].from_bus, self.grid.branches[i].to_bus
            )
            for i in remaining
        }
        cost = self.tree_cost
        added: list[int] = []
        steps: list[Step] = []

        while remaining:
            gains = self.supply_gains(network, w, remaining)
            # Lazy evaluation: rank by the upper bound and recount the bridges only
            # while a candidate could still beat the best exact score found.
            upper = {i: self.score(w, i, removable[i], gains[i]) for i in remaining}
            ranked = sorted(remaining, key=upper.__getitem__, reverse=True)
            best, best_score = None, 0.0
            for i in ranked:
                if upper[i] <= best_score:
                    break
                branch = self.grid.branches[i]
                removable[i] = tracker.bridges_on_path(branch.from_bus, branch.to_bus)
                exact = self.score(w, i, removable[i], gains[i])
                if exact > best_score:
                    best, best_score = i, exact
            if best is None:
                break

            branch = self.grid.branches[best]
            tracker.remove_bridges_on_path(branch.from_bus, branch.to_bus)
            network.add_branch(best)
            network.max_flow()
            cost += branch.cost
            remaining.remove(best)
            added.append(best)
            steps.append(Step(best, cost, tracker.count, network.value))

        return Design(
            tree=tuple(self.tree),
            added=tuple(added),
            cost=cost,
            bridges=tracker.count,
            supplied_mw=network.value,
            steps=tuple(steps),
        )

    def score(
        self, w: Weights, i: int, bridges_removed: int, supply_gain: float
    ) -> float:
        return (
            w.robustness * ratio(bridges_removed, self.max_bridges_removed)
            + w.supply * ratio(supply_gain, self.max_supply_gain)
            - w.cost * ratio(self.grid.branches[i].cost, self.max_extra_cost)
        )

    def supply_gains(
        self, network: FlowNetwork, w: Weights, candidates: list[int]
    ) -> dict[int, float]:
        """
        Estimated extra supply of each candidate. The exact gain would need a max
        flow per candidate; instead we use the minimum cut, the bottleneck of the
        current flow: only a branch that crosses it can raise the flow, by at most
        its capacity and the demand still unmet.
        """
        unmet = self.full_flow - network.value
        if w.supply == 0 or unmet <= EPSILON:
            return dict.fromkeys(candidates, 0.0)
        source_side = network.source_side()
        gains = {}
        for i in candidates:
            branch = self.grid.branches[i]
            crosses_cut = source_side[branch.from_bus] != source_side[branch.to_bus]
            gains[i] = min(branch.capacity_mva, unmet) if crosses_cut else 0.0
        return gains


def ratio(part: float, total: float) -> float:
    return part / total if total > EPSILON else 0.0
