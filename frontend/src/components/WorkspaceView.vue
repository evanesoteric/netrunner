<script setup>
import { computed, ref, nextTick, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
import { GripVertical, Maximize2, X, Square, Play } from 'lucide-vue-next'
import TerminalConsole from './TerminalConsole.vue'
import PasswordBreaker from './PasswordBreaker.vue'
import ServerLogin from './ServerLogin.vue'
import NetworkMap from './NetworkMap.vue'
import BrokerView from './BrokerView.vue'
import ExchangeView from './ExchangeView.vue'
import FieldNotes from './FieldNotes.vue'
import ServerHistory from './ServerHistory.vue'
import BlackMarket from './BlackMarket.vue'
import BackdoorsView from './BackdoorsView.vue'
const props = defineProps({ slot: Object, username: String, busy: Boolean, api: Function, send: Function, launch: Function, close: Function, now: Number, offset: Number, ranks: Array, breakerAction: Function })
const emit = defineEmits(['route', 'directory', 'trade', 'contract', 'jump', 'open-cracker'])
const canvas = ref(null), panels = ref([]), starter = ref([]), revision = ref(0), identity = ref(''), saved = ref('[]')
const ready = ref(false), loading = ref(true), saving = ref(false), error = ref(''), conflict = ref(null), narrow = ref(false), drag = ref(null)
const selected = ref('cleaner-1-standard'), tileErrors = ref({}), launching = ref(false), recovery = ref(true)
const signature = layout => JSON.stringify(layout.map(({ id, product_id, x, y, w, h }) => ({ id, product_id, x, y, w, h })))
const dirty = computed(() => signature(panels.value) !== saved.value)
const saveStatus = computed(() => loading.value ? 'Loading arrangement…' : conflict.value ? 'Layout conflict — arrangement retained' : saving.value ? 'Saving arrangement…' : error.value ? 'Layout save failed' : dirty.value ? 'Unsaved arrangement' : 'Layout saved')
const extras = computed(() => [
  { id: 'notes', name: 'Field Notes' }, { id: 'history', name: 'Server Histories' },
  ...(props.slot.market_unlocked ? [{ id: 'blackmarket', name: 'Null Exchange' }] : []),
  ...(props.slot.installed_software.includes('rootkit-epic') ? [{ id: 'backdoors', name: 'Backdoored Servers' }] : []),
])
const choices = computed(() => [...props.slot.builtins.map(app => ({ ...app, product_id: app.id })),
  ...props.slot.catalog.filter(item => props.slot.installed_software.includes(item.id)).map(item => ({ ...item, product_id: item.id, id: item.kind })),
  ...extras.value.map(item => ({ ...item, product_id: item.id }))])
const rows = computed(() => Math.max(6, ...panels.value.map(panel => panel.y + panel.h)))
let timer, disposed = false, active = true, queued = null
const copy = value => JSON.parse(JSON.stringify(value))
const path = () => `slots/${props.slot.id}/workspace/`
const cacheKey = () => `netrunner.workspace:${props.username}:${props.slot.id}:${identity.value}`
const process = panel => props.slot.running_apps.find(app => app.id === panel.id)
const choice = panel => choices.value.find(item => item.product_id === panel.product_id)
const title = panel => process(panel)?.name || choice(panel)?.name || 'Unavailable tool'
const service = panel => ['notes', 'history', 'blackmarket', 'backdoors'].includes(panel.id)
const available = panel => !!choice(panel)
const overlap = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h
const clamp = (value, min, max) => Math.max(min, Math.min(max, value))
function pack(items, id, next) {
  const moved = { ...items.find(item => item.id === id), ...next }
  const placed = [moved]
  for (const original of items.filter(item => item.id !== id).sort((a, b) => a.y - b.y || a.x - b.x)) {
    const panel = { ...original }
    while (placed.some(item => overlap(panel, item))) {
      panel.y++
      if (panel.y + panel.h > 512) panel.y = 0
    }
    placed.push(panel)
  }
  return items.map(item => placed.find(panel => panel.id === item.id))
}
function cache() {
  if (!ready.value) return
  try {
    if (dirty.value) sessionStorage.setItem(cacheKey(), JSON.stringify({ layout: panels.value, revision: revision.value }))
    else sessionStorage.removeItem(cacheKey())
    recovery.value = true
  } catch { recovery.value = false }
}
function changed() {
  cache(); clearTimeout(timer)
  if (dirty.value && !conflict.value && !error.value && !disposed) timer = setTimeout(save, 500)
}
async function load() {
  if (saving.value || dirty.value || drag.value) return
  loading.value = true; error.value = ''
  try {
    const data = await props.api(path())
    if (disposed) return
    starter.value = data.starter_layout; identity.value = data.identity; revision.value = data.revision
    panels.value = copy(data.layout); saved.value = signature(data.layout); conflict.value = null
    try {
      const cached = JSON.parse(sessionStorage.getItem(cacheKey()) || 'null')
      if (cached && Array.isArray(cached.layout) && signature(cached.layout) !== saved.value) {
        panels.value = cached.layout
        if (cached.revision !== data.revision) { conflict.value = data; revision.value = cached.revision }
      }
    } catch { recovery.value = false }
    if (!choices.value.some(item => item.product_id === selected.value)) selected.value = choices.value[0]?.product_id || 'terminal'
    ready.value = true; changed()
  } catch (e) { error.value = e.message } finally {
    loading.value = false
    if (queued && ready.value) { const product = queued; queued = null; showApp(product) }
  }
}
async function save() {
  clearTimeout(timer)
  if (!ready.value || loading.value || saving.value || !dirty.value || conflict.value || drag.value) return
  const layout = copy(panels.value)
  saving.value = true; error.value = ''; cache()
  try {
    const data = await props.api(path(), { layout, revision: revision.value, identity: identity.value })
    saved.value = signature(data.layout); revision.value = data.revision; cache()
  } catch (e) {
    error.value = e.message
    if (e.status === 409 && e.data?.workspace) conflict.value = e.data.workspace
  } finally { saving.value = false; changed() }
}
function useSaved() {
  const data = conflict.value
  panels.value = copy(data.layout); saved.value = signature(data.layout); revision.value = data.revision
  identity.value = data.identity; conflict.value = null; error.value = ''; cache()
}
function keepLayout() {
  if (conflict.value.identity !== identity.value) return
  revision.value = conflict.value.revision; saved.value = signature(conflict.value.layout)
  conflict.value = null; error.value = ''; save()
}
function spot(id, product) {
  const panel = { id, product_id: product, x: 0, y: 0, w: 6, h: 5 }
  for (let y = 0; y < 508; y++) for (const x of [0, 6]) {
    panel.x = x; panel.y = y
    if (!panels.value.some(item => overlap(panel, item))) return panel
  }
}
async function focusPanel(id, reveal = false) {
  await nextTick()
  if (!active) return
  const window = canvas.value?.querySelector(`[data-workspace-window="${id}"]`)
  if (reveal) window?.scrollIntoView({ block: 'nearest' })
  window?.querySelector('input[aria-label$=" command"]')?.focus({ preventScroll: true })
}
function showApp(product, reveal = false) {
  if (!ready.value || loading.value) { queued = product; return }
  const item = choices.value.find(item => item.product_id === product)
  if (!item) return
  const existing = panels.value.find(panel => panel.id === item.id)
  if (existing) {
    if (existing.product_id !== product) { existing.product_id = product; changed() }
  } else if (panels.value.length < 16) {
    panels.value.push(spot(item.id, product)); changed()
  }
  focusPanel(item.id, reveal)
}
async function run(panel) {
  if (!available(panel) || service(panel) || !active) return
  const success = await props.launch(panel.product_id, props.slot.id)
  if (success) { delete tileErrors.value[panel.id]; focusPanel(panel.id) }
  else tileErrors.value[panel.id] = 'Unable to start this tool. Check free RAM and the message above.'
  return success
}
async function addPanel() {
  showApp(selected.value, true)
  const item = choices.value.find(item => item.product_id === selected.value)
  const panel = item && panels.value.find(panel => panel.id === item.id)
  if (panel && !service(panel) && process(panel)?.product_id !== panel.product_id) await run(panel)
}
async function launchVisible() {
  launching.value = true
  try {
    for (const panel of [...panels.value]) {
      if (!active) break
      if (!service(panel) && available(panel) && process(panel)?.product_id !== panel.product_id && !await run(panel)) break
    }
  } finally { launching.value = false }
}
function removePanel(id) { panels.value = panels.value.filter(panel => panel.id !== id); changed() }
function restore() { panels.value = copy(starter.value); error.value = ''; changed() }
function begin(event, panel, mode) {
  if (narrow.value || event.button !== 0 || loading.value) return
  event.preventDefault()
  drag.value = { id: panel.id, mode, x: event.clientX, y: event.clientY, original: copy(panels.value), panel: { ...panel }, step: (canvas.value.getBoundingClientRect().width + 12) / 12 }
  event.currentTarget.setPointerCapture(event.pointerId)
}
function move(event) {
  if (!drag.value) return
  const { id, mode, x, y, original, panel, step } = drag.value
  const dx = Math.round((event.clientX - x) / step), dy = Math.round((event.clientY - y) / 60)
  const next = mode === 'move' ? { x: clamp(panel.x + dx, 0, 12 - panel.w), y: clamp(panel.y + dy, 0, 512 - panel.h) }
    : { w: clamp(panel.w + dx, 3, 12 - panel.x), h: clamp(panel.h + dy, 3, Math.min(18, 512 - panel.y)) }
  panels.value = pack(original, id, next)
}
function finish(cancel = false) {
  if (!drag.value) return
  if (cancel) panels.value = drag.value.original
  drag.value = null; changed()
}
function keyMove(event, panel, mode) {
  const vector = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key]
  if (!vector || narrow.value) return
  event.preventDefault()
  const next = mode === 'move' ? { x: clamp(panel.x + vector[0], 0, 12 - panel.w), y: clamp(panel.y + vector[1], 0, 512 - panel.h) }
    : { w: clamp(panel.w + vector[0], 3, 12 - panel.x), h: clamp(panel.h + vector[1], 3, Math.min(18, 512 - panel.y)) }
  panels.value = pack(panels.value, panel.id, next); changed()
}
function resized() { narrow.value = window.matchMedia('(max-width: 1050px)').matches; if (drag.value) finish(true) }
function unload(event) { if (dirty.value) { event.preventDefault(); event.returnValue = '' } }
onMounted(() => { resized(); load(); window.addEventListener('resize', resized); window.addEventListener('beforeunload', unload) })
onActivated(() => { active = true; if (ready.value && !dirty.value) load() })
onDeactivated(() => { active = false; cache(); if (!error.value) save() })
onBeforeUnmount(() => { disposed = true; clearTimeout(timer); cache(); window.removeEventListener('resize', resized); window.removeEventListener('beforeunload', unload) })
defineExpose({ showApp })
</script>

