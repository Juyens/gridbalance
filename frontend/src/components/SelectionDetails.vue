<script setup lang="ts">
import { computed } from 'vue'
import { formatMoney, formatNumber } from '../format'
import type { CaseData, DesignData, Selection } from '../types'
import { t } from '../i18n'
import { busCosts } from '../mapFeatures'
import { busName } from '../names'

const props = defineProps<{
  caseData: CaseData
  design: DesignData | null
  selection: Selection
}>()

const bus = computed(() =>
  props.selection?.kind === 'bus' ? props.caseData.buses[props.selection.index] : undefined,
)

const branch = computed(() =>
  props.selection?.kind === 'branch' ? props.caseData.branches[props.selection.index] : undefined,
)

const linesCost = computed(() =>
  bus.value ? busCosts(props.caseData, props.design)[bus.value.index]! : 0,
)

const branchStatus = computed(() => {
  if (!branch.value) return ''
  const index = branch.value.index
  const role = props.caseData.tree.includes(index)
    ? t('mst')
    : props.design?.added.includes(index)
      ? t('added')
      : t('notUsed')
  return props.design?.bridgeBranches.includes(index) ? `${role}, ${t('bridge')}` : role
})

function nameOf(index: number): string {
  return busName(props.caseData.buses[index]!)
}
</script>

<template>
  <section class="selection-details">
    <h2>{{ t('elementDetails') }}</h2>
    <dl v-if="bus">
      <dt>{{ t('bus') }}</dt>
      <dd>{{ busName(bus) }}</dd>
      <dt>{{ t('type') }}</dt>
      <dd>{{ t(bus.kind) }}</dd>
      <dt>{{ t('voltage') }}</dt>
      <dd>{{ formatNumber(bus.baseKv, bus.baseKv % 1 ? 1 : 0) }} kV</dd>
      <template v-if="bus.population !== null">
        <dt>{{ t('population') }}</dt>
        <dd>{{ formatNumber(bus.population) }}</dd>
      </template>
      <dt>{{ t('load') }}</dt>
      <dd>{{ formatNumber(bus.loadMw, 2) }} MW</dd>
      <dt>{{ t('supply') }}</dt>
      <dd>{{ formatNumber(bus.supplyMw, 1) }} MW</dd>
      <dt>{{ t('linesCost') }}</dt>
      <dd>{{ formatMoney(linesCost) }}</dd>
    </dl>
    <dl v-else-if="branch">
      <dt>{{ t('branch') }}</dt>
      <dd>{{ nameOf(branch.from) }} – {{ nameOf(branch.to) }}</dd>
      <dt>{{ t('voltage') }}</dt>
      <dd>{{ formatNumber(branch.kv, branch.kv % 1 ? 1 : 0) }} kV</dd>
      <dt>{{ t('length') }}</dt>
      <dd>{{ formatNumber(branch.lengthKm, 2) }} km</dd>
      <dt>{{ t('cost') }}</dt>
      <dd>{{ formatMoney(branch.cost) }}</dd>
      <dt>{{ t('capacity') }}</dt>
      <dd>
        {{
          branch.capacityMva === null ? t('unlimited') : `${formatNumber(branch.capacityMva)} MVA`
        }}
      </dd>
      <dt>{{ t('status') }}</dt>
      <dd>{{ branchStatus }}</dd>
    </dl>
    <p v-else class="muted">{{ t('selectionHint') }}</p>
  </section>
</template>

<style scoped>
h2 {
  margin: 0 0 8px;
  font-size: 13px;
}

dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px 16px;
  margin: 0;
  font-size: 13px;
}

dt {
  color: var(--muted);
}

dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.muted {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}
</style>
