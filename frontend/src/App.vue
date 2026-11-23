<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
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

const panelsHidden = ref(false)
const selection = ref<Selection>(null)
const replay = useReplay(caseData, design)
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
      :panels-hidden="panelsHidden"
      :dark-mode="darkMode"
      :theme-busy="themeBusy"
      :language-busy="languageBusy"
      @toggle-theme="toggleTheme"
      @toggle-panels="panelsHidden = !panelsHidden"
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

    <main class="layout" :class="{ wide: panelsHidden }">
      <aside v-show="!panelsHidden" class="sidebar controls" :aria-label="t('controls')">
        <WeightPanel v-model="weights" />
      </aside>

      <GridMap
        v-model:radius="radiusKm"
        :case-data="caseData"
        :design="design"
        :frame="replayFrame"
        :weights="weights"
        :busy="loadingCase || designing"
        :selection="selection"
        :dark-mode="darkMode"
        @place="goTo($event.center[1], $event.center[0], $event.name)"
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
        v-if="caseData"
        v-show="!panelsHidden"
        class="sidebar results"
        :aria-label="t('results')"
      >
        <MetricsPanel
          :case-data="caseData"
          :design="displayedDesign"
          :designing="designing"
          :step="replayStep"
          :building="building"
          :zone-name="zoneName"
        />
        <SelectionDetails :case-data="caseData" :design="displayedDesign" :selection="selection" />
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
  grid-template-columns: 280px minmax(0, 1fr) 324px;
  flex: 1;
  min-height: 0;
}

.layout.wide {
  grid-template-columns: minmax(0, 1fr);
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 28px;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: 18px 20px;
  background: var(--surface);
}

.controls {
  border-right: 1px solid var(--border);
}

.results {
  border-left: 1px solid var(--border);
}

@media (max-width: 1100px) {
  .layout:not(.wide) {
    grid-template-columns: 240px minmax(0, 1fr) 288px;
  }
  .sidebar {
    padding: 20px 16px;
  }
}

@media (max-width: 900px) {
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
