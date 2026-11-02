import math
from pathlib import Path

import pytest

from gridbalance.grid import build_grid, load_grid
from gridbalance.matpower import CaseFormatError, RawCase

CASES_DIR = Path(__file__).resolve().parents[1] / "cases"


def bus_row(bus_id, demand=0.0, base_kv=110.0, bus_type=1, zone=1):
    #       bus_i   type      Pd      Qd Gs Bs area Vm Va baseKV zone Vmax Vmin
    return [bus_id, bus_type, demand, 0, 0, 0, 1, 1, 0, base_kv, zone, 1.1, 0.9]


def branch_row(from_id, to_id, x=0.1, rate_a=100.0, tap=0.0, status=1):
    #       fbus     tbus   r  x  b  rateA   rateB rateC ratio angle status
    return [from_id, to_id, 0, x, 0, rate_a, 0, 0, tap, 0, status, -360, 360]


def gen_row(bus_id, pmax, status=1):
    #       bus     Pg Qg Qmax Qmin Vg mBase status  Pmax
    return [bus_id, 0, 0, 0, 0, 1, 100, status, pmax] + [0] * 12


def make_case(buses, branches, gens, base_mva=100.0):
    return RawCase(
        name="test",
        base_mva=base_mva,
        matrices={"bus": buses, "branch": branches, "gen": gens},
    )


def test_buses_are_renumbered_but_keep_their_id():
    grid = build_grid(
        make_case([bus_row(10), bus_row(20), bus_row(35)], [branch_row(10, 35)], [])
    )

    assert [bus.index for bus in grid.buses] == [0, 1, 2]
    assert [bus.id for bus in grid.buses] == [10, 20, 35]
    assert (grid.branches[0].from_bus, grid.branches[0].to_bus) == (0, 2)


def test_cost_is_reactance_in_ohms_on_from_side_voltage():
    # Transformer from 400 kV to 110 kV: Z_base = 400^2 / 100 = 1600 ohm.
    grid = build_grid(
        make_case(
            [bus_row(1, base_kv=400), bus_row(2, base_kv=110)],
            [branch_row(1, 2, x=-0.5, tap=1.05)],
            [],
        )
    )

    branch = grid.branches[0]
    assert grid.cost_unit == "ohm"
    assert branch.cost == pytest.approx(0.5 * 1600)
    assert branch.is_transformer


def test_cost_falls_back_to_per_unit_without_base_voltages():
    grid = build_grid(
        make_case(
            [bus_row(1, base_kv=0), bus_row(2, base_kv=0)], [branch_row(1, 2)], []
        )
    )

    assert grid.cost_unit == "p.u."
    assert grid.branches[0].cost == pytest.approx(0.1)


def test_zero_rate_means_unlimited_capacity():
    grid = build_grid(
        make_case([bus_row(1), bus_row(2)], [branch_row(1, 2, rate_a=0)], [])
    )

    assert grid.branches[0].capacity_mva == math.inf


def test_out_of_service_and_isolated_elements_are_dropped():
    grid = build_grid(
        make_case(
            [bus_row(1), bus_row(2), bus_row(3, bus_type=4)],
            [branch_row(1, 2), branch_row(1, 2, status=0), branch_row(2, 3)],
            [gen_row(1, 50), gen_row(2, 80, status=0), gen_row(3, 30)],
        )
    )

    assert [bus.id for bus in grid.buses] == [1, 2]
    assert len(grid.branches) == 1
    assert [gen.pmax_mw for gen in grid.generators] == [50]


def test_supply_and_load_split_negative_demand():
    grid = build_grid(
        make_case(
            [bus_row(1, demand=-5), bus_row(2, demand=40), bus_row(3)],
            [branch_row(1, 2), branch_row(2, 3)],
            [gen_row(1, 100), gen_row(1, 20), gen_row(3, -10)],
        )
    )

    assert grid.supply_mw() == [125, 0, 0]
    assert grid.load_mw() == [0, 40, 0]


def test_self_loop_branch_is_rejected():
    with pytest.raises(CaseFormatError, match="itself"):
        build_grid(make_case([bus_row(1)], [branch_row(1, 1)], []))


def test_polish_grid():
    grid = load_grid(CASES_DIR / "case2383wp.m")

    assert len(grid.buses) == 2383
    assert len(grid.branches) == 2896
    assert len(grid.generators) == 327
    assert grid.cost_unit == "ohm"
    # Same total as the x_ohm column used in the Hito 1 report.
    assert grid.total_cost() == pytest.approx(18203, abs=1)
    assert sum(grid.load_mw()) == pytest.approx(24580, abs=1)
    assert sum(grid.supply_mw()) == pytest.approx(29594 + 22, abs=1)
    assert sum(branch.is_transformer for branch in grid.branches) == 170
