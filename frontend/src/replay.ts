import type { BusData, CaseData, DesignData } from './types'

export function designAtStep(data: CaseData, design: DesignData, step: number): DesignData {
  if (!Number.isInteger(step) || step < 0 || step > design.steps.length) {
    throw new RangeError('invalid replay step')
  }
  if (step === design.steps.length) return design
  const steps = design.steps.slice(0, step)
  const removed = new Set(steps.flatMap((entry) => entry.removedBridges))
  return {
    ...design,
    ...(steps.at(-1) ?? data.mst),
    added: design.added.slice(0, step),
    bridgeBranches: data.tree.filter((branch) => !removed.has(branch)),
    steps,
  }
}

export function findBus(data: CaseData, query: string): BusData | null {
  const text = query.trim()
  if (!/^-?\d+$/.test(text) || !Number.isSafeInteger(Number(text))) return null
  return data.buses.find((bus) => bus.id === Number(text)) ?? null
}
