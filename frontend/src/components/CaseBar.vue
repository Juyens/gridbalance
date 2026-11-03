<script setup lang="ts">
defineProps<{
  cases: string[]
  current: string | null
  loading: boolean
  darkMode: boolean
  themeBusy: boolean
}>()

const emit = defineEmits<{
  load: [fileName: string]
  open: []
  toggleTheme: []
}>()

function onChange(event: Event) {
  emit('load', (event.target as HTMLSelectElement).value)
}
</script>

<template>
  <header class="case-bar">
    <h1><img src="/favicon.svg" width="28" height="28" alt="" />GridBalance</h1>
    <label>
      <span class="sr-only">Network case</span>
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
    <button type="button" :disabled="loading" @click="emit('open')">Open .m file</button>
    <button
      class="theme-toggle"
      type="button"
      :aria-pressed="darkMode"
      :disabled="themeBusy"
      @click="emit('toggleTheme')"
    >
      Dark mode
    </button>
    <span v-if="loading" class="status" role="status">Loading…</span>
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
