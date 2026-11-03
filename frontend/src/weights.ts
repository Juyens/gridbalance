// The three weights are percentages that always add up to 100.

import type { Weights } from './types'

export const WEIGHT_KEYS: (keyof Weights)[] = ['cost', 'robustness', 'supply']

export const PRESETS: Record<string, Weights> = {
  Cheapest: { cost: 100, robustness: 0, supply: 0 },
  Economic: { cost: 60, robustness: 20, supply: 20 },
  Balanced: { cost: 100 / 3, robustness: 100 / 3, supply: 100 / 3 },
  Robust: { cost: 0, robustness: 50, supply: 50 },
}

/**
 * Sets one weight and shares what is left of the 100% among the other two,
 * keeping the ratio between them. If both were zero, they split it evenly.
 */
export function rebalance(weights: Weights, key: keyof Weights, value: number): Weights {
  const others = WEIGHT_KEYS.filter((other) => other !== key)
  const othersTotal = others.reduce((sum, other) => sum + weights[other], 0)
  const rest = 100 - value
  const result = { ...weights, [key]: value }
  for (const other of others) {
    result[other] = othersTotal > 0 ? (weights[other] / othersTotal) * rest : rest / others.length
  }
  return result
}

// Rebalancing leaves tiny float differences, so presets match with a tolerance.
export function sameWeights(a: Weights, b: Weights): boolean {
  return WEIGHT_KEYS.every((key) => Math.abs(a[key] - b[key]) < 0.05)
}
