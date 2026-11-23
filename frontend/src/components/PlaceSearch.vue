<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { t } from '../i18n'
import { EXAMPLES, searchPlaces, type LngLat, type Place } from '../places'

const props = defineProps<{ near: LngLat }>()
const emit = defineEmits<{ select: [place: Place] }>()

const DEBOUNCE_MS = 300
const MIN_LENGTH = 3

const query = ref('')
const results = ref<Place[]>([])
const status = ref<'idle' | 'searching' | 'empty' | 'failed'>('idle')

const focused = ref(false)
// Before typing, the list offers the examples.
const options = computed(() =>
  results.value.length > 0 ? results.value : focused.value && !query.value ? EXAMPLES : [],
)

let timer: ReturnType<typeof setTimeout> | undefined
let request: AbortController | undefined
let chosenText = ''

watch(query, (text) => {
  if (text === chosenText) return // the text was filled in by choose()
  chosenText = ''
  clearTimeout(timer)
  request?.abort()
  results.value = []
  status.value = 'idle'
  if (text.trim().length >= MIN_LENGTH) timer = setTimeout(search, DEBOUNCE_MS)
})

onUnmounted(() => {
  clearTimeout(timer)
  request?.abort()
})

async function search() {
  clearTimeout(timer)
  request?.abort()
  const current = (request = new AbortController())
  status.value = 'searching'
  try {
    const places = await searchPlaces(query.value.trim(), props.near, current.signal)
    if (current.signal.aborted) return
    results.value = places
    status.value = places.length > 0 ? 'idle' : 'empty'
  } catch {
    if (!current.signal.aborted) status.value = 'failed'
  }
}

async function submit() {
  if (query.value.trim().length < MIN_LENGTH) return
  if (results.value.length === 0) await search()
  const first = results.value[0]
  if (first) choose(first)
}

function onFocusOut(event: FocusEvent) {
  const form = event.currentTarget as HTMLElement
  if (!form.contains(event.relatedTarget as Node | null)) focused.value = false
}

function choose(place: Place) {
  focused.value = false
  chosenText = query.value = place.name
  results.value = []
  status.value = 'idle'
  emit('select', place)
}
</script>

<template>
  <form
    class="place-search"
    role="search"
    @submit.prevent="submit"
    @focusin="focused = true"
    @focusout="onFocusOut"
  >
    <svg class="icon" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="8.5" cy="8.5" r="5.5" />
      <path d="m13 13 4.5 4.5" />
    </svg>
    <label for="place-search" class="sr-only">{{ t('searchPlace') }}</label>
    <input
      id="place-search"
      v-model="query"
      type="search"
      autocomplete="off"
      :placeholder="t('searchPlace')"
      @keydown.esc="((results = []), (focused = false))"
      @focus="($event.target as HTMLInputElement).select()"
    />
    <button type="submit" class="submit">{{ t('search') }}</button>
    <p v-if="status === 'searching'" class="status" role="status">{{ t('searchingPlaces') }}</p>
    <p v-else-if="status === 'empty'" class="status" role="status">{{ t('noPlaces') }}</p>
    <p v-else-if="status === 'failed'" class="status" role="alert">{{ t('placesFailed') }}</p>
    <div v-else-if="options.length > 0" class="results">
      <p v-if="options === EXAMPLES" class="hint">{{ t('tryPlace') }}</p>
      <ul>
        <li v-for="(place, index) in options" :key="index">
          <button type="button" @click="choose(place)">
            <strong>{{ place.name }}</strong>
            <span>{{ place.address }}</span>
          </button>
        </li>
      </ul>
    </div>
  </form>
</template>

<style scoped>
.place-search {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 6px 0 12px;
}

.icon {
  flex: none;
  width: 18px;
  height: 18px;
  fill: none;
  stroke: var(--muted);
  stroke-width: 1.8;
  stroke-linecap: round;
}

input {
  flex: 1;
  min-width: 0;
  min-height: 44px;
  padding: 0;
  border: 0;
  outline: 0;
  background: none;
  color: var(--text);
  font-size: 15px;
}

input::placeholder {
  color: var(--muted);
  opacity: 1;
}

.submit {
  min-height: 32px;
  padding: 4px 14px;
  border: 0;
  border-radius: 6px;
  background: var(--accent);
  color: var(--surface);
  font-weight: 600;
}

.submit:hover:not(:disabled) {
  background: color-mix(in oklch, var(--accent) 85%, var(--text));
}

.status,
.results {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  left: 0;
  z-index: 10;
  margin: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.status {
  padding: 12px;
  color: var(--muted);
}

.hint {
  margin: 0;
  padding: 10px 12px 4px;
  color: var(--muted);
  font-size: 12px;
}

ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.results button {
  display: grid;
  gap: 2px;
  width: 100%;
  padding: 8px 12px;
  border: 0;
  background: none;
  color: var(--text);
  text-align: left;
  white-space: normal;
}

.results button:focus-visible {
  outline-offset: -2px;
}

.results span {
  color: var(--muted);
  font-size: 12px;
}
</style>
