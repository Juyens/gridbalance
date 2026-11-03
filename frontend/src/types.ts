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
  id: number
  baseKv: number
  zone: number
  supplyMw: number
  loadMw: number
}

export interface BranchData {
  index: number
  from: number
  to: number
  cost: number
  capacityMva: number | null // null means unlimited
  isTransformer: boolean
}

export type Position = [number, number]

export interface CaseData {
  name: string
  costUnit: string
  buses: BusData[]
  branches: BranchData[]
  tree: number[]
  totalLoadMw: number
  original: Metrics
  mst: Metrics
  positions: Position[] | null
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

export type BranchStatus = 'tree' | 'added' | 'unused'

export type Selection = { kind: 'bus'; index: number } | { kind: 'branch'; index: number } | null
