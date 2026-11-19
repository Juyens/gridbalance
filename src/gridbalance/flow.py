"""Maximum flow with Edmonds-Karp (BFS augmenting paths)."""

import copy
from collections import deque

EPSILON = 1e-9  #residual capacities below this count as zero
NO_ARC = -1


class FlowNetwork:
  """Grid as a flow network; branches can be added incrementally."""

  def __init__(self, grid, active=()):
    self.grid = grid
    self.source = len(grid.buses)
    self.sink = len(grid.buses) + 1
    self.n = len(grid.buses) + 2
    self.value = 0.0  #flow sent from source to sink so far

    #Arcs are stored in pairs: arc e and its reverse e ^ 1.
    self.head = [[] for _ in range(self.n)]
    self.to = []
    self.cap = []
    self.arc_of = {}  #branch index -> its first arc

    supply, load = grid.supply_mw(), grid.load_mw()
    #No branch can carry more than all the supply together.
    self.unlimited = sum(supply)
    for u, power in enumerate(supply):
      if power > 0:
        self.add_arc(self.source, u, power, 0.0)
    for u, power in enumerate(load):
      if power > 0:
        self.add_arc(u, self.sink, power, 0.0)
    for index in active:
      self.add_branch(index)

  def copy(self):
    """Independent copy, so a flow can be extended many times."""
    clone = copy.copy(self)
    clone.head = [list(arcs) for arcs in self.head]
    clone.to = list(self.to)
    clone.cap = list(self.cap)
    clone.arc_of = dict(self.arc_of)
    return clone

  def add_arc(self, u, v, forward, backward):
    arc = len(self.to)
    self.head[u].append(arc)
    self.to.append(v)
    self.cap.append(forward)
    self.head[v].append(arc + 1)
    self.to.append(u)
    self.cap.append(backward)
    return arc

  def add_branch(self, index):
    """Adds a branch with full capacity in both directions."""
    if index in self.arc_of:
      return
    branch = self.grid.branches[index]
    capacity = min(branch.capacity_mva, self.unlimited)
    self.arc_of[index] = self.add_arc(
      branch.from_bus, branch.to_bus, capacity, capacity
    )

  def find_augmenting_path(self):
    """Shortest source-sink path in the residual graph, as a list of arcs."""
    parent = [NO_ARC] * self.n
    visited = [False] * self.n
    visited[self.source] = True
    queue = deque([self.source])
    while queue:
      u = queue.popleft()
      for arc in self.head[u]:
        v = self.to[arc]
        if not visited[v] and self.cap[arc] > EPSILON:
          visited[v] = True
          parent[v] = arc
          if v == self.sink:
            return self.rebuild_path(parent)
          queue.append(v)
    return None

  def rebuild_path(self, parent):
    path = []
    v = self.sink
    while v != self.source:
      arc = parent[v]
      path.append(arc)
      v = self.to[arc ^ 1]  #the reverse arc points back to the tail
    return path

  def max_flow(self):
    """Augments along shortest paths until none is left."""
    path = self.find_augmenting_path()
    while path is not None:
      bottleneck = min(self.cap[arc] for arc in path)
      for arc in path:
        self.cap[arc] -= bottleneck
        self.cap[arc ^ 1] += bottleneck
      self.value += bottleneck
      path = self.find_augmenting_path()
    return self.value

  def branch_flow(self, index):
    """Net power on a branch, positive from from_bus to to_bus."""
    arc = self.arc_of[index]
    return (self.cap[arc + 1] - self.cap[arc]) / 2

  def source_side(self):
    """Buses still reachable from the source in the residual graph."""
    reachable = [False] * self.n
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


def max_flow(grid, active=None):
  """Maximum power the active branches (all if None) can carry to the loads."""
  if active is None:
    active = range(len(grid.branches))
  return FlowNetwork(grid, active).max_flow()
