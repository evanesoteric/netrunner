<script setup>
import { computed, ref, nextTick, onMounted, watch } from 'vue'
import { completion } from '../terminalCompletion.js'
import { Terminal, ArrowRight } from 'lucide-vue-next'
const props = defineProps({ slot: Object, application: String, busy: Boolean, send: Function, embedded: Boolean, autofocus: { type: Boolean, default: true } })
const emit = defineEmits(['open-cracker'])
const cleaner = ref('')
const cleaners = computed(() => props.slot.catalog.filter(item => item.kind === 'cleaner' && props.slot.installed_software.includes(item.id)))
watch(cleaners, items => { if (!items.some(item => item.id === cleaner.value)) cleaner.value = items.find(item => item.id === props.slot.applet_preferences?.cleaner)?.id || items[0]?.id || '' }, { immediate: true })
watch(() => props.slot.applet_preferences?.cleaner, selected => { if (cleaners.value.some(item => item.id === selected)) cleaner.value = selected })
const input = ref(null), output = ref(null), value = ref(''), histories = ref({}), historyIndex = ref(-1)
const entries = computed(() => props.slot.mission_log.filter(line => line.app === props.application))
const name = computed(() => props.slot.running_apps.find(app => app.id === props.application)?.name || (props.application === 'bank' ? 'Cipher bank' : props.application))
const inputId = computed(() => `console-command-${props.application}${props.embedded ? '-workspace' : ''}`)
const following = ref(true), matches = ref([]), matchRange = ref(null)
const logSignature = computed(() => JSON.stringify(entries.value))
const focus = () => input.value?.focus({ preventScroll: true })
async function scroll(force = false) {
  const follow = force || following.value
  await nextTick()
  if (output.value && follow) { output.value.scrollTop = output.value.scrollHeight; following.value = true }
}
function trackScroll() {
  if (output.value) following.value = output.value.scrollHeight - output.value.clientHeight - output.value.scrollTop <= 24
}
function resetCompletion() { matches.value = []; matchRange.value = null }
function applyCompletion(candidate) {
  const range = matchRange.value
  if (!range) return
  const suffix = value.value.slice(range.end)
  const replacement = candidate + ' '
  value.value = value.value.slice(0, range.start) + replacement + (suffix.startsWith(' ') ? suffix.slice(1) : suffix)
  const cursor = range.start + replacement.length
  resetCompletion()
  nextTick(() => { focus(); input.value?.setSelectionRange(cursor, cursor); input.value?.scrollIntoView({ block:'nearest', inline:'nearest' }) })
}
function complete(event) {
  // Shift+Tab retains normal keyboard navigation out of the terminal.
  if (event.shiftKey || event.ctrlKey || event.altKey || event.metaKey || event.isComposing) return
  event.preventDefault()
  if (props.busy) return
  const result = completion(value.value, input.value?.selectionStart ?? value.value.length, props.application, props.slot)
  matchRange.value = result
  if (result.candidates.length === 1) applyCompletion(result.candidates[0])
  else {
    matches.value = result.candidates
    if (result.common.length > value.value.slice(result.start, result.end).length) {
      value.value = value.value.slice(0, result.start) + result.common + value.value.slice(result.end)
      matchRange.value.end = result.start + result.common.length
      nextTick(() => input.value?.setSelectionRange(matchRange.value.end, matchRange.value.end))
    }
    nextTick(() => input.value?.scrollIntoView({ block:'nearest', inline:'nearest' }))
  }
}

