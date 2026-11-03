<script setup lang="ts">
import { computed } from 'vue'
import { formatNumber, unitSymbol } from '../format'
import type { CaseData, DesignData, Selection } from '../types'

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
    ? 'MST'
    : props.design?.added.includes(index)
      ? 'Added'
      : 'Not used'
  return props.design?.bridgeBranches.includes(index) ? `${role}, bridge` : role
})

function busId(index: number): number {
  return props.caseData.buses[index]!.id
}
</script>

<template>
  <section class="selection-details">
    <h2>Element details</h2>
    <dl v-if="bus">
      <dt>Bus</dt>
      <dd>{{ bus.id }}</dd>
      <dt>Voltage</dt>
      <dd>{{ formatNumber(bus.baseKv) }} kV</dd>
      <dt>Zone</dt>
      <dd>{{ bus.zone }}</dd>
      <dt>Load</dt>
      <dd>{{ formatNumber(bus.loadMw) }} MW</dd>
      <dt>Supply</dt>
      <dd>{{ formatNumber(bus.supplyMw) }} MW</dd>
    </dl>
    <dl v-else-if="branch">
      <dt>Branch</dt>
      <dd>{{ busId(branch.from) }} to {{ busId(branch.to) }}</dd>
      <dt>Type</dt>
      <dd>{{ branch.isTransformer ? 'Transformer' : 'Line' }}</dd>
      <dt>Cost</dt>
      <dd>{{ branch.cost.toFixed(2) }} {{ unitSymbol(caseData.costUnit) }}</dd>
      <dt>Capacity</dt>
      <dd>
        {{ branch.capacityMva === null ? 'Unlimited' : `${formatNumber(branch.capacityMva)} MVA` }}
      </dd>
      <dt>Status</dt>
      <dd>{{ branchStatus }}</dd>
    </dl>
    <p v-else class="muted">Select a bus or line on the network.</p>
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
