<script setup lang="ts">
import cytoscape, { type Core, type ElementDefinition, type StylesheetJson } from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { BranchStatus, CaseData, DesignData, Position, Selection, Weights } from '../types'
import { t } from '../i18n'
import { formatNumber } from '../format'
import { findBus } from '../replay'
import { resultsCsv } from '../export'
import { errorMessage, getApi } from '../api'

cytoscape.use(fcose)

const props = defineProps<{
  caseData: CaseData | null
  design: DesignData | null
  showUnused: boolean
  showBridges: boolean
  darkMode: boolean
  fullDesign: DesignData | null
  weights: Weights
  busy: boolean
  selection: Selection
}>()

const emit = defineEmits<{
  layoutComputed: [positions: Position[]]
  select: [selection: Selection]
  error: [message: string]
}>()

const container = ref<HTMLDivElement>()
const computingLayout = ref(false)
const searchTerm = ref('')
const searchFailed = ref(false)
const exporting = ref(false)
const exportSaved = ref(false)
let resizeObserver: ResizeObserver | null = null

// Plain variable, not ref(): Vue must not wrap Cytoscape's internals in proxies.
let cy: Core | null = null

function graphStyle(): StylesheetJson {
  const tokens = getComputedStyle(document.documentElement)
  const color = (name: string) => tokens.getPropertyValue(`--graph-${name}`).trim()
  return [
    {
      selector: 'node',
      style: { width: 5, height: 5, 'background-color': color('low'), 'border-width': 0 },
    },
    { selector: 'node.kv400', style: { 'background-color': color('kv400') } },
    { selector: 'node.kv220', style: { 'background-color': color('kv220') } },
    { selector: 'node.kv110', style: { 'background-color': color('kv110') } },
    { selector: 'node.generator', style: { width: 10, height: 10, shape: 'diamond' } },
    {
      selector: 'edge',
      style: { 'curve-style': 'haystack', width: 1, 'line-color': color('unused') },
    },
    { selector: 'edge.tree', style: { width: 1.4, 'line-color': color('tree') } },
    { selector: 'edge.added', style: { width: 2.6, 'line-color': color('added'), 'z-index': 2 } },
    {
      selector: 'edge.bridge',
      style: { width: 2.6, 'line-color': color('bridge'), 'line-style': 'dashed', 'z-index': 3 },
    },
    { selector: 'edge.hidden', style: { display: 'none' } },
    { selector: ':selected', style: { 'border-width': 2, 'border-color': color('selected') } },
    { selector: 'node:selected', style: { width: 14, height: 14 } },
    {
      selector: 'edge:selected',
      style: { width: 5, 'line-color': color('selected'), 'z-index': 4 },
    },
  ]
}

function fitView() {
  cy?.fit(undefined, 32)
}

function searchBus() {
  if (!cy || !props.caseData) return
  const bus = findBus(props.caseData, searchTerm.value)
  searchFailed.value = !bus
  if (!bus) return
  const node = cy.getElementById(`b${bus.index}`)
  cy.zoom(Math.max(cy.zoom(), 1.2))
  cy.center(node)
  emit('select', { kind: 'bus', index: bus.index })
}

function applySelection() {
  if (!cy) return
  cy.$(':selected').unselect()
  if (props.selection) {
    const prefix = props.selection.kind === 'bus' ? 'b' : 'e'
    cy.getElementById(`${prefix}${props.selection.index}`).select()
  }
}

async function saveExport(kind: 'png' | 'csv') {
  if (!cy || !props.caseData || !props.fullDesign) return
  exporting.value = true
  exportSaved.value = false
  try {
    const content =
      kind === 'png'
        ? cy
            .png({
              full: true,
              scale: 2,
              maxWidth: 4096,
              maxHeight: 4096,
              bg: getComputedStyle(document.documentElement).getPropertyValue('--surface').trim(),
            })
            .replace(/^data:image\/png;base64,/, '')
        : resultsCsv(props.caseData, props.fullDesign, props.weights)
    exportSaved.value = await (await getApi()).save_export(kind, content)
  } catch (reason) {
    emit('error', errorMessage(reason))
  } finally {
    exporting.value = false
  }
}

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
  applySelection()
}

onMounted(() => {
  cy = cytoscape({
    container: container.value,
    style: graphStyle(),
    minZoom: 0.02,
    maxZoom: 6,
    textureOnViewport: true, // pan and zoom move a snapshot instead of redrawing
    boxSelectionEnabled: false,
  })
  resizeObserver = new ResizeObserver(() => {
    cy?.resize()
  })
  resizeObserver.observe(container.value!)
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
  resizeObserver?.disconnect()
  cy?.destroy()
  cy = null
})

