import type { CaseData, DesignData, Metrics, Weights } from './types'

function csvCell(value: string | number): string {
  let text = String(value)
  if (typeof value === 'string' && /^[\s]*[=+@-]|^[\t\r\n]/.test(text)) text = `'${text}`
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function resultsCsv(data: CaseData, design: DesignData, weights: Weights): string {
  const rows: (string | number)[][] = [
    [
      'case',
      'network',
      'step',
      'branch_index',
      'from_bus_id',
      'to_bus_id',
      'cost',
      'cost_unit',
      'bridges',
      'supplied_mw',
      'demand_mw',
      'supply_percent',
      'lines',
      'weight_cost',
      'weight_robustness',
      'weight_supply',
    ],
  ]
  function add(
    name: string,
    step: number | '',
    metrics: Metrics,
    lines: number,
    branchIndex?: number,
  ) {
    const branch = branchIndex === undefined ? null : data.branches[branchIndex]!
    rows.push([
      data.name,
      name,
      step,
      branchIndex ?? '',
      branch ? data.buses[branch.from]!.id : '',
      branch ? data.buses[branch.to]!.id : '',
      metrics.cost,
      data.costUnit,
      metrics.bridges,
      metrics.suppliedMw,
      data.totalLoadMw,
      data.totalLoadMw > 0 ? (metrics.suppliedMw / data.totalLoadMw) * 100 : '',
      lines,
      weights.cost,
      weights.robustness,
      weights.supply,
    ])
  }
  add('original', '', data.original, data.branches.length)
  add('mst', 0, data.mst, data.tree.length)
  design.steps.forEach((entry, index) =>
    add('step', index + 1, entry, data.tree.length + index + 1, entry.branch),
  )
  add('design', design.steps.length, design, data.tree.length + design.added.length)
  return rows.map((row) => row.map(csvCell).join(',')).join('\r\n') + '\r\n'
}
