def test_supply_and_load_split_negative_demand(make_grid):
    grid = make_grid(
        3,
        [(0, 1, 1), (1, 2, 1)],
        demands=[-5, 40, 0],
        generators=[(0, 100), (0, 20)],
    )

    assert grid.supply_mw() == [125, 0, 0]
    assert grid.load_mw() == [0, 40, 0]


def test_total_cost_adds_every_branch(make_grid):
    assert make_grid(3, [(0, 1, 2.5), (1, 2, 4)]).total_cost() == 6.5
