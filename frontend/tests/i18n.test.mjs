import assert from 'node:assert/strict'
import test from 'node:test'
import { createJiti } from 'jiti'

const jiti = createJiti(import.meta.url)
const { locale, messages, t } = await jiti.import('../src/i18n.ts')
const { formatNumber, formatPercent } = await jiti.import('../src/format.ts')

test('both languages cover the same messages and interpolation values', () => {
  assert.deepEqual(Object.keys(messages.en).sort(), Object.keys(messages.es).sort())
  for (const key of Object.keys(messages.en)) {
    const placeholders = (value) => (value.match(/\{\w+\}/g) ?? []).sort()
    assert.deepEqual(placeholders(messages.en[key]), placeholders(messages.es[key]), key)
    assert.ok(messages.en[key].trim() && messages.es[key].trim(), key)
  }
})

test('translations react to language changes and interpolate formatted values', () => {
  locale.value = 'es'
  assert.equal(t('cost'), 'Costo')
  assert.equal(t('networkSize', { buses: '2.383', lines: '2.896' }), '2.383 barras / 2.896 líneas')
  locale.value = 'en'
  assert.equal(t('cost'), 'Cost')
  assert.equal(t('networkSize', { buses: '2,383', lines: '2,896' }), '2,383 buses / 2,896 lines')
})

test('numbers, decimals and percentages follow the selected language', () => {
  locale.value = 'en'
  assert.equal(formatNumber(12345.67), '12,346')
  assert.equal(formatNumber(12.5, 2), '12.50')
  assert.equal(formatPercent(1, 4), '25%')
  locale.value = 'es'
  assert.equal(formatNumber(12345.67), '12.346')
  assert.equal(formatNumber(12.5, 2), '12,50')
  assert.equal(formatPercent(1, 4).replace(/\s/g, ''), '25%')
  assert.equal(formatPercent(0, 0), '—')
})