<template>
  <div class="eyebrow">OPERATIONS / PERSONAL WORKSPACE</div>
  <div class="page-heading workspace-heading"><div><h1>Workspace<span>_</span></h1><p>Arrange your tools. Keep the whole operation in view.</p></div><span class="badge">RAM {{ slot.ram_used }} / {{ slot.equipment.memory.ram }} GB</span></div>
  <section class="panel workspace-toolbar">
    <div class="workspace-picker"><label for="workspace-panel">ADD A PANEL</label><select id="workspace-panel" v-model="selected" aria-label="Workspace panel"><option v-for="item in choices" :key="item.product_id" :value="item.product_id">{{ item.name }}{{ panels.some(panel => panel.id === item.id) ? ' / on workspace' : '' }}</option></select><button class="button secondary" :disabled="busy || !ready || loading" @click="addPanel">Add panel</button></div>
    <div class="workspace-actions"><button class="button secondary" :disabled="busy || launching || !ready || loading" @click="launchVisible">Launch visible tools</button><button class="text-link" :disabled="!ready || loading" @click="restore">Restore starter arrangement</button><span class="workspace-save-status" role="status">{{ saveStatus }}</span></div>
    <p>{{ narrow ? 'Panels stack on this screen. Your desktop arrangement is kept.' : 'Drag the grip to move. Drag the lower corner to resize. Focus either handle and use arrow keys to snap to the grid.' }} Removing a panel keeps its process running; Stop frees RAM.</p>
  </section>
  <div v-if="error && !conflict" class="message error" role="alert"><span>{{ error }}</span><button class="button secondary" @click="ready ? save() : load()">Retry layout save</button></div>
  <div v-if="!recovery && dirty" class="info-banner">Browser recovery is unavailable. Keep this tab open until your arrangement is saved.</div>
  <section v-if="conflict" class="panel workspace-conflict" role="alert"><p>{{ error || 'Another window saved a different workspace.' }} Review your panels before choosing.</p><button class="button secondary" @click="useSaved">Reload saved arrangement</button><button class="button primary" :disabled="conflict.identity !== identity" @click="keepLayout">Keep my arrangement</button></section>
  <div v-if="ready" ref="canvas" class="workspace-canvas" :class="{ narrow, arranging: drag }" :style="{ gridTemplateRows: narrow ? undefined : `repeat(${rows}, 48px)` }">
    <section v-for="panel in panels" :key="panel.id" class="workspace-window panel" :data-workspace-window="panel.id" :style="narrow ? {} : { gridColumn: `${panel.x + 1} / span ${panel.w}`, gridRow: `${panel.y + 1} / span ${panel.h}` }" :aria-label="`${title(panel)} panel`">
      <header class="workspace-window-header"><button class="workspace-grip" :aria-label="`Move ${title(panel)}`" :disabled="narrow || loading" @pointerdown="begin($event, panel, 'move')" @pointermove="move" @pointerup="finish()" @pointercancel="finish(true)" @keydown="keyMove($event, panel, 'move')"><GripVertical :size="15" /></button><strong>{{ title(panel) }}</strong><span v-if="process(panel)" class="workspace-process-ram">{{ process(panel).ram }} GB</span><button v-if="process(panel)" class="workspace-control" :aria-label="`Stop ${title(panel)}`" :disabled="busy" @click="close(panel.id, slot.id)"><Square :size="12" /></button><button class="workspace-control" :aria-label="`Remove ${title(panel)} panel`" @click="removePanel(panel.id)"><X :size="14" /></button></header>
      <div class="workspace-window-body" :class="{ 'workspace-console-body': process(panel)?.console, 'workspace-atlas-body': panel.id === 'atlas' && process(panel) }">
        <PasswordBreaker v-if="panel.id === 'cracker' && process(panel)" :slot="slot" :busy="busy" :action="breakerAction" />
        <template v-else-if="process(panel)?.console">
        <ServerLogin v-if="panel.id === 'terminal'" :slot="slot" :busy="busy" @open-cracker="emit('open-cracker')" />
        <TerminalConsole :slot="slot" :application="panel.id" :busy="busy" :send="send" embedded :autofocus="false" />
        </template>
        <NetworkMap v-else-if="panel.id === 'atlas' && process(panel)" map-only :slot="slot" :busy="busy" @save="emit('route', $event)" @directory="(action, id) => emit('directory', action, id)" />
        <BrokerView v-else-if="panel.id === 'broker' && process(panel)" :slot="slot" :busy="busy" :now="now" :offset="offset" :ranks="ranks" @action="(action, job) => emit('contract', action, job)" />
        <ExchangeView v-else-if="panel.id === 'market' && process(panel)" :slot="slot" :busy="busy" @trade="(action, id) => emit('trade', action, id)" />
        <FieldNotes v-else-if="panel.id === 'notes'" :slot-id="slot.id" :username="username" :api="api" />
        <ServerHistory v-else-if="panel.id === 'history'" :slot-id="slot.id" :api="api" :remote-target="slot.remote_target" />
        <BlackMarket v-else-if="panel.id === 'blackmarket' && slot.market_unlocked" :slot="slot" :busy="busy" @trade="(action, id) => emit('trade', action, id)" />
        <BackdoorsView v-else-if="panel.id === 'backdoors' && slot.installed_software.includes('rootkit-epic')" :slot="slot" :busy="busy" @connect="emit('jump', $event)" />
        <div v-else class="workspace-stopped"><Play :size="25" /><h2>{{ title(panel) }}</h2><p>{{ available(panel) ? 'This tool is stopped. Launch it here to begin.' : 'This panel needs software or service access that this runner does not own.' }}</p><button v-if="available(panel) && !service(panel)" class="button primary" :disabled="busy" @click="run(panel)">Launch {{ title(panel) }}</button><p v-if="tileErrors[panel.id]" role="alert">{{ tileErrors[panel.id] }}</p></div>
      </div>
      <button class="workspace-resize" :aria-label="`Resize ${title(panel)}`" :disabled="narrow || loading" @pointerdown="begin($event, panel, 'resize')" @pointermove="move" @pointerup="finish()" @pointercancel="finish(true)" @keydown="keyMove($event, panel, 'resize')"><Maximize2 :size="12" /></button>
    </section>
    <div v-if="!panels.length" class="empty-state workspace-empty">Your workspace is clear. Choose a tool above to add its panel.</div>
  </div>
</template>
