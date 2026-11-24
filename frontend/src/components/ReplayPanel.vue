<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { SPEEDS, type useReplay } from '../composables/useReplay'
import { formatMoney, formatNumber, formatPercent } from '../format'
import { t, type MessageKey } from '../i18n'
import type { Chapter } from '../replay'
import type { CaseData, DesignData } from '../types'

const props = defineProps<{
  replay: ReturnType<typeof useReplay>
  caseData: CaseData
  shown: DesignData // the design at the current step
  disabled: boolean
}>()

const { time, playing, speed, timeline, frame, toggle, seek, step, close } = props.replay

const CAPTIONS: Record<Chapter, { title: MessageKey; text: MessageKey }> = {
  tree: { title: 'chapterTree', text: 'captionTree' },
  bridges: { title: 'chapterBridges', text: 'captionBridges' },
  reinforce: { title: 'chapterReinforce', text: 'captionReinforce' },
  end: { title: 'chapterEnd', text: 'captionEnd' },
}

const chapters = computed(() => {
  const { treeEnd, bridgesEnd, end } = timeline.value
  return (
    [
      ['tree', 0, treeEnd],
      ['bridges', treeEnd, bridgesEnd],
      ['reinforce', bridgesEnd, end],
    ] as const
  )
    .filter(([, from, to]) => to > from)
    .map(([name, from, to]) => ({
      name,
      from,
      length: to - from,
      fill: Math.min(1, Math.max(0, ((time.value ?? 0) - from) / (to - from))),
    }))
})

// Cost of the first lines of the tree, in the order Kruskal takes them.
const treeCosts = computed(() => {
  const costs = [0]
  for (const index of props.caseData.tree) {
    costs.push(costs.at(-1)! + props.caseData.branches[index]!.cost)
  }
  return costs
})

const counters = computed(() => {
  const now = frame.value
  if (!now) return []
  const lines = Math.floor(now.lines) + Math.floor(now.steps)
  const inTree = now.chapter === 'tree'
  const cost = inTree ? treeCosts.value[Math.floor(now.lines)]! : props.shown.cost
  const list: { label: MessageKey; value: string; alert?: boolean }[] = [
    { label: 'linesBuilt', value: formatNumber(lines) },
    { label: 'cost', value: formatMoney(cost) },
  ]
  if (!inTree) {
    list.push(
      { label: 'bridges', value: formatNumber(props.shown.bridges), alert: true },
      {
        label: 'supply',
        value: formatPercent(props.shown.suppliedMw, props.caseData.totalLoadMw),
      },
    )
  }
  return list
})

