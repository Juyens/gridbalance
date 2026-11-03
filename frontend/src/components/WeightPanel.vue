<script setup lang="ts">
import type { Weights } from '../types'
import { PRESETS, rebalance, sameWeights } from '../weights'

const weights = defineModel<Weights>({ required: true })

const SLIDERS: { key: keyof Weights; label: string; hint: string }[] = [
  { key: 'cost', label: 'Cost', hint: 'Avoid adding lines' },
  { key: 'robustness', label: 'Robustness', hint: 'Remove bridges' },
  { key: 'supply', label: 'Supply', hint: 'Meet the demand' },
]

const percent = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

function update(key: keyof Weights, event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  // A new object, not a mutation, so the parent's watcher sees the change.
  weights.value = rebalance(weights.value, key, value)
}
</script>

<template>
  <section class="weight-panel">
    <h2>Design priorities</h2>

    <div class="presets">
      <button
        v-for="(preset, name) in PRESETS"
        :key="name"
        type="button"
        :class="{ active: sameWeights(preset, weights) }"
        :aria-pressed="sameWeights(preset, weights)"
        @click="weights = { ...preset }"
      >
        {{ name }}
      </button>
    </div>

    <label v-for="slider in SLIDERS" :key="slider.key" class="slider">
      <span class="slider-head" :title="slider.hint">
        <span>{{ slider.label }}</span>
        <strong>{{ percent.format(weights[slider.key]) }}%</strong>
      </span>
      <input
        type="range"
        min="0"
        max="100"
        step="0.1"
        :value="weights[slider.key]"
        :aria-label="slider.label"
        :aria-valuetext="`${percent.format(weights[slider.key])}% — ${slider.hint}`"
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
