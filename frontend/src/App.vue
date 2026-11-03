<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { getApi } from './api'
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

const showUnused = ref(false)
const showBridges = ref(false)
const selection = ref<Selection>(null)
const darkMode = ref(window.matchMedia('(prefers-color-scheme: dark)').matches)
const themeBusy = ref(true)
const themeError = ref<string | null>(null)

watch(
  darkMode,
  (dark) => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
  },
  { immediate: true, flush: 'sync' },
)

onMounted(async () => {
  try {
    const theme = await (await getApi()).get_theme()
    if (theme) darkMode.value = theme === 'dark'
  } catch {
    themeError.value = 'Could not load the saved theme. Using your system preference.'
  } finally {
    themeBusy.value = false
  }
})

async function toggleTheme() {
  darkMode.value = !darkMode.value
  themeBusy.value = true
  themeError.value = null
  try {
    await (await getApi()).set_theme(darkMode.value ? 'dark' : 'light')
  } catch {
    themeError.value = 'Theme changed, but the preference could not be saved.'
  } finally {
    themeBusy.value = false
  }
}

onMounted(start)
</script>

<template>
  <div class="app">
    <CaseBar
      :cases="cases"
      :current="caseData?.name ?? null"
      :loading="loadingCase"
      :dark-mode="darkMode"
      :theme-busy="themeBusy"
      @load="loadCase"
      @open="openCase"
      @toggle-theme="toggleTheme"
    />

    <p v-if="error || themeError" class="error" role="alert">{{ error || themeError }}</p>

    <main class="layout">
      <aside class="sidebar controls" aria-label="Design controls">
        <WeightPanel v-model="weights" />
        <section class="layers">
          <h2>Layers</h2>
          <label><input v-model="showBridges" type="checkbox" /> Bridges</label>
          <label><input v-model="showUnused" type="checkbox" /> Unused lines</label>
        </section>
      </aside>

      <GridCanvas
        :case-data="caseData"
        :design="design"
        :show-unused="showUnused"
        :show-bridges="showBridges"
        :dark-mode="darkMode"
        @layout-computed="saveLayout"
        @select="selection = $event"
      />

      <aside v-if="caseData" class="sidebar results" aria-label="Design results">
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
  background: var(--error-surface);
  color: var(--error-text);
}

.layout {
  display: grid;
  grid-template-columns: 224px minmax(0, 1fr) 304px;
  flex: 1;
  min-height: 0;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 28px;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: 24px 20px;
  background: var(--surface);
}

.controls {
  border-right: 1px solid var(--border);
}

.results {
  border-left: 1px solid var(--border);
}

.layers h2 {
  margin: 0 0 12px;
  font-size: 13px;
}

.layers label {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  color: var(--muted);
}

@media (max-width: 1050px) and (min-width: 761px) {
  .layout {
    grid-template-columns: 200px minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) 260px;
  }
  .results {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
    border-left: 0;
    border-top: 1px solid var(--border);
  }
}

@media (max-width: 760px) {
  .app {
    height: auto;
    min-height: 100%;
  }
  .layout {
    display: flex;
    flex-direction: column;
  }
  .sidebar {
    overflow: visible;
    padding: 20px;
  }
  .controls {
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }
  .results {
    border-left: 0;
    border-top: 1px solid var(--border);
  }
}
</style>
