// App state: the loaded zone, the current weights and the design they produce.

import { ref, shallowRef, watch } from 'vue'
import { errorMessage, getApi } from '../api'
import type { CaseData, DesignData, Weights } from '../types'
import { PRESETS } from '../weights'

// Wait until the sliders stop moving before asking Python for a new design.
const DEBOUNCE_MS = 250

// UPC San Miguel, Lima.
const START = { lat: -12.0764, lon: -77.0934, name: 'UPC San Miguel' }

export function useGridDesign() {
  // shallowRef: the zone holds thousands of buses and branches that never change,
  // so Vue only needs to notice when the whole object is replaced.
  const caseData = shallowRef<CaseData | null>(null)
  const design = shallowRef<DesignData | null>(null)
  const weights = ref<Weights>({ ...PRESETS.Balanced! })
  const point = ref(START)
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
    const { lat, lon, name } = point.value
    latestRequest += 1 // a design still on its way belongs to the previous zone
    loadingCase.value = true
    noData.value = false
    error.value = null
    try {
      const data = await (await getApi()).load_zone(lat, lon, radiusKm.value)
      if (request !== latestZone) return
      if (!data) {
        noData.value = true
        return
      }
      design.value = null
      caseData.value = data
      zoneName.value = name
      await requestDesign()
    } catch (reason) {
      if (request === latestZone) error.value = errorMessage(reason)
    } finally {
      if (request === latestZone) loadingCase.value = false
    }
  }

  async function goTo(lat: number, lon: number, name: string) {
    point.value = { lat, lon, name }
    await loadZone()
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
