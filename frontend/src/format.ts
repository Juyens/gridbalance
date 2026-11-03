const integer = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
const oneDecimal = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

export function formatNumber(value: number): string {
  return integer.format(value)
}

export function formatPercent(part: number, total: number): string {
  return total > 0 ? `${oneDecimal.format((part / total) * 100)}%` : '-'
}

export function unitSymbol(costUnit: string): string {
  return costUnit === 'ohm' ? 'Ω' : costUnit
}
