import assert from 'node:assert/strict'
import test from 'node:test'
import { setTimeout as delay } from 'node:timers/promises'
import { createJiti } from 'jiti'

const jiti = createJiti(import.meta.url)
const { useGridDesign } = await jiti.import('../src/composables/useGridDesign.ts')
const { nextTick } = await jiti.import('vue')

test('changed weights invalidate in-flight results while the next request is debounced', async () => {
  const initial = { cost: 1 }
  const pending = []
  let requests = 0
  globalThis.window = {
    pywebview: {
      api: {
        list_cases: async () => ['case.m'],
        load_case: async () => ({ name: 'case' }),
        design: () =>
          ++requests === 1
            ? Promise.resolve(initial)
            : new Promise((resolve) => pending.push(resolve)),
      },
    },
  }
  try {
    const state = useGridDesign()
    await state.start()
    state.weights.value = { cost: 60, robustness: 20, supply: 20 }
    await nextTick()
    assert.equal(state.designing.value, true)
    await delay(300)
    assert.equal(pending.length, 1)
    state.weights.value = { cost: 0, robustness: 50, supply: 50 }
    await nextTick()
    pending[0]({ cost: 999 })
    await nextTick()
    assert.strictEqual(state.design.value, initial)
    assert.equal(state.designing.value, true)
    await delay(300)
    assert.equal(pending.length, 2)
    pending[1]({ cost: 2 })
    await delay(0)
    assert.equal(state.design.value.cost, 2)
    assert.equal(state.designing.value, false)
  } finally {
    delete globalThis.window
  }
})
