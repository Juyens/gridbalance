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
    <h2>Weights</h2>

    <div class="presets">
      <button
        v-for="(preset, name) in PRESETS"
        :key="name"
        type="button"
        :class="{ active: sameWeights(preset, weights) }"
        @click="weights = { ...preset }"
      >
        {{ name }}
      </button>
    </div>

    <label v-for="slider in SLIDERS" :key="slider.key" class="slider">
      <span class="slider-head">
        <span>{{ slider.label }}</span>
        <strong>{{ percent.format(weights[slider.key]) }}%</strong>
      </span>
      <input
        type="range"
        min="0"
        max="100"
        step="0.1"
        :value="weights[slider.key]"
        @input="update(slider.key, $event)"
      />
      <small>{{ slider.hint }}</small>
    </label>
  </section>
</template>

<style scoped>
h2 {
  margin: 0 0 12px;
  font-size: 15px;
}

.presets {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-bottom: 16px;
}

.presets button {
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.presets button.active {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.slider {
  display: block;
  margin-bottom: 14px;
}

.slider-head {
  display: flex;
  justify-content: space-between;
}

.slider input {
  width: 100%;
  accent-color: var(--accent);
}

.slider small {
  color: var(--muted);
}
</style>
