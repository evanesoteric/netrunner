import { ref, watch, onMounted, onUnmounted } from 'vue'

// Never infer a hidden trace deadline: only use timing already visible in the HUD.
export function traceBeepInterval(remaining, budget) {
  const fraction = Math.min(1, Math.max(0, remaining / Math.max(1, budget)))
  return 450 + 2550 * fraction
}

export function useTraceAudio(props) {
  const enabled = ref(true)
  try { enabled.value = localStorage.getItem('netrunner.traceAudio') !== 'off' } catch { /* optional storage */ }
  const supported = !!(window.AudioContext || window.webkitAudioContext)
  let context, timer, lastBeep = -Infinity, voice, disposed = false
  const active = () => enabled.value && !document.hidden && props.slot?.connected && props.slot.trace_active && !props.slot.stealth_session && props.remaining != null && props.remaining > 0

  function silence() {
    if (voice) {
      try { voice.stop() } catch { /* already ended */ }
      voice = null
    }
    lastBeep = -Infinity
  }
  // Browsers require an explicit player gesture before producing audio.
  function unlock() {
    if (!supported || !enabled.value || disposed) return
    try {
      context ||= new (window.AudioContext || window.webkitAudioContext)()
      if (context.state === 'suspended') context.resume().catch(() => {})
    } catch { /* unavailable audio devices must not interrupt gameplay */ }
  }
  function tick() {
    if (!active()) { silence(); return }
    if (context?.state !== 'running') return
    const instant = performance.now()
    if (instant - lastBeep < traceBeepInterval(props.remaining, props.slot.trace_budget)) return
    lastBeep = instant
    try {
      const oscillator = context.createOscillator(), gain = context.createGain(), start = context.currentTime
      oscillator.type = 'sine'
      oscillator.frequency.setValueAtTime(620, start)
      gain.gain.setValueAtTime(0, start)
      gain.gain.linearRampToValueAtTime(0.035, start + 0.012)
      gain.gain.linearRampToValueAtTime(0, start + 0.085)
      oscillator.connect(gain); gain.connect(context.destination)
      voice = oscillator
      oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); if (voice === oscillator) voice = null }
      oscillator.start(start); oscillator.stop(start + 0.09)
    } catch { /* audio failures leave the visual tracker intact */ }
  }
  function toggle() {
    enabled.value = !enabled.value
    try { localStorage.setItem('netrunner.traceAudio', enabled.value ? 'on' : 'off') } catch { /* optional storage */ }
    if (enabled.value) unlock()
    else silence()
  }
  function visibilityChanged() { if (document.hidden) silence() }
  watch(() => [props.slot?.id, props.slot?.created_at, props.slot?.connected, props.slot?.trace_active, props.slot?.stealth_session, props.remaining == null], silence)
  onMounted(() => {
    window.addEventListener('pointerdown', unlock, true)
    window.addEventListener('keydown', unlock, true)
    document.addEventListener('visibilitychange', visibilityChanged)
    timer = setInterval(tick, 100)
  })
  onUnmounted(() => {
    disposed = true; clearInterval(timer); silence()
    window.removeEventListener('pointerdown', unlock, true)
    window.removeEventListener('keydown', unlock, true)
    document.removeEventListener('visibilitychange', visibilityChanged)
    context?.close().catch(() => {})
  })
  return { enabled, supported, toggle }
}
