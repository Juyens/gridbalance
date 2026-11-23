// App state: the loaded zone, the current weights and the design they produce.

import { ref, shallowRef, watch } from 'vue'
import { errorMessage, getApi } from '../api'
import { POLAND, type Place } from '../places'
import type { CaseData, DesignData, Weights } from '../types'
import { PRESETS } from '../weights'

// Wait until the sliders stop moving before asking Python for a new design.
const DEBOUNCE_MS = 250

// UPC San Miguel, Lima.
const START: Place = {
  name: 'UPC San Miguel',
  address: 'Lima',
  center: [-77.0934, -12.0764],
  bounds: null,
}

export function useGridDesign() {
  // shallowRef: the zone holds thousands of buses and branches that never change,
  // so Vue only needs to notice when the whole object is replaced.
  const caseData = shallowRef<CaseData | null>(null)
  const design = shallowRef<DesignData | null>(null)
  const weights = ref<Weights>({ ...PRESETS.Balanced! })
  const place = ref(START)
  const zoneName = ref(START.name)
  const radiusKm = ref<number | null>(null) // null lets Python choose it
  const noData = ref(false)
  const loadingCase = ref(false)
  const designing = ref(false)
  const error = ref<string | null>(null)

  // Each design request gets a number; only the answer to the latest one is kept,
  // so a slow answer to an old slider position never overwrites a newer one.
  let latestRequest = 0
  let debounceTimer: ReturnType<typeof setTimeout> | undefined

  async function requestDesign() {
    if (!caseData.value) return
    const request = ++latestRequest
    designing.value = true
    error.value = null
    try {
      const result = await (await getApi()).design({ ...weights.value })
      if (request === latestRequest) design.value = result
    } catch (reason) {
      if (request === latestRequest) error.value = errorMessage(reason)
    } finally {
      if (request === latestRequest) designing.value = false
    }
  }

  // Like designs, only the answer to the latest zone request is kept.
  let latestZone = 0

  async function loadZone() {
    const request = ++latestZone
    const { center, isCase, name } = place.value
    latestRequest += 1 // a design still on its way belongs to the previous zone
    loadingCase.value = true
    noData.value = false
    error.value = null
    try {
      const api = await getApi()
      const data = isCase
        ? await api.load_case()
        : await api.load_zone(center[1], center[0], radiusKm.value)
      if (request !== latestZone) return
      if (!data) {
        noData.value = true
        return
      }
      design.value = null
      caseData.value = data
      zoneName.value = isCase ? `${POLAND.name} (${POLAND.address})` : name
      await requestDesign()
    } catch (reason) {
      if (request === latestZone) error.value = errorMessage(reason)
    } finally {
      if (request === latestZone) loadingCase.value = false
    }
  }

  // Without a radius, the zone keeps the one chosen before.
  async function goTo(target: Place, radius: number | null = radiusKm.value) {
    place.value = target
    // Changing the radius already loads the zone.
    if (radius !== radiusKm.value) radiusKm.value = radius
    else await loadZone()
  }

  watch(radiusKm, loadZone)

  watch(weights, () => {
    latestRequest += 1
    designing.value = caseData.value !== null
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(requestDesign, DEBOUNCE_MS)
  })

  return {
    caseData,
    design,
    weights,
    zoneName,
    radiusKm,
    noData,
    loadingCase,
    designing,
    error,
    goTo,
    start: loadZone,
  }
}
