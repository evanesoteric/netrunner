import { test, expect } from '@playwright/test'

test('trace tones accelerate, stay gentle, mute persistently and stop when timing is hidden', async ({ page }) => {
  await page.goto('/')
  await page.clock.install()
  await page.evaluate(async () => {
    window.tones = []
    window.AudioContext = class {
      state = 'running'
      currentTime = 0
      destination = {}
      createOscillator() {
        const tone = { time: performance.now() }; window.tones.push(tone)
        return { frequency: { setValueAtTime: value => { tone.frequency = value } }, connect() {}, disconnect() {}, start() {}, stop: value => { tone.stop = value } }
      }
      createGain() { return { gain: { setValueAtTime() {}, linearRampToValueAtTime: value => { if (value) window.tones.at(-1).volume = value } }, connect() {}, disconnect() {} } }
      close() { return Promise.resolve() }
    }
    const { createApp, reactive } = await import('/node_modules/.vite/deps/vue.js')
    const { default: Tracker } = await import('/src/components/TraceTracker.vue')
    const state = reactive({ slot: { id: 999, connected: true, trace_active: true, authenticated: true, trace_budget: 100, remote_name: 'Audio fixture' }, remaining: 100, elapsed: 0 })
    window.audioState = state
    const host = document.createElement('div'); document.body.append(host)
    const { h } = await import('/node_modules/.vite/deps/vue.js')
    window.mountAudio = () => { window.audioApp = createApp({ render: () => h(Tracker, state) }); window.audioApp.mount(host) }
    window.mountAudio()
  })
  await page.getByRole('heading').first().click() // Explicit gesture unlocks browser audio.
  await page.clock.runFor(6100)
  const slow = await page.evaluate(() => window.tones.length)
  expect(slow).toBe(3)
  await page.evaluate(() => { window.audioState.remaining = 1; window.tones = [] })
  await page.clock.runFor(3100)
  expect(await page.evaluate(() => window.tones.length)).toBeGreaterThanOrEqual(6)
  expect(await page.evaluate(() => window.tones.every(t => t.frequency === 620 && t.volume === 0.035 && t.stop === 0.09))).toBeTruthy()
  await page.getByRole('button', { name: 'Mute trace audio' }).click()
  await page.evaluate(() => { window.tones = [] })
  await page.clock.runFor(4000)
  expect(await page.evaluate(() => window.tones.length)).toBe(0)
  expect(await page.evaluate(() => localStorage.getItem('netrunner.traceAudio'))).toBe('off')
  await page.evaluate(() => { window.audioApp.unmount(); window.mountAudio() })
  await expect(page.getByRole('button', { name: 'Enable trace audio' })).toBeVisible()
  await page.clock.runFor(2000)
  expect(await page.evaluate(() => window.tones.length)).toBe(0)
  await page.getByRole('button', { name: 'Enable trace audio' }).click()
  for (const mode of ['hiddenTiming', 'stealth', 'inactive', 'disconnected', 'expired', 'background']) {
    await page.evaluate(mode => {
      window.audioState.remaining = mode === 'hiddenTiming' ? null : mode === 'expired' ? 0 : 1
      window.audioState.slot.connected = mode !== 'disconnected'
      window.audioState.slot.trace_active = mode !== 'inactive'
      window.audioState.slot.stealth_session = mode === 'stealth'
      Object.defineProperty(document, 'hidden', { configurable: true, value: mode === 'background' })
      document.dispatchEvent(new Event('visibilitychange'))
      window.tones = []
    }, mode)
    await page.clock.runFor(2000)
    expect(await page.evaluate(() => window.tones.length), mode).toBe(0)
  }
  await page.evaluate(() => { window.audioApp.unmount(); window.tones = [] })
  await page.clock.runFor(3000)
  expect(await page.evaluate(() => window.tones.length)).toBe(0)
  await page.reload()
  // Preference is browser-local and survives a new component/session.
  expect(await page.evaluate(() => localStorage.getItem('netrunner.traceAudio'))).toBe('on')
})
