<script setup lang="ts">
import {
  LngLatBounds,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  Popup,
  setWorkerUrl,
  type GeoJSONSource,
  type MapMouseEvent,
} from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { errorMessage, getApi } from '../api'
import { resultsCsv } from '../export'
import { formatCost, formatNumber } from '../format'
import { locale, t } from '../i18n'
import {
  branchFeatures,
  busCosts,
  busFeatures,
  circleFeature,
  circlePoints,
  existingFeatures,
  position,
  type FeatureCollection,
} from '../mapFeatures'
import { MapReplay } from '../mapReplay'
import {
  addOverlay,
  CLICKABLE,
  HIDDEN_IN_REPLAY,
  isLineLayer,
  REPLAY_LAYERS,
  type SourceName,
} from '../mapStyle'
import { busName } from '../names'
import { POLAND, type LngLat, type Place } from '../places'
import type { Frame } from '../replay'
import type { BranchData, BusData, CaseData, DesignData, Selection, Weights } from '../types'
import MapLegend from './MapLegend.vue'
import PlaceSearch from './PlaceSearch.vue'
import { showWorldGrid, WORLD_GRID_SOURCE } from '../worldGrid'

const props = defineProps<{
  caseData: CaseData | null
  design: DesignData | null
  frame: Frame | null // of the replay, while it is open
  weights: Weights
  busy: boolean
  loading: boolean
  selection: Selection
  darkMode: boolean
}>()

const radiusKm = defineModel<number | null>('radius', { required: true })
const worldMode = defineModel<boolean>('world', { required: true })

const emit = defineEmits<{
  place: [place: Place]
  select: [selection: Selection]
  error: [message: string]
}>()

setWorkerUrl(workerUrl)

const START: LngLat = [-77.0934, -12.0764]
const START_ZOOM = 13
const RADII_KM = [2, 5, 10, 20, 40, 80]
const CLICK_TOLERANCE = 5 // pixels
const HOVER_DELAY_MS = 250
// Room for the search on top and, while it is open, the replay at the bottom.
const FIT_PADDING = { top: 124, right: 24, bottom: 48, left: 24 }
const REPLAY_HEIGHT = 170
const styleUrl = (dark: boolean) =>
  `https://tiles.openfreemap.org/styles/${dark ? 'fiord' : 'liberty'}`

const mapElement = ref<HTMLDivElement>()
const center = ref<LngLat>(START)
const radiusDraft = ref<number | ''>('')
const failed = ref(false)
const worldFailed = ref(false)
const showExisting = ref(true)
const showBridges = ref(false)
const showUnused = ref(false)
const exporting = ref(false)
const exportSaved = ref(false)

// Plain variables: the map objects must not become reactive.
let map: MapLibreMap | undefined
let marker: Marker | undefined
let popup: Popup | undefined
let hoverPopup: Popup | undefined
let hovered = ''
let hoverTimer: ReturnType<typeof setTimeout> | undefined
let replay: MapReplay | undefined
let styleReady = false
let localLayers: string[] = []

const trimmedNote = computed(() =>
  props.caseData && props.caseData.zone.totalSites > props.caseData.buses.length
    ? t('zoneTrimmed', { total: formatNumber(props.caseData.zone.totalSites) })
    : undefined,
)

onMounted(() => {
  map = new MapLibreMap({
    container: mapElement.value!,
    style: styleUrl(props.darkMode),
    center: START,
    zoom: START_ZOOM,
    attributionControl: { compact: false },
    canvasContextAttributes: { preserveDrawingBuffer: true }, // needed to save the PNG
  })
  map.addControl(new NavigationControl({ showCompass: false }), 'bottom-right')
  map.on('moveend', () => {
    const { lng, lat } = map!.getCenter().wrap()
    center.value = [lng, lat]
  })
  map.on('style.load', () => {
    styleReady = true
    failed.value = false
    localLayers = addOverlay(map!)
    drawZone()
    drawDesign()
    updateWorldLayer()
    applySelection()
    replay = undefined // its states were lost with the old style
    showFrame()
  })
  map.on('error', (event) => {
    // A missing tile is harmless; without a style there is no map at all.
    if (!styleReady) failed.value = true
    if ('sourceId' in event && event.sourceId === WORLD_GRID_SOURCE) worldFailed.value = true
  })
  map.on('click', onClick)
  map.on('mousemove', onHover)
  map.on('mouseout', clearHover)
  const dot = document.createElement('div')
  dot.className = 'place-marker'
  marker = new Marker({ element: dot })
  const benchmark = document.createElement('button')
  benchmark.type = 'button'
  benchmark.className = 'benchmark-marker'
  benchmark.textContent = POLAND.address
  benchmark.onclick = (event) => {
    event.stopPropagation()
    goTo(POLAND)
  }
  new Marker({ element: benchmark, anchor: 'bottom', offset: [0, -15] })
    .setLngLat(POLAND.center)
    .addTo(map)
  watch(
    [locale, worldMode, () => props.caseData],
    () => {
      benchmark.title = t('polandCase')
      benchmark.hidden = !worldMode.value && props.caseData?.zone.radiusKm === null
    },
    { immediate: true },
  )
})

