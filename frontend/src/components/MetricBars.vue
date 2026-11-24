<script setup lang="ts">
import { computed } from 'vue'

export interface BarRow {
  name: 'mst' | 'design' | 'original'
  label: string
  value: number
  text: string
}

const props = defineProps<{ title: string; hint: string; rows: BarRow[]; max?: number }>()

const top = computed(() => props.max ?? Math.max(...props.rows.map((row) => row.value)))
const width = (value: number) =>
  top.value > 0 ? `${Math.min(100, (value / top.value) * 100)}%` : 0
</script>

<template>
  <section class="metric">
    <h3>
      {{ title }} <small>{{ hint }}</small>
    </h3>
    <dl>
      <div v-for="row in rows" :key="row.name" :class="row.name">
        <dt>{{ row.label }}</dt>
        <dd>
          <span class="track"><span class="fill" :style="{ width: width(row.value) }"></span></span>
          <span class="value">{{ row.text }}</span>
        </dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.metric {
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
}

h3 {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 600;
}

h3 small {
  color: var(--muted);
  font-size: 11px;
  font-weight: normal;
}

dl {
  margin: 0;
}

dl > div {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-height: 24px;
  color: var(--muted);
  font-size: 12px;
}

dd {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 88px;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.track {
  height: 8px;
  border-radius: 4px;
  background: var(--background);
}

.fill {
  display: block;
  height: 100%;
  min-width: 2px;
  border-radius: 4px;
  background: var(--graph-unused);
  transition: width 250ms cubic-bezier(0.16, 1, 0.3, 1);
}

.value {
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.mst .fill {
  background: var(--graph-tree);
}

.design {
  color: var(--text);
}

.design .fill {
  background: var(--graph-added);
}

.design .value {
  font-size: 15px;
  font-weight: 650;
}

@media (prefers-reduced-motion: reduce) {
  .fill {
    transition: none;
  }
}
</style>
