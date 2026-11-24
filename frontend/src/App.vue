<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { getApi } from './api'
import AppHeader from './components/AppHeader.vue'
import GridMap from './components/GridMap.vue'
import MetricsPanel from './components/MetricsPanel.vue'
import SelectionDetails from './components/SelectionDetails.vue'
import WeightPanel from './components/WeightPanel.vue'
import ReplayPanel from './components/ReplayPanel.vue'
import { designAtStep } from './replay'
import { useGridDesign } from './composables/useGridDesign'
import { useReplay } from './composables/useReplay'
import { locale, t, type Locale, type MessageKey } from './i18n'
import type { Selection } from './types'

const {
  caseData,
  design,
  weights,
  zoneName,
  radiusKm,
  noData,
  loadingCase,
  designing,
  error,
  goTo,
  start,
} = useGridDesign()

const activePanel = ref<'controls' | 'results' | null>(null)
const worldMode = ref(false)
const panelClose = ref<HTMLButtonElement | null>(null)
let panelTrigger: HTMLButtonElement | null = null

function closePanel() {
  activePanel.value = null
  panelTrigger?.focus()
  panelTrigger = null
}

async function togglePanel(panel: 'controls' | 'results', trigger: HTMLButtonElement) {
  if (activePanel.value === panel) {
    closePanel()
    return
  }
  panelTrigger = trigger
  activePanel.value = panel
  await nextTick()
  panelClose.value?.focus()
}

const selection = ref<Selection>(null)
const replay = useReplay(caseData, design)
watch(worldMode, (enabled) => {
  if (enabled) {
    activePanel.value = null
    panelTrigger = null
    selection.value = null
    replay.close()
  }
})
const replayFrame = replay.frame
// Whole steps, so the panels only change when a line is complete.
const replayStep = computed(() => (replayFrame.value ? Math.floor(replayFrame.value.steps) : null))
const building = computed(() => replayFrame.value?.chapter === 'tree')
const displayedDesign = computed(() =>
  caseData.value && design.value
    ? designAtStep(caseData.value, design.value, replayStep.value ?? design.value.steps.length)
    : null,
)

watch(
  [caseData, design, weights, () => replayFrame.value === null],
  () => {
    selection.value = null
  },
  { flush: 'sync' },
)
watch(weights, replay.close, { flush: 'sync' })
const darkMode = ref(window.matchMedia('(prefers-color-scheme: dark)').matches)
const themeBusy = ref(true)
const themeError = ref<MessageKey | null>(null)
const languageBusy = ref(true)
const languageError = ref<MessageKey | null>(null)

watch(
  locale,
  (language) => {
    document.documentElement.lang = language
  },
  { immediate: true },
)

onMounted(async () => {
  try {
    const language = await (await getApi()).get_language()
    if (language) locale.value = language
  } catch {
    languageError.value = 'languageLoadError'
  } finally {
    languageBusy.value = false
  }
})

async function changeLanguage(language: Locale) {
  locale.value = language
  languageBusy.value = true
  languageError.value = null
  try {
    await (await getApi()).set_language(language)
  } catch {
    languageError.value = 'languageSaveError'
  } finally {
    languageBusy.value = false
  }
}

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
    themeError.value = 'themeLoadError'
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
    themeError.value = 'themeSaveError'
  } finally {
    themeBusy.value = false
  }
}

onMounted(start)
</script>

<template>
  <div class="app">
    <AppHeader
      :active-panel="activePanel"
      :has-results="Boolean(caseData) && !worldMode"
      :world-mode="worldMode"
      :dark-mode="darkMode"
      :theme-busy="themeBusy"
      :language-busy="languageBusy"
      @toggle-theme="toggleTheme"
      @toggle-panel="togglePanel"
      @language="changeLanguage"
    />

    <div v-if="error" class="error" role="alert">
      {{ t('operationFailed') }}
      <details>
        <summary>{{ t('technicalDetails') }}</summary>
        {{ error }}
      </details>
    </div>
    <p v-if="noData" class="error" role="alert">{{ t('noZoneData') }}</p>
    <p v-if="themeError" class="error" role="alert">{{ t(themeError) }}</p>
    <p v-if="languageError" class="error" role="alert">{{ t(languageError) }}</p>

    <main class="layout">
      <GridMap
        v-model:radius="radiusKm"
        v-model:world="worldMode"
        :case-data="caseData"
        :design="design"
        :frame="replayFrame"
        :weights="weights"
        :busy="loadingCase || designing"
        :loading="loadingCase"
        :selection="selection"
        :dark-mode="darkMode"
        @place="goTo"
        @select="selection = $event"
        @error="error = $event"
      >
        <template #bottom>
          <ReplayPanel
            v-if="caseData && displayedDesign"
            :replay="replay"
            :case-data="caseData"
            :shown="displayedDesign"
            :disabled="loadingCase || designing"
          />
        </template>
      </GridMap>

      <aside
        v-if="activePanel"
        id="workspace-panel"
        class="tool-panel"
        aria-labelledby="panel-title"
        @keydown.esc="closePanel"
      >
        <div class="panel-bar">
          <h2 id="panel-title">{{ t(activePanel) }}</h2>
          <button ref="panelClose" type="button" :aria-label="t('closePanel')" @click="closePanel">
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <path d="m5 5 10 10M15 5 5 15" />
            </svg>
          </button>
        </div>
        <div :key="activePanel" class="panel-content">
          <WeightPanel v-if="activePanel === 'controls'" v-model="weights" />
          <template v-else-if="caseData">
            <MetricsPanel
              :case-data="caseData"
              :design="displayedDesign"
              :designing="designing"
              :step="replayStep"
              :building="building"
              :zone-name="zoneName"
            />
            <SelectionDetails
              :case-data="caseData"
              :design="displayedDesign"
              :selection="selection"
            />
          </template>
        </div>
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
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  flex: 1;
  min-height: 0;
}

.tool-panel {
  position: absolute;
  inset-block-start: 62px;
  inset-inline-end: 12px;
  z-index: 8;
  display: flex;
  flex-direction: column;
  width: min(350px, calc(100% - 24px));
  max-height: calc(100% - 82px);
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

.panel-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px 6px 16px;
  border-bottom: 1px solid var(--border);
}

.panel-bar h2 {
  margin: 0;
  font-size: 13px;
  font-weight: 650;
}

.panel-bar button {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: inherit;
}

.panel-bar svg {
  width: 18px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 1.6;
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
  overflow: auto;
  padding: 16px;
}

@media (max-width: 900px) {
  .tool-panel {
    inset-block-start: auto;
    inset-block-end: 20px;
    max-height: 65%;
  }
}
</style>
