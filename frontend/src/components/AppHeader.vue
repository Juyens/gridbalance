<script setup lang="ts">
import { locale, t, type Locale } from '../i18n'

defineProps<{
  activePanel: 'controls' | 'results' | null
  hasResults: boolean
  worldMode: boolean
  darkMode: boolean
  themeBusy: boolean
  languageBusy: boolean
}>()

const emit = defineEmits<{
  toggleTheme: []
  togglePanel: [panel: 'controls' | 'results', trigger: HTMLButtonElement]
  language: [language: Locale]
}>()

function onLanguageChange(event: Event) {
  emit('language', (event.target as HTMLSelectElement).value as Locale)
}
</script>

<template>
  <header class="app-header">
    <h1><img src="/favicon.svg" width="28" height="28" alt="" />PwrGrid</h1>
    <button
      class="tool-button"
      type="button"
      :disabled="worldMode"
      :aria-expanded="activePanel === 'controls'"
      :aria-controls="activePanel === 'controls' ? 'workspace-panel' : undefined"
      @click="emit('togglePanel', 'controls', $event.currentTarget as HTMLButtonElement)"
    >
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path d="M3 5h5m4 0h5M3 10h9m4 0h1M3 15h2m4 0h8M8 3v4m4 1v4m-7 1v4" />
      </svg>
      {{ t('controls') }}
    </button>
    <button
      class="tool-button"
      type="button"
      :disabled="!hasResults"
      :aria-expanded="activePanel === 'results'"
      :aria-controls="activePanel === 'results' ? 'workspace-panel' : undefined"
      @click="emit('togglePanel', 'results', $event.currentTarget as HTMLButtonElement)"
    >
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path d="M3 3v14h14M7 13v-3m4 3V6m4 7V4" />
      </svg>
      {{ t('results') }}
    </button>
    <button
      class="icon-button"
      type="button"
      :aria-label="t('darkMode')"
      :title="t('darkMode')"
      :aria-pressed="darkMode"
      :disabled="themeBusy"
      @click="emit('toggleTheme')"
    >
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path v-if="darkMode" d="M16.5 12A7 7 0 0 1 8 3.5a7 7 0 1 0 8.5 8.5Z" />
        <template v-else>
          <circle cx="10" cy="10" r="3.5" />
          <path
            d="M10 2v1.6M10 16.4V18M2 10h1.6M16.4 10H18M4.3 4.3l1.2 1.2M14.5 14.5l1.2 1.2M4.3 15.7l1.2-1.2M14.5 5.5l1.2-1.2"
          />
        </template>
      </svg>
    </button>
    <label>
      <span class="sr-only">{{ t('language') }}</span>
      <select :value="locale" :disabled="languageBusy" @change="onLanguageChange">
        <option value="en" lang="en">English</option>
        <option value="es" lang="es">Español</option>
      </select>
    </label>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 52px;
  padding: 8px 12px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

h1 {
  margin: 0 auto 0 0;
  font-size: 19px;
  font-weight: 675;
  letter-spacing: -0.035em;
  display: flex;
  align-items: center;
  gap: 10px;
}

label {
  display: flex;
  align-items: center;
  gap: 8px;
}

select,
button {
  min-height: 36px;
  padding: 6px 12px;
  max-width: 100%;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: inherit;
  font: inherit;
}

button {
  cursor: pointer;
}

.icon-button {
  display: grid;
  place-items: center;
  width: 36px;
  padding: 0;
}

.tool-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

button svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentcolor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.icon-button[aria-pressed='true'],
.tool-button[aria-expanded='true'] {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
}

@media (max-width: 480px) {
  h1 {
    flex-basis: 100%;
  }
  label {
    flex: 1;
    min-width: 0;
  }
  select {
    width: 100%;
  }
}
</style>
