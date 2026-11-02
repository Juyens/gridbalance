"""Power grid model built from a MATPOWER case.

Each MATPOWER matrix row becomes an object whose fields have a meaning. Buses are
renumbered 0..n-1 ('index') so algorithms can use plain lists; the original
MATPOWER number is kept in 'id' for display.
"""

import math
from dataclasses import dataclass
from pathlib import Path

from gridbalance.matpower import CaseFormatError, RawCase, read_case

# Column positions defined by the MATPOWER case format (idx_bus, idx_brch, idx_gen).
BUS_I, BUS_TYPE, PD, BASE_KV, ZONE = 0, 1, 2, 9, 10
F_BUS, T_BUS, BR_X, RATE_A, TAP, BR_STATUS = 0, 1, 3, 5, 8, 10
GEN_BUS, GEN_STATUS, PMAX = 0, 7, 8

ISOLATED_BUS_TYPE = 4


@dataclass(frozen=True, slots=True)
class Bus:
    index: int
    id: int
    bus_type: int
    demand_mw: float  # Pd; negative means the bus injects power
    base_kv: float
    zone: int


@dataclass(frozen=True, slots=True)
class Branch:
    index: int
    from_bus: int  # bus index, not MATPOWER id
    to_bus: int
    cost: float  # reactance used as building cost, in Grid.cost_unit
    capacity_mva: float  # rateA; math.inf when the case leaves it unlimited
    is_transformer: bool


@dataclass(frozen=True, slots=True)
class Generator:
    bus: int  # bus index
    pmax_mw: float


@dataclass(frozen=True, slots=True)
class Grid:
    name: str
    base_mva: float
    buses: tuple[Bus, ...]
    branches: tuple[Branch, ...]
    generators: tuple[Generator, ...]
    cost_unit: str  # "ohm", or "p.u." when the case lacks base voltages

    def supply_mw(self) -> list[float]:
        """Power each bus can inject: generator capacity plus negative demand."""
        supply = [max(-bus.demand_mw, 0.0) for bus in self.buses]
        for generator in self.generators:
            supply[generator.bus] += generator.pmax_mw
        return supply

    def load_mw(self) -> list[float]:
        """Power each bus consumes (positive demand only)."""
        return [max(bus.demand_mw, 0.0) for bus in self.buses]

    def total_cost(self) -> float:
        return sum(branch.cost for branch in self.branches)


def build_buses(rows: list[list[float]]) -> list[Bus]:
    buses = []
    for row in rows:
        if int(row[BUS_TYPE]) == ISOLATED_BUS_TYPE:
            continue
        buses.append(
            Bus(
                index=len(buses),
                id=int(row[BUS_I]),
                bus_type=int(row[BUS_TYPE]),
                demand_mw=row[PD],
                base_kv=row[BASE_KV],
                zone=int(row[ZONE]),
            )
        )
    return buses


def build_branches(
    rows: list[list[float]], buses: list[Bus], base_mva: float, cost_unit: str
) -> list[Branch]:
    index_of = {bus.id: bus.index for bus in buses}
    branches = []
    for row in rows:
        if row[BR_STATUS] == 0:
            continue
        from_id, to_id = int(row[F_BUS]), int(row[T_BUS])
        if from_id not in index_of or to_id not in index_of:
            continue  # touches an isolated bus
        if from_id == to_id:
            raise CaseFormatError(f"branch connects bus {from_id} to itself")

        from_bus = buses[index_of[from_id]]
        # Series compensation can give negative reactance; cost uses magnitude.
        reactance_pu = abs(row[BR_X])
        if cost_unit == "ohm":
            # Z_base = kV^2 / MVA. Lines have the same kV at both ends; for
            # transformers the side is a convention, and we use the 'from' side.
            cost = reactance_pu * from_bus.base_kv**2 / base_mva
        else:
            cost = reactance_pu

        branches.append(
            Branch(
                index=len(branches),
                from_bus=from_bus.index,
                to_bus=index_of[to_id],
                cost=cost,
                capacity_mva=row[RATE_A] if row[RATE_A] > 0 else math.inf,
                is_transformer=row[TAP] != 0,
            )
        )
    return branches


def build_generators(rows: list[list[float]], buses: list[Bus]) -> list[Generator]:
    index_of = {bus.id: bus.index for bus in buses}
    return [
        Generator(bus=index_of[int(row[GEN_BUS])], pmax_mw=max(row[PMAX], 0.0))
        for row in rows
        if row[GEN_STATUS] > 0 and int(row[GEN_BUS]) in index_of
    ]


def build_grid(raw: RawCase) -> Grid:
    buses = build_buses(raw.matrices["bus"])
    # Ohms are only comparable across voltage levels if every bus has a base kV.
    cost_unit = "ohm" if all(bus.base_kv > 0 for bus in buses) else "p.u."
    branches = build_branches(raw.matrices["branch"], buses, raw.base_mva, cost_unit)
    generators = build_generators(raw.matrices["gen"], buses)
    return Grid(
        name=raw.name,
        base_mva=raw.base_mva,
        buses=tuple(buses),
        branches=tuple(branches),
        generators=tuple(generators),
        cost_unit=cost_unit,
    )


def load_grid(path: Path) -> Grid:
    return build_grid(read_case(path))
