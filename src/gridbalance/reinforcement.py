"""Greedy reinforcement of the minimum spanning tree."""

from collections import deque

from gridbalance.bridges import find_bridges
from gridbalance.flow import FlowNetwork, max_flow
from gridbalance.mst import kruskal
from gridbalance.ufds import find, union

NO_PARENT = -1
EPSILON = 1e-9


class Weights:
  """Cost, robustness and supply weights."""

  def __init__(self, cost, robustness, supply):
    self.cost = cost
    self.robustness = robustness
    self.supply = supply

  def normalized(self):
    """Same proportions scaled to add up to 1."""
    total = self.cost + self.robustness + self.supply
    if min(self.cost, self.robustness, self.supply) < 0 or total <= 0:
      raise ValueError("weights must be non-negative and not all zero")
    return Weights(self.cost / total, self.robustness / total, self.supply / total)

  def __eq__(self, other):
    return (
      isinstance(other, Weights)
      and self.cost == other.cost
      and self.robustness == other.robustness
      and self.supply == other.supply
    )

  def __repr__(self):
    return f"Weights({self.cost}, {self.robustness}, {self.supply})"


class Step:
  """Network totals right after the greedy added a branch."""

  def __init__(self, branch, cost, bridges, supplied_mw):
    self.branch = branch
    self.cost = cost
    self.bridges = bridges
    self.supplied_mw = supplied_mw

  def __eq__(self, other):
    return (
      isinstance(other, Step)
      and self.branch == other.branch
      and self.cost == other.cost
      and self.bridges == other.bridges
      and self.supplied_mw == other.supplied_mw
    )


class Design:
  """Branches chosen by the greedy, with the totals after each step."""

  def __init__(self, tree, added, cost, bridges, supplied_mw, steps):
    self.tree = tree
    self.added = added
    self.cost = cost
    self.bridges = bridges
    self.supplied_mw = supplied_mw
    self.steps = steps

  @property
  def branches(self):
    return self.tree + self.added

  def __eq__(self, other):
    return (
      isinstance(other, Design)
      and self.tree == other.tree
      and self.added == other.added
      and self.cost == other.cost
      and self.bridges == other.bridges
      and self.supplied_mw == other.supplied_mw
      and self.steps == other.steps
    )


class BridgeTracker:
  """Bridges of a spanning tree while non-tree branches are added to it."""

  def __init__(self, grid, tree):
    n = len(grid.buses)
    G = [[] for _ in range(n)]  # noqa: N806
    for index in tree:
      branch = grid.branches[index]
      G[branch.from_bus].append(branch.to_bus)
      G[branch.to_bus].append(branch.from_bus)

    #Root every tree of the forest with BFS to get parent and depth.
    self.parent = [NO_PARENT] * n
    self.depth = [0] * n
    visited = [False] * n
    for root in range(n):
      if visited[root]:
        continue
      visited[root] = True
      queue = deque([root])
      while queue:
        u = queue.popleft()
        for v in G[u]:
          if not visited[v]:
            visited[v] = True
            self.parent[v] = u
            self.depth[v] = self.depth[u] + 1
            queue.append(v)

    self.s = list(range(n))
    self.rank = [0] * n
    self.top = list(range(n))
    self.count = len(tree)  #in a tree every branch is a bridge

  def group_top(self, bus):
    return self.top[find(self.s, bus)]

  def walk(self, u, v, remove):
    """Bridges on the tree path from u to v; remove marks them as covered."""
    x, y = self.group_top(u), self.group_top(v)
    total = 0
    while x != y:
      #The deeper top cannot be an ancestor of the other one.
      if self.depth[x] < self.depth[y]:
        x, y = y, x
      parent = self.parent[x]
      total += 1
      if remove:
        parent_top = self.group_top(parent)
        union(self.s, self.rank, x, parent)
        self.top[find(self.s, x)] = parent_top
      x = self.group_top(parent)
    if remove:
      self.count -= total
    return total

  def bridges_on_path(self, u, v):
    return self.walk(u, v, False)

  def remove_bridges_on_path(self, u, v):
    return self.walk(u, v, True)


class Reinforcer:
  """Precomputes everything that does not depend on the weights."""

  def __init__(self, grid):
    self.grid = grid
    self.tree = kruskal(grid)
    in_tree = set(self.tree)
    self.candidates = [i for i in range(len(grid.branches)) if i not in in_tree]
    self.tree_cost = sum(grid.branches[i].cost for i in self.tree)

    self.tree_flow = FlowNetwork(grid, self.tree)
    self.tree_flow.max_flow()
    self.full_flow = max_flow(grid)
    self.full_bridges = len(find_bridges(grid))

    #Totals of adding every candidate, used to normalize the score terms.
    self.max_bridges_removed = len(self.tree) - self.full_bridges
    self.max_supply_gain = self.full_flow - self.tree_flow.value
    self.max_extra_cost = grid.total_cost() - self.tree_cost

  def design(self, weights):
    w = weights.normalized()
    tracker = BridgeTracker(self.grid, self.tree)
    network = self.tree_flow.copy()
    remaining = list(self.candidates)
    #Bridges each candidate would remove. They can only go down as branches
    #are added, so a stored value is an upper bound of the current one.
    removable = {
      i: tracker.bridges_on_path(
        self.grid.branches[i].from_bus, self.grid.branches[i].to_bus
      )
      for i in remaining
    }
    cost = self.tree_cost
    added = []
    steps = []

    while remaining:
      gains = self.supply_gains(network, w, remaining)
      #Lazy evaluation: rank by the upper bound and recount the bridges only
      #while a candidate could still beat the best exact score found.
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

  def score(self, w, i, bridges_removed, supply_gain):
    return (
      w.robustness * ratio(bridges_removed, self.max_bridges_removed)
      + w.supply * ratio(supply_gain, self.max_supply_gain)
      - w.cost * ratio(self.grid.branches[i].cost, self.max_extra_cost)
    )

  def supply_gains(self, network, w, candidates):
    """Estimated extra supply of each candidate, from the current min cut."""
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


def ratio(part, total):
  return part / total if total > EPSILON else 0.0
