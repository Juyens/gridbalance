"""Union-Find Disjoint Sets (UFDS).

Keeps elements 0..n-1 split into disjoint sets. Each set is a tree stored in
'parent'; the root of the tree identifies the set.

    find(x)      -> root of the set that contains x
    union(a, b)  -> merges the sets of a and b

With union by rank and path compression, both run in O(alpha(n)) amortized time,
where alpha is the inverse Ackermann function (at most 4 for any real n).
"""


class DisjointSets:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))  # every element starts as its own root
        self.rank = [0] * size  # upper bound on the height of each root's tree
        self.count = size  # number of disjoint sets

    def find(self, x: int) -> int:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        # Path compression: point every node on the way directly to the root.
        while x != root:
            next_node = self.parent[x]
            self.parent[x] = root
            x = next_node
        return root

    def union(self, a: int, b: int) -> bool:
        """Merges the sets of a and b; returns False if they were already one set."""
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return False
        # Union by rank: hang the shorter tree under the taller one.
        if self.rank[root_a] < self.rank[root_b]:
            root_a, root_b = root_b, root_a
        self.parent[root_b] = root_a
        if self.rank[root_a] == self.rank[root_b]:
            self.rank[root_a] += 1
        self.count -= 1
        return True

    def connected(self, a: int, b: int) -> bool:
        return self.find(a) == self.find(b)
