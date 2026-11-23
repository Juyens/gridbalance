<script setup lang="ts">
import { computed, ref } from 'vue'
import { t, type MessageKey } from '../i18n'
import type { Weights } from '../types'
import { CORNERS, pointToWeights, PRESETS, weightsToPoint, type Point } from '../weights'

const weights = defineModel<Weights>({ required: true })

// The sliders below are the keyboard and screen reader way to do the same.
const LABELS: { key: keyof Weights; x: number; y: number; anchor: string }[] = [
  { key: 'robustness', x: 110, y: 14, anchor: 'middle' },
  { key: 'cost', x: 4, y: 190, anchor: 'start' },
  { key: 'supply', x: 216, y: 190, anchor: 'end' },
]

const svg = ref<SVGSVGElement>()
const dragging = ref(false)
const point = computed(() => weightsToPoint(weights.value))
const outline = [CORNERS.robustness, CORNERS.supply, CORNERS.cost].join(' ')

function mix(a: Point, b: Point, share: number): Point {
  return [a[0] + (b[0] - a[0]) * share, a[1] + (b[1] - a[1]) * share]
}

// Lines of equal weight at 0.25, 0.5 and 0.75 of each corner.
const guides = [0.25, 0.5, 0.75].flatMap((share) =>
  (
    [
      ['cost', 'robustness', 'supply'],
      ['robustness', 'cost', 'supply'],
      ['supply', 'cost', 'robustness'],
    ] as const
  ).map(([corner, left, right]) => ({
    from: mix(CORNERS[corner], CORNERS[left], share),
    to: mix(CORNERS[corner], CORNERS[right], share),
  })),
)
const presets = Object.entries(PRESETS).map(([name, preset]) => ({
  name: name as MessageKey,
  point: weightsToPoint(preset),
  weights: preset,
}))

function pick(event: PointerEvent) {
  const matrix = svg.value!.getScreenCTM()
  if (!matrix) return
  const { x, y } = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse())
  const near = presets.find((preset) => Math.hypot(preset.point[0] - x, preset.point[1] - y) < 8)
  weights.value = near ? { ...near.weights } : pointToWeights([x, y])
}

function start(event: PointerEvent) {
  dragging.value = true
  svg.value!.setPointerCapture(event.pointerId)
  pick(event)
}
</script>

<template>
  <svg
    ref="svg"
    class="triangle"
    :class="{ dragging }"
    viewBox="0 0 220 200"
    aria-hidden="true"
    @pointerdown="start"
    @pointermove="dragging && pick($event)"
    @pointerup="dragging = false"
    @pointercancel="dragging = false"
  >
    <polygon class="area" :points="outline" />
    <line
      v-for="(guide, index) in guides"
      :key="index"
      class="guide"
      :x1="guide.from[0]"
      :y1="guide.from[1]"
      :x2="guide.to[0]"
      :y2="guide.to[1]"
    />
    <line
      v-for="label in LABELS"
      :key="`pull-${label.key}`"
      class="pull"
      :class="label.key"
      :x1="CORNERS[label.key][0]"
      :y1="CORNERS[label.key][1]"
      :x2="point[0]"
      :y2="point[1]"
      :stroke-width="1 + weights[label.key] * 7"
    />
    <polygon class="border" :points="outline" />
    <circle
      v-for="preset in presets"
      :key="preset.name"
      class="preset"
      :cx="preset.point[0]"
      :cy="preset.point[1]"
      r="4"
    >
      <title>{{ t(preset.name) }}</title>
    </circle>
    <text
      v-for="label in LABELS"
      :key="label.key"
      :class="label.key"
      :x="label.x"
      :y="label.y"
      :text-anchor="label.anchor"
    >
      {{ t(label.key) }}
    </text>
    <circle class="handle" :cx="point[0]" :cy="point[1]" r="9" />
  </svg>
</template>

<style scoped>
.triangle {
  display: block;
  width: 100%;
  max-width: 212px;
  margin: 0 auto;
  cursor: grab;
  touch-action: none;
  user-select: none;
}

.dragging {
  cursor: grabbing;
}

.area {
  fill: var(--background);
}

.border {
  fill: none;
  stroke: var(--border);
  stroke-width: 1.5;
  stroke-linejoin: round;
}

.guide {
  stroke: var(--border);
  stroke-width: 1;
  stroke-dasharray: 2 3;
}

.pull {
  stroke-linecap: round;
  opacity: 0.85;
}

.pull.cost {
  stroke: var(--objective-cost);
}

.pull.robustness {
  stroke: var(--objective-robustness);
}

.pull.supply {
  stroke: var(--objective-supply);
}

.preset {
  fill: var(--surface);
  stroke: var(--muted);
  stroke-width: 1.5;
  cursor: pointer;
}

.handle {
  fill: var(--text);
  stroke: var(--surface);
  stroke-width: 3;
}

text {
  fill: var(--text);
  font-size: 12px;
  font-weight: 600;
  pointer-events: none;
}

text.cost {
  fill: var(--objective-cost);
}

text.robustness {
  fill: var(--objective-robustness);
}

text.supply {
  fill: var(--objective-supply);
}
</style>
