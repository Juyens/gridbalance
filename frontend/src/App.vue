<script setup lang="ts">
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { onMounted, ref } from 'vue'
import { getApi } from './api'

cytoscape.use(fcose)

const status = ref('Waiting for backend...')
const graphContainer = ref<HTMLDivElement>()

onMounted(async () => {
  cytoscape({
    container: graphContainer.value,
    elements: [
      { data: { id: 'a' } },
      { data: { id: 'b' } },
      { data: { id: 'c' } },
      { data: { id: 'ab', source: 'a', target: 'b' } },
      { data: { id: 'bc', source: 'b', target: 'c' } },
      { data: { id: 'ca', source: 'c', target: 'a' } },
    ],
    layout: { name: 'fcose' },
  })

  const api = await getApi()
  status.value = await api.ping()
})
</script>

<template>
  <main class="app">
    <header>
      <h1>GridBalance</h1>
      <p>{{ status }}</p>
    </header>
    <div ref="graphContainer" class="graph"></div>
  </main>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
}

.graph {
  flex: 1;
  border: 1px solid #d0d7de;
  border-radius: 8px;
}
</style>
