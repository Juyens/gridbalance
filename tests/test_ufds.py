from gridbalance.ufds import connected, count, find, union


def test_every_element_starts_alone():
    s = list(range(4))

    assert count(s) == 4
    assert [find(s, x) for x in range(4)] == [0, 1, 2, 3]
    assert not connected(s, 0, 1)


def test_union_merges_sets_transitively():
    s = list(range(5))
    rank = [0] * 5

    assert union(s, rank, 0, 1)
    assert union(s, rank, 1, 2)

    assert connected(s, 0, 2)
    assert not connected(s, 0, 3)
    assert count(s) == 3  # {0, 1, 2}, {3}, {4}


def test_union_inside_one_set_returns_false():
    s = list(range(3))
    rank = [0] * 3
    union(s, rank, 0, 1)
    union(s, rank, 1, 2)

    # 0 and 2 are already connected: this edge would close a cycle.
    assert not union(s, rank, 0, 2)
    assert count(s) == 1


def test_union_by_rank_keeps_the_taller_root():
    s = list(range(3))
    rank = [0] * 3
    union(s, rank, 0, 1)  # tree rooted at 0 with rank 1
    union(s, rank, 2, 0)  # rank 0 tree must go under the rank 1 root

    assert find(s, 2) == 0
    assert rank[0] == 1


def test_find_compresses_the_path():
    s = [0, 0, 1, 2]
    # Build the chain 3 -> 2 -> 1 -> 0 by hand to force a deep tree.

    assert find(s, 3) == 0
    assert s == [0, 0, 0, 0]