watch(
  () => props.caseData,
  (data) => {
    searchTerm.value = ''
    searchFailed.value = false
    exportSaved.value = false
    emit('select', null)
    if (data) renderCase(data)
  },
)
watch(() => [props.design, props.showUnused, props.showBridges], applyDesign)
watch(() => props.selection, applySelection)
watch(searchTerm, () => {
  searchFailed.value = false
})
watch(
  () => props.darkMode,
  () => {
    cy?.style(graphStyle())
  },
)
</script>

<template>
  <section class="grid-canvas" :aria-label="t('powerNetwork')">
    <div class="canvas-bar">
      <span v-if="caseData">{{
        t('networkSize', {
          buses: formatNumber(caseData.buses.length),
          lines: formatNumber(caseData.branches.length),
        })
      }}</span>
      <span v-else>{{ t('network') }}</span>
      <div class="canvas-actions">
        <button type="button" :disabled="!caseData || computingLayout" @click="fitView">
          {{ t('fitView') }}
        </button>
        <button
          type="button"
          :disabled="!fullDesign || busy || computingLayout || exporting"
          :title="t('pngDescription')"
          @click="saveExport('png')"
        >
          PNG
        </button>
        <button
          type="button"
          :disabled="!fullDesign || busy || computingLayout || exporting"
          :title="t('csvDescription')"
          @click="saveExport('csv')"
        >
          CSV
        </button>
      </div>
    </div>
    <form class="bus-search" @submit.prevent="searchBus">
      <label for="bus-search" class="sr-only">{{ t('busId') }}</label>
      <input
        id="bus-search"
        v-model="searchTerm"
        type="search"
        inputmode="numeric"
        :placeholder="t('busId')"
        :aria-invalid="searchFailed"
        :aria-describedby="searchFailed ? 'bus-search-error' : undefined"
        :disabled="!caseData || busy || computingLayout"
      />
      <button type="submit" :disabled="!caseData || busy || computingLayout">
        {{ t('search') }}
      </button>
      <span v-if="searchFailed" id="bus-search-error" role="status">{{
        t('busNotFound', { id: searchTerm })
      }}</span>
      <span v-else-if="exporting" role="status">{{ t('exporting') }}</span>
      <span v-else-if="exportSaved" role="status">{{ t('exportSaved') }}</span>
    </form>
    <div ref="container" class="cytoscape" role="img" :aria-label="t('graphDescription')"></div>

    <div v-if="computingLayout" class="overlay" role="status">
      {{ t('arranging', { count: formatNumber(caseData?.buses.length ?? 0) }) }}
    </div>

    <ul class="legend">
      <li><span class="line tree"></span>{{ t('mst') }}</li>
      <li><span class="line added"></span>{{ t('added') }}</li>
      <li v-if="showBridges"><span class="line bridge"></span>{{ t('bridge') }}</li>
      <li v-if="showUnused"><span class="line unused"></span>{{ t('unused') }}</li>
      <li><span class="dot kv400"></span>400 kV</li>
      <li><span class="dot kv220"></span>220 kV</li>
      <li><span class="dot kv110"></span>110 kV</li>
      <li><span class="diamond"></span>{{ t('generation') }}</li>
    </ul>
  </section>
</template>

<style scoped>
.grid-canvas {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: var(--surface);
  overflow: hidden;
}

.canvas-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  color: var(--muted);
  font-size: 12px;
  flex-wrap: wrap;
}
.canvas-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
button {
  min-height: 32px;
  padding: 4px 12px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  color: var(--text);
}
.bus-search {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 16px 12px;
}
.bus-search input {
  min-width: 0;
  width: 144px;
  max-width: 100%;
  min-height: 32px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  color: var(--text);
  padding: 4px 8px;
}
.bus-search input::placeholder {
  color: var(--muted);
  opacity: 1;
}
.bus-search input[aria-invalid='true'] {
  border-color: var(--error-text);
}
.bus-search span {
  font-size: 12px;
  color: var(--muted);
}
.cytoscape {
  position: relative;
  flex: 1;
  min-height: 200px;
}

.overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: var(--surface);
  text-align: center;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  margin: 0;
  padding: 12px 16px;
  list-style: none;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 11px;
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
  background: var(--graph-tree);
}

.line.added {
  background: var(--graph-added);
}

.line.bridge {
  border-top: 2px dashed var(--graph-bridge);
}

.line.unused {
  background: var(--graph-unused);
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.kv400 {
  background: var(--graph-kv400);
}

.dot.kv220 {
  background: var(--graph-kv220);
}

.dot.kv110 {
  background: var(--graph-kv110);
}

.diamond {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: var(--graph-tree);
  transform: rotate(45deg);
}

@media (max-width: 760px) {
  .grid-canvas {
    height: 65vh;
    min-height: 400px;
  }
}
</style>
