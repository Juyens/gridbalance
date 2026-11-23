// Sources, layers and pins added on top of the OpenFreeMap style.

import type {
  ExpressionSpecification,
  FilterSpecification,
  LayerSpecification,
  Map as MapLibreMap,
} from 'maplibre-gl'
import type { FeatureCollection } from './mapFeatures'

export const SOURCES = ['circle', 'existing', 'branches', 'active', 'buses'] as const
export type SourceName = (typeof SOURCES)[number]

// Layers that answer to a click, the first ones win.
export const CLICKABLE = [
  'pins',
  'pins-load',
  'dots-load',
  'lines-bridge',
  'lines-added',
  'lines-tree',
  'lines-unused',
]

// What the replay shows instead of the finished network.
export const REPLAY_LAYERS = ['replay-flash', 'replay-lines', 'replay-active', 'replay-head']
export const HIDDEN_IN_REPLAY = [
  'lines-existing',
  'lines-unused',
  'lines-tree',
  'lines-added',
  'lines-bridge',
  'lines-selected',
  'line-labels',
  'labels-load',
]

export const isLineLayer = (layer: string) => layer.startsWith('lines-')

const FONT = ['Noto Sans Regular']
const LINE_LABEL_ZOOM = 14.5
const SOURCE_LABEL_ZOOM = 11
// Farther than this, demand is drawn as dots so the network stays readable.
const PIN_ZOOM = 13.5
const PIXEL_RATIO = 2
const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] }

export function mapColors() {
  const tokens = getComputedStyle(document.documentElement)
  const color = (name: string) => tokens.getPropertyValue(`--graph-${name}`).trim()
  return {
    tree: color('tree'),
    added: color('added'),
    bridge: color('bridge'),
    unused: color('unused'),
    existing: color('existing'),
    source: color('source'),
    plant: color('plant'),
    load: color('load'),
    selected: color('selected'),
    text: color('text'),
    halo: color('halo'),
  }
}

type Colors = ReturnType<typeof mapColors>

// Teardrop pin with its tip at the bottom centre.
function pinImage(color: string, halo: string): ImageData {
  const size = 24 * PIXEL_RATIO
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  context.scale(size / 24, size / 24)
  context.fillStyle = color
  context.strokeStyle = halo
  context.lineWidth = 1.5
  context.beginPath()
  context.moveTo(12, 23)
  context.bezierCurveTo(6, 16, 4, 13, 4, 9.5)
  context.arc(12, 9.5, 8, Math.PI, 0)
  context.bezierCurveTo(20, 13, 18, 16, 12, 23)
  context.closePath()
  context.fill()
  context.stroke()
  context.fillStyle = halo
  context.beginPath()
  context.arc(12, 9.5, 3, 0, 2 * Math.PI)
  context.fill()
  return context.getImageData(0, 0, size, size)
}

// High voltage lines are drawn thicker.
function lineWidth(base: number): ExpressionSpecification {
  const at = (scale: number): ExpressionSpecification => [
    '*',
    base * scale,
    ['case', ['>=', ['coalesce', ['get', 'kv'], 0], 60], 1.6, 1],
  ]
  return ['interpolate', ['linear'], ['zoom'], 5, at(0.3), 9, at(0.5), 13, at(1), 17, at(2)]
}

