<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { formatNumber, unitSymbol } from '../format'
import { t } from '../i18n'
import type { CaseData, DesignData } from '../types'

const props = defineProps<{ caseData: CaseData; design: DesignData; disabled: boolean }>()
const step = defineModel<number | null>({ required: true })
const playing = ref(false)
let timer: ReturnType<typeof setInterval> | undefined
const total = computed(() => props.design.steps.length)
const position = computed(() => step.value ?? total.value)
const current = computed(() => props.design.steps[position.value - 1])
const previous = computed(() => props.design.steps[position.value - 2] ?? props.caseData.mst)
const branch = computed(() =>
  current.value ? props.caseData.branches[current.value.branch] : null,
)

function stop() {
  clearInterval(timer)
  playing.value = false
}

function seek(value: number) {
  stop()
  step.value = Math.max(0, Math.min(total.value, value))
}

function togglePlay() {
  if (playing.value) {
    stop()
    return
  }
  if (position.value === total.value) step.value = 0
  playing.value = true
  timer = setInterval(() => {
    step.value = position.value + 1
  }, 1200)
}

function togglePanel(event: Event) {
  const open = (event.target as HTMLDetailsElement).open
  if (open && step.value === null) seek(0)
  if (!open) {
    stop()
    step.value = null
  }
}

watch(step, (value) => {
  if (value === null || value >= total.value) stop()
})
watch(
  () => props.disabled,
  (busy) => {
    if (busy) stop()
  },
)
onUnmounted(stop)
</script>

<template>
  <details :open="step !== null" class="replay" @toggle="togglePanel">
    <summary>{{ t('replay') }}</summary>
    <p class="progress">
      {{ t('stepProgress', { step: formatNumber(position), total: formatNumber(total) }) }}
    </p>
    <div class="playback">
      <button
        type="button"
        :aria-label="t('previousStep')"
        :disabled="disabled || position === 0"
        @click="seek(position - 1)"
      >
        ←
      </button>
      <button type="button" :disabled="disabled || total === 0" @click="togglePlay">
        {{ t(playing ? 'pause' : 'play') }}
      </button>
      <button
        type="button"
        :aria-label="t('nextStep')"
        :disabled="disabled || position === total"
        @click="seek(position + 1)"
      >
        →
      </button>
    </div>
    <input
      type="range"
      min="0"
      :max="total"
      step="1"
      :value="position"
      :aria-label="t('replayStep')"
      :aria-valuetext="
        t('stepProgress', { step: formatNumber(position), total: formatNumber(total) })
      "
      :disabled="disabled || total === 0"
      @input="seek(Number(($event.target as HTMLInputElement).value))"
    />
    <p v-if="branch" class="branch" role="status">
      {{
        t('stepBranch', {
          from: caseData.buses[branch.from]!.id,
          to: caseData.buses[branch.to]!.id,
        })
      }}
    </p>
    <p v-else class="branch">{{ t('startingTree') }}</p>
    <dl v-if="current">
      <dt>{{ t('cost') }}</dt>
      <dd>
        +{{ formatNumber(current.cost - previous.cost, 2) }} {{ unitSymbol(caseData.costUnit) }}
      </dd>
      <dt>{{ t('bridges') }}</dt>
      <dd>{{ formatNumber(current.bridges - previous.bridges) }}</dd>
      <dt>{{ t('supply') }}</dt>
      <dd>+{{ formatNumber(current.suppliedMw - previous.suppliedMw, 2) }} MW</dd>
    </dl>
  </details>
</template>

<style scoped>
summary {
  font-size: 13px;
  font-weight: 600;
  min-height: 24px;
}
.progress,
.branch {
  font-size: 12px;
  color: var(--muted);
  margin: 12px 0;
}
.playback {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) 36px;
  gap: 4px;
}
button {
  min-height: 36px;
  padding: 4px;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
}
input {
  width: 100%;
  margin: 12px 0 0;
}
dl {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  margin: 0;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}
dt {
  color: var(--muted);
}
dd {
  margin: 0;
}
</style>
