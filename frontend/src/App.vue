<script setup lang="ts">
import { onMounted, ref } from 'vue'
import CaseBar from './components/CaseBar.vue'
import GridCanvas from './components/GridCanvas.vue'
import MetricsPanel from './components/MetricsPanel.vue'
import SelectionDetails from './components/SelectionDetails.vue'
import WeightPanel from './components/WeightPanel.vue'
import { useGridDesign } from './composables/useGridDesign'
import type { Selection } from './types'

const {
  caseData,
  design,
  weights,
  cases,
  loadingCase,
  designing,
  error,
  loadCase,
  openCase,
  saveLayout,
  start,
} = useGridDesign()

const showUnused = ref(true)
const showBridges = ref(true)
const selection = ref<Selection>(null)

onMounted(start)
</script>

<template>
  <div class="app">
    <CaseBar
      :cases="cases"
      :current="caseData?.name ?? null"
      :loading="loadingCase"
      @load="loadCase"
      @open="openCase"
    />

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <main class="layout">
      <aside class="sidebar">
        <WeightPanel v-model="weights" />
        <section class="layers">
          <h2>Layers</h2>
          <label><input v-model="showBridges" type="checkbox" /> Highlight bridges</label>
          <label><input v-model="showUnused" type="checkbox" /> Show unused lines</label>
        </section>
      </aside>

      <GridCanvas
        :case-data="caseData"
        :design="design"
        :show-unused="showUnused"
        :show-bridges="showBridges"
        @layout-computed="saveLayout"
        @select="selection = $event"
      />

      <aside v-if="caseData" class="sidebar">
        <MetricsPanel :case-data="caseData" :design="design" :designing="designing" />
        <SelectionDetails :case-data="caseData" :design="design" :selection="selection" />
      </aside>
    </main>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.error {
  margin: 0;
  padding: 8px 16px;
  background: #ffebe9;
  color: #82071e;
}

.layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 320px;
  gap: 12px;
  flex: 1;
  min-height: 0;
  padding: 12px;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
  overflow-y: auto;
}

.layers h2 {
  margin: 0 0 8px;
  font-size: 15px;
}

.layers label {
  display: block;
  margin-bottom: 6px;
}
</style>
