<script setup lang="ts">
import { t } from '../i18n'

const showExisting = defineModel<boolean>('existing', { required: true })
const showBridges = defineModel<boolean>('bridges', { required: true })
const showUnused = defineModel<boolean>('unused', { required: true })
</script>

<template>
  <details class="legend" open>
    <summary>{{ t('legend') }}</summary>
    <ul>
      <li><span class="line tree"></span>{{ t('mst') }}</li>
      <li><span class="line added"></span>{{ t('addedLine') }}</li>
    </ul>
    <ul>
      <li>
        <label>
          <input v-model="showExisting" type="checkbox" />
          <span class="line existing"></span>{{ t('existingNetwork') }}
        </label>
      </li>
      <li>
        <label>
          <input v-model="showBridges" type="checkbox" />
          <span class="line bridge"></span>{{ t('bridges') }}
        </label>
      </li>
      <li>
        <label>
          <input v-model="showUnused" type="checkbox" />
          <span class="line unused"></span>{{ t('unusedLines') }}
        </label>
      </li>
    </ul>
    <ul>
      <li><span class="dot source"></span>{{ t('mainSubstation') }}</li>
      <li><span class="dot plant"></span>{{ t('plant') }}</li>
      <li><span class="dot load"></span>{{ t('loadSite') }}</li>
    </ul>
  </details>
</template>

<style scoped>
.legend {
  flex: none;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
  font-size: 12px;
}

summary {
  font-weight: 600;
}

ul {
  margin: 6px 0 0;
  padding: 6px 0 0;
  border-top: 1px solid var(--border);
  list-style: none;
}

li,
label {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
}

label {
  cursor: pointer;
}

input {
  margin: 0;
}

.line {
  flex: none;
  width: 20px;
  height: 3px;
  border-radius: 2px;
}

.line.tree {
  background: var(--graph-tree);
}

.line.added {
  background: var(--graph-added);
}

.line.unused {
  background: var(--graph-unused);
}

.line.existing,
.line.bridge {
  height: 0;
  border-top: 3px dashed var(--graph-existing);
  border-radius: 0;
}

.line.bridge {
  border-top-color: var(--graph-bridge);
}

.dot {
  flex: none;
  width: 10px;
  height: 10px;
  margin: 0 5px;
  border-radius: 50%;
}

.dot.source {
  background: var(--graph-source);
}

.dot.plant {
  background: var(--graph-plant);
}

.dot.load {
  background: var(--graph-load);
}
</style>
