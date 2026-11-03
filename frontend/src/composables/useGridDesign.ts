// App state: the loaded case, the current weights and the design they produce.

import { ref, shallowRef, watch } from 'vue'
import { errorMessage, getApi } from '../api'
import type { CaseData, DesignData, Position, Weights } from '../types'
import { PRESETS } from '../weights'

// Wait until the sliders stop moving before asking Python for a new design.
const DEBOUNCE_MS = 250

export function useGridDesign() {
  // shallowRef: the case holds thousands of buses and branches that never change,
  // so Vue only needs to notice when the whole object is replaced.
  const caseData = shallowRef<CaseData | null>(null)
  const design = shallowRef<DesignData | null>(null)
  const weights = ref<Weights>({ ...PRESETS.Balanced! })
  const cases = ref<string[]>([])
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

  async function load(loader: () => Promise<CaseData | null>) {
    loadingCase.value = true
    error.value = null
    try {
      const data = await loader()
      if (!data) return // dialog cancelled
      design.value = null
      caseData.value = data
      await requestDesign()
    } catch (reason) {
      error.value = errorMessage(reason)
    } finally {
      loadingCase.value = false
    }
  }

  async function loadCase(fileName: string) {
    const api = await getApi()
    await load(() => api.load_case(fileName))
  }

  async function openCase() {
    const api = await getApi()
    await load(() => api.open_case())
  }

  async function saveLayout(positions: Position[]) {
    try {
      await (await getApi()).save_layout(positions)
    } catch (reason) {
      error.value = errorMessage(reason)
    }
  }

  async function start() {
    const api = await getApi()
    cases.value = await api.list_cases()
    if (cases.value.length > 0) await loadCase(cases.value[0]!)
  }

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
    cases,
    loadingCase,
    designing,
    error,
    loadCase,
    openCase,
    saveLayout,
    start,
  }
}