async function submit() {
  if (props.busy || !value.value.trim()) return
  resetCompletion()
  const raw = value.value
  if (props.application === 'terminal' && ['lockpick', 'login'].includes(raw.trim().toLowerCase())) { value.value = ''; emit('open-cracker'); return }
  const history = histories.value[props.application] ||= []
  history.push(raw); historyIndex.value = history.length
  try {
    if (await props.send(raw, props.application)) value.value = ''
  } finally {
    await scroll(true)
    const focusedPanel = document.activeElement?.closest('.workspace-window')
    if (!props.embedded || !focusedPanel || focusedPanel === input.value?.closest('.workspace-window')) focus()
  }
}
async function clean() {
  if (props.busy || !cleaner.value) return
  await props.send(`logcleaner ${cleaner.value}`, 'terminal')
  await scroll(true)
  const focusedPanel = document.activeElement?.closest('.workspace-window')
  if (!props.embedded || !focusedPanel || focusedPanel === input.value?.closest('.workspace-window')) focus()
}
function recall(delta) {
  resetCompletion()
  const history = histories.value[props.application] || []
  historyIndex.value = Math.max(0, Math.min(history.length, historyIndex.value + delta))
  value.value = history[historyIndex.value] || ''
}
function focusOutput() {
  // Selecting/copying output and keyboard navigation remain available.
  if (window.getSelection()?.isCollapsed !== false) focus()
}
watch(() => props.application, async () => { value.value = ''; historyIndex.value = (histories.value[props.application] || []).length; resetCompletion(); await scroll(true); if (props.autofocus) focus() })
watch(logSignature, () => scroll())
onMounted(async () => { resetCompletion(); await scroll(true); if (props.autofocus) focus() })
</script>

<template>
  <section class="panel terminal-panel">
    <div class="panel-title"><span><Terminal :size="16" /> {{ name.toUpperCase() }}</span><span class="panel-meta">{{ application === 'bank' ? 'CIPHER PRIVATE ACCOUNT' : slot.connected ? 'REMOTE LINK ACTIVE' : application === 'terminal' ? `LOCAL DRIVE ${slot.storage_used} / ${slot.equipment.storage.capacity} MB` : 'LOCAL SESSION' }}</span></div>
    <div ref="output" class="terminal-log" role="log" :aria-label="`${application} output`" @pointerup="focusOutput" @scroll="trackScroll">
      <div class="terminal-banner">NETRUNNER / {{ application.toUpperCase() }} [v0.13]<br>{{ application === 'terminal' ? (slot.authenticated ? `Remote shell / admin@${slot.remote_target}.` : 'Local shell ready. Owned software applets run here. Type applets to list them.') : 'Application process ready.' }} Type help for its reference manual.<br>─────────────────────────────────────────────────────</div>
      <pre v-for="(entry, i) in entries" :key="i">{{ entry.text }}</pre>
      <span v-if="busy" class="terminal-muted" role="status">PROCESSING…</span>
    </div>
    <div v-if="!following" class="terminal-scroll-actions"><button class="text-link" @click="scroll(true)">Jump to latest output</button></div>
    <div v-if="matches.length" :id="`${inputId}-matches`" class="terminal-completions"><span role="status">{{ matches.length }} matches · type more to narrow</span><div role="listbox" aria-label="Terminal completions"><button v-for="candidate in matches" :key="candidate" role="option" :aria-selected="false" tabindex="-1" @pointerdown.prevent @click="applyCompletion(candidate)">{{ candidate }}</button></div></div>
    <div v-if="application === 'terminal' && cleaners.length" class="terminal-extensions"><label :for="`${inputId}-cleaner`">LOGCLEANER</label><select :id="`${inputId}-cleaner`" v-model="cleaner" aria-label="Logcleaner license" :disabled="busy"><option v-for="tool in cleaners" :key="tool.id" :value="tool.id">{{ tool.name }}</option></select><button class="text-link" :disabled="busy || !slot.authenticated" @click="clean">Clean logs</button></div>
    <form class="command-line" @submit.prevent="submit">
      <label :for="inputId">{{ application === 'terminal' && slot.authenticated ? `admin@${slot.remote_target}` : `${slot.alias}@${application}` }}:~$</label>
      <input :id="inputId" ref="input" v-model="value" :aria-label="embedded ? `${name} command` : 'Terminal command'" placeholder="" autocomplete="off" aria-autocomplete="list" :aria-describedby="`${inputId}-hint`" spellcheck="false" maxlength="160" :readonly="busy" :aria-busy="busy" @input="resetCompletion" @keydown.tab="complete" @keydown.esc="resetCompletion" @keydown.up.prevent="recall(-1)" @keydown.down.prevent="recall(1)" />
      <button class="icon-button" :disabled="busy || !value.trim()" aria-label="Execute command"><ArrowRight :size="18" /></button>
    </form>
    <span :id="`${inputId}-hint`" class="terminal-keyboard-hint">Tab completes · Shift+Tab moves focus</span>
  </section>
</template>
