<script setup lang="ts">
import cytoscape, { type Core, type ElementDefinition, type StylesheetJson } from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { BranchStatus, CaseData, DesignData, Position, Selection } from '../types'

cytoscape.use(fcose)

const props = defineProps<{
  caseData: CaseData | null
  design: DesignData | null
  showUnused: boolean
  showBridges: boolean
}>()

const emit = defineEmits<{
  layoutComputed: [positions: Position[]]
  select: [selection: Selection]
}>()

const container = ref<HTMLDivElement>()
const computingLayout = ref(false)

// Plain variable, not ref(): Vue must not wrap Cytoscape's internals in proxies.
let cy: Core | null = null

const STYLE: StylesheetJson = [
  {
    selector: 'node',
    style: { width: 5, height: 5, 'background-color': '#8c959f', 'border-width': 0 },
  },
  { selector: 'node.kv400', style: { 'background-color': '#cf222e' } },
  { selector: 'node.kv220', style: { 'background-color': '#bc4c00' } },
  { selector: 'node.kv110', style: { 'background-color': '#0969da' } },
  { selector: 'node.generator', style: { width: 10, height: 10, shape: 'diamond' } },
  { selector: 'edge', style: { 'curve-style': 'haystack', width: 1, 'line-color': '#d0d7de' } },
  { selector: 'edge.tree', style: { width: 1.4, 'line-color': '#57606a' } },
  { selector: 'edge.added', style: { width: 2.6, 'line-color': '#1a7f37', 'z-index': 2 } },
  { selector: 'edge.bridge', style: { width: 2.6, 'line-color': '#cf222e', 'z-index': 3 } },
  { selector: 'edge.hidden', style: { display: 'none' } },
  { selector: ':selected', style: { 'border-width': 2, 'border-color': '#1f2328' } },
  { selector: 'edge:selected', style: { width: 5, 'line-color': '#8250df', 'z-index': 4 } },
]

const FCOSE_OPTIONS = {
  name: 'fcose',
  quality: 'default',
  randomize: true,
  animate: false,
  nodeDimensionsIncludeLabels: false,
  nodeRepulsion: 6000,
  idealEdgeLength: 30,
}

function voltageClass(baseKv: number): string {
  if (baseKv >= 380) return 'kv400'
  if (baseKv >= 200) return 'kv220'
  if (baseKv >= 100) return 'kv110'
  return 'kvlow'
}

function buildElements(data: CaseData): ElementDefinition[] {
  const nodes: ElementDefinition[] = data.buses.map((bus) => {
    const position = data.positions?.[bus.index]
    return {
      group: 'nodes',
      data: { id: `b${bus.index}`, index: bus.index },
      classes: `${voltageClass(bus.baseKv)}${bus.supplyMw > 0 ? ' generator' : ''}`,
      ...(position && { position: { x: position[0], y: position[1] } }),
    }
  })
  const edges: ElementDefinition[] = data.branches.map((branch) => ({
    group: 'edges',
    data: {
      id: `e${branch.index}`,
      index: branch.index,
      source: `b${branch.from}`,
      target: `b${branch.to}`,
    },
  }))
  return [...nodes, ...edges]
}

async function renderCase(data: CaseData) {
  if (!cy) return
  cy.elements().remove()
  cy.add(buildElements(data))
  applyDesign()

  if (data.positions) {
    cy.layout({ name: 'preset' }).run()
    cy.fit(undefined, 20)
    return
  }

  // fcose blocks the page while it runs: show the overlay first, then start it.
  computingLayout.value = true
  await nextTick()
  await new Promise((resolve) => setTimeout(resolve, 50))
  const layout = cy.layout(FCOSE_OPTIONS)
  layout.one('layoutstop', () => {
    computingLayout.value = false
    cy!.fit(undefined, 20)
    const positions = data.buses.map((bus): Position => {
      const { x, y } = cy!.getElementById(`b${bus.index}`).position()
      return [x, y]
    })
    emit('layoutComputed', positions)
  })
  layout.run()
}

function applyDesign() {
  if (!cy || !props.caseData) return
  const tree = new Set(props.caseData.tree)
  const added = new Set(props.design?.added ?? [])
  const bridges = new Set(props.design?.bridgeBranches ?? [])

  // batch() repaints once at the end instead of once per edge.
  cy.batch(() => {
    cy!.edges().forEach((edge) => {
      const index = edge.data('index') as number
      const status: BranchStatus = tree.has(index) ? 'tree' : added.has(index) ? 'added' : 'unused'
      const classes: string[] = [status]
      if (props.showBridges && bridges.has(index)) classes.push('bridge')
      if (status === 'unused' && !props.showUnused) classes.push('hidden')
      edge.classes(classes)
    })
  })
}

onMounted(() => {
  cy = cytoscape({
    container: container.value,
    style: STYLE,
    minZoom: 0.02,
    maxZoom: 6,
    textureOnViewport: true, // pan and zoom move a snapshot instead of redrawing
    boxSelectionEnabled: false,
  })
  cy.on('tap', 'node', (event) =>
    emit('select', { kind: 'bus', index: event.target.data('index') }),
  )
  cy.on('tap', 'edge', (event) =>
    emit('select', { kind: 'branch', index: event.target.data('index') }),
  )
  cy.on('tap', (event) => {
    if (event.target === cy) emit('select', null)
  })
  if (props.caseData) renderCase(props.caseData)
})

onUnmounted(() => {
  cy?.destroy()
  cy = null
})

watch(
  () => props.caseData,
  (data) => {
    emit('select', null)
    if (data) renderCase(data)
  },
)
watch(() => [props.design, props.showUnused, props.showBridges], applyDesign)
</script>

<template>
  <div class="grid-canvas">
    <div ref="container" class="cytoscape"></div>

    <div v-if="computingLayout" class="overlay">
      Computing layout for {{ caseData?.buses.length }} buses. This happens only the first time.
    </div>

    <ul class="legend">
      <li><span class="line tree"></span>MST</li>
      <li><span class="line added"></span>Added</li>
      <li><span class="line bridge"></span>Bridge</li>
      <li><span class="line unused"></span>Unused</li>
      <li><span class="dot kv400"></span>400 kV</li>
      <li><span class="dot kv220"></span>220 kV</li>
      <li><span class="dot kv110"></span>110 kV</li>
      <li><span class="diamond"></span>Generation</li>
    </ul>
  </div>
</template>

<style scoped>
.grid-canvas {
  position: relative;
  height: 100%;
  min-height: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  overflow: hidden;
}

.cytoscape {
  position: absolute;
  inset: 0;
}

.overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(255 255 255 / 85%);
  text-align: center;
}

.legend {
  position: absolute;
  left: 10px;
  bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  max-width: calc(100% - 20px);
  margin: 0;
  padding: 6px 10px;
  list-style: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: rgb(255 255 255 / 90%);
  font-size: 12px;
}

.legend li {
  display: flex;
  align-items: center;
  gap: 5px;
}

.line {
  display: inline-block;
  width: 16px;
  height: 3px;
}

.line.tree {
  background: #57606a;
}

.line.added {
  background: #1a7f37;
}

.line.bridge {
  background: #cf222e;
}

.line.unused {
  background: #d0d7de;
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.kv400 {
  background: #cf222e;
}

.dot.kv220 {
  background: #bc4c00;
}

.dot.kv110 {
  background: #0969da;
}

.diamond {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: #57606a;
  transform: rotate(45deg);
}
</style>