function layers(colors: Colors): LayerSpecification[] {
  const status = (value: string): FilterSpecification => ['==', ['get', 'status'], value]
  const round = { 'line-cap': 'round', 'line-join': 'round' } as const
  return [
    {
      id: 'circle',
      type: 'line',
      source: 'circle',
      paint: { 'line-color': colors.text, 'line-opacity': 0.5, 'line-dasharray': [2, 3] },
    },
    {
      id: 'lines-existing',
      type: 'line',
      source: 'existing',
      layout: round,
      paint: {
        'line-color': colors.existing,
        'line-width': lineWidth(2),
        'line-dasharray': [4, 2],
      },
    },
    {
      id: 'lines-unused',
      type: 'line',
      source: 'branches',
      filter: status('unused'),
      paint: { 'line-color': colors.unused, 'line-width': lineWidth(1.2) },
    },
    {
      id: 'lines-tree',
      type: 'line',
      source: 'branches',
      filter: status('tree'),
      layout: round,
      paint: { 'line-color': colors.tree, 'line-width': lineWidth(2) },
    },
    {
      id: 'lines-added',
      type: 'line',
      source: 'branches',
      filter: status('added'),
      layout: round,
      paint: { 'line-color': colors.added, 'line-width': lineWidth(3) },
    },
    {
      id: 'lines-bridge',
      type: 'line',
      source: 'branches',
      filter: ['get', 'bridge'],
      paint: {
        'line-color': colors.bridge,
        'line-width': lineWidth(3),
        'line-dasharray': [2, 1],
      },
    },
    {
      id: 'lines-selected',
      type: 'line',
      source: 'branches',
      filter: ['==', ['get', 'index'], -1],
      layout: round,
      paint: { 'line-color': colors.selected, 'line-width': lineWidth(6) },
    },
    {
      id: 'replay-flash',
      type: 'line',
      source: 'branches',
      filter: ['!=', ['get', 'status'], 'unused'],
      layout: { ...round, visibility: 'none' },
      paint: {
        'line-color': colors.selected,
        'line-width': lineWidth(9),
        'line-blur': 4,
        'line-opacity': ['case', ['boolean', ['feature-state', 'flash'], false], 0.9, 0],
      },
    },
    {
      id: 'replay-lines',
      type: 'line',
      source: 'branches',
      filter: ['!=', ['get', 'status'], 'unused'],
      layout: { ...round, visibility: 'none' },
      paint: {
        'line-color': [
          'case',
          ['==', ['get', 'status'], 'added'],
          colors.added,
          ['boolean', ['feature-state', 'bridge'], false],
          colors.bridge,
          colors.tree,
        ],
        'line-width': lineWidth(2.6),
        'line-opacity': ['case', ['boolean', ['feature-state', 'on'], false], 1, 0],
      },
    },
    {
      id: 'replay-active',
      type: 'line',
      source: 'active',
      layout: { ...round, visibility: 'none' },
      paint: { 'line-color': colors.selected, 'line-width': lineWidth(4.5) },
    },
    {
      id: 'replay-head',
      type: 'circle',
      source: 'active',
      filter: ['==', ['geometry-type'], 'Point'],
      layout: { visibility: 'none' },
      paint: {
        'circle-radius': 6,
        'circle-color': colors.selected,
        'circle-stroke-color': colors.halo,
        'circle-stroke-width': 2,
      },
    },
    {
      id: 'line-labels',
      type: 'symbol',
      source: 'branches',
      filter: ['!=', ['get', 'status'], 'unused'],
      minzoom: LINE_LABEL_ZOOM,
      layout: {
        'symbol-placement': 'line-center',
        'text-field': ['get', 'label'],
        'text-font': FONT,
        'text-size': 11,
      },
      paint: { 'text-color': colors.text, 'text-halo-color': colors.halo, 'text-halo-width': 1.5 },
    },
    {
      id: 'pin-selected',
      type: 'circle',
      source: 'buses',
      filter: ['==', ['get', 'index'], -1],
      paint: { 'circle-radius': 9, 'circle-color': colors.selected, 'circle-opacity': 0.5 },
    },
    {
      id: 'dots-load',
      type: 'circle',
      source: 'buses',
      filter: ['!', ['get', 'source']],
      maxzoom: PIN_ZOOM,
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 0.8, 9, 1.4, 13, 3.5],
        'circle-color': colors.load,
        'circle-stroke-color': colors.halo,
        'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 10, 0, 13, 1],
      },
    },
    {
      id: 'pins-load',
      type: 'symbol',
      source: 'buses',
      filter: ['!', ['get', 'source']],
      minzoom: PIN_ZOOM,
      layout: {
        'icon-image': 'pin-load',
        'icon-anchor': 'bottom',
        'icon-allow-overlap': true,
        'icon-size': ['interpolate', ['linear'], ['zoom'], PIN_ZOOM, 0.7, 16, 1],
      },
    },
    {
      id: 'pins',
      type: 'symbol',
      source: 'buses',
      filter: ['get', 'source'],
      layout: {
        'icon-image': ['concat', 'pin-', ['get', 'icon']],
        'icon-anchor': 'bottom',
        'icon-allow-overlap': true,
        'icon-size': [
          'interpolate',
          ['linear'],
          ['zoom'],
          5,
          0.22,
          7,
          0.4,
          9,
          0.7,
          13,
          1.2,
          16,
          1.5,
        ],
      },
    },
    {
      id: 'labels-source',
      type: 'symbol',
      source: 'buses',
      filter: ['get', 'source'],
      minzoom: SOURCE_LABEL_ZOOM,
      layout: {
        // From afar only the name; closer, the cost too.
        'text-field': ['step', ['zoom'], ['get', 'name'], PIN_ZOOM, ['get', 'label']],
        'text-font': FONT,
        'text-size': 12,
        'text-anchor': 'top',
        'text-offset': [0, 0.3],
      },
      paint: { 'text-color': colors.text, 'text-halo-color': colors.halo, 'text-halo-width': 1.8 },
    },
    {
      id: 'labels-load',
      type: 'symbol',
      source: 'buses',
      filter: ['!', ['get', 'source']],
      minzoom: PIN_ZOOM,
      layout: {
        'text-field': ['get', 'label'],
        'text-font': FONT,
        'text-size': 11,
        'text-anchor': 'top',
        'text-offset': [0, 0.3],
      },
      paint: { 'text-color': colors.text, 'text-halo-color': colors.halo, 'text-halo-width': 1.5 },
    },
  ]
}

// A style change (light or dark) removes everything, so this runs after each one.
export function addOverlay(map: MapLibreMap) {
  const colors = mapColors()
  for (const icon of ['source', 'plant', 'load'] as const) {
    map.addImage(`pin-${icon}`, pinImage(colors[icon], colors.halo), { pixelRatio: PIXEL_RATIO })
  }
  for (const name of SOURCES) {
    // The replay changes the state of each line by its index.
    const ids = name === 'branches' ? { promoteId: 'index' } : {}
    map.addSource(name, { type: 'geojson', data: EMPTY, ...ids })
  }
  for (const layer of layers(colors)) map.addLayer(layer)
}
