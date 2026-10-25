import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { requestReference } from './requestReference'

// Each editor writes its own durable recovery key, so tabs never overwrite
// another editor's fallback. Session storage chooses this tab's draft first.
export function useMailDraft(key, read, restore, hasContent) {
  const available = ref(true), owner = requestReference(), prefix = `${key}:copy:`
  let ready = false, inherited = null
  function localCopies() {
    const storage = window.localStorage, copies = []
    for (let index = 0; index < storage.length; index++) {
      const storedKey = storage.key(index)
      if (!storedKey?.startsWith(prefix) && storedKey !== key) continue
      try {
        const record = JSON.parse(storage.getItem(storedKey))
        if (record && typeof record.owner === 'string' && record.draft) copies.push({ ...record, key:storedKey })
      } catch { /* skip a malformed recovery copy */ }
    }
    return copies.sort((a,b) => (b.updated_at || 0) - (a.updated_at || 0))
  }
  function persist() {
    if (!ready) return
    const draft = read(), content = hasContent(), record = { owner, draft, updated_at:Date.now() }
    let stored = false
    try {
      if (content) sessionStorage.setItem(key, JSON.stringify(record))
      else sessionStorage.removeItem(key)
      stored = true
    } catch { /* a durable local copy can still recover this draft */ }
    try {
      if (content) {
        localStorage.setItem(prefix + owner, JSON.stringify(record))
        // Move a restored copy only after writing its replacement. If its old
        // editor has changed it, retain that editor's newer text independently.
        if (inherited && inherited.key !== prefix + owner) {
          const previous = JSON.parse(localStorage.getItem(inherited.key) || 'null')
          if (previous && JSON.stringify(previous.draft) === inherited.signature) localStorage.removeItem(inherited.key)
        }
        inherited = null
      } else localStorage.removeItem(prefix + owner)
      stored = true
    } catch { /* keep the tab's session copy and in-memory editor */ }
    available.value = stored
  }
  function prune() {
    try {
      // Bound closed-tab fallbacks per runner; active tabs also retain their
      // independent session copy. Never delete this editor's current record.
      for (const record of localCopies().filter(row => row.owner !== owner).slice(7)) localStorage.removeItem(record.key)
    } catch { /* storage may be disabled or full */ }
  }
  onMounted(() => {
    let candidates = []
    try {
      const cached = JSON.parse(sessionStorage.getItem(key) || 'null')
      if (cached) candidates.push({ ...cached, key:prefix + cached.owner })
    } catch { /* try durable browser copies */ }
    try { candidates.push(...localCopies()) } catch { /* in-memory editing remains available */ }
    for (const cached of candidates) {
      try {
        if (typeof cached.owner === 'string' && restore(cached.draft)) {
          inherited = { key:cached.key, signature:JSON.stringify(cached.draft) }
          break
        }
      } catch { /* malformed caches must not prevent opening Email */ }
    }
    ready = true; persist(); prune()
  })
  watch(read, persist, { deep:true })
  function beforeUnload(event) { if (hasContent() && !available.value) { event.preventDefault(); event.returnValue = '' } }
  onMounted(() => window.addEventListener('beforeunload', beforeUnload))
  onBeforeUnmount(() => { persist(); prune(); window.removeEventListener('beforeunload', beforeUnload) })
  return { draftAvailable:available, persistDraft:persist }
}
