import assert from 'node:assert/strict'
import test from 'node:test'
import { createJiti } from 'jiti'

const jiti = createJiti(import.meta.url)
const { frameAt, makeTimeline, stepTime, timeOfLine } = await jiti.import('../src/replay.ts')
const { CORNERS, pointToWeights, PRESETS, rebalance, weightsToPoint } =
  await jiti.import('../src/weights.ts')

const { EXAMPLES, SCALE_PLACES, toPlace } = await jiti.import('../src/places.ts')
const { formatCost } = await jiti.import('../src/format.ts')
const { locale } = await jiti.import('../src/i18n.ts')

const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-4, `${a} is not ${b}`)

test('the video goes through the tree, the bridges and the reinforcement in order', () => {
  const timeline = makeTimeline(114, 34)
  const chapters = []
  for (let time = 0; time <= timeline.end; time += 0.1) {
    const { chapter } = frameAt(timeline, time)
    if (chapters.at(-1) !== chapter) chapters.push(chapter)
  }
  assert.deepEqual(chapters.slice(0, 3), ['tree', 'bridges', 'reinforce'])
  assert.deepEqual(frameAt(timeline, timeline.end), { chapter: 'end', lines: 114, steps: 34 })
  assert.equal(Math.floor(frameAt(timeline, 0).lines), 0)
})

test('the time of a line shows exactly that many lines', () => {
  const timeline = makeTimeline(114, 34)
  for (let count = 0; count <= 148; count++) {
    const frame = frameAt(timeline, timeOfLine(timeline, count))
    assert.equal(Math.floor(frame.lines) + Math.floor(frame.steps), count)
  }
})

test('stepping moves one line at a time and stops at both ends', () => {
  const timeline = makeTimeline(5, 3)
  let time = 0
  for (let count = 1; count <= 8; count++) {
    time = stepTime(timeline, time, 1)
    const frame = frameAt(timeline, time)
    assert.equal(Math.floor(frame.lines) + Math.floor(frame.steps), count)
  }
  assert.equal(stepTime(timeline, time, 1), timeline.end)
  for (let i = 0; i < 20; i++) time = stepTime(timeline, time, -1)
  assert.equal(time, 0)
})

test('networks without lines or without reinforcement still have a video', () => {
  const single = makeTimeline(0, 0)
  assert.equal(frameAt(single, 0).chapter, 'bridges')
  assert.equal(frameAt(single, single.end).chapter, 'end')
  const tree = makeTimeline(4, 0)
  assert.equal(frameAt(tree, tree.end).chapter, 'end')
  assert.equal(stepTime(tree, tree.treeEnd, 1), tree.treeEnd)
})

test('large networks do not make the video longer than a minute', () => {
  assert.ok(makeTimeline(2499, 540).end < 60)
})

test('weights always add up to 1', () => {
  const total = (weights) => weights.cost + weights.robustness + weights.supply
  for (const preset of Object.values(PRESETS)) close(total(preset), 1)
  const moved = rebalance(PRESETS.Economic, 'robustness', 0.5)
  close(total(moved), 1)
  close(moved.cost / moved.supply, 3)
  close(rebalance(PRESETS.Cheapest, 'cost', 0.4).supply, 0.3)
})

test('the triangle converts weights to a point and back', () => {
  for (const preset of Object.values(PRESETS)) {
    const back = pointToWeights(weightsToPoint(preset))
    for (const key of Object.keys(preset)) close(back[key], preset[key])
  }
  assert.deepEqual(weightsToPoint(PRESETS.Cheapest), CORNERS.cost)
})

test('a point outside the triangle gives valid weights', () => {
  for (const point of [
    [-50, 300],
    [110, -80],
    [400, 170],
    [110, 400],
  ]) {
    const { cost, robustness, supply } = pointToWeights(point)
    assert.ok(Math.min(cost, robustness, supply) >= 0)
    close(cost + robustness + supply, 1)
  }
})

test('any place in Poland opens the Polish grid and the rest open a zone', () => {
  const place = (name, countrycode) =>
    toPlace({ geometry: { coordinates: [21, 52.2] }, properties: { name, countrycode } })
  assert.equal(place('Warszawa', 'PL').isCase, true)
  assert.equal(place('Cusco', 'PE').isCase, false)
  assert.equal(EXAMPLES.filter((example) => example.isCase).length, 1)
  assert.equal(SCALE_PLACES.filter((entry) => entry.place.isCase).length, 1)
})

test('costs are dollars in Peru and ohms in Poland', () => {
  locale.value = 'en'
  assert.equal(formatCost(1036, 'kUSD'), '$1.04M')
  assert.equal(formatCost(13550, 'ohm'), '13,550 Ω')
})
