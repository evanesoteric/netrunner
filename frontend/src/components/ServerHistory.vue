<script setup>
import { computed, ref, onMounted } from 'vue'
const props = defineProps({ slotId: Number, api: Function, remoteTarget: String })
const servers = ref([]), address = ref(''), events = ref([]), next = ref(null), busy = ref(false), error = ref('')
const selected = computed(() => servers.value.find(server => server.address === address.value))
let revision = 0
const stamp = value => value ? new Date(value).toLocaleString() : 'Not visited'
async function load(target = address.value, older = false) {
  const current = ++revision
  busy.value = true; error.value = ''
  try {
    const query = target ? `?server=${encodeURIComponent(target)}${older && next.value ? `&before=${next.value}` : ''}` : ''
    const response = await props.api(`slots/${props.slotId}/history/${query}`)
    if (current !== revision) return
    servers.value = response.servers
    address.value = target
    events.value = older ? [...events.value, ...response.events] : response.events
    next.value = response.next_before
    if (!target && servers.value.length) {
      const initial = servers.value.some(server => server.address === props.remoteTarget) ? props.remoteTarget : servers.value[0].address
      await load(initial)
    }
  } catch (e) { if (current === revision) error.value = e.message } finally { if (current === revision) busy.value = false }
}
onMounted(() => load())
</script>

<template>
  <div class="eyebrow">INTELLIGENCE / PERSISTENT WORLD</div><div class="page-heading"><div><h1>Server Histories<span>_</span></h1><p>Your operator journal. Each server remembers this runner's actions.</p></div><button class="button secondary" :disabled="busy" @click="load()">Refresh history</button></div>
  <div v-if="error" class="message error" role="alert">{{ error }}</div>
  <div v-if="busy" role="status" class="micro">READING JOURNAL…</div>
  <p v-if="!busy && !servers.length" class="empty-state">No recorded servers yet. Scan or connect to a target to begin its history.</p>
  <div v-if="servers.length" class="history-layout"><section class="panel history-server-list" aria-label="Recorded servers"><button v-for="server in servers" :key="server.address" :aria-pressed="address === server.address" :disabled="busy" @click="load(server.address)"><strong>{{ server.name }}</strong><code>{{ server.address }}</code><small>{{ server.visits }} VISITS / REV {{ server.revision }}</small></button></section>
    <section v-if="selected" class="panel server-journal"><div class="panel-title"><span>OPERATOR JOURNAL</span><span class="panel-meta">{{ selected.visits }} VISITS</span></div><div class="history-server-heading"><h2>{{ selected.name }}</h2><code>{{ selected.address }}</code><p>Last visit: {{ stamp(selected.last_visit) }}</p><div class="history-badges"><span class="badge">{{ selected.backdoor_installed ? 'WRAITH INSTALLED' : 'NO BACKDOOR' }}</span><span class="badge">{{ selected.remote_log_count }} REMOTE LOG ENTRIES</span></div><p v-if="selected.maintenance_due" class="opportunity-label">Maintenance due {{ stamp(selected.maintenance_due) }}. Live connections postpone it.</p></div>
      <details class="observed-files"><summary>Last observed filesystem and service</summary><template v-if="selected.observed.at"><p>Observed {{ stamp(selected.observed.at) }} / revision {{ selected.observed.revision }} / port {{ selected.observed.port }} / class {{ selected.observed.security }}</p><p v-for="file in selected.observed.files" :key="file.name"><code>{{ file.name }}</code> — {{ !file.present ? 'DELETED' : file.encrypted ? 'ENCRYPTED' : 'READABLE' }}</p></template><p v-else>No successful scan or directory listing recorded.</p><small>This is your last observation. Scan again after maintenance to refresh it.</small></details>
      <p class="journal-help">Erasing remote logs leaves this private journal intact. Maintenance can restore and move archives or rotate service ports.</p>
      <ol class="history-events"><li v-for="entry in events" :key="entry.id" :data-event="entry.kind"><time>{{ stamp(entry.created_at) }}</time><span class="micro">{{ entry.kind.replaceAll('_', ' ').toUpperCase() }}</span><p>{{ entry.summary }}</p></li></ol><button v-if="next" class="button secondary" :disabled="busy" @click="load(address, true)">Load older events</button>
    </section></div>
</template>
