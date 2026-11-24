// Turns the zone and its design into the GeoJSON the map draws.

import type { BusData, CaseData, DesignData } from './types'

type Coordinates = [number, number]

interface Feature {
  type: 'Feature'
  id?: number
  geometry:
    { type: 'Point'; coordinates: Coordinates } | { type: 'LineString'; coordinates: Coordinates[] }
  properties: Record<string, string | number | boolean>
}

export interface FeatureCollection {
  type: 'FeatureCollection'
  features: Feature[]
}

const EARTH_RADIUS_KM = 6371.0088
const CIRCLE_POINTS = 96

const collection = (features: Feature[]): FeatureCollection => ({
  type: 'FeatureCollection',
  features,
})

export function position(bus: BusData): Coordinates {
  return [bus.lon, bus.lat]
}

export function isSource(bus: BusData): boolean {
  return bus.supplyMw > 0
}

// Cost of the design lines that reach each bus; a line counts at both of its ends.
export function busCosts(data: CaseData, design: DesignData | null): number[] {
  const costs = data.buses.map(() => 0)
  for (const index of [...data.tree, ...(design?.added ?? [])]) {
    const branch = data.branches[index]!
    costs[branch.from]! += branch.cost
    costs[branch.to]! += branch.cost
  }
  return costs
}

export function busFeatures(
  data: CaseData,
  design: DesignData | null,
  label: (bus: BusData, cost: number) => string,
): FeatureCollection {
  const costs = busCosts(data, design)
  return collection(
    data.buses.map((bus) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: position(bus) },
      properties: {
        index: bus.index,
        source: isSource(bus),
        name: bus.name,
        icon: isSource(bus) ? (bus.kind === 'plant' ? 'plant' : 'source') : 'load',
        label: label(bus, costs[bus.index]!),
      },
    })),
  )
}

export function branchFeatures(
  data: CaseData,
  design: DesignData | null,
  label: (cost: number) => string,
): FeatureCollection {
  const tree = new Set(data.tree)
  const added = new Set(design?.added ?? [])
  const bridges = new Set(design?.bridgeBranches ?? [])
  return collection(
    data.branches.map(({ index, from, to, cost, kv }) => ({
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [position(data.buses[from]!), position(data.buses[to]!)],
      },
      properties: {
        index,
        from,
        to,
        kv,
        status: tree.has(index) ? 'tree' : added.has(index) ? 'added' : 'unused',
        bridge: bridges.has(index),
        label: label(cost),
      },
    })),
  )
}

export function existingFeatures(data: CaseData): FeatureCollection {
  return collection(
    data.existingLines.map((line) => ({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: line.points },
      properties: {
        label: [line.name, line.voltagesKv.map((kv) => `${kv} kV`).join(' / ')]
          .filter(Boolean)
          .join(' · '),
      },
    })),
  )
}

export function circlePoints({ lat, lon, radiusKm }: CaseData['zone']): Coordinates[] {
  if (radiusKm === null) return []
  const radians = Math.PI / 180
  const latitude = lat * radians
  const angular = radiusKm / EARTH_RADIUS_KM
  return Array.from({ length: CIRCLE_POINTS + 1 }, (_, i) => {
    const bearing = (2 * Math.PI * i) / CIRCLE_POINTS
    const nextLat = Math.asin(
      Math.sin(latitude) * Math.cos(angular) +
        Math.cos(latitude) * Math.sin(angular) * Math.cos(bearing),
    )
    const deltaLon = Math.atan2(
      Math.sin(bearing) * Math.sin(angular) * Math.cos(latitude),
      Math.cos(angular) - Math.sin(latitude) * Math.sin(nextLat),
    )
    return [lon + deltaLon / radians, nextLat / radians]
  })
}

export function circleFeature(zone: CaseData['zone']): FeatureCollection {
  if (zone.radiusKm === null) return collection([])
  return collection([
    {
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: circlePoints(zone) },
      properties: {},
    },
  ])
}