onUnmounted(() => {
  clearTimeout(hoverTimer)
  map?.remove()
})

function setData(name: SourceName, data: FeatureCollection) {
  map?.getSource<GeoJSONSource>(name)?.setData(data)
}

function drawZone() {
  if (!styleReady || !props.caseData) return
  setData('circle', circleFeature(props.caseData.zone))
  setData('existing', existingFeatures(props.caseData))
}

function drawDesign() {
  if (!styleReady || !props.caseData) return
  const { costUnit } = props.caseData
  const cost = (value: number) => formatCost(value, costUnit)
  const label = (bus: BusData, value: number) => `${busName(bus)}\n${cost(value)}`
  setData('branches', branchFeatures(props.caseData, props.design, cost))
  setData('buses', busFeatures(props.caseData, props.design, label))
}

function applyVisibility() {
  if (!styleReady) return
  const playing = props.frame !== null
  const visibleLines: Record<string, boolean> = {
    'lines-unused': showUnused.value,
    'lines-bridge': showBridges.value,
    'lines-existing': showExisting.value,
  }
  for (const layer of localLayers) {
    const visible = REPLAY_LAYERS.includes(layer)
      ? playing
      : !(playing && HIDDEN_IN_REPLAY.includes(layer)) && (visibleLines[layer] ?? true)
    map!.setLayoutProperty(layer, 'visibility', visible && !worldMode.value ? 'visible' : 'none')
  }
}

function updateWorldLayer() {
  if (!map || !styleReady) return
  worldFailed.value = false
  showWorldGrid(map, worldMode.value, props.darkMode)
  applyVisibility()
}

function showFrame() {
  const { caseData, design, frame } = props
  if (!styleReady || worldMode.value || !caseData || !design || !frame) {
    replay?.stop()
    replay = undefined
    return
  }
  replay ??= new MapReplay(map!, caseData, design)
  replay.show(frame)
}

function fitZone() {
  if (!props.caseData || worldMode.value) return
  const bounds = new LngLatBounds()
  const { zone, buses } = props.caseData
  const points = zone.radiusKm === null ? buses.map(position) : circlePoints(zone)
  for (const point of points) bounds.extend(point)
  const bottom = props.frame ? REPLAY_HEIGHT : FIT_PADDING.bottom
  map?.fitBounds(bounds, { padding: { ...FIT_PADDING, bottom } })
}

function featureAt(event: MapMouseEvent) {
  if (!styleReady || worldMode.value || props.frame) return undefined
  const { x, y } = event.point
  const box: [[number, number], [number, number]] = [
    [x - CLICK_TOLERANCE, y - CLICK_TOLERANCE],
    [x + CLICK_TOLERANCE, y + CLICK_TOLERANCE],
  ]
  for (const layer of CLICKABLE) {
    const features = map!.queryRenderedFeatures(box, { layers: [layer] })
    // Pins overlap when zoomed out: a substation wins over the demand around it.
    const feature = features.find(({ properties }) => properties.source) ?? features[0]
    if (feature) return { kind: isLineLayer(layer) ? 'branch' : 'bus', feature } as const
  }
  return undefined
}

function clearHover() {
  clearTimeout(hoverTimer)
  hoverPopup?.remove()
  hoverPopup = undefined
  hovered = ''
}

// Pointing at a pin or line shows the same summary as selecting it.
function onHover(event: MapMouseEvent) {
  const hit = featureAt(event)
  map!.getCanvas().style.cursor = hit ? 'pointer' : ''
  const index = Number(hit?.feature.properties.index)
  const key = hit ? `${hit.kind}${index}` : ''
  if (key === hovered) return
  clearHover()
  hovered = key
  const { caseData, selection } = props
  if (!hit || !caseData) return
  if (selection?.kind === hit.kind && selection.index === index) return
  // A short wait, so crossing the map does not leave a trail of popups.
  hoverTimer = setTimeout(() => {
    hoverPopup =
      hit.kind === 'bus'
        ? openPopup(position(caseData.buses[index]!), busPopup(caseData.buses[index]!))
        : openPopup(event.lngLat.toArray() as LngLat, branchPopup(caseData.branches[index]!))
  }, HOVER_DELAY_MS)
}

