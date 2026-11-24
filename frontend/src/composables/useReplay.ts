// Clock of the replay: plays, pauses and seeks like a video.

import { computed, onUnmounted, ref, watch, type Ref } from 'vue'
import { frameAt, makeTimeline, stepTime } from '../replay'
import type { CaseData, DesignData } from '../types'

export const SPEEDS = [0.5, 1, 2, 4]

export function useReplay(caseData: Ref<CaseData | null>, design: Ref<DesignData | null>) {
  const time = ref<number | null>(null) // seconds; null while closed
  const playing = ref(false)
  const speed = ref(1)
  const timeline = computed(() =>
    makeTimeline(caseData.value?.tree.length ?? 0, design.value?.steps.length ?? 0),
  )
  const frame = computed(() => (time.value === null ? null : frameAt(timeline.value, time.value)))

  let request = 0
  let last = 0

  function tick(now: number) {
    if (time.value === null || !playing.value) return
    // After a hidden window the gap is long: do not jump ahead.
    const seconds = Math.min(0.1, (now - last) / 1000) * speed.value
    last = now
    time.value = Math.min(timeline.value.end, time.value + seconds)
    if (time.value >= timeline.value.end) playing.value = false
    else request = requestAnimationFrame(tick)
  }

  function play() {
    if (time.value === null || time.value >= timeline.value.end) time.value = 0
    playing.value = true
    last = performance.now()
    cancelAnimationFrame(request)
    request = requestAnimationFrame(tick)
  }

  function pause() {
    playing.value = false
    cancelAnimationFrame(request)
  }

  function toggle() {
    if (playing.value) pause()
    else play()
  }

  // Seeking keeps playing, like a video.
  function seek(value: number) {
    time.value = Math.min(timeline.value.end, Math.max(0, value))
  }

  function step(direction: -1 | 1) {
    pause()
    seek(stepTime(timeline.value, time.value ?? 0, direction))
  }

  function close() {
    pause()
    time.value = null
  }

  watch([caseData, design], close, { flush: 'sync' })
  onUnmounted(pause)

  return { time, playing, speed, timeline, frame, toggle, seek, step, close }
}
