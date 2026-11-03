<script setup lang="ts">
import { computed } from 'vue'
import { formatNumber, unitSymbol } from '../format'
import type { CaseData, DesignData, Selection } from '../types'
import { t } from '../i18n'

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

function busId(index: number): number {
  return props.caseData.buses[index]!.id
}
</script>

<template>
  <section class="selection-details">
    <h2>{{ t('elementDetails') }}</h2>
    <dl v-if="bus">
      <dt>{{ t('bus') }}</dt>
      <dd>{{ bus.id }}</dd>
      <dt>{{ t('voltage') }}</dt>
      <dd>{{ formatNumber(bus.baseKv) }} kV</dd>
      <dt>{{ t('zone') }}</dt>
      <dd>{{ bus.zone }}</dd>
      <dt>{{ t('load') }}</dt>
      <dd>{{ formatNumber(bus.loadMw) }} MW</dd>
      <dt>{{ t('supply') }}</dt>
      <dd>{{ formatNumber(bus.supplyMw) }} MW</dd>
    </dl>
    <dl v-else-if="branch">
      <dt>{{ t('branch') }}</dt>
      <dd>{{ busId(branch.from) }} → {{ busId(branch.to) }}</dd>
      <dt>{{ t('type') }}</dt>
      <dd>{{ branch.isTransformer ? t('transformer') : t('line') }}</dd>
      <dt>{{ t('cost') }}</dt>
      <dd>{{ formatNumber(branch.cost, 2) }} {{ unitSymbol(caseData.costUnit) }}</dd>
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