function onClick(event: MapMouseEvent) {
  if (props.frame) return // the replay has its own controls
  clearHover()
  const hit = featureAt(event)
  emit('select', hit ? { kind: hit.kind, index: Number(hit.feature.properties.index) } : null)
}

function applySelection() {
  popup?.remove()
  popup = undefined
  if (!styleReady) return
  const { caseData, selection } = props
  const selected = (kind: 'bus' | 'branch') =>
    caseData && selection?.kind === kind ? selection.index : -1
  map!.setFilter('pin-selected', ['==', ['get', 'index'], selected('bus')])
  // A selected pin highlights the lines of the design that reach it.
  const bus = selected('bus')
  map!.setFilter('lines-selected', [
    'any',
    ['==', ['get', 'index'], selected('branch')],
    [
      'all',
      ['!=', ['get', 'status'], 'unused'],
      ['any', ['==', ['get', 'from'], bus], ['==', ['get', 'to'], bus]],
    ],
  ])
  if (!caseData || !selection) return
  if (selection.kind === 'bus') {
    const bus = caseData.buses[selection.index]!
    popup = openPopup(position(bus), busPopup(bus))
  } else {
    const branch = caseData.branches[selection.index]!
    const from = caseData.buses[branch.from]!
    const to = caseData.buses[branch.to]!
    popup = openPopup([(from.lon + to.lon) / 2, (from.lat + to.lat) / 2], branchPopup(branch))
  }
}

function openPopup(at: LngLat, lines: string[]): Popup {
  const content = document.createElement('div')
  lines.forEach((text, index) => {
    const row = document.createElement(index === 0 ? 'strong' : 'div')
    row.textContent = text // never as HTML: names come from OpenStreetMap
    content.append(row)
  })
  return new Popup({ closeButton: false, closeOnClick: false, offset: 12 })
    .setLngLat(at)
    .setDOMContent(content)
    .addTo(map!)
}

function busPopup(bus: BusData): string[] {
  const lines = [busName(bus)]
  if (bus.supplyMw > 0) lines.push(`${t('supply')}: ${formatNumber(bus.supplyMw, 1)} MW`)
  if (bus.loadMw > 0) lines.push(`${t('load')}: ${formatNumber(bus.loadMw, 2)} MW`)
  lines.push(
    `${t('linesCost')}: ${formatCost(busCosts(props.caseData!, props.design)[bus.index]!, props.caseData!.costUnit)}`,
  )
  return lines
}

function branchPopup(branch: BranchData): string[] {
  const { buses, costUnit } = props.caseData!
  const voltage = `${formatNumber(branch.kv, branch.kv % 1 ? 1 : 0)} kV`
  return [
    `${busName(buses[branch.from]!)} – ${busName(buses[branch.to]!)}`,
    `${t('cost')}: ${formatCost(branch.cost, costUnit)}`,
    branch.lengthKm === null ? voltage : `${formatNumber(branch.lengthKm, 2)} km, ${voltage}`,
  ]
}

function goTo(place: Place) {
  worldMode.value = false
  marker?.setLngLat(place.center).addTo(map!)
  map?.flyTo({ center: place.center, zoom: place.source === 'poland' ? 5 : START_ZOOM })
  emit('place', place)
}

async function toggleWorld() {
  const enabled = !worldMode.value
  worldMode.value = enabled
  await nextTick()
  if (worldMode.value !== enabled) return
  if (enabled) {
    clearHover()
    marker?.remove()
    map?.fitBounds(
      [
        [-179.5, -63],
        [179.5, 79],
      ],
      {
        padding: { top: 78, right: 20, bottom: 48, left: 20 },
      animate: false,
      },
    )
  } else if (props.caseData) {
    const { lon, lat, radiusKm } = props.caseData.zone
    if (radiusKm !== null && map) marker?.setLngLat([lon, lat]).addTo(map)
    fitZone()
  }
}

function analyzeHere() {
  const [lon, lat] = map?.getCenter().wrap().toArray() ?? center.value
  goTo({
    name: `${lat.toFixed(4)}, ${lon.toFixed(4)}`,
    address: '',
    center: [lon, lat],
    bounds: null,
  })
}

