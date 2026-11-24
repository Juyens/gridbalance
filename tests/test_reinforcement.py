import random

import pytest

from gridbalance.bridges import find_bridges
from gridbalance.flow import max_flow
from gridbalance.mst import kruskal
from gridbalance.reinforcement import BridgeTracker, Reinforcer, Weights


def random_connected_grid(make_grid, rng):
    node_count = rng.randint(3, 9)
    order = rng.sample(range(node_count), node_count)
    # A random path keeps the grid connected; extra branches create cycles.
    edges = [
        (order[i], order[i + 1], rng.randint(1, 20), rng.choice([10, 20, 40]))
        for i in range(node_count - 1)
    ]
    for _ in range(rng.randint(1, 8)):
        u, v = rng.sample(range(node_count), 2)
        edges.append((u, v, rng.randint(1, 20), rng.choice([10, 20, 40])))
    demands = [rng.choice([0, 0, 15, 30]) for _ in range(node_count)]
    generators = [(rng.randrange(node_count), rng.choice([40, 80])) for _ in range(2)]
    return make_grid(node_count, edges, demands=demands, generators=generators)


def test_weights_are_normalized():
    assert Weights(2, 1, 1).normalized() == Weights(0.5, 0.25, 0.25)


@pytest.mark.parametrize("weights", [Weights(0, 0, 0), Weights(-1, 1, 1)])
def test_invalid_weights_are_rejected(weights):
    with pytest.raises(ValueError, match="non-negative"):
        weights.normalized()


def test_bridge_tracker_matches_tarjan(make_grid):
    rng = random.Random(2026)
    for _ in range(40):
        grid = random_connected_grid(make_grid, rng)
        tree = kruskal(grid)
        extra = [i for i in range(len(grid.branches)) if i not in set(tree)]
        rng.shuffle(extra)
        tracker = BridgeTracker(grid, tree)

        for added in range(1, len(extra) + 1):
            branch = grid.branches[extra[added - 1]]
            tracker.remove_bridges_on_path(branch.from_bus, branch.to_bus)
            assert tracker.count == len(find_bridges(grid, tree + extra[:added]))


def test_only_cost_keeps_the_tree(make_grid):
    grid = random_connected_grid(make_grid, random.Random(1))

    design = Reinforcer(grid).design(Weights(cost=1, robustness=0, supply=0))

    assert design.added == ()
    assert design.cost == pytest.approx(sum(grid.branches[i].cost for i in design.tree))


def test_only_robustness_removes_every_removable_bridge(make_grid):
    rng = random.Random(3)
    for _ in range(30):
        grid = random_connected_grid(make_grid, rng)

        design = Reinforcer(grid).design(Weights(cost=0, robustness=1, supply=0))

        assert design.bridges == len(find_bridges(grid))


def test_only_supply_reaches_the_full_grid_flow(make_grid):
    rng = random.Random(4)
    for _ in range(30):
        grid = random_connected_grid(make_grid, rng)

        design = Reinforcer(grid).design(Weights(cost=0, robustness=0, supply=1))

        assert design.supplied_mw == pytest.approx(max_flow(grid))


def test_steps_trace_the_design(make_grid):
    grid = random_connected_grid(make_grid, random.Random(5))

    design = Reinforcer(grid).design(Weights(1, 1, 1))

    assert [step.branch for step in design.steps] == list(design.added)
    for before, after in zip(design.steps, design.steps[1:], strict=False):
        assert after.cost > before.cost
        assert after.bridges <= before.bridges
        assert after.supplied_mw >= before.supplied_mw - 1e-9
    if design.steps:
        last = design.steps[-1]
        assert (last.cost, last.bridges, last.supplied_mw) == (
            design.cost,
            design.bridges,
            design.supplied_mw,
        )


@pytest.fixture(scope="module")
def upc_reinforcer(upc_grid):
    return Reinforcer(upc_grid)


def test_upc_trade_off(upc_reinforcer):
    grid = upc_reinforcer.grid
    cheap = upc_reinforcer.design(Weights(cost=0.6, robustness=0.2, supply=0.2))
    balanced = upc_reinforcer.design(Weights(1, 1, 1))
    robust = upc_reinforcer.design(Weights(cost=0, robustness=1, supply=1))

    assert cheap.cost < balanced.cost < robust.cost < grid.total_cost()
    assert cheap.bridges > balanced.bridges > robust.bridges
    # With no weight on cost, it is as robust and supplies as much as building
    # every possible line, while still being cheaper.
    assert robust.bridges == len(find_bridges(grid))
    assert robust.supplied_mw == pytest.approx(max_flow(grid))
    for design in (cheap, balanced, robust):
        assert design.bridges == len(find_bridges(grid, design.branches))


def test_same_weights_give_the_same_design(upc_reinforcer):
    first = upc_reinforcer.design(Weights(1, 1, 1))
    second = upc_reinforcer.design(Weights(1, 1, 1))

    assert first == second
