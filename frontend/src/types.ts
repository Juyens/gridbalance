// Shapes of the JSON returned by the Python Api class (src/gridbalance/api.py).

export interface Weights {
  cost: number
  robustness: number
  supply: number
}

export interface Metrics {
  cost: number
  bridges: number
  suppliedMw: number
}

export interface BusData {
  index: number
  id: string | number
  kind: 'substation' | 'plant' | 'place' | 'bus'
  type: string
  name: string
  lat: number
  lon: number
  population: number | null
  baseKv: number
  supplyMw: number
  loadMw: number
}

export interface BranchData {
  index: number
  from: number
  to: number
  cost: number
  capacityMva: number | null // null means unlimited
  lengthKm: number | null
  kv: number
}

export interface ExistingLine {
  name: string
  voltagesKv: number[]
  points: [number, number][] // longitude, latitude
}

export interface CaseData {
  caseId: number
  name: string
  costUnit: string
  zone: { lat: number; lon: number; radiusKm: number | null; totalSites: number }
  buses: BusData[]
  branches: BranchData[]
  existingLines: ExistingLine[]
  tree: number[]
  totalLoadMw: number
  original: Metrics // using every possible line
  mst: Metrics
}

export interface DesignStep extends Metrics {
  branch: number
  removedBridges: number[]
}

export interface DesignData extends Metrics {
  added: number[]
  bridgeBranches: number[]
  steps: DesignStep[]
  elapsedMs: number
}

export type Selection = { kind: 'bus'; index: number } | { kind: 'branch'; index: number } | null