watch(radiusKm, (radius) => {
  radiusDraft.value = radius ?? ''
})
watch(worldMode, updateWorldLayer)

async function saveExport(kind: 'png' | 'csv') {
  if (!map || !props.caseData || !props.design) return
  exporting.value = true
  exportSaved.value = false
  try {
    const content =
      kind === 'png'
        ? map.getCanvas().toDataURL('image/png').replace('data:image/png;base64,', '')
        : resultsCsv(props.caseData, props.design, props.weights)
    exportSaved.value = await (await getApi()).save_export(kind, content)
  } catch (reason) {
    emit('error', errorMessage(reason))
  } finally {
    exporting.value = false
  }
}

watch(
  () => props.darkMode,
  (dark) => {
    styleReady = false
    map?.setStyle(styleUrl(dark), { diff: false })
  },
)
watch(
  () => props.caseData,
  (data) => {
    exportSaved.value = false
    if (!data) return
    if (worldMode.value) return
    if (data.zone.radiusKm === null) marker?.remove()
    else marker?.setLngLat([data.zone.lon, data.zone.lat]).addTo(map!)
    drawZone()
    fitZone()
  },
)
watch([() => props.caseData, () => props.design, locale], () => {
  drawDesign()
  applySelection()
})
watch(() => props.selection, applySelection)
watch(
  () => props.frame === null,
  (closed) => {
    clearHover()
    applyVisibility()
    if (closed) showFrame()
    fitZone()
  },
)
watch(
  () => props.frame,
  (frame) => {
    if (frame) showFrame()
  },
)
watch([showUnused, showBridges, showExisting], applyVisibility)
</script>

<template>
  <section class="grid-map" :aria-label="t('powerNetwork')">
    <div ref="mapElement" class="map" role="region" :aria-label="t('mapDescription')"></div>

    <div class="top">
      <div class="search-card">
        <PlaceSearch :near="center" @select="goTo" />
        <div v-if="!worldMode" class="zone-line">
          <form
            v-if="caseData?.zone.radiusKm !== null"
            class="radius-form"
            @submit.prevent="radiusKm = radiusDraft === '' ? null : Number(radiusDraft)"
          >
            <label>
              {{ t('radius') }} (km)
              <input
                v-model.number="radiusDraft"
                type="number"
                min="1"
                max="100"
                step="any"
                list="radius-suggestions"
                :placeholder="caseData?.zone.radiusKm?.toString()"
                :disabled="busy"
              />
            </label>
            <datalist id="radius-suggestions">
              <option v-for="radius in RADII_KM" :key="radius" :value="radius" />
            </datalist>
            <button type="submit" :disabled="busy">{{ t('applyRadius') }}</button>
            <button
              type="button"
              :aria-pressed="radiusKm === null"
              :disabled="busy"
              @click="((radiusDraft = ''), (radiusKm = null))"
            >
              {{ t('automatic') }}
            </button>
          </form>
          <span v-else>{{ t('polandCase') }}</span>
          <span v-if="busy" class="busy" role="status">{{
            t(loading ? 'loadingNetwork' : 'designing')
          }}</span>
          <span v-else-if="caseData" :title="trimmedNote">
            {{
              t('networkSize', {
                buses: formatNumber(caseData.buses.length),
                lines: formatNumber(caseData.branches.length),
              })
            }}{{ trimmedNote ? ' *' : '' }}
          </span>
        </div>
      </div>

      <div class="actions">
        <span v-if="exporting" class="note" role="status">{{ t('exporting') }}</span>
        <span v-else-if="exportSaved" class="note" role="status">{{ t('exportSaved') }}</span>
        <button type="button" :disabled="busy" :aria-pressed="worldMode" @click="toggleWorld">
          {{ t('worldView') }}
        </button>
        <button type="button" :disabled="busy" @click="analyzeHere">{{ t('analyzeHere') }}</button>
        <button v-if="!worldMode" type="button" :disabled="!caseData" @click="fitZone">
          {{ t('fitView') }}
        </button>
        <button
          v-if="!worldMode"
          type="button"
          :disabled="!design || busy || exporting"
          :title="t('pngDescription')"
          @click="saveExport('png')"
        >
          PNG
        </button>
        <button
          v-if="!worldMode"
          type="button"
          :disabled="!design || busy || exporting"
          :title="t('csvDescription')"
          @click="saveExport('csv')"
        >
          CSV
        </button>
      </div>
    </div>

    <p v-if="failed" class="failure" role="alert">{{ t('mapLoadError') }}</p>
    <p v-else-if="worldMode && worldFailed" class="failure" role="status">
      {{ t('worldGridError') }}
    </p>
    <div class="bottom">
      <p v-if="worldMode" class="world-legend">{{ t('worldGridLegend') }}</p>
      <MapLegend
        v-show="!worldMode && !frame"
        v-model:existing="showExisting"
        v-model:bridges="showBridges"
        v-model:unused="showUnused"
      />
      <slot v-if="!worldMode" name="bottom"></slot>
    </div>
  </section>
