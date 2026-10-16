<script setup>
import { computed, ref, nextTick, onMounted, watch } from 'vue'
import { Terminal, ArrowRight } from 'lucide-vue-next'
const props = defineProps({ slot: Object, application: String, busy: Boolean, send: Function, embedded: Boolean, autofocus: { type: Boolean, default: true } })
const emit = defineEmits(['open-cracker'])
const cleaner = ref('')
const cleaners = computed(() => props.slot.catalog.filter(item => item.kind === 'cleaner' && props.slot.installed_software.includes(item.id)))
watch(cleaners, items => { if (!items.some(item => item.id === cleaner.value)) cleaner.value = items[0]?.id || '' }, { immediate: true })
const input = ref(null), output = ref(null), value = ref(''), histories = ref({}), historyIndex = ref(-1)
const entries = computed(() => props.slot.mission_log.filter(line => line.app === props.application))
const name = computed(() => props.slot.running_apps.find(app => app.id === props.application)?.name || props.application)
const inputId = computed(() => `console-command-${props.application}${props.embedded ? '-workspace' : ''}`)
const focus = () => input.value?.focus({ preventScroll: true })
async function scroll() { await nextTick(); if (output.value) output.value.scrollTop = output.value.scrollHeight }
async function submit() {
  if (props.busy || !value.value.trim()) return
  const raw = value.value
  if (props.application === 'terminal' && ['lockpick', 'login'].includes(raw.trim().toLowerCase())) { value.value = ''; emit('open-cracker'); return }
  const history = histories.value[props.application] ||= []
  history.push(raw); historyIndex.value = history.length
  try {
    if (await props.send(raw, props.application)) value.value = ''
  } finally {
    await scroll()
    const focusedPanel = document.activeElement?.closest('.workspace-window')
    if (!props.embedded || !focusedPanel || focusedPanel === input.value?.closest('.workspace-window')) focus()
  }
}
async function clean() {
  if (props.busy || !cleaner.value) return
  await props.send(`logcleaner ${cleaner.value}`, 'terminal')
  await scroll()
  const focusedPanel = document.activeElement?.closest('.workspace-window')
  if (!props.embedded || !focusedPanel || focusedPanel === input.value?.closest('.workspace-window')) focus()
}
function recall(delta) {
  const history = histories.value[props.application] || []
  historyIndex.value = Math.max(0, Math.min(history.length, historyIndex.value + delta))
  value.value = history[historyIndex.value] || ''
}
function focusOutput() {
  // Selecting/copying output and keyboard navigation remain available.
  if (window.getSelection()?.isCollapsed !== false) focus()
}
watch(() => props.application, async () => { value.value = ''; historyIndex.value = (histories.value[props.application] || []).length; await scroll(); if (props.autofocus) focus() })
watch(entries, scroll)
onMounted(async () => { await scroll(); if (props.autofocus) focus() })
</script>

<template>
  <section class="panel terminal-panel">
    <div class="panel-title"><span><Terminal :size="16" /> {{ name.toUpperCase() }}</span><span class="panel-meta">{{ application === 'bank' ? 'CIPHER PRIVATE ACCOUNT' : slot.connected ? 'REMOTE LINK ACTIVE' : 'LOCAL SESSION' }}</span></div>
    <div ref="output" class="terminal-log" role="log" :aria-label="`${application} output`" @pointerup="focusOutput">
      <div class="terminal-banner">NETRUNNER / {{ application.toUpperCase() }} [v0.10]<br>{{ application === 'terminal' ? (slot.authenticated ? `Remote shell / admin@${slot.remote_target}.` : 'Local shell ready. Launch separate tools from Applications.') : 'Application process ready.' }} Type help for its reference manual.<br>─────────────────────────────────────────────────────</div>
      <pre v-for="(entry, i) in entries" :key="i">{{ entry.text }}</pre>
      <span v-if="busy" class="terminal-muted" role="status">PROCESSING…</span>
    </div>
    <div v-if="application === 'terminal' && cleaners.length" class="terminal-extensions"><label :for="`${inputId}-cleaner`">LOGCLEANER</label><select :id="`${inputId}-cleaner`" v-model="cleaner" aria-label="Logcleaner license" :disabled="busy"><option v-for="tool in cleaners" :key="tool.id" :value="tool.id">{{ tool.name }}</option></select><button class="text-link" :disabled="busy || !slot.authenticated" @click="clean">Clean logs</button></div>
    <form class="command-line" @submit.prevent="submit">
      <label :for="inputId">{{ application === 'terminal' && slot.authenticated ? `admin@${slot.remote_target}` : `${slot.alias}@${application}` }}:~$</label>
      <input :id="inputId" ref="input" v-model="value" :aria-label="embedded ? `${name} command` : 'Terminal command'" placeholder="" autocomplete="off" spellcheck="false" maxlength="160" :readonly="busy" :aria-busy="busy" @keydown.up.prevent="recall(-1)" @keydown.down.prevent="recall(1)" />
      <button class="icon-button" :disabled="busy || !value.trim()" aria-label="Execute command"><ArrowRight :size="18" /></button>
    </form>
  </section>
</template>
