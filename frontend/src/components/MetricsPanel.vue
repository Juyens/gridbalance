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
  <section class="metrics-panel" :class="{ stale: designing }" :aria-busy="designing">
    <h2>
      Design results
      <small v-if="designing" role="status">Updating…</small>
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
    <p v-else class="muted" role="status">Computing design…</p>

    <details class="comparison">
      <summary>Compare networks</summary>
      <div class="table-scroll">
        <table>
          <caption class="sr-only">
            Network comparison. Cost in
            {{
              unitSymbol(caseData.costUnit)
            }}; supply as percentage of demand.
          </caption>
          <thead>
            <tr>
              <th scope="col"><span class="sr-only">Network</span></th>
              <th scope="col">Cost</th>
              <th scope="col">Bridges</th>
              <th scope="col">Supply</th>
              <th scope="col">Lines</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.name" :class="{ highlight: row.name === 'Design' }">
              <th scope="row">{{ row.name }}</th>
              <td>{{ formatNumber(row.metrics.cost) }}</td>
              <td>{{ formatNumber(row.metrics.bridges) }}</td>
              <td>{{ formatPercent(row.metrics.suppliedMw, caseData.totalLoadMw) }}</td>
              <td>{{ formatNumber(row.lines) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="design" class="timing">Calculated in {{ formatNumber(design.elapsedMs) }} ms</p>
    </details>
  </section>
</template>

<style scoped>
h2 {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 0 0 12px;
  font-size: 13px;
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
  margin-bottom: 20px;
}

.card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: baseline;
  gap: 4px 8px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
}

.card span,
.card small {
  color: var(--muted);
  font-size: 12px;
}

.card strong {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.5px;
  font-variant-numeric: tabular-nums;
}

.card small {
  grid-column: 1 / -1;
}
.comparison summary {
  font-size: 12px;
  min-height: 32px;
}
.table-scroll {
  max-width: 100%;
  overflow-x: auto;
}
.timing {
  margin-bottom: 0;
  color: var(--muted);
  font-size: 12px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

th,
td {
  padding: 8px 4px;
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
