<script setup lang="ts">
import { computed, ref } from 'vue'
import { errorMessage, getApi } from '../api'
import { formatNumber } from '../format'
import { t } from '../i18n'
import { SCALE_PLACES, type Place } from '../places'
import type { Measure } from '../types'

const emit = defineEmits<{ open: [place: Place, radiusKm: number | null] }>()

interface Row {
  place: Place
  radiusKm: number | null
  result: Measure | null
}

const dialog = ref<HTMLDialogElement>()
const rows = ref<Row[]>([])
const measuring = ref(false)
const error = ref<string | null>(null)

const maxNodes = computed(() => Math.max(1, ...rows.value.map((row) => row.result?.nodes ?? 0)))
const maxTime = computed(() => Math.max(1, ...rows.value.map((row) => row.result?.designMs ?? 0)))

const summary = computed(() => {
  const done = rows.value.flatMap((row) => row.result ?? [])
  const first = done[0]
  const last = done.at(-1)
  if (!first || !last || done.length < SCALE_PLACES.length) return null
  return t('scaleSummary', {
    from: formatNumber(first.nodes),
    to: formatNumber(last.nodes),
    time: seconds(last.designMs),
  })
})

function seconds(ms: number): string {
  return ms < 10 ? `${formatNumber(ms, 1)} ms` : `${formatNumber(ms / 1000, 2)} s`
}

async function measure() {
  measuring.value = true
  error.value = null
  rows.value = SCALE_PLACES.map((entry) => ({ ...entry, result: null }))
  try {
    const api = await getApi()
    // One by one, so each row appears as soon as it is ready.
    for (const row of rows.value) {
      const [lon, lat] = row.place.center
      row.result = await api.measure(
        row.place.source === 'poland' ? null : { lat, lon, radiusKm: row.radiusKm },
      )
    }
  } catch (reason) {
    error.value = errorMessage(reason)
  } finally {
    measuring.value = false
  }
}

function show() {
  dialog.value?.showModal()
  if (rows.value.length === 0) measure()
}

function openPlace(row: Row) {
  dialog.value?.close()
  emit('open', row.place, row.radiusKm)
}

defineExpose({ show })
</script>

<template>
  <dialog ref="dialog" aria-labelledby="scale-title">
    <header>
      <div>
        <h2 id="scale-title">{{ t('scaleTitle') }}</h2>
        <p>{{ t('scaleIntro') }}</p>
      </div>
      <button type="button" class="close" :aria-label="t('close')" @click="dialog?.close()">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" /></svg>
      </button>
    </header>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">{{ t('network') }}</th>
            <th scope="col">{{ t('nodes') }}</th>
            <th scope="col" class="number">{{ t('possibleLines') }}</th>
            <th scope="col" class="number">{{ t('prepareTime') }}</th>
            <th scope="col">{{ t('designTime') }}</th>
            <th scope="col" class="number">{{ t('bridges') }}</th>
            <th scope="col">
              <span class="sr-only">{{ t('openPlace') }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="`${row.place.name}${row.radiusKm}`">
            <th scope="row">
              {{ row.place.name }}
              <small>
                {{ row.place.source === 'poland' ? row.place.address : `${row.radiusKm} km` }}
              </small>
            </th>
            <template v-if="row.result">
              <td>
                <span class="bar">
                  <span :style="{ width: `${(row.result.nodes / maxNodes) * 100}%` }"></span>
                </span>
                {{ formatNumber(row.result.nodes) }}
              </td>
              <td class="number">{{ formatNumber(row.result.lines) }}</td>
              <td class="number">{{ seconds(row.result.prepareMs) }}</td>
              <td>
                <span class="bar time">
                  <span :style="{ width: `${(row.result.designMs / maxTime) * 100}%` }"></span>
                </span>
                {{ seconds(row.result.designMs) }}
              </td>
              <td class="number">
                {{ formatNumber(row.result.treeBridges) }} /
                <strong>{{ formatNumber(row.result.designBridges) }}</strong>
              </td>
              <td>
                <button type="button" :disabled="measuring" @click="openPlace(row)">
                  {{ t('openPlace') }}
                </button>
              </td>
            </template>
            <td v-else colspan="6" class="waiting">{{ measuring ? t('measuring') : '' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <footer>
      <p role="status">{{ measuring ? t('measuring') : summary }}</p>
      <button type="button" :disabled="measuring" @click="measure">{{ t('measureAgain') }}</button>
    </footer>
  </dialog>
</template>

<style scoped>
dialog {
  width: min(920px, calc(100vw - 32px));
  max-height: calc(100vh - 32px);
  padding: 20px 24px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow);
}

dialog::backdrop {
  background: rgb(0 0 0 / 45%);
}

header,
footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

footer {
  align-items: center;
  margin-top: 16px;
}

h2 {
  margin: 0;
  font-size: 18px;
}

p {
  max-width: 68ch;
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
}

.error {
  color: var(--error-text);
}

button {
  min-height: 30px;
  padding: 2px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
}

.close {
  display: grid;
  flex: none;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
}

svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentcolor;
  stroke-width: 1.8;
  stroke-linecap: round;
}

.table-scroll {
  margin-top: 16px;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

th,
td {
  padding: 8px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  white-space: nowrap;
}

thead th {
  color: var(--muted);
  font-size: 12px;
  font-weight: normal;
}

tbody th small {
  display: block;
  color: var(--muted);
  font-size: 11px;
  font-weight: normal;
}

.number {
  text-align: right;
}

.waiting {
  color: var(--muted);
}

.bar {
  display: inline-block;
  width: 84px;
  height: 8px;
  margin-right: 8px;
  border-radius: 4px;
  background: var(--background);
}

.bar span {
  display: block;
  height: 100%;
  min-width: 2px;
  border-radius: 4px;
  background: var(--graph-tree);
}

.bar.time span {
  background: var(--graph-added);
}
</style>
