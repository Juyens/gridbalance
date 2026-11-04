"""Minimum spanning tree with Kruskal's algorithm."""

from gridbalance.ufds import union


def kruskal(grid):
  """Branch indices of a minimum spanning tree, or forest if disconnected."""
  n = len(grid.buses)
  s = list(range(n))
  rank = [0] * n
  e = [[b.from_bus, b.to_bus, b.cost, b.index] for b in grid.branches]
  #Ties are broken by index so the result is always the same.
  e = sorted(e, key=lambda item: (item[2], item[3]))
  result = []
  i = 0
  while i < len(e) and len(result) < n - 1:
    a = e[i][0]
    b = e[i][1]
    index = e[i][3]
    if union(s, rank, a, b):
      result.append(index)
    i += 1
  return result
