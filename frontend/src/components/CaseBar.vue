<script setup lang="ts">
import { locale, t, type Locale } from '../i18n'

defineProps<{
  cases: string[]
  current: string | null
  loading: boolean
  darkMode: boolean
  themeBusy: boolean
  languageBusy: boolean
}>()

const emit = defineEmits<{
  load: [fileName: string]
  open: []
  toggleTheme: []
  language: [language: Locale]
}>()

function onChange(event: Event) {
  emit('load', (event.target as HTMLSelectElement).value)
}

function onLanguageChange(event: Event) {
  emit('language', (event.target as HTMLSelectElement).value as Locale)
}
</script>

<template>
  <header class="case-bar">
    <h1><img src="/favicon.svg" width="28" height="28" alt="" />GridBalance</h1>
    <label>
      <span class="sr-only">{{ t('networkCase') }}</span>
      <select :disabled="loading" @change="onChange">
        <option
          v-for="name in cases"
          :key="name"
          :value="name"
          :selected="current !== null && name === `${current}.m`"
        >
          {{ name }}
        </option>
      </select>
    </label>
    <button type="button" :disabled="loading" @click="emit('open')">{{ t('openFile') }}</button>
    <button
      class="theme-toggle"
      type="button"
      :aria-pressed="darkMode"
      :disabled="themeBusy"
      @click="emit('toggleTheme')"
    >
      {{ t('darkMode') }}
    </button>
    <label>
      <span class="sr-only">{{ t('language') }}</span>
      <select :value="locale" :disabled="languageBusy" @change="onLanguageChange">
        <option value="en" lang="en">English</option>
        <option value="es" lang="es">Español</option>
      </select>
    </label>
    <span v-if="loading" class="status" role="status">{{ t('loading') }}</span>
  </header>
</template>

<style scoped>
.case-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 64px;
  padding: 12px 20px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

h1 {
  margin: 0 auto 0 0;
  font-size: 18px;
  font-weight: 650;
  letter-spacing: -0.5px;
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

.status {
  color: var(--muted);
}

.theme-toggle[aria-pressed='true'] {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-soft);
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
