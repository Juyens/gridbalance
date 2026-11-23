// The three weights go from 0 to 1 and always add up to 1.

import type { Weights } from './types'

export const WEIGHT_KEYS: (keyof Weights)[] = ['cost', 'robustness', 'supply']

export const PRESETS: Record<string, Weights> = {
  Cheapest: { cost: 1, robustness: 0, supply: 0 },
  Economic: { cost: 0.6, robustness: 0.2, supply: 0.2 },
  Balanced: { cost: 1 / 3, robustness: 1 / 3, supply: 1 / 3 },
  Robust: { cost: 0, robustness: 0.5, supply: 0.5 },
}

/**
 * Sets one weight and shares what is left of the total among the other two,
 * keeping the ratio between them. If both were zero, they split it evenly.
 */
export function rebalance(weights: Weights, key: keyof Weights, value: number): Weights {
  const others = WEIGHT_KEYS.filter((other) => other !== key)
  const othersTotal = others.reduce((sum, other) => sum + weights[other], 0)
  const rest = 1 - value
  const result = { ...weights, [key]: value }
  for (const other of others) {
    result[other] = othersTotal > 0 ? (weights[other] / othersTotal) * rest : rest / others.length
  }
  return result
}

// Rebalancing leaves tiny float differences, so presets match with a tolerance.
export function sameWeights(a: Weights, b: Weights): boolean {
  return WEIGHT_KEYS.every((key) => Math.abs(a[key] - b[key]) < 0.0005)
}

export type Point = [number, number]

// Corners of the triangle where the weights are picked, in its SVG units.
export const CORNERS: Record<keyof Weights, Point> = {
  robustness: [110, 26],
  cost: [20, 170],
  supply: [200, 170],
}

// Each weight pulls the point towards its corner.
export function weightsToPoint(weights: Weights): Point {
  const sum = (axis: 0 | 1) =>
    WEIGHT_KEYS.reduce((total, key) => total + weights[key] * CORNERS[key][axis], 0)
  return [sum(0), sum(1)]
}

// Barycentric coordinates; a point outside the triangle goes to its border.
export function pointToWeights([x, y]: Point): Weights {
  const [ax, ay] = CORNERS.cost
  const [bx, by] = CORNERS.robustness
  const [cx, cy] = CORNERS.supply
  const area = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
  const cost = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / area
  const robustness = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / area
  const raw = [cost, robustness, 1 - cost - robustness].map((value) => Math.max(0, value))
  const total = raw[0]! + raw[1]! + raw[2]!
  return { cost: raw[0]! / total, robustness: raw[1]! / total, supply: raw[2]! / total }
}
