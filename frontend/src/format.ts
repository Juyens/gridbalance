import { locale } from './i18n'

export function formatNumber(value: number, decimals = 0): string {
  return new Intl.NumberFormat(locale.value, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatPercent(part: number, total: number): string {
  return total > 0
    ? new Intl.NumberFormat(locale.value, { style: 'percent', maximumFractionDigits: 1 }).format(
        part / total,
      )
    : '—'
}

export function unitSymbol(costUnit: string): string {
  return costUnit === 'ohm' ? 'Ω' : costUnit
}
