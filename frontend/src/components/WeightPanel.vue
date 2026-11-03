<script setup lang="ts">
import type { Weights } from '../types'
import { PRESETS, rebalance, sameWeights } from '../weights'
import { t, type MessageKey } from '../i18n'
import { formatPercent } from '../format'

const weights = defineModel<Weights>({ required: true })

const SLIDERS: { key: keyof Weights; hint: MessageKey }[] = [
  { key: 'cost', hint: 'costHint' },
  { key: 'robustness', hint: 'robustnessHint' },
  { key: 'supply', hint: 'supplyHint' },
]

const presetLabels: Record<string, MessageKey> = {
  Cheapest: 'Cheapest',
  Economic: 'Economic',
  Balanced: 'Balanced',
  Robust: 'Robust',
}

function update(key: keyof Weights, event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  // A new object, not a mutation, so the parent's watcher sees the change.
  weights.value = rebalance(weights.value, key, value)
}
</script>

<template>
  <section class="weight-panel">
    <h2>{{ t('priorities') }}</h2>

    <div class="presets">
      <button
        v-for="(preset, name) in PRESETS"
        :key="name"
        type="button"
        :class="{ active: sameWeights(preset, weights) }"
        :aria-pressed="sameWeights(preset, weights)"
        @click="weights = { ...preset }"
      >
        {{ t(presetLabels[name]!) }}
      </button>
    </div>

    <label v-for="slider in SLIDERS" :key="slider.key" class="slider">
      <span class="slider-head" :title="t(slider.hint)">
        <span>{{ t(slider.key) }}</span>
        <strong>{{ formatPercent(weights[slider.key], 100) }}</strong>
      </span>
      <input
        type="range"
        min="0"
        max="100"
        step="0.1"
        :value="weights[slider.key]"
        :aria-label="t(slider.key)"
        :aria-valuetext="`${formatPercent(weights[slider.key], 100)} — ${t(slider.hint)}`"
        @input="update(slider.key, $event)"
      />
    </label>
  </section>
</template>

<style scoped>
h2 {
  margin: 0 0 12px;
  font-size: 13px;
}

.presets {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 4px;
  padding: 4px;
  border-radius: 6px;
  background: var(--background);
  margin-bottom: 24px;
}

.presets button {
  min-width: 0;
  min-height: 32px;
  padding: 4px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.presets button.active {
  border-color: var(--border);
  background: var(--surface);
  color: var(--accent);
  font-weight: 600;
}

.slider {
  display: block;
  margin-bottom: 20px;
}

.slider-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.slider-head strong {
  font-weight: 500;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.slider input {
  width: 100%;
  min-width: 0;
  margin: 8px 0 0;
  height: 20px;
  accent-color: var(--accent);
}
</style>
