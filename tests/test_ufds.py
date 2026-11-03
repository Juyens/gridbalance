from gridbalance.ufds import DisjointSets


def test_every_element_starts_alone():
    sets = DisjointSets(4)

    assert sets.count == 4
    assert [sets.find(x) for x in range(4)] == [0, 1, 2, 3]
    assert not sets.connected(0, 1)


def test_union_merges_sets_transitively():
    sets = DisjointSets(5)

    assert sets.union(0, 1)
    assert sets.union(1, 2)

    assert sets.connected(0, 2)
    assert not sets.connected(0, 3)
    assert sets.count == 3  # {0, 1, 2}, {3}, {4}


def test_union_inside_one_set_returns_false():
    sets = DisjointSets(3)
    sets.union(0, 1)
    sets.union(1, 2)

    # 0 and 2 are already connected: this edge would close a cycle.
    assert not sets.union(0, 2)
    assert sets.count == 1


def test_union_by_rank_keeps_the_taller_root():
    sets = DisjointSets(3)
    sets.union(0, 1)  # tree rooted at 0 with rank 1
    sets.union(2, 0)  # rank 0 tree must go under the rank 1 root

    assert sets.find(2) == 0
    assert sets.rank[0] == 1


def test_find_compresses_the_path():
    sets = DisjointSets(4)
    # Build the chain 3 -> 2 -> 1 -> 0 by hand to force a deep tree.
    sets.parent = [0, 0, 1, 2]

    assert sets.find(3) == 0
    assert sets.parent == [0, 0, 0, 0]
