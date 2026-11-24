// The design told as a video: Kruskal builds the tree, then its bridges are
// shown, then the greedy adds the reinforcement lines.

import type { CaseData, DesignData } from './types'

export type Chapter = 'tree' | 'bridges' | 'reinforce' | 'end'

export interface Timeline {
  lines: number // branches of the tree
  steps: number // reinforcement lines
  treeEnd: number // seconds
  bridgesEnd: number
  end: number
}

export interface Frame {
  chapter: Chapter
  lines: number // branches of the tree drawn so far; the fraction is being drawn
  steps: number // the same for the reinforcement lines
}

const BRIDGES_SECONDS = 3
// Guards floor() against results like 11.999999.
const EPSILON = 1e-6

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

// Small networks get time for each line; large ones still end in seconds.
export function makeTimeline(lines: number, steps: number): Timeline {
  const treeEnd = lines > 0 ? clamp(lines * 0.08, 3, 9) : 0
  const bridgesEnd = treeEnd + BRIDGES_SECONDS
  const end = bridgesEnd + (steps > 0 ? clamp(steps * 0.6, 4, 24) : 0)
  return { lines, steps, treeEnd, bridgesEnd, end }
}

export function frameAt(timeline: Timeline, time: number): Frame {
  const { lines, steps, treeEnd, bridgesEnd, end } = timeline
  if (time < treeEnd) {
    const drawn = Math.min(lines, (lines * time) / treeEnd + EPSILON)
    return { chapter: 'tree', lines: drawn, steps: 0 }
  }
  if (time < bridgesEnd) return { chapter: 'bridges', lines, steps: 0 }
  if (time < end) {
    const drawn = Math.min(steps, (steps * (time - bridgesEnd)) / (end - bridgesEnd) + EPSILON)
    return { chapter: 'reinforce', lines, steps: drawn }
  }
  return { chapter: 'end', lines, steps }
}

// Time when the given number of lines is complete, counting tree and reinforcement.
export function timeOfLine(timeline: Timeline, count: number): number {
  const { lines, steps, treeEnd, bridgesEnd, end } = timeline
  if (count <= lines) return lines > 0 ? (count / lines) * treeEnd : 0
  return bridgesEnd + (Math.min(count - lines, steps) / steps) * (end - bridgesEnd)
}

// Time one line before (-1) or after (+1).
export function stepTime(timeline: Timeline, time: number, direction: -1 | 1): number {
  const frame = frameAt(timeline, time)
  const count = Math.floor(frame.lines) + Math.floor(frame.steps)
  return timeOfLine(timeline, clamp(count + direction, 0, timeline.lines + timeline.steps))
}

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
