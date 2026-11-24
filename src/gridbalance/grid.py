"""Power grid model the algorithms work on."""


class Bus:
  """One bus of the grid."""

  def __init__(self, index, id, demand_mw, base_kv):
    self.index = index
    self.id = id
    self.demand_mw = demand_mw  #negative means the bus injects power
    self.base_kv = base_kv


class Branch:
  """One possible line of the grid."""

  def __init__(self, index, from_bus, to_bus, cost, capacity_mva):
    self.index = index
    self.from_bus = from_bus  #bus index
    self.to_bus = to_bus
    self.cost = cost  #building cost, in Grid.cost_unit
    self.capacity_mva = capacity_mva  #inf when unlimited


class Generator:
  """One generator of the grid."""

  def __init__(self, bus, pmax_mw):
    self.bus = bus  #bus index
    self.pmax_mw = pmax_mw


class Grid:
  """Network with buses, branches and generators."""

  def __init__(self, name, buses, branches, generators, cost_unit):
    self.name = name
    self.buses = buses
    self.branches = branches
    self.generators = generators
    self.cost_unit = cost_unit

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
