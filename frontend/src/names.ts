import { t } from './i18n'
import type { BusData } from './types'

// Most sites have a name in OpenStreetMap; the rest are called by what they are.
export function busName(bus: BusData): string {
  if (bus.name) return bus.name
  if (bus.kind === 'bus') return `${t('busNumber')} ${bus.id}`
  const kind =
    bus.kind === 'plant' ? t('plant') : bus.kind === 'substation' ? t('substation') : t('place')
  return `${kind} ${bus.index + 1}`
}
