"""Union-Find over a plain parent list."""


def find(s, a):
  """Root of the set that contains a, with path compression."""
  i = a
  while s[i] != i:
    i = s[i]
  root = i
  i = a
  while s[i] != i:
    parent = s[i]
    s[i] = root
    i = parent
  return root


def union(s, rank, a, b):
  """Joins the sets of a and b; returns False if they were already joined."""
  ra = find(s, a)
  rb = find(s, b)
  if ra == rb:
    return False
  #Union by rank: hang the shorter tree under the taller one.
  if rank[ra] < rank[rb]:
    ra, rb = rb, ra
  s[rb] = ra
  if rank[ra] == rank[rb]:
    rank[ra] += 1
  return True


def connected(s, a, b):
  """True when a and b are in the same set."""
  return find(s, a) == find(s, b)


def count(s):
  """Number of disjoint sets."""
  total = 0
  for i in range(len(s)):
    if s[i] == i:
      total += 1
  return total