</template>

<style scoped>
.grid-map {
  position: relative;
  min-width: 0;
  min-height: 0;
  background: var(--background);
}

.map {
  position: absolute;
  inset: 0;
}

.top {
  position: absolute;
  top: 12px;
  right: 12px;
  left: 12px;
  z-index: 6;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  pointer-events: none; /* the map stays draggable between the cards */
}

.bottom {
  position: absolute;
  right: 56px; /* zoom buttons */
  bottom: 34px; /* map credits */
  left: 12px;
  z-index: 5;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  pointer-events: none;
}

.top > *,
.bottom > * {
  pointer-events: auto;
}

.search-card {
  flex: 0 1 440px;
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

.search-card:focus-within {
  border-color: var(--accent);
}

.zone-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px 12px;
  padding: 6px 12px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.zone-line label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.radius-form {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.radius-form input,
.radius-form button {
  min-height: 28px;
  padding: 2px 4px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  color: var(--text);
  font-weight: 600;
}

.radius-form input {
  width: 62px;
}

.radius-form button[aria-pressed='true'] {
  background: var(--accent-soft);
  color: var(--accent);
}

.map :deep(.benchmark-marker) {
  padding: 5px 8px;
  border: 1px solid var(--border);
  border-radius: 5px;
  background: var(--surface);
  color: var(--accent);
  box-shadow: var(--shadow);
  font: 600 12px var(--font-ui);
}

.busy {
  color: var(--accent);
}

.actions {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

.actions button {
  min-height: 32px;
  padding: 4px 10px;
  border: 0;
  border-radius: 5px;
  background: none;
  color: var(--text);
  font-size: 13px;
}

.actions button[aria-pressed='true'] {
  background: var(--accent-soft);
  color: var(--accent);
}

.world-legend {
  margin: 0;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
  font-size: 12px;
}

.note {
  padding: 0 8px;
  color: var(--muted);
  font-size: 12px;
}

.failure {
  position: absolute;
  top: 50%;
  left: 50%;
  z-index: 6;
  margin: 0;
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--error-surface);
  color: var(--error-text);
  transform: translate(-50%, -50%);
}

/* MapLibre's own controls follow the app theme. */
.map :deep(.place-marker) {
  width: 18px;
  height: 18px;
  border: 3px solid #fff;
  border-radius: 50%;
  background: #1a73e8;
  box-shadow: 0 1px 5px rgb(0 0 0 / 45%);
}

/* The pointer must reach the map under the popup, or it would close itself. */
.map :deep(.maplibregl-popup),
.map :deep(.maplibregl-popup-content) {
  pointer-events: none;
}

.map :deep(.maplibregl-popup-tip) {
  display: none;
}

.map :deep(.maplibregl-popup-content) {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
  color: var(--muted);
  font: 12px/1.5 var(--font-ui);
}

.map :deep(.maplibregl-popup-content strong) {
  display: block;
  color: var(--text);
  font-size: 13px;
}

.map :deep(.maplibregl-ctrl-group) {
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow);
}

.map :deep(.maplibregl-ctrl-group button + button) {
  border-top-color: var(--border);
}

:root[data-theme='dark'] .map :deep(.maplibregl-ctrl-icon) {
  filter: invert(1);
}

.map :deep(.maplibregl-ctrl-attrib) {
  background: color-mix(in oklch, var(--surface) 80%, transparent);
  color: var(--muted);
  font-size: 11px;
}

.map :deep(.maplibregl-ctrl-attrib a) {
  color: inherit;
}

@media (max-width: 1100px) {
  .bottom {
    flex-direction: column;
    align-items: stretch;
  }
  .bottom > * {
    align-self: flex-start;
  }
  .bottom > :deep(.replay) {
    align-self: stretch;
    flex: none;
  }
}

@media (max-width: 900px) {
  .top {
    flex-direction: column;
    align-items: stretch;
  }
  .search-card {
    flex-basis: auto;
  }
  .actions {
    align-self: flex-end;
  }
}
</style>
