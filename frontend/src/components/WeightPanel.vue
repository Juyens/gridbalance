<script setup lang="ts">
import { formatNumber } from '../format'
import { t, type MessageKey } from '../i18n'
import type { Weights } from '../types'
import { PRESETS, rebalance, sameWeights } from '../weights'
import WeightTriangle from './WeightTriangle.vue'

const weights = defineModel<Weights>({ required: true })

const OBJECTIVES: { key: keyof Weights; hint: MessageKey; sign: string; term: MessageKey }[] = [
  { key: 'robustness', hint: 'robustnessHint', sign: '+', term: 'robustnessTerm' },
  { key: 'supply', hint: 'supplyHint', sign: '+', term: 'supplyTerm' },
  { key: 'cost', hint: 'costHint', sign: '−', term: 'costTerm' },
]

function update(key: keyof Weights, event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  // A new object, not a mutation, so the parent's watcher sees the change.
  weights.value = rebalance(weights.value, key, value)
}
</script>

<template>
  <section class="weight-panel">
    <h2>{{ t('priorities') }}</h2>
    <p class="intro">{{ t('prioritiesIntro') }}</p>

    <WeightTriangle v-model="weights" />

    <div class="presets">
      <button
        v-for="(preset, name) in PRESETS"
        :key="name"
        type="button"
        :class="{ active: sameWeights(preset, weights) }"
        :aria-pressed="sameWeights(preset, weights)"
        @click="weights = { ...preset }"
      >
        {{ t(name as MessageKey) }}
      </button>
    </div>

    <label v-for="{ key, hint } in OBJECTIVES" :key="key" class="slider" :class="key">
      <span class="head">
        <span class="name">{{ t(key) }}</span>
        <strong>{{ formatNumber(weights[key], 2) }}</strong>
      </span>
      <small>{{ t(hint) }}</small>
      <input
        type="range"
        min="0"
        max="1"
        step="0.01"
        :value="weights[key]"
        :aria-label="t(key)"
        :aria-valuetext="`${formatNumber(weights[key], 2)}. ${t(hint)}`"
        @input="update(key, $event)"
      />
    </label>

    <section class="formula">
      <h3>{{ t('scoreTitle') }}</h3>
      <p v-for="{ key, sign, term } in OBJECTIVES" :key="key" :class="key">
        <span class="sign">{{ sign }}</span>
        <strong>{{ formatNumber(weights[key], 2) }}</strong>
        <span>× {{ t(term) }}</span>
      </p>
      <small>{{ t('scoreNote') }}</small>
    </section>
  </section>
</template>

<style scoped>
.weight-panel {
  --objective: var(--accent);
}

h2 {
  margin: 0;
  font-size: 16px;
}

.intro {
  margin: 4px 0 8px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
}

.cost {
  --objective: var(--objective-cost);
}

.robustness {
  --objective: var(--objective-robustness);
}

.supply {
  --objective: var(--objective-supply);
}

.presets {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 4px;
  margin: 8px 0 14px;
  padding: 4px;
  border-radius: 8px;
  background: var(--background);
}

.presets button {
  min-width: 0;
  min-height: 32px;
  padding: 4px 2px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font-size: 13px;
}

.presets button.active {
  border-color: var(--border);
  background: var(--surface);
  color: var(--accent);
  font-weight: 600;
}

.slider {
  display: block;
  margin-bottom: 8px;
}

.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-size: 13px;
}

.name {
  color: var(--objective);
  font-weight: 600;
}

.head strong {
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

small {
  color: var(--muted);
  font-size: 12px;
}

.slider input {
  width: 100%;
  min-width: 0;
  height: 20px;
  margin: 2px 0 0;
  accent-color: var(--objective);
}

.formula {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--background);
}

.formula h3 {
  margin: 0 0 8px;
  font-size: 13px;
}

.formula p {
  display: grid;
  grid-template-columns: 10px 34px minmax(0, 1fr);
  gap: 6px;
  margin: 0 0 4px;
  color: var(--objective);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.formula small {
  display: block;
  margin-top: 8px;
  line-height: 1.45;
}
</style>
