import assert from 'node:assert/strict'
import test from 'node:test'
import { createJiti } from 'jiti'

const jiti = createJiti(import.meta.url)
const { designAtStep, findBus } = await jiti.import('../src/replay.ts')
const { resultsCsv } = await jiti.import('../src/export.ts')
const data = {
  name: 'test',
  costUnit: 'ohm',
  totalLoadMw: 40,
  tree: [0, 1],
  buses: [10, 40, 90].map((id, index) => ({ id, index })),
  branches: [
    { index: 0, from: 0, to: 1 },
    { index: 1, from: 1, to: 2 },
    { index: 2, from: 0, to: 2 },
    { index: 3, from: 1, to: 2 },
  ],
  mst: { cost: 6, bridges: 2, suppliedMw: 20 },
  original: { cost: 11, bridges: 0, suppliedMw: 40 },
}
const design = {
  cost: 11,
  bridges: 0,
  suppliedMw: 35,
  added: [2, 3],
  bridgeBranches: [],
  elapsedMs: 5,
  steps: [
    { branch: 2, cost: 9, bridges: 0, suppliedMw: 30, removedBridges: [0, 1] },
    { branch: 3, cost: 11, bridges: 0, suppliedMw: 35, removedBridges: [] },
  ],
}

test('replay starts at MST and follows exactly the chosen additions and bridge changes', () => {
  const before = structuredClone(design)
  const start = designAtStep(data, design, 0)
  assert.deepEqual(start.added, [])
  assert.deepEqual(start.bridgeBranches, [0, 1])
  assert.equal(start.cost, 6)
  assert.equal(start.suppliedMw, 20)
  const first = designAtStep(data, design, 1)
  assert.deepEqual(first.added, [2])
  assert.deepEqual(first.bridgeBranches, [])
  assert.equal(first.cost, 9)
  assert.equal(first.suppliedMw, 30)
  assert.strictEqual(designAtStep(data, design, 2), design)
  assert.deepEqual(design, before)
})

test('replay handles zero additions and rejects invalid positions', () => {
  const empty = { ...design, ...data.mst, added: [], steps: [], bridgeBranches: [0, 1] }
  assert.strictEqual(designAtStep(data, empty, 0), empty)
  for (const step of [-1, 3, 0.5, NaN]) {
    assert.throws(() => designAtStep(data, design, step), RangeError)
  }
})

test('search uses real IDs, accepts surrounding spaces and rejects invalid/missing IDs', () => {
  assert.equal(findBus(data, ' 40 ').index, 1)
  assert.equal(findBus(data, '040').id, 40)
  for (const query of ['1', '', '40.0', '4e1', '999', '9007199254740993']) {
    assert.equal(findBus(data, query), null)
  }
})

test('CSV includes original, MST, each addition, final totals, units and weights', () => {
  const csv = resultsCsv(data, design, { cost: 60, robustness: 20, supply: 20 })
  const rows = csv
    .trimEnd()
    .split('\r\n')
    .map((line) => line.split(','))
  const header = rows.shift()
  assert.equal(rows.length, 5)
  const column = (name) => header.indexOf(name)
  assert.deepEqual(
    rows.map((row) => row[column('network')]),
    ['original', 'mst', 'step', 'step', 'design'],
  )
  assert.equal(rows[2][column('from_bus_id')], '10')
  assert.equal(rows[2][column('to_bus_id')], '90')
  assert.equal(rows[2][column('supplied_mw')], '30')
  assert.equal(rows[4][column('supply_percent')], '87.5')
  assert.equal(rows[4][column('cost_unit')], 'ohm')
  assert.equal(rows[4][column('weight_cost')], '60')
})

test('CSV escapes untrusted text, prevents spreadsheet formulas and handles zero demand', () => {
  const weights = { cost: 100, robustness: 0, supply: 0 }
  assert.ok(
    resultsCsv({ ...data, name: 'case, "quoted"' }, design, weights).includes('"case, ""quoted"""'),
  )
  assert.ok(resultsCsv({ ...data, name: ' =1+1' }, design, weights).includes("' =1+1"))
  const csv = resultsCsv({ ...data, totalLoadMw: 0 }, design, weights)
  assert.ok(!csv.includes('Infinity') && !csv.includes('NaN'))
})
