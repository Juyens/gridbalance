"""Power grid model built from a MATPOWER case."""

import math

from gridbalance.matpower import CaseFormatError, read_case

#Column positions defined by MATPOWER (idx_bus, idx_brch, idx_gen).
BUS_I, BUS_TYPE, PD, BASE_KV, ZONE = 0, 1, 2, 9, 10
F_BUS, T_BUS, BR_X, RATE_A, TAP, BR_STATUS = 0, 1, 3, 5, 8, 10
GEN_BUS, GEN_STATUS, PMAX = 0, 7, 8

ISOLATED_BUS_TYPE = 4


class Bus:
  """One bus of the grid."""

  def __init__(self, index, id, bus_type, demand_mw, base_kv, zone):
    self.index = index
    self.id = id
    self.bus_type = bus_type
    self.demand_mw = demand_mw  #negative means the bus injects power
    self.base_kv = base_kv
    self.zone = zone


class Branch:
  """One branch (line or transformer) of the grid."""

  def __init__(
    self, index, from_bus, to_bus, cost, capacity_mva, is_transformer
  ):
    self.index = index
    self.from_bus = from_bus  #bus index, not MATPOWER id
    self.to_bus = to_bus
    self.cost = cost  #reactance used as building cost, in Grid.cost_unit
    self.capacity_mva = capacity_mva  #rateA; inf when unlimited
    self.is_transformer = is_transformer


class Generator:
  """One generator of the grid."""

  def __init__(self, bus, pmax_mw):
    self.bus = bus  #bus index
    self.pmax_mw = pmax_mw


class Grid:
  """Network with buses, branches and generators."""

  def __init__(self, name, base_mva, buses, branches, generators, cost_unit):
    self.name = name
    self.base_mva = base_mva
    self.buses = buses
    self.branches = branches
    self.generators = generators
    self.cost_unit = cost_unit  #"ohm", or "p.u." without base voltages

  def supply_mw(self):
    """Power each bus can inject."""
    supply = [max(-bus.demand_mw, 0.0) for bus in self.buses]
    for generator in self.generators:
      supply[generator.bus] += generator.pmax_mw
    return supply

  def load_mw(self):
    """Power each bus consumes (positive demand only)."""
    return [max(bus.demand_mw, 0.0) for bus in self.buses]

  def total_cost(self):
    return sum(branch.cost for branch in self.branches)


def build_buses(rows):
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


def build_branches(rows, buses, base_mva, cost_unit):
  index_of = {bus.id: bus.index for bus in buses}
  branches = []
  for row in rows:
    if row[BR_STATUS] == 0:
      continue
    from_id, to_id = int(row[F_BUS]), int(row[T_BUS])
    if from_id not in index_of or to_id not in index_of:
      continue  #touches an isolated bus
    if from_id == to_id:
      raise CaseFormatError(f"branch connects bus {from_id} to itself")

    from_bus = buses[index_of[from_id]]
    #Series compensation can give negative reactance; cost uses magnitude.
    reactance_pu = abs(row[BR_X])
    if cost_unit == "ohm":
      #Z_base = kV^2 / MVA, using the from side for transformers.
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


def build_generators(rows, buses):
  index_of = {bus.id: bus.index for bus in buses}
  return [
    Generator(bus=index_of[int(row[GEN_BUS])], pmax_mw=max(row[PMAX], 0.0))
    for row in rows
    if row[GEN_STATUS] > 0 and int(row[GEN_BUS]) in index_of
  ]


def build_grid(raw):
  buses = build_buses(raw.matrices["bus"])
  #Ohms are only comparable across voltage levels if every bus has a base kV.
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


def load_grid(path):
  return build_grid(read_case(path))