const clock = (seconds: number) =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`

function onKey(event: KeyboardEvent) {
  if (time.value === null) return
  const target = event.target as HTMLElement
  if (target.closest('input, select, textarea, button, summary')) return
  if (event.code === 'Space') toggle()
  else if (event.code === 'ArrowRight') step(1)
  else if (event.code === 'ArrowLeft') step(-1)
  else if (event.code === 'Escape') close()
  else return
  event.preventDefault()
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <button v-if="!frame" type="button" class="open" :disabled="disabled" @click="toggle">
    <svg viewBox="0 0 20 20" aria-hidden="true"><path class="solid" d="M7 5v10l8-5z" /></svg>
    {{ t('replay') }}
  </button>

  <section v-else class="replay" :aria-label="t('replay')">
    <div class="story">
      <p class="caption" role="status">
        <strong>{{ t(CAPTIONS[frame.chapter].title) }}</strong>
        {{ t(CAPTIONS[frame.chapter].text, { count: formatNumber(caseData.tree.length) }) }}
      </p>
      <dl>
        <div v-for="counter in counters" :key="counter.label" :class="{ alert: counter.alert }">
          <dt>{{ t(counter.label) }}</dt>
          <dd>{{ counter.value }}</dd>
        </div>
      </dl>
    </div>

    <div class="track">
      <button
        v-for="chapter in chapters"
        :key="chapter.name"
        type="button"
        class="chapter"
        :class="[chapter.name, { active: chapter.name === frame.chapter }]"
        :style="{ flexGrow: chapter.length }"
        :title="t(CAPTIONS[chapter.name].title)"
        tabindex="-1"
        @click="seek(chapter.from)"
      >
        <span class="bar"><span :style="{ width: `${chapter.fill * 100}%` }"></span></span>
      </button>
      <input
        type="range"
        min="0"
        :max="timeline.end"
        step="0.01"
        :value="time"
        :aria-label="t('replayPosition')"
        :aria-valuetext="`${clock(time ?? 0)}. ${t(CAPTIONS[frame.chapter].title)}`"
        @input="seek(Number(($event.target as HTMLInputElement).value))"
      />
    </div>

    <div class="controls">
      <button type="button" class="icon" :aria-label="t('previousStep')" @click="step(-1)">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M13.5 5 8 10l5.5 5M6 5v10" /></svg>
      </button>
      <button
        type="button"
        class="icon play"
        :aria-label="t(playing ? 'pause' : 'play')"
        @click="toggle"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <path v-if="playing" d="M7.5 5v10M12.5 5v10" />
          <path v-else class="solid" d="M7 5v10l8-5z" />
        </svg>
      </button>
      <button type="button" class="icon" :aria-label="t('nextStep')" @click="step(1)">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m6.5 5 5.5 5-5.5 5M14 5v10" /></svg>
      </button>
      <span class="clock">{{ clock(time ?? 0) }} / {{ clock(timeline.end) }}</span>
      <div class="speeds" role="group" :aria-label="t('speed')">
        <button
          v-for="option in SPEEDS"
          :key="option"
          type="button"
          :aria-pressed="speed === option"
          @click="speed = option"
        >
          {{ formatNumber(option, option % 1 ? 1 : 0) }}×
        </button>
      </div>
      <button type="button" class="icon" :aria-label="t('closeReplay')" @click="close">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m6 6 8 8M14 6l-8 8" /></svg>
      </button>
    </div>
  </section>
</template>

<style scoped>
.open,
.replay {
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow);
  color: var(--text);
}

.open {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 4px 18px 4px 12px;
  border-color: transparent;
  border-radius: 20px;
  background: var(--accent);
  color: var(--surface);
  font-weight: 600;
}

.open:hover:not(:disabled) {
  background: color-mix(in oklch, var(--accent) 85%, var(--text));
}

.replay {
  flex: 1 1 0;
  min-width: 0;
  max-width: 760px;
  padding: 12px 14px 8px;
  border-radius: 10px;
}

.story {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 20px;
}

.caption {
  flex: 1 1 260px;
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.4;
}

.caption strong {
  display: block;
  color: var(--text);
  font-size: 15px;
}

dl {
  display: flex;
  gap: 18px;
  margin: 0;
}

dt {
  color: var(--muted);
  font-size: 11px;
}

dd {
  margin: 0;
  min-width: 48px;
  font-size: 18px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.alert dd {
  color: var(--graph-bridge);
}

.track {
  position: relative;
  display: flex;
  gap: 3px;
  height: 20px;
  margin-top: 8px;
}

.chapter {
  flex: 1 1 0;
  min-width: 12px;
  padding: 0;
  border: 0;
  background: none !important;
}

.bar {
  display: block;
  height: 6px;
  border-radius: 3px;
  background: var(--border);
  overflow: hidden;
}

.bar span {
  display: block;
  height: 100%;
  background: var(--graph-tree);
}

.bridges .bar span {
  background: var(--graph-bridge);
}

.reinforce .bar span {
  background: var(--graph-added);
}

.track input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.track:hover .bar,
.track:focus-within .bar {
  height: 9px;
}

.track:focus-within {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: 4px;
}

.controls {
  display: flex;
  align-items: center;
  gap: 2px;
}

.icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: none;
  color: var(--text);
}

.play {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--accent);
  color: var(--surface);
}

.play:hover {
  background: color-mix(in oklch, var(--accent) 85%, var(--text)) !important;
}

svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentcolor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.solid {
  fill: currentcolor;
}

.clock {
  margin-left: 8px;
  color: var(--muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.speeds {
  display: flex;
  margin-left: auto;
}

.speeds button {
  min-height: 28px;
  padding: 2px 8px;
  border: 0;
  border-radius: 5px;
  background: none;
  color: var(--muted);
  font-size: 12px;
}

.speeds button[aria-pressed='true'] {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}
</style>
