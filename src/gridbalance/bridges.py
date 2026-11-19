"""Bridge detection with Tarjan's algorithm (iterative DFS)."""

UNVISITED = -1


def build_adjacency(grid, active):
  """G[u] = [(v, branch_index), ...] using only the active branches."""
  G = [[] for _ in grid.buses]  # noqa: N806
  for index in active:
    branch = grid.branches[index]
    G[branch.from_bus].append((branch.to_bus, index))
    G[branch.to_bus].append((branch.from_bus, index))
  return G


def find_bridges(grid, active=None):
  """Indices of the bridges of the active branches (all by default)."""
  if active is None:
    active = range(len(grid.branches))
  G = build_adjacency(grid, active)  # noqa: N806

  n = len(grid.buses)
  disc = [UNVISITED] * n
  low = [UNVISITED] * n
  result = []
  time = 0

  for root in range(n):
    if disc[root] != UNVISITED:
      continue
    disc[root] = low[root] = time
    time += 1
    #Each frame: (bus, branch used to reach it, iterator over its neighbors).
    stack = [(root, -1, iter(G[root]))]
    while stack:
      u, parent_branch, neighbors = stack[-1]
      step = next(neighbors, None)

      if step is None:  #u finished: report to its parent
        stack.pop()
        if stack:
          parent = stack[-1][0]
          if low[u] > disc[parent]:
            result.append(parent_branch)
          if low[u] < low[parent]:
            low[parent] = low[u]
        continue

      v, index = step
      #Skip only the branch used to arrive, not every branch to the parent.
      if index == parent_branch:
        continue
      if disc[v] != UNVISITED:  #back edge
        if disc[v] < low[u]:
          low[u] = disc[v]
      else:  #tree edge: go down into v
        disc[v] = low[v] = time
        time += 1
        stack.append((v, index, iter(G[v])))

  return result
