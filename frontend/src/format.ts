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

// Costs come in thousands of dollars: 1036 reads as "1,04 M US$".
export function formatMoney(thousands: number): string {
  return new Intl.NumberFormat(locale.value, {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumSignificantDigits: 3,
  }).format(thousands * 1000)
}

export function formatCost(cost: number, unit: string): string {
  if (unit === 'kUSD') return formatMoney(cost)
  return `${formatNumber(cost, cost < 100 ? 1 : 0)} ${unit === 'ohm' ? 'Ω' : unit}`
}
