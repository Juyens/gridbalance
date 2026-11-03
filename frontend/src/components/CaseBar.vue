<script setup lang="ts">
defineProps<{
  cases: string[]
  current: string | null
  loading: boolean
}>()

const emit = defineEmits<{
  load: [fileName: string]
  open: []
}>()

function onChange(event: Event) {
  emit('load', (event.target as HTMLSelectElement).value)
}
</script>

<template>
  <header class="case-bar">
    <h1>GridBalance</h1>
    <label>
      Case
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
    <button type="button" :disabled="loading" @click="emit('open')">Open .m file...</button>
    <span v-if="loading" class="status">Loading case...</span>
  </header>
</template>

<style scoped>
.case-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

h1 {
  margin: 0 auto 0 0;
  font-size: 18px;
}

label {
  display: flex;
  align-items: center;
  gap: 8px;
}

select,
button {
  padding: 5px 8px;
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
</style>
