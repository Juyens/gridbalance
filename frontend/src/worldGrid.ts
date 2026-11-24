import type { Map as MapLibreMap } from 'maplibre-gl'

export const WORLD_GRID_SOURCE = 'world-power'
const WORLD_LAYERS = ['world-power-lines', 'world-power-stations']

export function showWorldGrid(map: MapLibreMap, visible: boolean, dark: boolean) {
  if (!visible) {
    if (!map.getSource(WORLD_GRID_SOURCE)) return
    for (const id of WORLD_LAYERS) map.removeLayer(id)
    map.removeSource(WORLD_GRID_SOURCE)
    return
  }
  if (map.getSource(WORLD_GRID_SOURCE)) return

  map.addSource(WORLD_GRID_SOURCE, {
    type: 'vector',
    tiles: ['https://openinframap.org/map/power/{z}/{x}/{y}.pbf'],
    maxzoom: 17,
    attribution:
      '<a href="https://openinframap.org/copyright">Open Infrastructure Map</a> · ' +
      '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>',
  })

  map.addLayer({
    id: 'world-power-lines',
    type: 'line',
    source: WORLD_GRID_SOURCE,
    'source-layer': 'power_line',
    paint: {
      'line-color': dark ? '#6ddfc1' : '#0d6b57',
      'line-opacity': ['interpolate', ['linear'], ['zoom'], 1, 0.82, 12, 0.72],
      'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.8, 7, 1.15, 13, 2],
    },
  })
  map.addLayer({
    id: 'world-power-stations',
    type: 'circle',
    source: WORLD_GRID_SOURCE,
    'source-layer': 'power_substation_point',
    minzoom: 6,
    paint: {
      'circle-color': dark ? '#f4c66b' : '#99590b',
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 1.6, 13, 3.5],
      'circle-stroke-width': 0.8,
      'circle-stroke-color': dark ? '#101820' : '#ffffff',
    },
  })
}
