<script setup lang="ts">
import { computed } from 'vue'
import { formatNumber, formatPercent, unitSymbol } from '../format'
import type { CaseData, DesignData, Metrics } from '../types'

const props = defineProps<{
  caseData: CaseData
  design: DesignData | null
  designing: boolean
}>()

const lineCount = computed(() =>
  props.design ? props.caseData.tree.length + props.design.added.length : null,
)

const rows = computed(() => {
  const result: { name: string; metrics: Metrics; lines: number }[] = [
    {
      name: 'Original',
      metrics: props.caseData.original,
      lines: props.caseData.branches.length,
    },
    { name: 'MST', metrics: props.caseData.mst, lines: props.caseData.tree.length },
  ]
  if (props.design && lineCount.value !== null) {
    result.push({ name: 'Design', metrics: props.design, lines: lineCount.value })
  }
  return result
})
</script>

<template>
  <section class="metrics-panel" :class="{ stale: designing }">
    <h2>
      Design
      <small v-if="designing">updating...</small>
      <small v-else-if="design">{{ formatNumber(design.elapsedMs) }} ms</small>
    </h2>

    <div v-if="design" class="cards">
      <div class="card">
        <span>Cost</span>
        <strong>{{ formatNumber(design.cost) }} {{ unitSymbol(caseData.costUnit) }}</strong>
        <small>{{ formatPercent(design.cost, caseData.original.cost) }} of the original</small>
      </div>
      <div class="card">
        <span>Bridges</span>
        <strong>{{ formatNumber(design.bridges) }}</strong>
        <small>original has {{ formatNumber(caseData.original.bridges) }}</small>
      </div>
      <div class="card">
        <span>Supply</span>
        <strong>{{ formatPercent(design.suppliedMw, caseData.totalLoadMw) }}</strong>
        <small>
          {{ formatNumber(design.suppliedMw) }} of {{ formatNumber(caseData.totalLoadMw) }} MW
        </small>
      </div>
      <div class="card">
        <span>Lines</span>
        <strong>{{ formatNumber(lineCount ?? 0) }}</strong>
        <small>MST + {{ formatNumber(design.added.length) }} added</small>
      </div>
    </div>
    <p v-else class="muted">Computing the first design...</p>

    <table>
      <thead>
        <tr>
          <th></th>
          <th>Cost</th>
          <th>Bridges</th>
          <th>Supply</th>
          <th>Lines</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.name" :class="{ highlight: row.name === 'Design' }">
          <th>{{ row.name }}</th>
          <td>{{ formatNumber(row.metrics.cost) }}</td>
          <td>{{ formatNumber(row.metrics.bridges) }}</td>
          <td>{{ formatPercent(row.metrics.suppliedMw, caseData.totalLoadMw) }}</td>
          <td>{{ formatNumber(row.lines) }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
h2 {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 0 0 12px;
  font-size: 15px;
}

h2 small,
.muted {
  color: var(--muted);
  font-weight: normal;
}

.stale .cards {
  opacity: 0.6;
}

.cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 16px;
}

.card {
  display: flex;
  flex-direction: column;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
}

.card span,
.card small {
  color: var(--muted);
  font-size: 12px;
}

.card strong {
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

th,
td {
  padding: 4px 6px;
  border-bottom: 1px solid var(--border);
  text-align: right;
}

tbody th,
thead th:first-child {
  text-align: left;
}

tr.highlight {
  background: var(--accent-soft);
}
</style>
