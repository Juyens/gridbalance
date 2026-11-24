// Draws the frames of the replay. Every line is already on the map, hidden: a
// frame only flips the state of the lines that changed, so playing is fluid
// even with thousands of them.

import type { GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl'
import { position, type FeatureCollection } from './mapFeatures'
import type { Frame } from './replay'
import type { CaseData, DesignData } from './types'

const FLASH_MS = 700

export class MapReplay {
  private lines = 0
  private steps = 0
  private bridgesShown = false
  private readonly flashes = new Map<number, ReturnType<typeof setTimeout>>()

  private readonly map: MapLibreMap
  private readonly data: CaseData
  private readonly design: DesignData

  constructor(map: MapLibreMap, data: CaseData, design: DesignData) {
    this.map = map
    this.data = data
    this.design = design
    map.removeFeatureState({ source: 'branches' })
  }

  stop() {
    for (const timer of this.flashes.values()) clearTimeout(timer)
    this.flashes.clear()
    this.map.removeFeatureState({ source: 'branches' })
    this.drawActive(null, 0)
  }

  show(frame: Frame) {
    const { tree } = this.data
    const { added, steps } = this.design
    const lines = Math.floor(frame.lines)
    const done = Math.floor(frame.steps)

    for (; this.lines < lines; this.lines++) this.set(tree[this.lines]!, { on: true })
    for (; this.lines > lines; this.lines--) this.set(tree[this.lines - 1]!, { on: false })

    for (; this.steps < done; this.steps++) {
      this.set(added[this.steps]!, { on: true })
      for (const branch of steps[this.steps]!.removedBridges) {
        this.set(branch, { bridge: false })
        this.flash(branch)
      }
    }
    for (; this.steps > done; this.steps--) {
      this.set(added[this.steps - 1]!, { on: false })
      for (const branch of steps[this.steps - 1]!.removedBridges) this.set(branch, { bridge: true })
    }

    const bridgesShown = frame.chapter !== 'tree'
    if (bridgesShown !== this.bridgesShown) {
      this.bridgesShown = bridgesShown
      const saved = new Set(steps.slice(0, done).flatMap((step) => step.removedBridges))
      for (const branch of tree) this.set(branch, { bridge: bridgesShown && !saved.has(branch) })
    }

    if (frame.chapter === 'tree') this.drawActive(tree[lines] ?? null, frame.lines - lines)
    else if (frame.chapter === 'reinforce') {
      this.drawActive(added[done] ?? null, frame.steps - done)
    } else this.drawActive(null, 0)
  }

  private set(branch: number, state: { on?: boolean; bridge?: boolean; flash?: boolean }) {
    this.map.setFeatureState({ source: 'branches', id: branch }, state)
  }

  private flash(branch: number) {
    clearTimeout(this.flashes.get(branch))
    this.set(branch, { flash: true })
    this.flashes.set(
      branch,
      setTimeout(() => {
        this.flashes.delete(branch)
        this.set(branch, { flash: false })
      }, FLASH_MS),
    )
  }

  // The line being built grows from one end to the other.
  private drawActive(index: number | null, share: number) {
    const source = this.map.getSource<GeoJSONSource>('active')
    const branch = index === null ? undefined : this.data.branches[index]
    const features: FeatureCollection['features'] = []
    if (branch) {
      const [x1, y1] = position(this.data.buses[branch.from]!)
      const [x2, y2] = position(this.data.buses[branch.to]!)
      const head: [number, number] = [x1 + (x2 - x1) * share, y1 + (y2 - y1) * share]
      features.push(
        {
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: [[x1, y1], head] },
          properties: {},
        },
        { type: 'Feature', geometry: { type: 'Point', coordinates: head }, properties: {} },
      )
    }
    source?.setData({ type: 'FeatureCollection', features })
  }
}
