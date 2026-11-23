<script setup lang="ts">
import { computed } from 'vue'
import { formatMoney, formatNumber, formatPercent } from '../format'
import type { CaseData, DesignData, Metrics } from '../types'
import { t } from '../i18n'
import MetricBars, { type BarRow } from './MetricBars.vue'

const props = defineProps<{
  caseData: CaseData
  design: DesignData | null
  designing: boolean
  step: number | null
  building: boolean // the tree is not complete yet
  zoneName: string
}>()

function rows(value: (metrics: Metrics) => number, text: (metrics: Metrics) => string): BarRow[] {
  const { building, caseData, design, step } = props
  const networks: [BarRow['name'], string, Metrics | null][] = [
    ['mst', t('mstShort'), caseData.mst],
    ['design', step === null ? t('design') : t('stepShort', { step }), building ? null : design],
    ['original', t('original'), caseData.original],
  ]
  return networks.flatMap(([name, label, metrics]) =>
    metrics ? [{ name, label, value: value(metrics), text: text(metrics) }] : [],
  )
}

const costRows = computed(() =>
  rows(
    (m) => m.cost,
    (m) => formatMoney(m.cost),
  ),
)
const bridgeRows = computed(() =>
  rows(
    (m) => m.bridges,
    (m) => formatNumber(m.bridges),
  ),
)
const supplyRows = computed(() =>
  rows(
    (m) => m.suppliedMw,
    (m) => formatPercent(m.suppliedMw, props.caseData.totalLoadMw),
  ),
)
</script>

<template>
  <section class="metrics-panel" :class="{ stale: designing }" :aria-busy="designing">
    <h2>{{ zoneName }}</h2>
    <p class="subtitle">
      {{
        step === null
          ? t('results')
          : building
            ? t('chapterTree')
            : t('stepResults', { step: formatNumber(step) })
      }}
      <span v-if="designing" role="status">{{ t('updating') }}</span>
    </p>

    <template v-if="design">
      <MetricBars :title="t('cost')" :hint="t('lowerBetter')" :rows="costRows" />
      <MetricBars :title="t('bridges')" :hint="t('lowerBetter')" :rows="bridgeRows" />
      <MetricBars
        :title="t('supply')"
        :hint="t('higherBetter')"
        :rows="supplyRows"
        :max="caseData.totalLoadMw"
      />
      <p v-if="!building" class="summary">
        {{
          t('suppliedLoad', {
            supplied: formatNumber(design.suppliedMw, 1),
            total: formatNumber(caseData.totalLoadMw, 1),
          })
        }}
        <br />
        {{
          t('lineSummary', {
            lines: formatNumber(caseData.tree.length + design.added.length),
            added: formatNumber(design.added.length),
          })
        }}
        <br />
        {{ t('calculated', { time: formatNumber(design.elapsedMs) }) }}
      </p>
    </template>
    <p v-else class="subtitle" role="status">{{ t('computing') }}</p>
  </section>
</template>

<style scoped>
h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 650;
  line-height: 1.25;
  text-wrap: balance;
}

.subtitle {
  margin: 2px 0 4px;
  color: var(--muted);
  font-size: 12px;
}

.stale {
  opacity: 0.6;
}

.summary {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
  font-variant-numeric: tabular-nums;
}
</style>
