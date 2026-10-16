<script setup>
import { computed, ref, watch, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
const props = defineProps({ slotId: Number, username: String, api: Function })
const draft = ref(''), saved = ref(''), revision = ref(0), identity = ref(''), updated = ref(null)
const loading = ref(true), saving = ref(false), ready = ref(false), error = ref(''), conflict = ref(null), recovery = ref(true), retired = ref(false)
const dirty = computed(() => draft.value !== saved.value)
const status = computed(() => loading.value ? 'Loading notes…' : conflict.value ? 'Conflicting edits — your draft is preserved' : saving.value ? 'Saving…' : error.value ? 'Save failed — draft retained' : dirty.value ? 'Unsaved changes' : 'Saved')
let timer, disposed = false, lastCachedText = null
const path = () => `slots/${props.slotId}/notes/`
const cacheKey = () => `netrunner.notes:${props.username}:${props.slotId}:${identity.value}`
function readCache() {
  // Session storage preserves each tab's draft; local storage is a last-draft fallback.
  for (const name of ['sessionStorage', 'localStorage']) {
    try {
      const raw = window[name].getItem(cacheKey())
      if (raw) { lastCachedText = JSON.parse(raw).text; return JSON.parse(raw) }
    } catch { /* try the other browser store */ }
  }
  return null
}
function cache() {
  if (!ready.value) return
  let available = false
  for (const name of ['sessionStorage', 'localStorage']) {
    try {
      const storage = window[name]
      if (dirty.value) storage.setItem(cacheKey(), JSON.stringify({ text: draft.value, revision: revision.value }))
      else {
        const previous = JSON.parse(storage.getItem(cacheKey()) || 'null')
        if (name === 'sessionStorage' || !previous || previous.text === saved.value || previous.text === lastCachedText) storage.removeItem(cacheKey())
      }
      available = true
    } catch { /* an in-memory draft and unload warning still protect this tab */ }
  }
  lastCachedText = dirty.value ? draft.value : null
  recovery.value = available
}
function schedule() {
  clearTimeout(timer)
  if (ready.value && dirty.value && !conflict.value && !error.value && !retired.value && !disposed) timer = setTimeout(save, 800)
}
async function load() {
  if (saving.value || (ready.value && dirty.value)) return
  loading.value = true; error.value = ''
  try {
    const note = await props.api(path())
    if (disposed) return
    identity.value = note.identity; revision.value = note.revision; saved.value = note.text; updated.value = note.updated_at
    draft.value = note.text; conflict.value = null; retired.value = false
    try {
      const cached = readCache()
      if (cached && typeof cached.text === 'string' && cached.text.length <= 50000 && cached.text !== note.text) {
        draft.value = cached.text
        if (cached.revision !== note.revision) {
          conflict.value = note
          revision.value = Number.isInteger(cached.revision) ? cached.revision : -1
        }
      }
    } catch { recovery.value = false }
    ready.value = true
    cache(); schedule()
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
async function save() {
  clearTimeout(timer)
  if (!ready.value || loading.value || saving.value || !dirty.value || conflict.value || retired.value) return
  const text = draft.value, base = revision.value
  saving.value = true; error.value = ''; cache()
  try {
    const note = await props.api(path(), { text, revision: base, identity: identity.value })
    saved.value = note.text; revision.value = note.revision; updated.value = note.updated_at
    cache()
  } catch (e) {
    error.value = e.message
    if (e.status === 409 && e.data?.note) {
      conflict.value = e.data.note
      retired.value = conflict.value.identity !== identity.value
    }
  } finally { saving.value = false; schedule() }
}
function useSaved() {
  const note = conflict.value
  draft.value = note.text; saved.value = note.text; revision.value = note.revision; updated.value = note.updated_at
  error.value = ''; conflict.value = null; cache()
}
function keepDraft() {
  if (retired.value) return
  saved.value = conflict.value.text; revision.value = conflict.value.revision; updated.value = conflict.value.updated_at
  conflict.value = null; error.value = ''; cache(); save()
}
function beforeUnload(event) { if (dirty.value) { event.preventDefault(); event.returnValue = '' } }
watch(draft, () => { cache(); if (!saving.value && !conflict.value) error.value = ''; schedule() })
onMounted(() => { load(); window.addEventListener('beforeunload', beforeUnload) })
onActivated(() => { if (ready.value && !dirty.value && !saving.value) load() })
onDeactivated(() => { cache(); if (!error.value) save() })
onBeforeUnmount(() => { cache(); disposed = true; clearTimeout(timer); window.removeEventListener('beforeunload', beforeUnload) })
</script>

<template>
  <div class="eyebrow">WORKSPACE / PRIVATE NOTEBOOK</div>
  <div class="page-heading"><div><h1>Field Notes<span>_</span></h1><p>Addresses, routes, aliases, and loose ends. Saved separately for this runner.</p></div><span class="badge">{{ draft.length.toLocaleString() }} / 50,000</span></div>
  <section class="panel field-notes-panel">
    <div class="panel-title"><span>RUNNER NOTEBOOK</span><span role="status" class="notes-status" :class="{ warning: error || conflict }">{{ status }}</span></div>
    <label class="notes-label" for="field-notes">FIELD NOTES</label>
    <textarea id="field-notes" v-model="draft" :disabled="!ready" :readonly="retired" maxlength="50000" spellcheck="false" placeholder="Leave a thread for your future self…" aria-describedby="notes-saving-help"></textarea>
    <div class="notes-toolbar"><small id="notes-saving-help">Autosaves after typing. {{ updated ? `Last saved ${new Date(updated).toLocaleString()}` : 'No saved notes yet.' }}</small><button class="button secondary" :disabled="saving || loading || conflict || !ready || !dirty" @click="save">Save now</button></div>
  </section>
  <div v-if="error && !conflict" class="message error" role="alert"><span>{{ error }}</span><button class="button secondary" @click="ready ? save() : load()">Retry</button></div>
  <div v-if="!recovery && dirty" class="info-banner">Browser draft recovery is unavailable. Keep this tab open until your notes are saved.</div>
  <section v-if="conflict" class="panel notes-conflict" role="alert"><h2>{{ retired ? 'This runner was restarted.' : 'Another window saved newer notes.' }}</h2><p>Your draft remains in the editor. Review the saved version before choosing which text to keep.</p><details><summary>View saved version</summary><pre>{{ conflict.text || '(Empty notes)' }}</pre></details><div class="notes-toolbar"><button class="button secondary" :disabled="retired" @click="useSaved">Use saved version</button><button class="button primary" :disabled="retired" @click="keepDraft">Save my draft</button></div><p v-if="retired">Copy your old draft if you wish to keep it. Open the current runner to edit its new notebook.</p></section>
</template>
