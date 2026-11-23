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

// Thousands of dollars read as "1,04 M US$"; the Polish case costs are ohms.
export function formatCost(cost: number, unit: string): string {
  if (unit !== 'kUSD')
    return `${formatNumber(cost, cost < 100 ? 1 : 0)} ${unit === 'ohm' ? 'Ω' : unit}`
  return new Intl.NumberFormat(locale.value, {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumSignificantDigits: 3,
  }).format(cost * 1000)
}
