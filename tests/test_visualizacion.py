from gridbalance.visualizacion import Adjshow, show


def test_adjshow_undirected_draws_each_edge_once():
    dot = Adjshow([[1], [0, 2], [1]])

    assert dot.source.count(" -- ") == 2


def test_adjshow_directed_keeps_every_arc():
    dot = Adjshow([[1], [2], []], directed=True)
    back = Adjshow([[2], [], [1]], directed=True)

    assert dot.source.count(" -> ") == 2
    assert "2 -> 1" in back.source


def test_adjshow_shows_weights():
    dot = Adjshow([[(1, 4)], [(0, 4), (2, 3)], [(1, 3)]])

    assert "label=4" in dot.source
    assert "label=3" in dot.source


def test_show_marks_the_tree_and_keeps_parallel_branches(make_grid):
    grid = make_grid(3, [(0, 1, 1), (0, 1, 2), (1, 2, 3)])

    dot = show(grid, tree=[0, 2])

    assert dot.source.count(" -- ") == 3
    assert dot.source.count("0 -- 1") == 2
    assert dot.source.count("color=red") == 2


def test_show_directed_uses_arrows(make_grid):
    grid = make_grid(2, [(0, 1, 1)])

    dot = show(grid, directed=True)

    assert dot.source.count(" -> ") == 1
